"""
CriticalAuditService - Módulo de Auditoría de Acciones Críticas
Registra todas las acciones críticas del sistema según documento oficial
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from dataclasses import dataclass

from models import CriticalAuditLog

logger = logging.getLogger("critical_audit_service")

class CriticalActions:
    """Constantes para acciones críticas auditables"""
    LOGIN = "login"
    CONFIG_CHANGE = "config_change"
    LINK_GENERATED = "link_generated"
    WEBHOOK_RECEIVED = "webhook_received"
    PAYMENT_APPROVED = "payment_approved"
    SECURITY_ALERT = "security_alert"
    USER_CREATED = "user_created"
    USER_DELETED = "user_deleted"
    INTEGRATION_CHANGE = "integration_change"

@dataclass
class AuditContext:
    """Contexto para auditoría crítica"""
    user_email: str
    ip_address: str
    user_agent: Optional[str] = None
    tenant_id: Optional[str] = None

class CriticalAuditService:
    """
    Servicio de auditoría para acciones críticas del sistema
    Registra quién, qué, cuándo y desde dónde se ejecutan acciones sensibles
    """
    
    def __init__(self, db: Session):
        self.db = db
        logger.info("CriticalAuditService initialized")
    
    def log_critical_action(
        self,
        context: AuditContext,
        action: str,
        entity: Optional[str] = None,
        entity_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None
    ) -> CriticalAuditLog:
        """
        Registra una acción crítica en el sistema
        """
        try:
            audit_log = CriticalAuditLog(
                tenant_id=context.tenant_id,
                user_email=context.user_email,
                action=action,
                entity=entity,
                entity_id=entity_id,
                ip_address=context.ip_address,
                user_agent=context.user_agent,
                details=json.dumps(details, default=str) if details else None,
                old_values=json.dumps(old_values, default=str) if old_values else None,
                new_values=json.dumps(new_values, default=str) if new_values else None
            )
            
            self.db.add(audit_log)
            self.db.commit()
            
            logger.info(f"Critical action logged: {action} by {context.user_email} from {context.ip_address}")
            
            return audit_log
            
        except Exception as e:
            logger.error(f"Error logging critical action: {str(e)}")
            self.db.rollback()
            raise e
    
    def log_login_attempt(
        self,
        context: AuditContext,
        success: bool,
        details: Optional[Dict[str, Any]] = None
    ) -> CriticalAuditLog:
        """
        Registra intento de login (exitoso o fallido)
        """
        login_details = {
            "success": success,
            "timestamp": datetime.utcnow().isoformat(),
            **(details or {})
        }
        
        return self.log_critical_action(
            context=context,
            action=CriticalActions.LOGIN,
            entity="user_session",
            entity_id=context.user_email,
            details=login_details
        )
    
    def log_payment_link_generated(
        self,
        context: AuditContext,
        payment_id: int,
        amount: float,
        customer_email: str,
        mp_preference_id: Optional[str] = None
    ) -> CriticalAuditLog:
        """
        Gancho de Auditoría: Registra generación de link de pago
        """
        details = {
            "payment_id": payment_id,
            "amount": amount,
            "customer_email": customer_email,
            "mp_preference_id": mp_preference_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return self.log_critical_action(
            context=context,
            action=CriticalActions.LINK_GENERATED,
            entity="payment",
            entity_id=str(payment_id),  # Usar ID de negocio, no UUID interno
            details=details
        )
    
    def log_config_change(
        self,
        context: AuditContext,
        config_type: str,
        config_id: str,
        old_values: Dict[str, Any],
        new_values: Dict[str, Any]
    ) -> CriticalAuditLog:
        """
        Gancho de Auditoría: Registra cambios en IntegrationSettings
        """
        details = {
            "config_type": config_type,
            "timestamp": datetime.utcnow().isoformat(),
            "changes_count": len(new_values)
        }
        
        return self.log_critical_action(
            context=context,
            action=CriticalActions.CONFIG_CHANGE,
            entity=config_type,
            entity_id=config_id,
            details=details,
            old_values=old_values,
            new_values=new_values
        )
    
    def log_webhook_received(
        self,
        ip_address: str,
        webhook_type: str,
        payment_id: Optional[str] = None,
        signature_valid: bool = True
    ) -> CriticalAuditLog:
        """
        Registra recepción de webhook (especialmente de MercadoPago)
        """
        context = AuditContext(
            user_email="system_webhook",
            ip_address=ip_address,
            tenant_id="system"
        )
        
        details = {
            "webhook_type": webhook_type,
            "payment_id": payment_id,
            "signature_valid": signature_valid,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return self.log_critical_action(
            context=context,
            action=CriticalActions.WEBHOOK_RECEIVED,
            entity="webhook",
            entity_id=payment_id,
            details=details
        )
    
    def get_audit_trail(
        self,
        limit: int = 100,
        user_email: Optional[str] = None,
        action: Optional[str] = None,
        tenant_id: Optional[str] = None,
        hours_back: int = 24
    ) -> List[CriticalAuditLog]:
        """
        Obtiene el rastro de auditoría con filtros
        """
        try:
            query = self.db.query(CriticalAuditLog)
            
            # Filtros opcionales
            if user_email:
                query = query.filter(CriticalAuditLog.user_email == user_email)
            
            if action:
                query = query.filter(CriticalAuditLog.action == action)
            
            if tenant_id:
                query = query.filter(CriticalAuditLog.tenant_id == tenant_id)
            
            # Filtro de tiempo
            if hours_back > 0:
                from datetime import timedelta
                cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
                query = query.filter(CriticalAuditLog.created_at >= cutoff_time)
            
            # Ordenar por más reciente y limitar
            audit_logs = query.order_by(CriticalAuditLog.created_at.desc()).limit(limit).all()
            
            return audit_logs
            
        except Exception as e:
            logger.error(f"Error getting audit trail: {str(e)}")
            return []
    
    def get_user_activity(self, user_email: str, hours_back: int = 24) -> List[CriticalAuditLog]:
        """
        Obtiene toda la actividad de un usuario específico
        """
        return self.get_audit_trail(
            user_email=user_email,
            hours_back=hours_back,
            limit=50
        )
    
    def get_recent_logins(self, hours_back: int = 24) -> List[CriticalAuditLog]:
        """
        Obtiene los logins recientes del sistema
        """
        return self.get_audit_trail(
            action=CriticalActions.LOGIN,
            hours_back=hours_back,
            limit=50
        )
    
    def get_config_changes(self, hours_back: int = 24) -> List[CriticalAuditLog]:
        """
        Obtiene los cambios de configuración recientes
        """
        return self.get_audit_trail(
            action=CriticalActions.CONFIG_CHANGE,
            hours_back=hours_back,
            limit=50
        )
    
    def get_payment_activity(self, hours_back: int = 24) -> List[CriticalAuditLog]:
        """
        Obtiene la actividad de generación de links de pago
        """
        return self.get_audit_trail(
            action=CriticalActions.LINK_GENERATED,
            hours_back=hours_back,
            limit=100
        )
    
    def get_suspicious_activity(self, hours_back: int = 24) -> List[Dict[str, Any]]:
        """
        Detecta actividad sospechosa en el sistema
        """
        try:
            from datetime import timedelta
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
            
            # Buscar múltiples logins fallidos desde la misma IP
            failed_logins = self.db.query(CriticalAuditLog).filter(
                CriticalAuditLog.action == CriticalActions.LOGIN,
                CriticalAuditLog.created_at >= cutoff_time,
                CriticalAuditLog.details.like('%"success": false%')
            ).all()
            
            # Agrupar por IP
            ip_failures = {}
            for log in failed_logins:
                ip = log.ip_address
                if ip not in ip_failures:
                    ip_failures[ip] = []
                ip_failures[ip].append(log)
            
            # Detectar IPs con múltiples fallos
            suspicious = []
            for ip, failures in ip_failures.items():
                if len(failures) >= 3:  # 3 o más fallos
                    suspicious.append({
                        "type": "multiple_failed_logins",
                        "ip_address": ip,
                        "failure_count": len(failures),
                        "time_range": f"{failures[-1].created_at} - {failures[0].created_at}",
                        "users_attempted": list(set([f.user_email for f in failures]))
                    })
            
            return suspicious
            
        except Exception as e:
            logger.error(f"Error detecting suspicious activity: {str(e)}")
            return []
    
    def get_audit_stats(self, hours_back: int = 24) -> Dict[str, Any]:
        """
        Obtiene estadísticas de auditoría
        """
        try:
            from datetime import timedelta
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
            
            # Contar por acción
            action_counts = {}
            actions = [CriticalActions.LOGIN, CriticalActions.CONFIG_CHANGE, 
                      CriticalActions.LINK_GENERATED, CriticalActions.WEBHOOK_RECEIVED]
            
            for action in actions:
                count = self.db.query(CriticalAuditLog).filter(
                    CriticalAuditLog.action == action,
                    CriticalAuditLog.created_at >= cutoff_time
                ).count()
                action_counts[action] = count
            
            # Usuarios únicos activos
            unique_users = self.db.query(CriticalAuditLog.user_email).filter(
                CriticalAuditLog.created_at >= cutoff_time,
                CriticalAuditLog.user_email != "system_webhook"
            ).distinct().count()
            
            # IPs únicas
            unique_ips = self.db.query(CriticalAuditLog.ip_address).filter(
                CriticalAuditLog.created_at >= cutoff_time
            ).distinct().count()
            
            return {
                "time_range_hours": hours_back,
                "action_counts": action_counts,
                "unique_users": unique_users,
                "unique_ips": unique_ips,
                "total_events": sum(action_counts.values()),
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting audit stats: {str(e)}")
            return {
                "error": str(e),
                "time_range_hours": hours_back,
                "generated_at": datetime.utcnow().isoformat()
            }