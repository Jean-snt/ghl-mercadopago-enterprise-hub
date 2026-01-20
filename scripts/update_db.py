"""
Script para actualizar la base de datos con columnas faltantes
Agrega mp_account_id y otras columnas necesarias a la tabla payments
"""
import sqlite3
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def get_db_path():
    """Obtiene la ruta de la base de datos desde DATABASE_URL"""
    database_url = os.getenv("DATABASE_URL", "sqlite:///./mercadopago_enterprise.db")
    
    # Extraer path del SQLite URL
    if database_url.startswith("sqlite:///"):
        db_path = database_url.replace("sqlite:///", "")
    elif database_url.startswith("sqlite://"):
        db_path = database_url.replace("sqlite://", "")
    else:
        db_path = "./mercadopago_enterprise.db"
    
    return db_path

def column_exists(cursor, table_name, column_name):
    """Verifica si una columna existe en una tabla"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def table_exists(cursor, table_name):
    """Verifica si una tabla existe"""
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    return cursor.fetchone() is not None

def update_database():
    """Actualiza la base de datos con las columnas faltantes"""
    db_path = get_db_path()
    
    print(f"🔧 Actualizando base de datos: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"❌ Error: Base de datos no encontrada en {db_path}")
        print("   Ejecuta primero: python recreate_db.py")
        return False
    
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("✅ Conexión establecida")
        
        # Verificar que la tabla payments existe
        if not table_exists(cursor, 'payments'):
            print("❌ Error: La tabla 'payments' no existe")
            print("   Ejecuta: python recreate_db.py")
            conn.close()
            return False
        
        print("✅ Tabla 'payments' encontrada")
        
        # Lista de columnas a agregar
        columns_to_add = [
            {
                'name': 'mp_account_id',
                'definition': 'INTEGER',
                'description': 'Relación con cuenta OAuth de MercadoPago'
            }
        ]
        
        # Verificar y agregar columnas faltantes
        columns_added = 0
        columns_skipped = 0
        
        for column_info in columns_to_add:
            column_name = column_info['name']
            column_def = column_info['definition']
            description = column_info['description']
            
            if column_exists(cursor, 'payments', column_name):
                print(f"⏭️  Columna '{column_name}' ya existe - omitiendo")
                columns_skipped += 1
            else:
                print(f"➕ Agregando columna '{column_name}'...")
                try:
                    cursor.execute(f"ALTER TABLE payments ADD COLUMN {column_name} {column_def}")
                    print(f"   ✅ Columna '{column_name}' agregada exitosamente")
                    print(f"      Descripción: {description}")
                    columns_added += 1
                except sqlite3.OperationalError as e:
                    print(f"   ❌ Error agregando columna '{column_name}': {str(e)}")
        
        # Verificar índices (opcional)
        print("\n🔍 Verificando índices...")
        try:
            # Crear índice para mp_account_id si no existe
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_payment_mp_account 
                ON payments(mp_account_id)
            """)
            print("✅ Índice idx_payment_mp_account verificado/creado")
        except Exception as e:
            print(f"⚠️  Advertencia creando índice: {str(e)}")
        
        # Commit de cambios
        conn.commit()
        
        # Mostrar resumen
        print("\n" + "="*60)
        print("📊 Resumen de actualización:")
        print(f"   Columnas agregadas: {columns_added}")
        print(f"   Columnas existentes: {columns_skipped}")
        print("="*60)
        
        # Mostrar estructura actual de la tabla
        print("\n📋 Estructura actual de la tabla 'payments':")
        cursor.execute("PRAGMA table_info(payments)")
        columns = cursor.fetchall()
        for col in columns:
            col_id, col_name, col_type, not_null, default_val, pk = col
            nullable = "NOT NULL" if not_null else "NULL"
            pk_marker = " (PK)" if pk else ""
            print(f"   - {col_name}: {col_type} {nullable}{pk_marker}")
        
        conn.close()
        
        print("\n✅ Base de datos actualizada exitosamente")
        print("\n🚀 Próximos pasos:")
        print("   1. Reinicia el servidor: uvicorn main:app --reload")
        print("   2. Prueba el endpoint: python test_quick_payment.py")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Error de SQLite: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {str(e)}")
        return False

def verify_all_tables():
    """Verifica que todas las tablas necesarias existan"""
    db_path = get_db_path()
    
    print("\n🔍 Verificando todas las tablas...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        required_tables = [
            'payments',
            'audit_logs',
            'security_alerts',
            'webhook_logs',
            'mercadopago_accounts'
        ]
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        all_exist = True
        for table in required_tables:
            if table in existing_tables:
                print(f"   ✅ {table}")
            else:
                print(f"   ❌ {table} - FALTANTE")
                all_exist = False
        
        conn.close()
        
        if not all_exist:
            print("\n⚠️  Algunas tablas faltan. Ejecuta: python recreate_db.py")
            return False
        
        print("\n✅ Todas las tablas necesarias existen")
        return True
        
    except Exception as e:
        print(f"❌ Error verificando tablas: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Script de actualización de base de datos\n")
    
    # Verificar tablas
    if not verify_all_tables():
        print("\n❌ Ejecuta primero: python recreate_db.py")
        exit(1)
    
    # Actualizar base de datos
    success = update_database()
    
    if success:
        print("\n✅ Actualización completada exitosamente")
        exit(0)
    else:
        print("\n❌ La actualización falló")
        exit(1)