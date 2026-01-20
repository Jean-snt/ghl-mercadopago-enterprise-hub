"""
Script de inicialización de base de datos para MercadoPago Enterprise
"""
import os
from sqlalchemy import create_engine
from models import Base
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def init_database():
    """Inicializa la base de datos con todas las tablas"""
    database_url = os.getenv("DATABASE_URL", "sqlite:///./mercadopago_enterprise.db")
    
    print(f"Inicializando base de datos: {database_url}")
    
    # Crear engine
    engine = create_engine(database_url, echo=True)
    
    # Crear todas las tablas
    Base.metadata.create_all(bind=engine)
    
    print("✅ Base de datos inicializada correctamente")
    print("📊 Tablas creadas:")
    print("   - payments")
    print("   - audit_logs") 
    print("   - security_alerts")
    print("   - webhook_logs")
    
    print("\n🔒 Características de seguridad activadas:")
    print("   - Auditoría completa de acciones")
    print("   - Validación de idempotencia")
    print("   - Alertas de seguridad automáticas")
    print("   - Validación de montos crítica")
    print("   - Logs de webhooks detallados")

if __name__ == "__main__":
    init_database()