"""
Middleware personalizado para la aplicación
"""
from fastapi import Request
import time
import logging

logger = logging.getLogger(__name__)

async def add_correlation_id_middleware(request: Request, call_next):
    """Middleware para agregar correlation_id a todas las requests de forma segura"""
    correlation_id = request.headers.get("x-correlation-id", f"req_{int(time.time() * 1000)}")
    
    # Almacenar en el request para uso posterior
    request.state.correlation_id = correlation_id
    
    try:
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
    except Exception as e:
        # Log simple sin extra para evitar conflictos
        print(f"[ERROR] Request failed with correlation_id {correlation_id}: {str(e)}")
        raise e