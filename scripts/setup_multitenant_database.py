#!/usr/bin/env python3
"""
Script para migrar la base de datos a arquitectura Multi-tenant
Agrega tabla client_accounts y actualiza relaciones existentes
"""
import sys
import os
import sqlite3
from pathlib import Path

# Agregar el directorio raíz al path para imports
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

def setup_multitenant_database():
    """
    Migra la base de datos a arquitectura multi-tenant
    Agrega tabla client_accounts y actualiza relaciones
    """
    database_url = os.getenv("DATABASE_URL", "sqlite:///./mercadopago_enterprise.db")
    
    # Extraer path de la base de datos SQLite
    if database_url.startswith("sqlite:///"):
        db_path = database_url.replace("sqlite:///", "")
        if db_path.startswith("./"):
            db_path = db_path[2:]
    else:
        print("❌ Este script solo funciona con SQLite")
        return False
    
    print(f"🔧 Migrando base de datos a Multi-tenant: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Crear tabla client_accounts
        print("📋 Creando tabla client_accounts...")
        
        create_client_accounts_table = """
        CREATE TABLE IF NOT EXISTS client_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT UNIQUE NOT NULL,
            client_name TEXT NOT NULL,
            client_email TEXT,
            client_phone TEXT,
            company_name TEXT,
            industry TEXT,
            website TEXT,
            ghl_location_id TEXT,
            ghl_access_token TEXT,
            ghl_refresh_token TEXT,
            ghl_token_type TEXT DEFAULT 'Bearer',
            ghl_expires_at DATETIME,
            ghl_scope TEXT,
            ghl_last_refreshed DATETIME,
            mp_account_id INTEGER,
            is_active BOOLEAN DEFAULT TRUE NOT NULL,
            is_sandbox BOOLEAN DEFAULT FALSE NOT NULL,
            subscription_plan TEXT DEFAULT 'basic',
            auto_tag_payments BOOLEAN DEFAULT TRUE NOT NULL,
            payment_tag_prefix TEXT DEFAULT 'MP_PAGADO',
            webhook_url TEXT,
            monthly_payment_limit INTEGER,
            current_month_payments INTEGER DEFAULT 0 NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
            last_login_at DATETIME,
            registration_ip TEXT,
            last_ip TEXT,
            FOREIGN KEY (mp_account_id) REFERENCES mercadopago_accounts (id)
        )
        """
        
        cursor.execute(create_client_accounts_table)
        print("   ✅ Tabla client_accounts creada")
        
        # 2. Verificar si la columna client_account_id existe en payments
        print("📋 Verificando tabla payments...")
        
        cursor.execute("PRAGMA table_info(payments)")
        payment_columns = [row[1] for row in cursor.fetchall()]
        
        if 'client_account_id' not in payment_columns:
            try:
                cursor.execute("ALTER TABLE payments ADD COLUMN client_account_id INTEGER")
                print("   ✅ Agregada columna client_account_id a payments")
            except sqlite3.Error as e:
                print(f"   ⚠️  Error agregando client_account_id: {e}")
        else:
            print("   ✅ Columna client_account_id ya existe en payments")
        
        # 3. Crear índices para performance multi-tenant
        print("📋 Creando índices multi-tenant...")
        
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_client_active ON client_accounts(is_active, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_client_ghl_location ON client_accounts(ghl_location_id, is_active)",
            "CREATE INDEX IF NOT EXISTS idx_client_subscription ON client_accounts(subscription_plan, is_active)",
            "CREATE INDEX IF NOT EXISTS idx_client_mp_account ON client_accounts(mp_account_id, is_active)",
            "CREATE INDEX IF NOT EXISTS idx_payment_client_account ON payments(client_account_id, status)",
            "CREATE INDEX IF NOT EXISTS idx_payment_client_created ON payments(client_account_id, created_at)"
        ]
        
        for index_sql in indices:
            try:
                cursor.execute(index_sql)
                index_name = index_sql.split('idx_')[1].split(' ')[0]
                print(f"   ✅ Índice creado: {index_name}")
            except sqlite3.Error as e:
                print(f"   ⚠️  Error creando índice: {e}")
        
        # 4. Insertar cliente por defecto para datos existentes
        print("📋 Configurando cliente por defecto...")
        
        # Verificar si ya existe un cliente por defecto
        cursor.execute("SELECT COUNT(*) FROM client_accounts WHERE client_id = 'default'")
        default_exists = cursor.fetchone()[0] > 0
        
        if not default_exists:
            cursor.execute("""
                INSERT INTO client_accounts (
                    client_id, client_name, company_name, is_active, 
                    subscription_plan, created_at, updated_at
                ) VALUES (
                    'default', 'Cliente Por Defecto', 'Sistema Legacy', 
                    TRUE, 'enterprise', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
            """)
            print("   ✅ Cliente por defecto creado")
        else:
            print("   ✅ Cliente por defecto ya existe")
        
        # 5. Actualizar pagos existentes sin client_account_id
        print("📋 Actualizando pagos existentes...")
        
        cursor.execute("SELECT id FROM client_accounts WHERE client_id = 'default'")
        default_client_id = cursor.fetchone()[0]
        
        cursor.execute("""
            UPDATE payments 
            SET client_account_id = ? 
            WHERE client_account_id IS NULL
        """, (default_client_id,))
        
        updated_payments = cursor.rowcount
        print(f"   ✅ {updated_payments} pagos actualizados con cliente por defecto")
        
        # 6. Agregar configuraciones multi-tenant al sistema
        print("📋 Agregando configuraciones multi-tenant...")
        
        multitenant_configs = [
            ('multitenant_enabled', 'true', 'boolean'),
            ('default_client_id', 'default', 'string'),
            ('ghl_oauth_enabled', 'true', 'boolean'),
            ('auto_create_clients', 'true', 'boolean'),
            ('client_isolation_enabled', 'true', 'boolean')
        ]
        
        # Crear tabla system_config si no existe
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_key TEXT UNIQUE NOT NULL,
                config_value TEXT,
                config_type TEXT DEFAULT 'string',
                is_encrypted BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        for key, value, config_type in multitenant_configs:
            cursor.execute("""
                INSERT OR IGNORE INTO system_config (config_key, config_value, config_type)
                VALUES (?, ?, ?)
            """, (key, value, config_type))
        
        print("   ✅ Configuraciones multi-tenant agregadas")
        
        # Commit todos los cambios
        conn.commit()
        
        print(f"\n🎉 Migración multi-tenant completada exitosamente!")
        print(f"   📊 Tabla client_accounts creada")
        print(f"   🔗 Relaciones actualizadas en payments")
        print(f"   📈 Índices de performance creados")
        print(f"   👤 Cliente por defecto configurado")
        print(f"   ⚙️  Configuraciones multi-tenant establecidas")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Error en migración multi-tenant: {e}")
        return False
    
    finally:
        if conn:
            conn.close()

def verify_multitenant_schema():
    """Verifica el esquema multi-tenant de la base de datos"""
    database_url = os.getenv("DATABASE_URL", "sqlite:///./mercadopago_enterprise.db")
    
    if database_url.startswith("sqlite:///"):
        db_path = database_url.replace("sqlite:///", "")
        if db_path.startswith("./"):
            db_path = db_path[2:]
    else:
        print("❌ Este script solo funciona con SQLite")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("📋 VERIFICACIÓN ESQUEMA MULTI-TENANT")
        print("="*60)
        
        # Verificar tabla client_accounts
        try:
            cursor.execute("PRAGMA table_info(client_accounts)")
            columns = cursor.fetchall()
            
            if columns:
                print(f"\n📊 Tabla: client_accounts")
                print("-" * 40)
                for col in columns:
                    col_name = col[1]
                    col_type = col[2]
                    not_null = "NOT NULL" if col[3] else "NULL"
                    default = f"DEFAULT {col[4]}" if col[4] else ""
                    print(f"   {col_name:<25} {col_type:<15} {not_null:<8} {default}")
            else:
                print(f"\n❌ Tabla client_accounts no existe")
                
        except sqlite3.Error as e:
            print(f"\n❌ Error verificando client_accounts: {e}")
        
        # Verificar relación en payments
        try:
            cursor.execute("PRAGMA table_info(payments)")
            payment_columns = [row[1] for row in cursor.fetchall()]
            
            if 'client_account_id' in payment_columns:
                print(f"\n✅ Columna client_account_id existe en payments")
                
                # Contar pagos por cliente
                cursor.execute("""
                    SELECT ca.client_name, COUNT(p.id) as payment_count
                    FROM client_accounts ca
                    LEFT JOIN payments p ON ca.id = p.client_account_id
                    GROUP BY ca.id, ca.client_name
                """)
                
                client_stats = cursor.fetchall()
                print("   📊 Estadísticas por cliente:")
                for client_name, count in client_stats:
                    print(f"      {client_name}: {count} pagos")
            else:
                print(f"\n❌ Columna client_account_id no existe en payments")
                
        except sqlite3.Error as e:
            print(f"\n❌ Error verificando payments: {e}")
        
        # Verificar configuraciones multi-tenant
        try:
            cursor.execute("""
                SELECT config_key, config_value, config_type 
                FROM system_config 
                WHERE config_key LIKE '%tenant%' OR config_key LIKE '%client%' OR config_key LIKE '%ghl%'
            """)
            configs = cursor.fetchall()
            
            if configs:
                print(f"\n⚙️  Configuraciones Multi-tenant")
                print("-" * 40)
                for key, value, config_type in configs:
                    print(f"   {key:<25} = {value:<15} ({config_type})")
        except sqlite3.Error:
            print(f"\n⚠️  No se encontraron configuraciones multi-tenant")
        
        # Verificar índices multi-tenant
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE '%client%'")
            indices = cursor.fetchall()
            
            if indices:
                print(f"\n🔍 Índices Multi-tenant")
                print("-" * 40)
                for (index_name,) in indices:
                    print(f"   ✅ {index_name}")
        except sqlite3.Error:
            print(f"\n⚠️  Error verificando índices")
        
        print("\n" + "="*60)
        
    except sqlite3.Error as e:
        print(f"❌ Error verificando esquema multi-tenant: {e}")
    
    finally:
        if conn:
            conn.close()

def main():
    """Función principal del script"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Setup Multi-tenant database schema for MercadoPago Enterprise"
    )
    
    parser.add_argument(
        "--action",
        choices=["migrate", "verify", "both"],
        default="both",
        help="Action to perform"
    )
    
    args = parser.parse_args()
    
    print("🚀 MercadoPago Enterprise - Multi-tenant Database Migration")
    print("="*60)
    
    if args.action in ["migrate", "both"]:
        success = setup_multitenant_database()
        if not success:
            return 1
    
    if args.action in ["verify", "both"]:
        verify_multitenant_schema()
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)