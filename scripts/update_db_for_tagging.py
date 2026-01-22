#!/usr/bin/env python3
"""
Actualización de Base de Datos para Sistema de Tagging GHL
Agrega el campo default_tag_paid a la tabla client_accounts
"""
import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def update_database_for_tagging():
    """
    Actualiza la base de datos para soportar el sistema de tagging GHL
    """
    print("🔧 ACTUALIZACIÓN DE BASE DE DATOS PARA TAGGING GHL")
    print("=" * 60)
    
    try:
        # Conectar a la base de datos
        database_url = os.getenv("DATABASE_URL", "sqlite:///./mercadopago_enterprise.db")
        engine = create_engine(database_url, echo=False)
        
        print(f"📊 Conectando a: {database_url}")
        
        with engine.connect() as conn:
            # Verificar si la columna ya existe
            try:
                result = conn.execute(text("SELECT default_tag_paid FROM client_accounts LIMIT 1"))
                print("✅ La columna default_tag_paid ya existe")
                return True
            except Exception:
                print("🔧 La columna default_tag_paid no existe, agregándola...")
            
            # Agregar la nueva columna
            try:
                conn.execute(text("""
                    ALTER TABLE client_accounts 
                    ADD COLUMN default_tag_paid VARCHAR(100) DEFAULT 'Pago confirmado'
                """))
                conn.commit()
                print("✅ Columna default_tag_paid agregada exitosamente")
                
                # Actualizar registros existentes
                conn.execute(text("""
                    UPDATE client_accounts 
                    SET default_tag_paid = 'Pago confirmado' 
                    WHERE default_tag_paid IS NULL
                """))
                conn.commit()
                print("✅ Registros existentes actualizados")
                
                # Verificar la actualización
                result = conn.execute(text("SELECT COUNT(*) FROM client_accounts WHERE default_tag_paid IS NOT NULL"))
                count = result.scalar()
                print(f"✅ {count} registros tienen configurado default_tag_paid")
                
                return True
                
            except Exception as e:
                print(f"❌ Error agregando columna: {str(e)}")
                return False
                
    except Exception as e:
        print(f"❌ Error conectando a la base de datos: {str(e)}")
        return False

def main():
    """Función principal"""
    print("🚀 MIGRACIÓN DE BASE DE DATOS - SPRINT 2 TAGGING GHL")
    print("Agregando soporte para tags personalizados por cliente")
    print("=" * 70)
    
    success = update_database_for_tagging()
    
    if success:
        print(f"\n🎉 ¡MIGRACIÓN COMPLETADA EXITOSAMENTE!")
        print("✅ La base de datos ahora soporta tags personalizados por cliente")
        print("✅ Campo default_tag_paid agregado a client_accounts")
        print("✅ Valores por defecto configurados")
        print("\n🎯 Ahora puedes ejecutar:")
        print("python scripts/simulate_ghl_tagging.py")
    else:
        print(f"\n❌ La migración falló")
        print("⚠️ Revisar errores arriba para identificar problemas")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()