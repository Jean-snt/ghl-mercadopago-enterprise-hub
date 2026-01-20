"""
Script para recrear la base de datos con los nuevos cambios
"""
import os
import sys
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Agregar el directorio padre al path para importar models
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models import Base

# Cargar variables de entorno
load_dotenv()

def recreate_database():
    """Recrea la base de datos eliminando la anterior"""
    database_url = os.getenv("DATABASE_URL", "sqlite:///./mercadopago_enterprise.db")
    
    print(f"🗑️  Recreando base de datos: {database_url}")
    
    # Si es SQLite, eliminar el archivo
    if database_url.startswith("sqlite"):
        db_file = database_url.replace("sqlite:///", "").replace("sqlite://", "")
        if os.path.exists(db_file):
            os.remove(db_file)
            print(f"   ✅ Archivo anterior eliminado: {db_file}")
    
    # Crear engine
    engine = create_engine(database_url, echo=True)
    
    # Crear todas las tablas
    Base.metadata.create_all(bind=engine)
    
    print("✅ Base de datos recreada correctamente")
    print("📊 Tablas creadas:")
    print("   - payments (con mp_account_id para OAuth)")
    print("   - audit_logs") 
    print("   - security_alerts")
    print("   - webhook_logs")
    print("   - webhook_events (nueva tabla resiliente)")
    print("   - mercadopago_accounts (tabla OAuth)")
    
    print("\n🔧 Nuevas funcionalidades de Resiliencia:")
    print("   - Webhooks resilientes con cola de procesamiento")
    print("   - Procesamiento en segundo plano")
    print("   - Sistema de reintentos automático")
    print("   - Gestión de eventos fallidos")
    print("   - Endpoints de administración de webhooks")
    print("   - Estadísticas de procesamiento")

if __name__ == "__main__":
    recreate_database()