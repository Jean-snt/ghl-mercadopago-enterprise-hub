#!/usr/bin/env python3
"""
Script para configurar y actualizar esquema de base de datos
Agrega columnas de seguridad blockchain si no existen
"""
import sys
import os
import sqlite3
from pathlib import Path

# Agregar el directorio raíz al path para imports
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

def setup_database():
    """
    Configura y actualiza el esquema de base de datos
    Agrega columnas de seguridad blockchain si no existen
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
    
    print(f"🔧 Configurando base de datos: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar y agregar columnas a audit_logs
        print("📋 Verificando tabla audit_logs...")
        
        # Obtener columnas existentes
        cursor.execute("PRAGMA table_info(audit_logs)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        print(f"   Columnas existentes: {existing_columns}")
        
        # Columnas de seguridad blockchain que necesitamos
        security_columns = {
            'previous_hash': 'TEXT',
            'current_hash': 'TEXT', 
            'block_number': 'INTEGER DEFAULT 0',
            'signature': 'TEXT',
            'merkle_root': 'TEXT',
            'nonce': 'INTEGER DEFAULT 0',
            'difficulty': 'INTEGER DEFAULT 1',
            'is_verified': 'BOOLEAN DEFAULT TRUE',
            'blockchain_enabled': 'BOOLEAN DEFAULT FALSE'
        }
        
        columns_added = 0
        for column_name, column_type in security_columns.items():
            if column_name not in existing_columns:
                try:
                    alter_sql = f"ALTER TABLE audit_logs ADD COLUMN {column_name} {column_type}"
                    cursor.execute(alter_sql)
                    print(f"   ✅ Agregada columna: {column_name}")
                    columns_added += 1
                except sqlite3.Error as e:
                    print(f"   ⚠️  Error agregando {column_name}: {e}")
        
        # Verificar y agregar columnas a security_alerts si es necesario
        print("📋 Verificando tabla security_alerts...")
        
        try:
            cursor.execute("PRAGMA table_info(security_alerts)")
            alert_columns = [row[1] for row in cursor.fetchall()]
            
            alert_security_columns = {
                'hash_verified': 'BOOLEAN DEFAULT TRUE',
                'threat_score': 'INTEGER DEFAULT 0',
                'mitigation_applied': 'BOOLEAN DEFAULT FALSE',
                'escalation_level': 'INTEGER DEFAULT 1'
            }
            
            for column_name, column_type in alert_security_columns.items():
                if column_name not in alert_columns:
                    try:
                        alter_sql = f"ALTER TABLE security_alerts ADD COLUMN {column_name} {column_type}"
                        cursor.execute(alter_sql)
                        print(f"   ✅ Agregada columna a security_alerts: {column_name}")
                        columns_added += 1
                    except sqlite3.Error as e:
                        print(f"   ⚠️  Error agregando {column_name} a security_alerts: {e}")
        
        except sqlite3.Error:
            print("   ⚠️  Tabla security_alerts no existe, se creará automáticamente")
        
        # Crear tabla de configuración del sistema si no existe
        print("📋 Verificando tabla system_config...")
        
        create_config_table = """
        CREATE TABLE IF NOT EXISTS system_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key TEXT UNIQUE NOT NULL,
            config_value TEXT,
            config_type TEXT DEFAULT 'string',
            is_encrypted BOOLEAN DEFAULT FALSE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        cursor.execute(create_config_table)
        print("   ✅ Tabla system_config verificada/creada")
        
        # Insertar configuraciones por defecto
        default_configs = [
            ('blockchain_enabled', 'false', 'boolean'),
            ('development_mode', 'true', 'boolean'),
            ('audit_hash_validation', 'false', 'boolean'),
            ('security_level', 'medium', 'string'),
            ('alert_cooldown_minutes', '15', 'integer')
        ]
        
        for key, value, config_type in default_configs:
            cursor.execute("""
                INSERT OR IGNORE INTO system_config (config_key, config_value, config_type)
                VALUES (?, ?, ?)
            """, (key, value, config_type))
        
        print("   ✅ Configuraciones por defecto insertadas")
        
        # Crear índices para performance si no existen
        print("📋 Creando índices de performance...")
        
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_audit_hash ON audit_logs(current_hash)",
            "CREATE INDEX IF NOT EXISTS idx_audit_block ON audit_logs(block_number)",
            "CREATE INDEX IF NOT EXISTS idx_audit_verified ON audit_logs(is_verified)",
            "CREATE INDEX IF NOT EXISTS idx_security_threat_score ON security_alerts(threat_score)",
            "CREATE INDEX IF NOT EXISTS idx_config_key ON system_config(config_key)"
        ]
        
        for index_sql in indices:
            try:
                cursor.execute(index_sql)
                print(f"   ✅ Índice creado: {index_sql.split('idx_')[1].split(' ')[0]}")
            except sqlite3.Error as e:
                print(f"   ⚠️  Error creando índice: {e}")
        
        # Commit todos los cambios
        conn.commit()
        
        print(f"\n🎉 Base de datos configurada exitosamente!")
        print(f"   📊 Columnas agregadas: {columns_added}")
        print(f"   🔧 Esquema actualizado para seguridad blockchain")
        print(f"   ⚙️  Configuraciones por defecto establecidas")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Error configurando base de datos: {e}")
        return False
    
    finally:
        if conn:
            conn.close()

def verify_database_schema():
    """Verifica el esquema actual de la base de datos"""
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
        
        # Verificar tablas principales
        tables = ['audit_logs', 'security_alerts', 'system_config', 'payments', 'webhook_events']
        
        print("📋 ESQUEMA ACTUAL DE LA BASE DE DATOS")
        print("="*60)
        
        for table in tables:
            try:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                
                if columns:
                    print(f"\n📊 Tabla: {table}")
                    print("-" * 40)
                    for col in columns:
                        col_name = col[1]
                        col_type = col[2]
                        not_null = "NOT NULL" if col[3] else "NULL"
                        default = f"DEFAULT {col[4]}" if col[4] else ""
                        print(f"   {col_name:<20} {col_type:<15} {not_null:<8} {default}")
                else:
                    print(f"\n❌ Tabla {table} no existe")
                    
            except sqlite3.Error as e:
                print(f"\n❌ Error verificando tabla {table}: {e}")
        
        # Verificar configuraciones del sistema
        try:
            cursor.execute("SELECT config_key, config_value, config_type FROM system_config")
            configs = cursor.fetchall()
            
            if configs:
                print(f"\n⚙️  Configuraciones del Sistema")
                print("-" * 40)
                for key, value, config_type in configs:
                    print(f"   {key:<25} = {value:<15} ({config_type})")
        except sqlite3.Error:
            print(f"\n⚠️  Tabla system_config no existe")
        
        print("\n" + "="*60)
        
    except sqlite3.Error as e:
        print(f"❌ Error verificando esquema: {e}")
    
    finally:
        if conn:
            conn.close()

def main():
    """Función principal del script"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Setup and verify MercadoPago Enterprise database schema"
    )
    
    parser.add_argument(
        "--action",
        choices=["setup", "verify", "both"],
        default="both",
        help="Action to perform"
    )
    
    args = parser.parse_args()
    
    print("🚀 MercadoPago Enterprise - Database Setup")
    print("="*50)
    
    if args.action in ["setup", "both"]:
        success = setup_database()
        if not success:
            return 1
    
    if args.action in ["verify", "both"]:
        verify_database_schema()
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)