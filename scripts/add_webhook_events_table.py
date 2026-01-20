"""
Script para agregar la tabla webhook_events para el sistema resiliente
"""
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_path():
    database_url = os.getenv("DATABASE_URL", "sqlite:///./mercadopago_enterprise.db")
    if database_url.startswith("sqlite:///"):
        return database_url.replace("sqlite:///", "")
    elif database_url.startswith("sqlite://"):
        return database_url.replace("sqlite://", "")
    return "./mercadopago_enterprise.db"

def create_webhook_events_table():
    db_path = get_db_path()
    print(f"🔧 Agregando tabla webhook_events a: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar si la tabla ya existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='webhook_events'")
        if cursor.fetchone():
            print("⏭️  Tabla 'webhook_events' ya existe - omitiendo")
            conn.close()
            return True
        
        # Crear tabla webhook_events
        print("➕ Creando tabla 'webhook_events'...")
        
        create_table_sql = """
        CREATE TABLE webhook_events (
            id INTEGER PRIMARY KEY,
            mp_event_id VARCHAR(100),
            topic VARCHAR(50) NOT NULL,
            resource VARCHAR(200),
            raw_data TEXT NOT NULL,
            headers TEXT,
            source_ip VARCHAR(45),
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            attempts INTEGER NOT NULL DEFAULT 0,
            max_attempts INTEGER NOT NULL DEFAULT 3,
            last_attempt_at DATETIME,
            last_error TEXT,
            processed_at DATETIME,
            payment_id INTEGER,
            mp_payment_id VARCHAR(50),
            signature_valid BOOLEAN,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (payment_id) REFERENCES payments (id)
        )
        """
        
        cursor.execute(create_table_sql)
        
        # Crear índices
        print("📊 Creando índices...")
        
        indices = [
            "CREATE INDEX idx_webhook_event_status_created ON webhook_events(status, created_at)",
            "CREATE INDEX idx_webhook_event_topic_status ON webhook_events(topic, status)",
            "CREATE INDEX idx_webhook_event_attempts ON webhook_events(attempts, status)",
            "CREATE INDEX idx_webhook_event_mp_payment ON webhook_events(mp_payment_id, status)",
            "CREATE INDEX idx_webhook_event_mp_event ON webhook_events(mp_event_id)",
            "CREATE INDEX idx_webhook_event_topic ON webhook_events(topic)"
        ]
        
        for index_sql in indices:
            try:
                cursor.execute(index_sql)
                print(f"   ✅ Índice creado")
            except sqlite3.OperationalError as e:
                if "already exists" not in str(e):
                    print(f"   ⚠️  Error creando índice: {e}")
        
        conn.commit()
        
        # Verificar estructura
        print("\n📋 Estructura de la tabla 'webhook_events':")
        cursor.execute("PRAGMA table_info(webhook_events)")
        columns = cursor.fetchall()
        for col in columns:
            col_id, col_name, col_type, not_null, default_val, pk = col
            nullable = "NOT NULL" if not_null else "NULL"
            pk_marker = " (PK)" if pk else ""
            default_info = f" DEFAULT {default_val}" if default_val else ""
            print(f"   - {col_name}: {col_type} {nullable}{default_info}{pk_marker}")
        
        conn.close()
        
        print("\n✅ Tabla 'webhook_events' creada exitosamente")
        print("\n🔄 Características del sistema resiliente:")
        print("   - Recepción inmediata de webhooks")
        print("   - Procesamiento en segundo plano")
        print("   - Sistema de reintentos automático")
        print("   - Gestión de eventos fallidos")
        print("   - Estadísticas y monitoreo")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando tabla: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Agregando tabla webhook_events para sistema resiliente\n")
    
    if create_webhook_events_table():
        print("\n✅ Tabla agregada exitosamente")
        print("\n🚀 Próximos pasos:")
        print("   1. Reinicia el servidor: uvicorn main:app --reload")
        print("   2. Prueba el sistema: python tests/test_resilient_webhooks.py")
        exit(0)
    else:
        print("\n❌ Error agregando tabla")
        exit(1)