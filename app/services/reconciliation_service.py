"""
ReconciliationService - Servicio de Reconciliación Diaria Multi-tenant
Sincroniza pagos pendientes con MercadoPago API y detecta discrepancias
"""
import os
import time
import json
import requests
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from models import (
    Payment, PaymentStatus, AuditLog, AuditAction, SecurityAlert, 
    MercadoPagoAccount, ClientAccount
)

logger = logging.getLogger("reconciliation_service")

@dataclass
class ReconciliationConfig:
    """Configuración para el proceso de reconciliación"""
    hours_back: int = 24
    max_retries: int = 3
    retry_delay_seconds: int = 5
    batch_size: int = 50
    enable_auto_correction: bool = True
    dry_run: bool = False
    include_pending_payments: bool = True
    ghl_tag_prefix: str = "MP_PAGADO"
    report_formats: List[str] = None
    notification_webhooks: List[str] = None
    
    def __post_init__(self):
        if self.report_formats is None:
            self.report_formats = ["json", "csv"]
        if self.notification_webhooks is None:
            self.notification_webhooks = []

@dataclass
class PaymentDiscrepancy:
    """Representa una discrepancia encontrada durante la reconciliación"""
    payment_id: int
    internal_uuid: str
    mp_payment_id: Optional[str]
    client_id: Optional[str]
    discrepancy_type: str
    expected_status: str
    actual_status: str
    expected_amount: Optional[Decimal]
    actual_amount: Optional[Decimal]
    description: str
    severity: str
    auto_correctable: bool
    correction_applied: bool = False
    error_message: Optional[str] = None

@dataclass
class ReconciliationResult:
    """Resultado del proceso de reconciliación"""
    execution_id: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: float
    status: str  # "success", "warning", "error", "critical"
    total_payments_checked: int
    discrepancies_found: int
    corrections_applied: int
    ghl_updates_attempted: int
    ghl_updates_successful: int
    discrepancies: List[PaymentDiscrepancy]
    summary: Dict[str, Any]
    reports_generated: List[str]
    error_message: Optional[str] = None

