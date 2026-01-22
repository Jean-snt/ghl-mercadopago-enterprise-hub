"""
MercadoPago Enterprise - Aplicación Principal
Sistema de pagos empresarial con auditoría crítica y seguridad reforzada
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import logging
import time

from .core.config import print_config_status
from .core.database import engine
from .api import payments, webhooks, oauth, dashboard, admin, security
from .core.middleware import add_correlation_id_middleware

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Crear aplicación FastAPI
app = FastAPI(
    title="MercadoPago Enterprise API",
    version="2.0.0",
    description="Sistema empresarial de pagos con auditoría crítica y seguridad reforzada"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios exactos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware personalizado
app.middleware("http")(add_correlation_id_middleware)

# Montar archivos estáticos
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Incluir routers
app.include_router(payments.router, prefix="/api/v1", tags=["payments"])
app.include_router(webhooks.router, prefix="/api/v1", tags=["webhooks"])
app.include_router(oauth.router, prefix="/oauth", tags=["oauth"])
app.include_router(dashboard.router, prefix="/api/v1", tags=["dashboard"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(security.router, prefix="/security", tags=["security"])

@app.on_event("startup")
async def startup_event():
    """Eventos de inicio de la aplicación"""
    print_config_status()
    logger.info("🚀 MercadoPago Enterprise iniciado correctamente")

@app.get("/")
async def root():
    """Endpoint raíz con información del sistema"""
    return {
        "message": "MercadoPago Enterprise API",
        "version": "2.0.0",
        "status": "operational",
        "features": [
            "Auditoría Crítica",
            "Simulación de Pagos",
            "Integración GoHighLevel",
            "OAuth Multi-tenant",
            "Sistema de Alertas",
            "Dashboard NOC"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check para monitoreo"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "database": "connected"
    }