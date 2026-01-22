"""
MercadoPago Enterprise - Punto de entrada principal
"""
import uvicorn
from app.main import app
from app.core.config import HOST, PORT

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=True,
        log_level="info"
    )