"""
Utilidades de seguridad y autenticación
"""
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer
from .config import ADMIN_API_KEY

security = HTTPBearer()

def verify_admin_token(token: str = Depends(security)):
    """Verificación de token de administrador"""
    if not ADMIN_API_KEY:
        raise HTTPException(status_code=500, detail="Admin token not configured on server")
    
    if token.credentials != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin token")
    
    return token.credentials