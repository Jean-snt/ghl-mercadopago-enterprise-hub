"""
Router para webhooks de MercadoPago
"""
from fastapi import APIRouter, Request, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.schemas import WebhookPayload

router = APIRouter()

@router.post("/webhooks/mercadopago")
async def process_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Procesar webhook de MercadoPago"""
    # Implementar lógica de webhook
    return {"status": "received"}