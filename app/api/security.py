"""
Router para endpoints de seguridad
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.database import get_db

router = APIRouter()

@router.get("/alerts")
async def get_security_alerts(db: Session = Depends(get_db)):
    """Obtener alertas de seguridad"""
    return {"alerts": []}