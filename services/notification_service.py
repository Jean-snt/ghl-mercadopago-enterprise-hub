"""
NotificationService - Sistema de Notificaciones en Tiempo Real
Envía alertas por Slack, Email y Webhooks cuando ocurren eventos críticos
"""
import os
import json
import requests
import smtplib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from sqlalchemy.orm import Session
from dataclasses import dataclass
from enum import Enum

from models import SecurityAlert, AuditLog, Payment

logger = logging.getLogger("notification_service")

class NotificationChannel(Enum):
    SLACK = "slack"
    EMAIL = "email"
    WEBHOOK = "webhook"
    SMS = "sms"

class NotificationPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class NotificationConfig:
    """Configuración de notificaciones"""
    # Slack
    slack_webhook_url: Optional[str] = None
    slack_channel: str = "#alerts"
    slack_username: str = "MercadoPago-Bot"
    
    # Email
    smtp_server: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    from_email: Optional[str] = None
    to_emails: List[str] = None
    
    # Webhooks
    webhook_urls: List[str] = None
    
    # Configuración general
    enabled_channels: List[NotificationChannel] = None
    min_priority: NotificationPriority = NotificationPriority.MEDIUM
    rate_limit_minutes: int = 5  # Evitar spam
    
    def __post_init__(self):
        if self.enabled_channels is None:
            self.enabled_channels = []
        if self.to_emails is None:
            self.to_emails = []
        if self.webhook_urls is None:
            self.webhook_urls = []

@dataclass
class NotificationMessage:
    """Mensaje de notificación"""
    title: str
    message: str
    priority: NotificationPriority
    event_type: str
    data: Dict[str, Any] = None
    channels: List[NotificationChannel] = None
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}
        if self.channels is None:
            self.channels = [NotificationChannel.SLACK, NotificationChannel.EMAIL]

