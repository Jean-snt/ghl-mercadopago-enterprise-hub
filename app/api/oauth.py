"""
Router para OAuth de MercadoPago
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.database import get_db

router = APIRouter()

@router.get("/authorize")
async def oauth_authorize():
    """Iniciar flujo OAuth"""
    return {"message": "OAuth authorize endpoint"}