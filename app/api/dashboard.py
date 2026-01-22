"""
Router para endpoints del dashboard
"""
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..core.database import get_db

router = APIRouter()

@router.get("/dashboard")
async def serve_dashboard():
    """Sirve el dashboard HTML del Centro de Comando NOC"""
    return FileResponse("app/static/dashboard.html")

@router.get("/dashboard/client/{client_id}")
async def serve_client_dashboard(client_id: str):
    """Sirve el dashboard HTML específico para un cliente"""
    return FileResponse("app/static/client_dashboard.html")

@router.get("/dashboard/overview")
async def dashboard_overview(db: Session = Depends(get_db)):
    """Datos del dashboard principal"""
    return {"status": "success", "data": {}}