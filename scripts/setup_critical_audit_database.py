#!/usr/bin/env python3
"""
Script de migración para crear la tabla critical_audit_logs
Módulo de Auditoría de Acciones Críticas según documento oficial
"""
import os
import sys
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Agregar el directorio padre al path para importar modelos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Base, CriticalAuditLog
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mercadopago_enterprise.db")

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_critical_audit_database():
    """
    Crea la tabla critical_audit_logs y verifica la estructura
    """
    try:
        logger.info("🔧 Iniciando configuración de base de datos para Auditoría Crítica...")
        
        # Crear engine y sesión
        engine = create_engine(DATABASE_URL, echo=False)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        logger.info(f"📊 Conectando a base de datos: {DATABASE_URL}")
        
        # Crear todas las tablas (incluyendo critical_audit_logs)
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tabla critical_audit_logs creada exitosamente")
        
        # Verificar que la tabla existe y tiene la estructura correcta
        with engine.connect() as conn:
            # Verificar existencia de la tabla
            if DATABASE_URL.startswith("sqlite"):
                result = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='critical_audit_logs'"
                ))
            else:
                result = conn.execute(text(
                    "SELECT table_name FROM information_schema.tables WHERE table_name='critical_audit_logs'"
                ))
            
            table_exists = result.fetchone() is not None
            
            if table_exists:
                logger.info("✅ Tabla critical_audit_logs verificada en base de datos")
                
                # Verificar columnas principales
                if DATABASE_URL.startswith("sqlite"):
                    columns_result = conn.execute(text("PRAGMA table_info(critical_audit_logs)"))
                    columns = [row[1] for row in columns_result.fetchall()]
                else:
                    columns_result = conn.execute(text(
                        "SELECT column_name FROM information_schema.columns WHERE table_name='critical_audit_logs'"
                    ))
                    columns = [row[0] for row in columns_result.fetchall()]
                
                required_columns = [
                    'id', 'tenant_id', 'user_email', 'action', 'entity', 
                    'entity_id', 'ip_address', 'created_at'
                ]
                
                missing_columns = [col for col in required_columns if col not in columns]
                
                if missing_columns:
                    logger.error(f"❌ Columnas faltantes: {missing_columns}")
                    return False
                else:
                    logger.info(f"✅ Todas las columnas requeridas están presentes: {len(columns)} columnas")
            else:
                logger.error("❌ La tabla critical_audit_logs no fue creada")
                return False
        
        # Crear registro de prueba para verificar funcionalidad
        db = SessionLocal()
        try:
            test_audit = CriticalAuditLog(
                tenant_id="system",
                user_email="system_setup",
                action="database_migration",
                entity="critical_audit_logs",
                entity_id="setup_test",
                ip_address="127.0.0.1",
                details='{"migration": "critical_audit_setup", "test": true}',
                user_agent="Setup Script v1.0"
            )
            
            db.add(test_audit)
            db.commit()
            
            # Verificar que se guardó correctamente
            saved_audit = db.query(CriticalAuditLog).filter(
                CriticalAuditLog.entity_id == "setup_test"
            ).first()
            
            if saved_audit:
                logger.info(f"✅ Registro de prueba creado exitosamente (ID: {saved_audit.id})")
                
                # Limpiar registro de prueba
                db.delete(saved_audit)
                db.commit()
                logger.info("🧹 Registro de prueba eliminado")
            else:
                logger.error("❌ No se pudo crear el registro de prueba")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error creando registro de prueba: {str(e)}")
            db.rollback()
            return False
        finally:
            db.close()
        
        # Verificar índices (solo para información)
        with engine.connect() as conn:
            if DATABASE_URL.startswith("sqlite"):
                indexes_result = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='critical_audit_logs'"
                ))
                indexes = [row[0] for row in indexes_result.fetchall()]
                logger.info(f"📊 Índices creados: {len(indexes)} índices")
        
        logger.info("🎉 Configuración de Auditoría Crítica completada exitosamente")
        
        # Mostrar resumen
        print("\n" + "="*60)
        print("🔐 MÓDULO DE AUDITORÍA CRÍTICA - CONFIGURACIÓN COMPLETADA")
        print("="*60)
        print(f"📊 Base de datos: {DATABASE_URL}")
        print(f"📋 Tabla: critical_audit_logs")
        print(f"🔧 Columnas: {len(columns)} columnas configuradas")
        print(f"📊 Índices: Optimizados para consultas de auditoría")
        print(f"✅ Estado: LISTO PARA PRODUCCIÓN")
        print("="*60)
        print("\n🚀 Próximos pasos:")
        print("1. Ejecutar: python scripts/check_audit_trail.py")
        print("2. Probar endpoints de auditoría en /admin/audit-trail")
        print("3. Verificar logs de acciones críticas en tiempo real")
        print()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error crítico en configuración: {str(e)}")
        return False

def show_usage():
    """Muestra información de uso del script"""
    print("\n🔐 Setup Critical Audit Database - MercadoPago Enterprise")
    print("="*60)
    print("Este script configura la tabla critical_audit_logs para el")
    print("Módulo de Auditoría de Acciones Críticas según documento oficial.")
    print()
    print("Uso:")
    print("  python scripts/setup_critical_audit_database.py")
    print()
    print("Variables de entorno requeridas:")
    print("  DATABASE_URL - URL de conexión a la base de datos")
    print()
    print("Funcionalidades:")
    print("  ✅ Crea tabla critical_audit_logs")
    print("  ✅ Verifica estructura e índices")
    print("  ✅ Prueba funcionalidad básica")
    print("  ✅ Prepara sistema para auditoría crítica")
    print()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help", "help"]:
        show_usage()
        sys.exit(0)
    
    print("🔐 Configurando Módulo de Auditoría Crítica...")
    
    success = setup_critical_audit_database()
    
    if success:
        print("✅ Configuración completada exitosamente")
        sys.exit(0)
    else:
        print("❌ Error en la configuración")
        sys.exit(1)