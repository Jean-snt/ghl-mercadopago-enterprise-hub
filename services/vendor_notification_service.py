"""
VendorNotificationService - MVP de Notificaciones para el Vendedor
Maneja notificaciones de pagos aprobados con protección anti-duplicados
"""
import os
import json
import smtplib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from dataclasses import dataclass

from models import Payment, PaymentEvent, ClientAccount

logger = logging.getLogger("vendor_notification_service")

@dataclass
class VendorNotification:
    """Estructura de notificación para vendedor"""
    payment_id: int
    amount: float
    customer_name: str
    customer_email: str
    client_name: str
    approved_at: datetime
    notification_id: str

class VendorNotificationService:
    """
    Servicio MVP de notificaciones para vendedores
    Maneja notificaciones de dashboard y email con protección anti-duplicados
    """
    
    def __init__(self, db: Session):
        self.db = db
        
        # Configuración SMTP
        self.smtp_server = os.getenv("SMTP_SERVER")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("FROM_EMAIL")
        
        logger.info("VendorNotificationService initialized")
    
    def notify_payment_approved(self, payment: Payment) -> Dict[str, Any]:
        """
        Disparador único: Notifica pago aprobado desde el backend
        """
        try:
            # 1. Verificar protección anti-duplicados
            if self._is_notification_already_sent(payment.id):
                logger.info(f"Notification already sent for payment {payment.id}")
                return {
                    "success": True,
                    "message": "Notification already sent (anti-duplicate protection)",
                    "payment_id": payment.id
                }
            
            # 2. Obtener datos del cliente
            client_account = None
            if payment.client_account_id:
                client_account = self.db.query(ClientAccount).filter(
                    ClientAccount.id == payment.client_account_id
                ).first()
            
            # 3. Crear evento de notificación en dashboard
            notification_data = self._create_notification_data(payment, client_account)
            
            # 4. Registrar evento para dashboard
            dashboard_event = self._create_payment_event(
                payment_id=payment.id,
                event_type="payment_approved",
                event_data=notification_data
            )
            
            # 5. Enviar email SMTP si está configurado
            email_result = None
            if client_account and hasattr(client_account, 'owner_email') and client_account.owner_email:
                email_result = self._send_email_notification(payment, client_account, notification_data)
            elif self.from_email:
                # Fallback: usar email por defecto
                email_result = self._send_email_notification(payment, None, notification_data)
            
            # 6. Marcar notificación como enviada
            sent_event = self._create_payment_event(
                payment_id=payment.id,
                event_type="notification_sent",
                event_data={
                    "dashboard_notification_id": dashboard_event.id,
                    "email_sent": email_result.get("success", False) if email_result else False,
                    "email_error": email_result.get("error") if email_result and not email_result.get("success") else None
                }
            )
            
            logger.info(f"Vendor notification completed for payment {payment.id}")
            
            return {
                "success": True,
                "payment_id": payment.id,
                "dashboard_notification_id": dashboard_event.id,
                "notification_sent_id": sent_event.id,
                "email_sent": email_result.get("success", False) if email_result else False,
                "notification_data": notification_data
            }
            
        except Exception as e:
            logger.error(f"Error in vendor notification for payment {payment.id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "payment_id": payment.id
            }
    
    def _is_notification_already_sent(self, payment_id: int) -> bool:
        """
        Protección anti-duplicados: Verifica si ya se envió notificación
        """
        existing_notification = self.db.query(PaymentEvent).filter(
            PaymentEvent.payment_id == payment_id,
            PaymentEvent.event_type == "notification_sent"
        ).first()
        
        return existing_notification is not None
    
    def _create_notification_data(self, payment: Payment, client_account: ClientAccount = None) -> Dict[str, Any]:
        """
        Crea los datos de la notificación para dashboard
        """
        return {
            "payment_id": payment.id,
            "amount": float(payment.paid_amount or payment.expected_amount),
            "customer_name": payment.customer_name or "Cliente",
            "customer_email": payment.customer_email,
            "client_name": client_account.client_name if client_account else "Cliente Directo",
            "client_id": client_account.client_id if client_account else None,
            "approved_at": datetime.utcnow().isoformat(),
            "currency": payment.currency,
            "mp_payment_id": payment.mp_payment_id,
            "notification_id": f"notif_{payment.id}_{int(datetime.utcnow().timestamp())}"
        }
    
    def _create_payment_event(self, payment_id: int, event_type: str, event_data: Dict[str, Any]) -> PaymentEvent:
        """
        Crea un evento de pago en la base de datos
        """
        payment_event = PaymentEvent(
            payment_id=payment_id,
            event_type=event_type,
            event_data=json.dumps(event_data, default=str),
            processed_at=datetime.utcnow()
        )
        
        self.db.add(payment_event)
        self.db.commit()
        
        return payment_event
    
    def _send_email_notification(
        self, 
        payment: Payment, 
        client_account: ClientAccount = None,
        notification_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Email SMTP Simple: Envía email en texto plano
        """
        try:
            if not all([self.smtp_server, self.from_email]):
                return {"success": False, "error": "SMTP not configured"}
            
            # Determinar email destino
            to_email = None
            if client_account and hasattr(client_account, 'owner_email'):
                to_email = client_account.owner_email
            elif client_account and client_account.client_email:
                to_email = client_account.client_email
            else:
                # Fallback: usar email de configuración
                to_emails = os.getenv("TO_EMAILS", "").split(",")
                to_email = to_emails[0] if to_emails and to_emails[0] else None
            
            if not to_email:
                return {"success": False, "error": "No destination email configured"}
            
            # Asunto: Pago aprobado – RP PAY
            subject = "Pago aprobado – RP PAY"
            
            # Cuerpo: Debe incluir Monto, Cliente y Fecha
            amount = notification_data.get("amount", payment.expected_amount)
            customer_name = notification_data.get("customer_name", payment.customer_name or "Cliente")
            client_name = notification_data.get("client_name", "Cliente Directo")
            approved_date = datetime.utcnow().strftime("%d/%m/%Y %H:%M")
            
            body = f"""¡Pago Aprobado Exitosamente!

Detalles del Pago:
- Monto: ${amount} {payment.currency}
- Cliente: {customer_name}
- Email: {payment.customer_email}
- Cuenta: {client_name}
- Fecha de Aprobación: {approved_date}
- ID de Pago: {payment.mp_payment_id or payment.id}

Este pago ha sido procesado automáticamente y el contacto en GoHighLevel ha sido actualizado.

---
RP PAY - Sistema de Pagos Enterprise
Notificación automática del sistema
"""
            
            # Crear mensaje
            message = f"Subject: {subject}\r\nFrom: {self.from_email}\r\nTo: {to_email}\r\n\r\n{body}"
            
            # Enviar email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                server.sendmail(self.from_email, [to_email], message.encode('utf-8'))
            
            logger.info(f"Email notification sent to {to_email} for payment {payment.id}")
            
            return {
                "success": True,
                "to_email": to_email,
                "subject": subject,
                "message": "Email sent successfully"
            }
            
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_recent_notifications(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtiene las notificaciones recientes para el dashboard
        """
        try:
            # Buscar eventos de payment_approved recientes
            recent_events = self.db.query(PaymentEvent).filter(
                PaymentEvent.event_type == "payment_approved"
            ).order_by(PaymentEvent.created_at.desc()).limit(limit).all()
            
            notifications = []
            for event in recent_events:
                try:
                    event_data = json.loads(event.event_data) if event.event_data else {}
                    notifications.append({
                        "id": event.id,
                        "payment_id": event.payment_id,
                        "amount": event_data.get("amount"),
                        "customer_name": event_data.get("customer_name"),
                        "customer_email": event_data.get("customer_email"),
                        "client_name": event_data.get("client_name"),
                        "approved_at": event_data.get("approved_at"),
                        "currency": event_data.get("currency", "ARS"),
                        "notification_id": event_data.get("notification_id"),
                        "created_at": event.created_at.isoformat()
                    })
                except Exception as parse_error:
                    logger.error(f"Error parsing event data for event {event.id}: {str(parse_error)}")
                    continue
            
            return notifications
            
        except Exception as e:
            logger.error(f"Error getting recent notifications: {str(e)}")
            return []
    
    def get_notification_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de notificaciones para el dashboard
        """
        try:
            # Contar notificaciones por tipo
            total_approved = self.db.query(PaymentEvent).filter(
                PaymentEvent.event_type == "payment_approved"
            ).count()
            
            total_sent = self.db.query(PaymentEvent).filter(
                PaymentEvent.event_type == "notification_sent"
            ).count()
            
            # Notificaciones de hoy
            today = datetime.utcnow().date()
            today_approved = self.db.query(PaymentEvent).filter(
                PaymentEvent.event_type == "payment_approved",
                PaymentEvent.created_at >= today
            ).count()
            
            return {
                "total_approved_notifications": total_approved,
                "total_sent_notifications": total_sent,
                "today_approved": today_approved,
                "success_rate": (total_sent / total_approved * 100) if total_approved > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting notification stats: {str(e)}")
            return {
                "total_approved_notifications": 0,
                "total_sent_notifications": 0,
                "today_approved": 0,
                "success_rate": 0
            }