class NotificationService:
    """
    Servicio de notificaciones en tiempo real
    Soporta múltiples canales: Slack, Email, Webhooks
    """
    
    def __init__(self, db: Session, config: NotificationConfig = None):
        self.db = db
        self.config = config or self._load_config_from_env()
        self._last_notifications = {}  # Rate limiting
        logger.info("NotificationService initialized")
    
    def _load_config_from_env(self) -> NotificationConfig:
        """Carga configuración desde variables de entorno"""
        return NotificationConfig(
            # Slack
            slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
            slack_channel=os.getenv("SLACK_CHANNEL", "#alerts"),
            slack_username=os.getenv("SLACK_USERNAME", "MercadoPago-Bot"),
            
            # Email
            smtp_server=os.getenv("SMTP_SERVER"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=os.getenv("SMTP_USERNAME"),
            smtp_password=os.getenv("SMTP_PASSWORD"),
            from_email=os.getenv("FROM_EMAIL"),
            to_emails=os.getenv("TO_EMAILS", "").split(",") if os.getenv("TO_EMAILS") else [],
            
            # Webhooks
            webhook_urls=os.getenv("WEBHOOK_URLS", "").split(",") if os.getenv("WEBHOOK_URLS") else [],
            
            # General
            enabled_channels=[
                NotificationChannel.SLACK if os.getenv("SLACK_WEBHOOK_URL") else None,
                NotificationChannel.EMAIL if os.getenv("SMTP_SERVER") else None,
                NotificationChannel.WEBHOOK if os.getenv("WEBHOOK_URLS") else None
            ],
            min_priority=NotificationPriority(os.getenv("MIN_NOTIFICATION_PRIORITY", "medium")),
            rate_limit_minutes=int(os.getenv("NOTIFICATION_RATE_LIMIT", "5"))
        )
    
    def send_notification(self, notification: NotificationMessage) -> Dict[str, Any]:
        """
        Envía notificación por todos los canales configurados
        """
        try:
            # Verificar prioridad mínima
            if notification.priority.value < self.config.min_priority.value:
                logger.debug(f"Notification skipped - priority {notification.priority.value} below minimum {self.config.min_priority.value}")
                return {"success": True, "message": "Skipped due to priority", "channels": []}
            
            # Verificar rate limiting
            if self._is_rate_limited(notification.event_type):
                logger.debug(f"Notification rate limited for event type: {notification.event_type}")
                return {"success": True, "message": "Rate limited", "channels": []}
            
            results = {}
            successful_channels = []
            
            # Enviar por cada canal habilitado
            for channel in notification.channels:
                if channel in self.config.enabled_channels:
                    try:
                        if channel == NotificationChannel.SLACK:
                            result = self._send_slack(notification)
                        elif channel == NotificationChannel.EMAIL:
                            result = self._send_email(notification)
                        elif channel == NotificationChannel.WEBHOOK:
                            result = self._send_webhook(notification)
                        else:
                            result = {"success": False, "error": f"Channel {channel.value} not implemented"}
                        
                        results[channel.value] = result
                        if result.get("success"):
                            successful_channels.append(channel.value)
                            
                    except Exception as e:
                        logger.error(f"Error sending notification via {channel.value}: {str(e)}")
                        results[channel.value] = {"success": False, "error": str(e)}
            
            # Actualizar rate limiting
            self._update_rate_limit(notification.event_type)
            
            logger.info(f"Notification sent via {len(successful_channels)} channels: {successful_channels}")
            
            return {
                "success": len(successful_channels) > 0,
                "channels": successful_channels,
                "results": results,
                "message": f"Sent via {len(successful_channels)} channels"
            }
            
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _send_slack(self, notification: NotificationMessage) -> Dict[str, Any]:
        """Envía notificación por Slack"""
        if not self.config.slack_webhook_url:
            return {"success": False, "error": "Slack webhook URL not configured"}
        
        try:
            # Determinar color basado en prioridad
            colors = {
                NotificationPriority.LOW: "#36a64f",      # Verde
                NotificationPriority.MEDIUM: "#ff9500",   # Naranja
                NotificationPriority.HIGH: "#ff0000",     # Rojo
                NotificationPriority.CRITICAL: "#8B0000"  # Rojo oscuro
            }
            
            # Determinar emoji basado en tipo de evento
            emojis = {
                "security_alert": "🚨",
                "payment_approved": "✅",
                "payment_failed": "❌",
                "system_error": "⚠️",
                "brute_force": "🛡️",
                "webhook_failed": "🔗",
                "reconciliation": "📊",
                "backup_completed": "💾",
                "default": "📢"
            }
            
            emoji = emojis.get(notification.event_type, emojis["default"])
            color = colors.get(notification.priority, colors[NotificationPriority.MEDIUM])
            
            # Construir payload de Slack
            payload = {
                "channel": self.config.slack_channel,
                "username": self.config.slack_username,
                "icon_emoji": ":robot_face:",
                "attachments": [
                    {
                        "color": color,
                        "title": f"{emoji} {notification.title}",
                        "text": notification.message,
                        "fields": [
                            {
                                "title": "Prioridad",
                                "value": notification.priority.value.upper(),
                                "short": True
                            },
                            {
                                "title": "Tipo de Evento",
                                "value": notification.event_type,
                                "short": True
                            },
                            {
                                "title": "Timestamp",
                                "value": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                                "short": True
                            }
                        ],
                        "footer": "MercadoPago Enterprise",
                        "ts": int(datetime.utcnow().timestamp())
                    }
                ]
            }
            
            # Agregar campos adicionales si hay data
            if notification.data:
                for key, value in notification.data.items():
                    if len(payload["attachments"][0]["fields"]) < 10:  # Límite de Slack
                        payload["attachments"][0]["fields"].append({
                            "title": key.replace("_", " ").title(),
                            "value": str(value),
                            "short": True
                        })
            
            # Enviar a Slack
            response = requests.post(
                self.config.slack_webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                return {"success": True, "message": "Slack notification sent"}
            else:
                return {"success": False, "error": f"Slack API error: {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _send_email(self, notification: NotificationMessage) -> Dict[str, Any]:
        """Envía notificación por email"""
        if not all([self.config.smtp_server, self.config.from_email, self.config.to_emails]):
            return {"success": False, "error": "Email configuration incomplete"}
        
        try:
            # Crear mensaje
            msg = MimeMultipart()
            msg['From'] = self.config.from_email
            msg['To'] = ", ".join(self.config.to_emails)
            msg['Subject'] = f"[{notification.priority.value.upper()}] {notification.title}"
            
            # Construir cuerpo del email
            body = f"""
{notification.message}

Detalles del Evento:
- Tipo: {notification.event_type}
- Prioridad: {notification.priority.value.upper()}
- Timestamp: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}
"""
            
            # Agregar datos adicionales
            if notification.data:
                body += "\nDatos Adicionales:\n"
                for key, value in notification.data.items():
                    body += f"- {key.replace('_', ' ').title()}: {value}\n"
            
            body += "\n---\nMercadoPago Enterprise Notification System"
            
            msg.attach(MimeText(body, 'plain'))
            
            # Enviar email
            server = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port)
            server.starttls()
            
            if self.config.smtp_username and self.config.smtp_password:
                server.login(self.config.smtp_username, self.config.smtp_password)
            
            server.send_message(msg)
            server.quit()
            
            return {"success": True, "message": f"Email sent to {len(self.config.to_emails)} recipients"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _send_webhook(self, notification: NotificationMessage) -> Dict[str, Any]:
        """Envía notificación por webhook"""
        if not self.config.webhook_urls:
            return {"success": False, "error": "No webhook URLs configured"}
        
        try:
            # Construir payload
            payload = {
                "title": notification.title,
                "message": notification.message,
                "priority": notification.priority.value,
                "event_type": notification.event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "data": notification.data,
                "source": "mercadopago-enterprise"
            }
            
            successful_webhooks = 0
            errors = []
            
            # Enviar a cada webhook
            for webhook_url in self.config.webhook_urls:
                try:
                    response = requests.post(
                        webhook_url,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    )
                    
                    if response.status_code in [200, 201, 202]:
                        successful_webhooks += 1
                    else:
                        errors.append(f"{webhook_url}: HTTP {response.status_code}")
                        
                except Exception as e:
                    errors.append(f"{webhook_url}: {str(e)}")
            
            if successful_webhooks > 0:
                return {
                    "success": True, 
                    "message": f"Webhook sent to {successful_webhooks}/{len(self.config.webhook_urls)} endpoints",
                    "errors": errors if errors else None
                }
            else:
                return {"success": False, "error": f"All webhooks failed: {errors}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _is_rate_limited(self, event_type: str) -> bool:
        """Verifica si el evento está limitado por rate limiting"""
        if event_type not in self._last_notifications:
            return False
        
        last_time = self._last_notifications[event_type]
        time_diff = (datetime.utcnow() - last_time).total_seconds() / 60
        
        return time_diff < self.config.rate_limit_minutes
    
    def _update_rate_limit(self, event_type: str):
        """Actualiza el timestamp para rate limiting"""
        self._last_notifications[event_type] = datetime.utcnow()
    
    # Métodos de conveniencia para eventos específicos
    
    def notify_security_alert(self, alert: SecurityAlert) -> Dict[str, Any]:
        """Notifica una alerta de seguridad"""
        priority = NotificationPriority.CRITICAL if alert.severity == "CRITICAL" else NotificationPriority.HIGH
        
        notification = NotificationMessage(
            title=f"Alerta de Seguridad: {alert.alert_type}",
            message=f"{alert.title}\n\n{alert.description}",
            priority=priority,
            event_type="security_alert",
            data={
                "alert_id": alert.id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "payment_id": alert.payment_id,
                "source_ip": alert.source_ip,
                "created_at": alert.created_at.isoformat()
            }
        )
        
        return self.send_notification(notification)
    
    def notify_payment_approved(self, payment: Payment) -> Dict[str, Any]:
        """Notifica un pago aprobado"""
        notification = NotificationMessage(
            title=f"Pago Aprobado: ${payment.paid_amount}",
            message=f"Pago de {payment.customer_email} por ${payment.paid_amount} ha sido aprobado exitosamente.",
            priority=NotificationPriority.LOW,
            event_type="payment_approved",
            data={
                "payment_id": payment.id,
                "customer_email": payment.customer_email,
                "amount": str(payment.paid_amount),
                "ghl_contact_id": payment.ghl_contact_id,
                "processed_at": payment.processed_at.isoformat() if payment.processed_at else None
            }
        )
        
        return self.send_notification(notification)
    
    def notify_system_error(self, error_message: str, error_type: str = "system_error", **kwargs) -> Dict[str, Any]:
        """Notifica un error del sistema"""
        notification = NotificationMessage(
            title=f"Error del Sistema: {error_type}",
            message=error_message,
            priority=NotificationPriority.HIGH,
            event_type=error_type,
            data=kwargs
        )
        
        return self.send_notification(notification)
    
    def notify_brute_force_attack(self, source_ip: str, attempts: int) -> Dict[str, Any]:
        """Notifica un ataque de fuerza bruta"""
        notification = NotificationMessage(
            title="🛡️ ATAQUE DE FUERZA BRUTA DETECTADO",
            message=f"Se detectaron {attempts} intentos de login fallidos desde la IP {source_ip}. El sistema ha bloqueado automáticamente esta IP.",
            priority=NotificationPriority.CRITICAL,
            event_type="brute_force",
            data={
                "source_ip": source_ip,
                "attempts": attempts,
                "action_taken": "IP blocked automatically",
                "detection_time": datetime.utcnow().isoformat()
            }
        )
        
        return self.send_notification(notification)
    
    def notify_reconciliation_completed(self, execution_id: str, discrepancies: int, corrections: int) -> Dict[str, Any]:
        """Notifica finalización de reconciliación"""
        priority = NotificationPriority.HIGH if discrepancies > 0 else NotificationPriority.LOW
        
        notification = NotificationMessage(
            title=f"Reconciliación Completada: {discrepancies} discrepancias",
            message=f"La reconciliación diaria ha finalizado. Se encontraron {discrepancies} discrepancias y se aplicaron {corrections} correcciones automáticas.",
            priority=priority,
            event_type="reconciliation",
            data={
                "execution_id": execution_id,
                "discrepancies_found": discrepancies,
                "corrections_applied": corrections,
                "completion_time": datetime.utcnow().isoformat()
            }
        )
        
        return self.send_notification(notification)
    
    def test_notifications(self) -> Dict[str, Any]:
        """Prueba todas las configuraciones de notificación"""
        test_notification = NotificationMessage(
            title="🧪 Prueba de Notificaciones",
            message="Esta es una notificación de prueba para verificar que todos los canales están funcionando correctamente.",
            priority=NotificationPriority.LOW,
            event_type="test",
            data={
                "test_timestamp": datetime.utcnow().isoformat(),
                "system_status": "operational"
            }
        )
        
        return self.send_notification(test_notification)