class ReconciliationService:
    """
    Servicio enterprise para reconciliación diaria de pagos
    Implementa Service Layer Pattern con soporte multi-tenant
    """
    
    def __init__(self, db: Session, config: ReconciliationConfig = None):
        self.db = db
        self.config = config or ReconciliationConfig()
        self.execution_id = f"recon_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{int(time.time())}"
        self.mp_access_token = os.getenv("MP_ACCESS_TOKEN")
        
        logger.info(f"ReconciliationService initialized - Execution ID: {self.execution_id}")
    
    def execute_reconciliation(self) -> ReconciliationResult:
        """
        Ejecuta el proceso completo de reconciliación diaria
        """
        start_time = time.time()
        started_at = datetime.utcnow()
        
        logger.info(f"🔄 Iniciando reconciliación diaria - ID: {self.execution_id}")
        
        try:
            # 1. Obtener pagos pendientes
            pending_payments = self._get_pending_payments()
            logger.info(f"📊 Encontrados {len(pending_payments)} pagos pendientes para reconciliar")
            
            if not pending_payments:
                return ReconciliationResult(
                    execution_id=self.execution_id,
                    started_at=started_at,
                    completed_at=datetime.utcnow(),
                    duration_seconds=time.time() - start_time,
                    status="success",
                    total_payments_checked=0,
                    discrepancies_found=0,
                    corrections_applied=0,
                    ghl_updates_attempted=0,
                    ghl_updates_successful=0,
                    discrepancies=[],
                    summary={"message": "No hay pagos pendientes para reconciliar"},
                    reports_generated=[]
                )
            
            # 2. Procesar pagos en lotes
            all_discrepancies = []
            total_corrections = 0
            ghl_updates_attempted = 0
            ghl_updates_successful = 0
            
            for i in range(0, len(pending_payments), self.config.batch_size):
                batch = pending_payments[i:i + self.config.batch_size]
                logger.info(f"🔍 Procesando lote {i//self.config.batch_size + 1} ({len(batch)} pagos)")
                
                batch_result = self._process_payment_batch(batch)
                all_discrepancies.extend(batch_result["discrepancies"])
                total_corrections += batch_result["corrections_applied"]
                ghl_updates_attempted += batch_result["ghl_updates_attempted"]
                ghl_updates_successful += batch_result["ghl_updates_successful"]
                
                # Pausa entre lotes para no sobrecargar APIs
                if i + self.config.batch_size < len(pending_payments):
                    time.sleep(1)
            
            # 3. Generar reportes
            reports_generated = []
            if not self.config.dry_run:
                reports_generated = self._generate_reports(all_discrepancies)
            
            # 4. Determinar estado final
            status = self._determine_final_status(all_discrepancies, total_corrections)
            
            # 5. Crear resultado final
            result = ReconciliationResult(
                execution_id=self.execution_id,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                duration_seconds=time.time() - start_time,
                status=status,
                total_payments_checked=len(pending_payments),
                discrepancies_found=len(all_discrepancies),
                corrections_applied=total_corrections,
                ghl_updates_attempted=ghl_updates_attempted,
                ghl_updates_successful=ghl_updates_successful,
                discrepancies=all_discrepancies,
                summary=self._generate_summary(all_discrepancies, total_corrections),
                reports_generated=reports_generated
            )
            
            # 6. Log de auditoría
            self._log_reconciliation_result(result)
            
            logger.info(f"✅ Reconciliación completada - Estado: {status}, Discrepancias: {len(all_discrepancies)}, Correcciones: {total_corrections}")
            
            return result
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"❌ Error crítico en reconciliación: {error_message}")
            
            # Crear alerta crítica
            self._create_critical_alert(error_message)
            
            return ReconciliationResult(
                execution_id=self.execution_id,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                duration_seconds=time.time() - start_time,
                status="critical",
                total_payments_checked=0,
                discrepancies_found=0,
                corrections_applied=0,
                ghl_updates_attempted=0,
                ghl_updates_successful=0,
                discrepancies=[],
                summary={"error": error_message},
                reports_generated=[],
                error_message=error_message
            )
    
    def _get_pending_payments(self) -> List[Payment]:
        """
        Obtiene pagos pendientes de las últimas N horas
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=self.config.hours_back)
        
        query = self.db.query(Payment).filter(
            and_(
                Payment.created_at >= cutoff_time,
                or_(
                    Payment.status == PaymentStatus.PENDING.value,
                    and_(
                        Payment.status == PaymentStatus.APPROVED.value,
                        Payment.is_processed == False  # Aprobados pero no procesados en GHL
                    )
                )
            )
        ).order_by(Payment.created_at.desc())
        
        return query.all()
    
    def _process_payment_batch(self, payments: List[Payment]) -> Dict[str, Any]:
        """
        Procesa un lote de pagos para reconciliación
        """
        discrepancies = []
        corrections_applied = 0
        ghl_updates_attempted = 0
        ghl_updates_successful = 0
        
        for payment in payments:
            try:
                # Verificar estado en MercadoPago
                mp_status = self._get_mp_payment_status(payment)
                
                if mp_status is None:
                    # No se pudo obtener estado de MP
                    discrepancy = PaymentDiscrepancy(
                        payment_id=payment.id,
                        internal_uuid=payment.internal_uuid,
                        mp_payment_id=payment.mp_payment_id,
                        client_id=self._get_payment_client_id(payment),
                        discrepancy_type="MP_API_ERROR",
                        expected_status="accessible",
                        actual_status="inaccessible",
                        expected_amount=payment.expected_amount,
                        actual_amount=None,
                        description=f"No se pudo consultar estado en MercadoPago API",
                        severity="HIGH",
                        auto_correctable=False
                    )
                    discrepancies.append(discrepancy)
                    continue
                
                # Comparar estados
                discrepancy = self._compare_payment_status(payment, mp_status)
                
                if discrepancy:
                    discrepancies.append(discrepancy)
                    
                    # Intentar corrección automática si está habilitada
                    if (self.config.enable_auto_correction and 
                        discrepancy.auto_correctable and 
                        not self.config.dry_run):
                        
                        correction_success = self._apply_automatic_correction(payment, mp_status, discrepancy)
                        
                        if correction_success:
                            discrepancy.correction_applied = True
                            corrections_applied += 1
                            
                            # Si el pago se aprobó, intentar actualizar GHL
                            if mp_status.get("status") == "approved":
                                ghl_updates_attempted += 1
                                ghl_success = self._update_ghl_for_payment(payment)
                                if ghl_success:
                                    ghl_updates_successful += 1
                
            except Exception as e:
                logger.error(f"Error procesando payment {payment.id}: {str(e)}")
                
                error_discrepancy = PaymentDiscrepancy(
                    payment_id=payment.id,
                    internal_uuid=payment.internal_uuid,
                    mp_payment_id=payment.mp_payment_id,
                    client_id=self._get_payment_client_id(payment),
                    discrepancy_type="PROCESSING_ERROR",
                    expected_status="processable",
                    actual_status="error",
                    expected_amount=payment.expected_amount,
                    actual_amount=None,
                    description=f"Error procesando pago: {str(e)}",
                    severity="HIGH",
                    auto_correctable=False,
                    error_message=str(e)
                )
                discrepancies.append(error_discrepancy)
        
        return {
            "discrepancies": discrepancies,
            "corrections_applied": corrections_applied,
            "ghl_updates_attempted": ghl_updates_attempted,
            "ghl_updates_successful": ghl_updates_successful
        }
    
    def _get_mp_payment_status(self, payment: Payment) -> Optional[Dict[str, Any]]:
        """
        Consulta el estado real del pago en MercadoPago API
        """
        if not payment.mp_payment_id:
            logger.warning(f"Payment {payment.id} no tiene mp_payment_id")
            return None
        
        if not self.mp_access_token:
            logger.warning("No hay MP_ACCESS_TOKEN configurado")
            return None
        
        try:
            headers = {"Authorization": f"Bearer {self.mp_access_token}"}
            
            # Intentar con reintentos
            for attempt in range(self.config.max_retries):
                try:
                    response = requests.get(
                        f"https://api.mercadopago.com/v1/payments/{payment.mp_payment_id}",
                        headers=headers,
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        return response.json()
                    elif response.status_code == 404:
                        logger.warning(f"Payment {payment.mp_payment_id} no encontrado en MP")
                        return {"status": "not_found", "error": "Payment not found in MercadoPago"}
                    else:
                        logger.warning(f"MP API error {response.status_code} para payment {payment.mp_payment_id}")
                        
                        if attempt < self.config.max_retries - 1:
                            time.sleep(self.config.retry_delay_seconds)
                            continue
                        else:
                            return {"status": "api_error", "error": f"HTTP {response.status_code}"}
                
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Network error consultando MP (intento {attempt + 1}): {str(e)}")
                    
                    if attempt < self.config.max_retries - 1:
                        time.sleep(self.config.retry_delay_seconds)
                        continue
                    else:
                        return {"status": "network_error", "error": str(e)}
            
            return None
            
        except Exception as e:
            logger.error(f"Error crítico consultando MP para payment {payment.id}: {str(e)}")
            return None
    
    def _compare_payment_status(self, payment: Payment, mp_status: Dict[str, Any]) -> Optional[PaymentDiscrepancy]:
        """
        Compara el estado interno con el estado en MercadoPago
        """
        mp_payment_status = mp_status.get("status")
        internal_status = payment.status
        
        # Casos de discrepancia
        discrepancy = None
        
        # 1. Pago aprobado en MP pero pendiente internamente
        if mp_payment_status == "approved" and internal_status == PaymentStatus.PENDING.value:
            discrepancy = PaymentDiscrepancy(
                payment_id=payment.id,
                internal_uuid=payment.internal_uuid,
                mp_payment_id=payment.mp_payment_id,
                client_id=self._get_payment_client_id(payment),
                discrepancy_type="STATUS_MISMATCH_APPROVED",
                expected_status=PaymentStatus.PENDING.value,
                actual_status="approved",
                expected_amount=payment.expected_amount,
                actual_amount=Decimal(str(mp_status.get("transaction_amount", 0))),
                description=f"Pago aprobado en MP pero pendiente internamente",
                severity="MEDIUM",
                auto_correctable=True
            )
        
        # 2. Pago rechazado en MP pero pendiente internamente
        elif mp_payment_status in ["rejected", "cancelled"] and internal_status == PaymentStatus.PENDING.value:
            discrepancy = PaymentDiscrepancy(
                payment_id=payment.id,
                internal_uuid=payment.internal_uuid,
                mp_payment_id=payment.mp_payment_id,
                client_id=self._get_payment_client_id(payment),
                discrepancy_type="STATUS_MISMATCH_REJECTED",
                expected_status=PaymentStatus.PENDING.value,
                actual_status=mp_payment_status,
                expected_amount=payment.expected_amount,
                actual_amount=Decimal(str(mp_status.get("transaction_amount", 0))),
                description=f"Pago {mp_payment_status} en MP pero pendiente internamente",
                severity="LOW",
                auto_correctable=True
            )
        
        # 3. Discrepancia de montos
        elif mp_payment_status == "approved":
            mp_amount = Decimal(str(mp_status.get("transaction_amount", 0)))
            if abs(payment.expected_amount - mp_amount) > Decimal('0.01'):
                discrepancy = PaymentDiscrepancy(
                    payment_id=payment.id,
                    internal_uuid=payment.internal_uuid,
                    mp_payment_id=payment.mp_payment_id,
                    client_id=self._get_payment_client_id(payment),
                    discrepancy_type="AMOUNT_MISMATCH",
                    expected_status=internal_status,
                    actual_status=mp_payment_status,
                    expected_amount=payment.expected_amount,
                    actual_amount=mp_amount,
                    description=f"Monto esperado {payment.expected_amount} vs pagado {mp_amount}",
                    severity="HIGH",
                    auto_correctable=False
                )
        
        # 4. Pago aprobado pero no procesado en GHL
        elif (mp_payment_status == "approved" and 
              internal_status == PaymentStatus.APPROVED.value and 
              not payment.is_processed):
            
            discrepancy = PaymentDiscrepancy(
                payment_id=payment.id,
                internal_uuid=payment.internal_uuid,
                mp_payment_id=payment.mp_payment_id,
                client_id=self._get_payment_client_id(payment),
                discrepancy_type="GHL_NOT_UPDATED",
                expected_status="processed_in_ghl",
                actual_status="not_processed_in_ghl",
                expected_amount=payment.expected_amount,
                actual_amount=payment.paid_amount,
                description=f"Pago aprobado pero no actualizado en GoHighLevel",
                severity="CRITICAL",
                auto_correctable=True
            )
        
        return discrepancy
    
    def _apply_automatic_correction(self, payment: Payment, mp_status: Dict[str, Any], discrepancy: PaymentDiscrepancy) -> bool:
        """
        Aplica corrección automática basada en el tipo de discrepancia
        """
        try:
            if discrepancy.discrepancy_type == "STATUS_MISMATCH_APPROVED":
                # Actualizar estado a aprobado
                payment.status = PaymentStatus.APPROVED.value
                payment.paid_amount = Decimal(str(mp_status.get("transaction_amount", 0)))
                payment.mp_payment_method = mp_status.get("payment_method_id")
                payment.mp_status_detail = mp_status.get("status_detail")
                payment.processed_at = datetime.utcnow()
                
                self.db.commit()
                
                logger.info(f"✅ Corrección aplicada: Payment {payment.id} actualizado a 'approved'")
                return True
            
            elif discrepancy.discrepancy_type == "STATUS_MISMATCH_REJECTED":
                # Actualizar estado a rechazado
                payment.status = PaymentStatus.REJECTED.value
                payment.mp_status_detail = mp_status.get("status_detail")
                
                self.db.commit()
                
                logger.info(f"✅ Corrección aplicada: Payment {payment.id} actualizado a 'rejected'")
                return True
            
            elif discrepancy.discrepancy_type == "GHL_NOT_UPDATED":
                # Marcar para actualización en GHL (se hará después)
                logger.info(f"📝 Payment {payment.id} marcado para actualización GHL")
                return True
            
            else:
                logger.warning(f"Tipo de discrepancia no auto-corregible: {discrepancy.discrepancy_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error aplicando corrección automática para payment {payment.id}: {str(e)}")
            self.db.rollback()
            return False
    
    def _update_ghl_for_payment(self, payment: Payment) -> bool:
        """
        Actualiza GoHighLevel para un pago específico usando el sistema multi-tenant
        """
        try:
            # Importar WebhookService para usar su método de actualización GHL
            from main import WebhookService
            
            success = WebhookService._update_ghl_contact(payment)
            
            if success:
                payment.is_processed = True
                self.db.commit()
                logger.info(f"✅ GHL actualizado exitosamente para payment {payment.id}")
            else:
                logger.warning(f"⚠️ No se pudo actualizar GHL para payment {payment.id}")
                
                # Crear alerta crítica
                from main import SecurityManager
                SecurityManager.create_security_alert(
                    db=self.db,
                    alert_type="RECONCILIATION_GHL_FAILED",
                    title="Fallo en actualización GHL durante reconciliación",
                    description=f"No se pudo actualizar GHL para payment {payment.id} durante reconciliación {self.execution_id}",
                    payment_id=payment.id,
                    severity="CRITICAL"
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Error actualizando GHL para payment {payment.id}: {str(e)}")
            return False
    
    def _get_payment_client_id(self, payment: Payment) -> Optional[str]:
        """
        Obtiene el client_id asociado a un pago
        """
        try:
            if payment.client_account_id:
                client_account = self.db.query(ClientAccount).filter(
                    ClientAccount.id == payment.client_account_id
                ).first()
                return client_account.client_id if client_account else None
            
            elif payment.mp_account_id:
                mp_account = self.db.query(MercadoPagoAccount).filter(
                    MercadoPagoAccount.id == payment.mp_account_id
                ).first()
                return mp_account.client_id if mp_account else None
            
            elif payment.created_by and "client_dashboard_" in payment.created_by:
                return payment.created_by.replace("client_dashboard_", "")
            
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo client_id para payment {payment.id}: {str(e)}")
            return None
    
    def _determine_final_status(self, discrepancies: List[PaymentDiscrepancy], corrections_applied: int) -> str:
        """
        Determina el estado final de la reconciliación
        """
        critical_discrepancies = [d for d in discrepancies if d.severity == "CRITICAL"]
        high_discrepancies = [d for d in discrepancies if d.severity == "HIGH"]
        
        if critical_discrepancies:
            return "critical"
        elif high_discrepancies:
            return "error"
        elif discrepancies:
            return "warning"
        else:
            return "success"
    
    def _generate_summary(self, discrepancies: List[PaymentDiscrepancy], corrections_applied: int) -> Dict[str, Any]:
        """
        Genera resumen de la reconciliación
        """
        discrepancy_types = {}
        severity_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        
        for discrepancy in discrepancies:
            # Contar por tipo
            if discrepancy.discrepancy_type not in discrepancy_types:
                discrepancy_types[discrepancy.discrepancy_type] = 0
            discrepancy_types[discrepancy.discrepancy_type] += 1
            
            # Contar por severidad
            severity_counts[discrepancy.severity] += 1
        
        return {
            "total_discrepancies": len(discrepancies),
            "corrections_applied": corrections_applied,
            "discrepancy_types": discrepancy_types,
            "severity_breakdown": severity_counts,
            "auto_correction_rate": round((corrections_applied / len(discrepancies) * 100) if discrepancies else 0, 2)
        }
    
    def _generate_reports(self, discrepancies: List[PaymentDiscrepancy]) -> List[str]:
        """
        Genera reportes de reconciliación en múltiples formatos
        """
        reports_generated = []
        
        # Crear directorio de reportes si no existe
        os.makedirs("reports", exist_ok=True)
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        try:
            # Reporte JSON
            if "json" in self.config.report_formats:
                json_filename = f"reports/reconciliation_{timestamp}_{self.execution_id}.json"
                
                report_data = {
                    "execution_id": self.execution_id,
                    "generated_at": datetime.utcnow().isoformat(),
                    "config": asdict(self.config),
                    "discrepancies": [asdict(d) for d in discrepancies],
                    "summary": self._generate_summary(discrepancies, sum(1 for d in discrepancies if d.correction_applied))
                }
                
                with open(json_filename, 'w', encoding='utf-8') as f:
                    json.dump(report_data, f, indent=2, default=str, ensure_ascii=False)
                
                reports_generated.append(json_filename)
                logger.info(f"📄 Reporte JSON generado: {json_filename}")
            
            # Reporte CSV
            if "csv" in self.config.report_formats:
                csv_filename = f"reports/reconciliation_{timestamp}_{self.execution_id}.csv"
                
                import csv
                with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    
                    # Headers
                    writer.writerow([
                        "payment_id", "internal_uuid", "mp_payment_id", "client_id",
                        "discrepancy_type", "expected_status", "actual_status",
                        "expected_amount", "actual_amount", "description", "severity",
                        "auto_correctable", "correction_applied", "error_message"
                    ])
                    
                    # Data
                    for d in discrepancies:
                        writer.writerow([
                            d.payment_id, d.internal_uuid, d.mp_payment_id, d.client_id,
                            d.discrepancy_type, d.expected_status, d.actual_status,
                            d.expected_amount, d.actual_amount, d.description, d.severity,
                            d.auto_correctable, d.correction_applied, d.error_message
                        ])
                
                reports_generated.append(csv_filename)
                logger.info(f"📊 Reporte CSV generado: {csv_filename}")
        
        except Exception as e:
            logger.error(f"Error generando reportes: {str(e)}")
        
        return reports_generated
    
    def _log_reconciliation_result(self, result: ReconciliationResult):
        """
        Registra el resultado de la reconciliación en audit logs
        """
        try:
            from main import AuditLogger
            
            AuditLogger.log_action(
                db=self.db,
                action=AuditAction.WEBHOOK_PROCESSED,  # Usar acción existente
                description=f"Daily reconciliation completed - Status: {result.status}",
                performed_by="ReconciliationService",
                request_data={
                    "execution_id": result.execution_id,
                    "config": asdict(self.config)
                },
                response_data={
                    "status": result.status,
                    "total_payments_checked": result.total_payments_checked,
                    "discrepancies_found": result.discrepancies_found,
                    "corrections_applied": result.corrections_applied,
                    "ghl_updates_attempted": result.ghl_updates_attempted,
                    "ghl_updates_successful": result.ghl_updates_successful,
                    "duration_seconds": result.duration_seconds,
                    "reports_generated": result.reports_generated
                },
                error_message=result.error_message,
                correlation_id=result.execution_id
            )
            
        except Exception as e:
            logger.error(f"Error logging reconciliation result: {str(e)}")
    
    def _create_critical_alert(self, error_message: str):
        """
        Crea alerta crítica para errores en reconciliación
        """
        try:
            from main import SecurityManager
            
            SecurityManager.create_security_alert(
                db=self.db,
                alert_type="RECONCILIATION_CRITICAL_ERROR",
                title="Error crítico en reconciliación diaria",
                description=f"La reconciliación {self.execution_id} falló con error crítico: {error_message}",
                severity="CRITICAL"
            )
            
        except Exception as e:
            logger.error(f"Error creando alerta crítica: {str(e)}")