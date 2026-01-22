"""
Router para endpoints administrativos
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import verify_admin_token

router = APIRouter()

@router.get("/health")
async def admin_health(
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """Health check administrativo"""
    return {"status": "healthy"}