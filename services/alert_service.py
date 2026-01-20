"""
AlertService - Sistema de Alertas Inteligente NOC
Implementa notificaciones automáticas basadas en umbrales configurables
Integrado con NotificationService para alertas en tiempo real
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from models import Payment, PaymentStatus, WebhookEvent, MercadoPagoAccount, SecurityAlert, AuditLog
from .metrics_service import MetricsService, AlertLevel

# Importar NotificationService si está disponible
try:
    from .notification_service import NotificationService, NotificationMessage, NotificationPriority, NotificationChannel
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False

logger = logging.getLogger("alert_service")

class AlertType(Enum):
    WEBHOOK_ERROR_RATE = "webhook_error_rate"
    OAUTH_EXPIRATION = "oauth_expiration"
    PAYMENT_FAILURE_RATE = "payment_failure_rate"
    API_RESPONSE_TIME = "api_response_time"
    SECURITY_THREAT = "security_threat"
    SYSTEM_OVERLOAD = "system_overload"
    DATABASE_PERFORMANCE = "database_performance"
    BRUTE_FORCE_DETECTED = "brute_force_detected"

@dataclass
class AlertRule:
    """Regla de alerta configurable"""
    alert_type: AlertType
    level: AlertLevel
    threshold_value: float
    comparison: str  # "gt", "lt", "eq", "gte", "lte"
    check_interval_minutes: int
    cooldown_minutes: int
    enabled: bool = True
    description: str = ""
    
@dataclass
class AlertEvent:
    """Evento de alerta generado"""
    alert_type: AlertType
    level: AlertLevel
    title: str
    message: str
    current_value: float
    threshold_value: float
    timestamp: datetime
    metadata: Dict[str, Any]
    
class AlertNotifier:
    """Manejador de notificaciones de alertas con integración multi-canal"""
    
    def __init__(self, db: Session = None):
        self.db = db
        self.notification_service = None
        
        # Inicializar NotificationService si está disponible
        if NOTIFICATIONS_AVAILABLE and db:
            try:
                self.notification_service = NotificationService(db)
                logger.info("NotificationService initialized for AlertNotifier")
            except Exception as e:
                logger.warning(f"Failed to initialize NotificationService: {str(e)}")
        
        self.handlers: Dict[AlertLevel, List[Callable]] = {
            AlertLevel.INFO: [self._log_info, self._send_notification],
            AlertLevel.WARNING: [self._log_warning, self._console_warning, self._send_notification],
            AlertLevel.CRITICAL: [self._log_critical, self._console_critical, self._emergency_log, self._send_notification]
        }
    
    def notify(self, alert: AlertEvent) -> None:
        """Envía notificación según el nivel de alerta"""
        handlers = self.handlers.get(alert.level, [])
        
        for handler in handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {str(e)}")
    
    def _send_notification(self, alert: AlertEvent) -> None:
        """Envía notificación usando NotificationService"""
        if not self.notification_service:
            return
        
        try:
            # Mapear AlertLevel a NotificationPriority
            priority_map = {
                AlertLevel.INFO: NotificationPriority.LOW,
                AlertLevel.WARNING: NotificationPriority.MEDIUM,
                AlertLevel.CRITICAL: NotificationPriority.CRITICAL
            }
            
            # Mapear AlertType a event_type para notificaciones
            event_type_map = {
                AlertType.WEBHOOK_ERROR_RATE: "webhook_failed",
                AlertType.OAUTH_EXPIRATION: "oauth_expiring",
                AlertType.PAYMENT_FAILURE_RATE: "payment_failed",
                AlertType.API_RESPONSE_TIME: "api_slow",
                AlertType.SECURITY_THREAT: "security_alert",
                AlertType.SYSTEM_OVERLOAD: "system_error",
                AlertType.BRUTE_FORCE_DETECTED: "brute_force",
                AlertType.DATABASE_PERFORMANCE: "system_error"
            }
            
            notification = NotificationMessage(
                title=alert.title,
                message=alert.message,
                priority=priority_map.get(alert.level, NotificationPriority.MEDIUM),
                event_type=event_type_map.get(alert.alert_type, "system_alert"),
                data={
                    "alert_type": alert.alert_type.value,
                    "current_value": alert.current_value,
                    "threshold_value": alert.threshold_value,
                    "timestamp": alert.timestamp.isoformat(),
                    **alert.metadata
                }
            )
            
            # Enviar notificación
            result = self.notification_service.send_notification(notification)
            
            if result.get("success"):
                logger.info(f"Alert notification sent via {len(result.get('channels', []))} channels")
            else:
                logger.warning(f"Alert notification failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Error sending alert notification: {str(e)}")
    
    def _log_info(self, alert: AlertEvent) -> None:
        """Log nivel INFO"""
        logger.info(f"[ALERT-INFO] {alert.title}: {alert.message}")
    
    def _log_warning(self, alert: AlertEvent) -> None:
        """Log nivel WARNING"""
        logger.warning(f"[ALERT-WARNING] {alert.title}: {alert.message}")
    
    def _log_critical(self, alert: AlertEvent) -> None:
        """Log nivel CRITICAL"""
        logger.critical(f"[ALERT-CRITICAL] {alert.title}: {alert.message}")
    
    def _console_warning(self, alert: AlertEvent) -> None:
        """Notificación en consola para WARNING"""
        print(f"\n{'='*80}")
        print(f"[WARNING] WARNING ALERT - {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        print(f"Type: {alert.alert_type.value}")
        print(f"Title: {alert.title}")
        print(f"Message: {alert.message}")
        print(f"Current Value: {alert.current_value}")
        print(f"Threshold: {alert.threshold_value}")
        if alert.metadata:
            print(f"Metadata: {alert.metadata}")
        print(f"{'='*80}\n")
    
    def _console_critical(self, alert: AlertEvent) -> None:
        """Notificación en consola para CRITICAL"""
        print(f"\n{'[CRITICAL]'*10}")
        print(f"[CRITICAL] CRITICAL ALERT - {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')} [CRITICAL]")
        print(f"{'[CRITICAL]'*10}")
        print(f"[FIRE] Type: {alert.alert_type.value}")
        print(f"[FIRE] Title: {alert.title}")
        print(f"[FIRE] Message: {alert.message}")
        print(f"[FIRE] Current Value: {alert.current_value}")
        print(f"[FIRE] Threshold: {alert.threshold_value}")
        if alert.metadata:
            print(f"[FIRE] Metadata: {alert.metadata}")
        print(f"[FIRE] IMMEDIATE ACTION REQUIRED!")
        print(f"{'[CRITICAL]'*10}\n")
    
    def _emergency_log(self, alert: AlertEvent) -> None:
        """Log de emergencia para alertas críticas"""
        emergency_msg = (
            f"EMERGENCY: {alert.title} | "
            f"Value: {alert.current_value} | "
            f"Threshold: {alert.threshold_value} | "
            f"Time: {alert.timestamp.isoformat()}"
        )
        
        # En producción esto iría a un sistema de alertas externo
        # (PagerDuty, Slack, SMS, etc.)
        try:
            os.makedirs("logs", exist_ok=True)
            with open("logs/emergency_alerts.log", "a", encoding='utf-8') as f:
                f.write(f"{emergency_msg}\n")
        except Exception as e:
            print(f"[ERROR] Could not write emergency log: {e}")

class AlertService:
    """
    Servicio de alertas inteligente para monitoreo NOC
    Implementa umbrales configurables y notificaciones automáticas
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.metrics_service = MetricsService(db)
        self.notifier = AlertNotifier(db)  # Pasar db al notifier
        self.alert_history: Dict[str, datetime] = {}
        
        # Verificar modo de desarrollo
        self.is_development = os.getenv("ENVIRONMENT", "development") == "development"
        self.ignore_hash_errors = self.is_development
        
        # Configurar reglas de alerta por defecto
        self.alert_rules = self._get_default_alert_rules()
        
        logger.info(f"AlertService initialized with default rules (Development mode: {self.is_development})")
        if NOTIFICATIONS_AVAILABLE:
            logger.info("NotificationService integration enabled")
        else:
            logger.warning("NotificationService not available - notifications disabled")
    
    def _get_default_alert_rules(self) -> Dict[AlertType, AlertRule]:
        """Reglas de alerta por defecto enterprise"""
        return {
            AlertType.WEBHOOK_ERROR_RATE: AlertRule(
                alert_type=AlertType.WEBHOOK_ERROR_RATE,
                level=AlertLevel.CRITICAL,
                threshold_value=15.0,  # 15% error rate
                comparison="gt",
                check_interval_minutes=5,
                cooldown_minutes=15,
                description="Webhook error rate exceeds 15%"
            ),
            
            AlertType.OAUTH_EXPIRATION: AlertRule(
                alert_type=AlertType.OAUTH_EXPIRATION,
                level=AlertLevel.WARNING,
                threshold_value=7.0,  # 7 days
                comparison="lt",
                check_interval_minutes=60,
                cooldown_minutes=240,  # 4 hours
                description="OAuth credentials expiring within 7 days"
            ),
            
            AlertType.PAYMENT_FAILURE_RATE: AlertRule(
                alert_type=AlertType.PAYMENT_FAILURE_RATE,
                level=AlertLevel.WARNING,
                threshold_value=10.0,  # 10% failure rate
                comparison="gt",
                check_interval_minutes=10,
                cooldown_minutes=30,
                description="Payment failure rate exceeds 10%"
            ),
            
            AlertType.API_RESPONSE_TIME: AlertRule(
                alert_type=AlertType.API_RESPONSE_TIME,
                level=AlertLevel.WARNING,
                threshold_value=5000.0,  # 5 seconds
                comparison="gt",
                check_interval_minutes=5,
                cooldown_minutes=15,
                description="API response time exceeds 5 seconds"
            ),
            
            AlertType.SECURITY_THREAT: AlertRule(
                alert_type=AlertType.SECURITY_THREAT,
                level=AlertLevel.CRITICAL,
                threshold_value=5.0,  # 5 threats in period
                comparison="gte",
                check_interval_minutes=15,
                cooldown_minutes=60,
                description="Multiple security threats detected"
            ),
            
            AlertType.SYSTEM_OVERLOAD: AlertRule(
                alert_type=AlertType.SYSTEM_OVERLOAD,
                level=AlertLevel.WARNING,
                threshold_value=100.0,  # 100 payments per minute
                comparison="gt",
                check_interval_minutes=1,
                cooldown_minutes=5,
                description="System processing overload detected"
            ),
            
            AlertType.BRUTE_FORCE_DETECTED: AlertRule(
                alert_type=AlertType.BRUTE_FORCE_DETECTED,
                level=AlertLevel.CRITICAL,
                threshold_value=3.0,  # 3 failed login attempts
                comparison="gte",
                check_interval_minutes=5,
                cooldown_minutes=10,
                description="Brute force attack detected - multiple failed login attempts"
            )
        }
    
    def check_all_alerts(self) -> List[AlertEvent]:
        """
        Verifica todas las reglas de alerta configuradas
        Retorna lista de alertas generadas
        Maneja errores de hash en modo desarrollo
        """
        alerts_generated = []
        
        for alert_type, rule in self.alert_rules.items():
            if not rule.enabled:
                continue
            
            # Verificar cooldown
            if self._is_in_cooldown(alert_type, rule.cooldown_minutes):
                continue
            
            try:
                alert = self._check_single_alert(rule)
                if alert:
                    # Persistir alerta en base de datos
                    self._persist_alert_to_database(alert)
                    
                    alerts_generated.append(alert)
                    self.notifier.notify(alert)
                    self._update_alert_history(alert_type)
                    
            except Exception as e:
                error_msg = str(e)
                
                # En modo desarrollo, ignorar errores de hash/blockchain
                if self.ignore_hash_errors and any(keyword in error_msg.lower() for keyword in 
                    ['hash', 'blockchain', 'previous_hash', 'current_hash', 'block_number']):
                    logger.warning(f"Ignoring hash error in development mode for {alert_type.value}: {error_msg}")
                    continue
                
                logger.error(f"Error checking alert {alert_type.value}: {error_msg}")
                
                # Crear alerta sobre el error del sistema de alertas
                error_alert = AlertEvent(
                    alert_type=AlertType.SYSTEM_OVERLOAD,  # Usar tipo existente
                    level=AlertLevel.WARNING,
                    title=f"Alert System Error: {alert_type.value}",
                    message=f"Error checking alert rule: {error_msg}",
                    current_value=1,
                    threshold_value=0,
                    timestamp=datetime.utcnow(),
                    metadata={"original_error": error_msg, "alert_type": alert_type.value}
                )
                
                # Persistir error alert también
                self._persist_alert_to_database(error_alert)
                
                alerts_generated.append(error_alert)
                self.notifier.notify(error_alert)
        
        return alerts_generated
    
    def _check_single_alert(self, rule: AlertRule) -> Optional[AlertEvent]:
        """Verifica una regla de alerta específica"""
        
        if rule.alert_type == AlertType.WEBHOOK_ERROR_RATE:
            return self._check_webhook_error_rate(rule)
        
        elif rule.alert_type == AlertType.OAUTH_EXPIRATION:
            return self._check_oauth_expiration(rule)
        
        elif rule.alert_type == AlertType.PAYMENT_FAILURE_RATE:
            return self._check_payment_failure_rate(rule)
        
        elif rule.alert_type == AlertType.API_RESPONSE_TIME:
            return self._check_api_response_time(rule)
        
        elif rule.alert_type == AlertType.SECURITY_THREAT:
            return self._check_security_threats(rule)
        
        elif rule.alert_type == AlertType.SYSTEM_OVERLOAD:
            return self._check_system_overload(rule)
        
        elif rule.alert_type == AlertType.BRUTE_FORCE_DETECTED:
            return self._check_brute_force_attacks(rule)
        
        return None
    
    def _check_webhook_error_rate(self, rule: AlertRule) -> Optional[AlertEvent]:
        """Verifica tasa de error de webhooks"""
        last_hour = datetime.utcnow() - timedelta(hours=1)
        
        total_webhooks = self.db.query(WebhookEvent).filter(
            WebhookEvent.created_at >= last_hour
        ).count()
        
        if total_webhooks == 0:
            return None
        
        failed_webhooks = self.db.query(WebhookEvent).filter(
            and_(
                WebhookEvent.created_at >= last_hour,
                WebhookEvent.status.in_(['error', 'failed'])
            )
        ).count()
        
        error_rate = (failed_webhooks / total_webhooks) * 100
        
        if self._compare_values(error_rate, rule.threshold_value, rule.comparison):
            return AlertEvent(
                alert_type=rule.alert_type,
                level=rule.level,
                title="High Webhook Error Rate Detected",
                message=f"Webhook error rate is {error_rate:.1f}% (threshold: {rule.threshold_value}%)",
                current_value=error_rate,
                threshold_value=rule.threshold_value,
                timestamp=datetime.utcnow(),
                metadata={
                    "total_webhooks": total_webhooks,
                    "failed_webhooks": failed_webhooks,
                    "period": "last_hour"
                }
            )
        
        return None
    
    def _check_oauth_expiration(self, rule: AlertRule) -> Optional[AlertEvent]:
        """Verifica expiración de credenciales OAuth"""
        expiration_threshold = datetime.utcnow() + timedelta(days=rule.threshold_value)
        
        expiring_accounts = self.db.query(MercadoPagoAccount).filter(
            and_(
                MercadoPagoAccount.is_active == True,
                MercadoPagoAccount.expires_at <= expiration_threshold
            )
        ).all()
        
        if expiring_accounts:
            # Encontrar la cuenta que expira más pronto
            earliest_expiry = min(acc.expires_at for acc in expiring_accounts)
            days_until_expiry = (earliest_expiry - datetime.utcnow()).days
            
            return AlertEvent(
                alert_type=rule.alert_type,
                level=rule.level,
                title="OAuth Credentials Expiring Soon",
                message=f"{len(expiring_accounts)} OAuth credentials expiring within {rule.threshold_value} days. Earliest expires in {days_until_expiry} days.",
                current_value=days_until_expiry,
                threshold_value=rule.threshold_value,
                timestamp=datetime.utcnow(),
                metadata={
                    "expiring_accounts": len(expiring_accounts),
                    "earliest_expiry": earliest_expiry.isoformat(),
                    "account_ids": [acc.id for acc in expiring_accounts]
                }
            )
        
        return None
    
    def _check_payment_failure_rate(self, rule: AlertRule) -> Optional[AlertEvent]:
        """Verifica tasa de fallo de pagos"""
        last_24h = datetime.utcnow() - timedelta(hours=24)
        
        total_payments = self.db.query(Payment).filter(
            Payment.created_at >= last_24h
        ).count()
        
        if total_payments == 0:
            return None
        
        failed_payments = self.db.query(Payment).filter(
            and_(
                Payment.created_at >= last_24h,
                Payment.status.in_([PaymentStatus.REJECTED.value, PaymentStatus.CANCELLED.value])
            )
        ).count()
        
        failure_rate = (failed_payments / total_payments) * 100
        
        if self._compare_values(failure_rate, rule.threshold_value, rule.comparison):
            return AlertEvent(
                alert_type=rule.alert_type,
                level=rule.level,
                title="High Payment Failure Rate",
                message=f"Payment failure rate is {failure_rate:.1f}% (threshold: {rule.threshold_value}%)",
                current_value=failure_rate,
                threshold_value=rule.threshold_value,
                timestamp=datetime.utcnow(),
                metadata={
                    "total_payments": total_payments,
                    "failed_payments": failed_payments,
                    "period": "last_24h"
                }
            )
        
        return None
    
    def _check_api_response_time(self, rule: AlertRule) -> Optional[AlertEvent]:
        """Verifica tiempo de respuesta de APIs"""
        # Obtener métricas de salud de servicios
        services_health = self.metrics_service._check_services_health()
        
        for service in services_health:
            if service.response_time_ms and service.response_time_ms > rule.threshold_value:
                return AlertEvent(
                    alert_type=rule.alert_type,
                    level=rule.level,
                    title=f"Slow API Response: {service.name}",
                    message=f"{service.name} response time is {service.response_time_ms}ms (threshold: {rule.threshold_value}ms)",
                    current_value=service.response_time_ms,
                    threshold_value=rule.threshold_value,
                    timestamp=datetime.utcnow(),
                    metadata={
                        "service_name": service.name,
                        "service_status": service.status.value,
                        "error_message": service.error_message
                    }
                )
        
        return None
    
    def _check_security_threats(self, rule: AlertRule) -> Optional[AlertEvent]:
        """Verifica amenazas de seguridad"""
        last_hour = datetime.utcnow() - timedelta(hours=1)
        
        threat_count = self.db.query(SecurityAlert).filter(
            and_(
                SecurityAlert.created_at >= last_hour,
                SecurityAlert.is_resolved == False,
                SecurityAlert.severity.in_(['HIGH', 'CRITICAL'])
            )
        ).count()
        
        if self._compare_values(threat_count, rule.threshold_value, rule.comparison):
            # Obtener tipos de amenazas
            threat_types = self.db.query(SecurityAlert.alert_type).filter(
                and_(
                    SecurityAlert.created_at >= last_hour,
                    SecurityAlert.is_resolved == False,
                    SecurityAlert.severity.in_(['HIGH', 'CRITICAL'])
                )
            ).distinct().all()
            
            return AlertEvent(
                alert_type=rule.alert_type,
                level=rule.level,
                title="Multiple Security Threats Detected",
                message=f"{threat_count} security threats detected in the last hour (threshold: {rule.threshold_value})",
                current_value=threat_count,
                threshold_value=rule.threshold_value,
                timestamp=datetime.utcnow(),
                metadata={
                    "threat_types": [t[0] for t in threat_types],
                    "period": "last_hour"
                }
            )
        
        return None
    
    def _check_system_overload(self, rule: AlertRule) -> Optional[AlertEvent]:
        """Verifica sobrecarga del sistema"""
        last_minute = datetime.utcnow() - timedelta(minutes=1)
        
        payments_per_minute = self.db.query(Payment).filter(
            Payment.created_at >= last_minute
        ).count()
        
        if self._compare_values(payments_per_minute, rule.threshold_value, rule.comparison):
            return AlertEvent(
                alert_type=rule.alert_type,
                level=rule.level,
                title="System Overload Detected",
                message=f"Processing {payments_per_minute} payments per minute (threshold: {rule.threshold_value})",
                current_value=payments_per_minute,
                threshold_value=rule.threshold_value,
                timestamp=datetime.utcnow(),
                metadata={
                    "period": "last_minute",
                    "recommendation": "Consider scaling resources"
                }
            )
        
        return None
    
    def _check_brute_force_attacks(self, rule: AlertRule) -> Optional[AlertEvent]:
        """Verifica ataques de fuerza bruta basado en logs de auditoría"""
        # Buscar en los últimos 15 minutos para detección rápida
        time_window = datetime.utcnow() - timedelta(minutes=15)
        
        # Contar eventos de CUSTOM_FAILED_LOGIN en los logs de auditoría
        # Buscar tanto 'CUSTOM_FAILED_LOGIN' como 'CUSTOM_CUSTOM_FAILED_LOGIN' por el prefijo automático
        failed_login_count = self.db.query(AuditLog).filter(
            and_(
                AuditLog.timestamp >= time_window,
                or_(
                    AuditLog.action == 'CUSTOM_FAILED_LOGIN',
                    AuditLog.action == 'CUSTOM_CUSTOM_FAILED_LOGIN',
                    AuditLog.action.like('%FAILED_LOGIN%')
                )
            )
        ).count()
        
        if self._compare_values(failed_login_count, rule.threshold_value, rule.comparison):
            # Obtener detalles de los intentos fallidos
            failed_attempts = self.db.query(AuditLog).filter(
                and_(
                    AuditLog.timestamp >= time_window,
                    or_(
                        AuditLog.action == 'CUSTOM_FAILED_LOGIN',
                        AuditLog.action == 'CUSTOM_CUSTOM_FAILED_LOGIN',
                        AuditLog.action.like('%FAILED_LOGIN%')
                    )
                )
            ).order_by(AuditLog.timestamp.desc()).limit(10).all()
            
            # Extraer IPs únicas para análisis
            unique_ips = set()
            for attempt in failed_attempts:
                if attempt.ip_address:
                    unique_ips.add(attempt.ip_address)
            
            return AlertEvent(
                alert_type=rule.alert_type,
                level=rule.level,
                title="[CRITICAL] BRUTE FORCE ATTACK DETECTED",
                message=f"CRITICAL: {failed_login_count} failed login attempts detected in 15 minutes (threshold: {rule.threshold_value}). Possible brute force attack in progress!",
                current_value=failed_login_count,
                threshold_value=rule.threshold_value,
                timestamp=datetime.utcnow(),
                metadata={
                    "failed_attempts": failed_login_count,
                    "time_window": "15_minutes",
                    "unique_ips": list(unique_ips),
                    "total_unique_ips": len(unique_ips),
                    "latest_attempts": [
                        {
                            "timestamp": attempt.timestamp.isoformat(),
                            "ip_address": attempt.ip_address,
                            "performed_by": attempt.performed_by,
                            "description": attempt.description,
                            "action": attempt.action
                        }
                        for attempt in failed_attempts[:5]  # Últimos 5 intentos
                    ],
                    "recommendation": "IMMEDIATE ACTION: Block suspicious IPs, review security logs, enable rate limiting"
                }
            )
        
        return None
    
    def _persist_alert_to_database(self, alert: AlertEvent) -> None:
        """Persiste la alerta en la base de datos para consulta del dashboard"""
        try:
            # Mapear AlertLevel a string
            severity_map = {
                AlertLevel.INFO: "LOW",
                AlertLevel.WARNING: "MEDIUM", 
                AlertLevel.CRITICAL: "CRITICAL"
            }
            
            # Crear registro en SecurityAlert
            security_alert = SecurityAlert(
                alert_type=alert.alert_type.value,
                severity=severity_map.get(alert.level, "MEDIUM"),
                title=alert.title,
                description=alert.message,
                expected_value=str(alert.threshold_value),
                actual_value=str(alert.current_value),
                source_ip=alert.metadata.get("source_ip") if alert.metadata else None,
                is_resolved=False  # Nueva alerta, no resuelta
            )
            
            self.db.add(security_alert)
            self.db.commit()
            
            logger.info(f"Alert persisted to database: {alert.alert_type.value} - {alert.title}")
            
        except Exception as e:
            logger.error(f"Failed to persist alert to database: {str(e)}")
            # No fallar el proceso de alertas por error de persistencia
            try:
                self.db.rollback()
            except:
                pass
    
    def _compare_values(self, current: float, threshold: float, comparison: str) -> bool:
        """Compara valores según el operador especificado"""
        if comparison == "gt":
            return current > threshold
        elif comparison == "lt":
            return current < threshold
        elif comparison == "gte":
            return current >= threshold
        elif comparison == "lte":
            return current <= threshold
        elif comparison == "eq":
            return current == threshold
        else:
            return False
    
    def _is_in_cooldown(self, alert_type: AlertType, cooldown_minutes: int) -> bool:
        """Verifica si una alerta está en período de cooldown"""
        if alert_type.value not in self.alert_history:
            return False
        
        last_alert_time = self.alert_history[alert_type.value]
        cooldown_period = timedelta(minutes=cooldown_minutes)
        
        return datetime.utcnow() - last_alert_time < cooldown_period
    
    def _update_alert_history(self, alert_type: AlertType) -> None:
        """Actualiza historial de alertas"""
        self.alert_history[alert_type.value] = datetime.utcnow()
    
    def add_custom_rule(self, rule: AlertRule) -> None:
        """Agrega una regla de alerta personalizada"""
        self.alert_rules[rule.alert_type] = rule
        logger.info(f"Added custom alert rule: {rule.alert_type.value}")
    
    def disable_rule(self, alert_type: AlertType) -> None:
        """Desactiva una regla de alerta"""
        if alert_type in self.alert_rules:
            self.alert_rules[alert_type].enabled = False
            logger.info(f"Disabled alert rule: {alert_type.value}")
    
    def enable_rule(self, alert_type: AlertType) -> None:
        """Activa una regla de alerta"""
        if alert_type in self.alert_rules:
            self.alert_rules[alert_type].enabled = True
            logger.info(f"Enabled alert rule: {alert_type.value}")
    
    def get_alert_status(self) -> Dict[str, Any]:
        """Obtiene estado actual del sistema de alertas"""
        # Obtener últimas activaciones desde la base de datos
        last_triggered_data = {}
        
        try:
            for alert_type in self.alert_rules.keys():
                # Buscar la última alerta de este tipo en la base de datos
                last_alert = self.db.query(SecurityAlert).filter(
                    SecurityAlert.alert_type == alert_type.value
                ).order_by(SecurityAlert.created_at.desc()).first()
                
                if last_alert:
                    last_triggered_data[alert_type.value] = last_alert.created_at.isoformat()
                else:
                    last_triggered_data[alert_type.value] = None
        except Exception as e:
            logger.error(f"Error getting last triggered data: {str(e)}")
            # Fallback a historial en memoria
            last_triggered_data = {
                alert_type.value: self.alert_history.get(alert_type.value).isoformat() 
                if self.alert_history.get(alert_type.value) else None
                for alert_type in self.alert_rules.keys()
            }
        
        return {
            "total_rules": len(self.alert_rules),
            "enabled_rules": sum(1 for rule in self.alert_rules.values() if rule.enabled),
            "disabled_rules": sum(1 for rule in self.alert_rules.values() if not rule.enabled),
            "rules": {
                rule_type.value: {
                    "enabled": rule.enabled,
                    "level": rule.level.value,
                    "threshold": rule.threshold_value,
                    "last_triggered": last_triggered_data.get(rule_type.value)
                }
                for rule_type, rule in self.alert_rules.items()
            }
        }