"""
Servicio de pagos - Lógica de negocio
"""
from sqlalchemy.orm import Session
from typing import Dict, Any
from decimal import Decimal
import logging

from ..core.schemas import PaymentCreateRequest
from ..core.models import Payment

logger = logging.getLogger(__name__)

class PaymentService:
    """Servicio para manejo de pagos"""
    
    @staticmethod
    def create_payment_link(
        db: Session,
        payment_data: PaymentCreateRequest,
        client_ip: str,
        correlation_id: str
    ) -> Dict[str, Any]:
        """Crea un link de pago en MercadoPago"""
        try:
            # Crear registro de pago
            payment = Payment(
                customer_email=payment_data.customer_email,
                customer_name=payment_data.customer_name,
                ghl_contact_id=payment_data.ghl_contact_id,
                expected_amount=Decimal(str(payment_data.amount)),
                created_by=payment_data.created_by,
                client_ip=client_ip
            )
            
            db.add(payment)
            db.flush()  # Para obtener el ID
            
            # En modo desarrollo, crear link simulado
            checkout_url = f"http://localhost:8003/simulate-payment/{payment.id}"
            
            db.commit()
            
            return {
                "success": True,
                "payment_id": payment.id,
                "checkout_url": checkout_url,
                "message": "Payment link created successfully"
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating payment: {str(e)}")
            raise e