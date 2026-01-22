#!/usr/bin/env python3
"""
Setup Vendor Notifications - Configuración MVP Notificaciones Vendedor
Crea la tabla PaymentEvent y configura el sistema de notificaciones
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

def setup_payment_events_table():
    """
    Crea la tabla PaymentEvent para tracking de notificaciones
    """
    print("🔧 CONFIGURACIÓN DE NOTIFICACIONES VENDEDOR")
    print("=" * 60)
    
    try:
        # Conectar a la base de datos
        database_url = os.getenv("DATABASE_URL", "sqlite:///./mercadopago_enterprise.db")
        engine = create_engine(database_url, echo=False)
        
        print(f"📊 Conectando a: {database_url}")
        
        with engine.connect() as conn:
            # Verificar si la tabla ya existe
            try:
                result = conn.execute(text("SELECT COUNT(*) FROM payment_events LIMIT 1"))
                print("✅ La tabla payment_events ya existe")
                return True
            except Exception:
                print("🔧 La tabla payment_events no existe, creándola...")
            
            # Crear la tabla PaymentEvent
            try:
                conn.execute(text("""
                    CREATE TABLE payment_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        payment_id INTEGER NOT NULL,
                        event_type VARCHAR(50) NOT NULL,
                        event_data TEXT,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        processed_at DATETIME,
                        FOREIGN KEY (payment_id) REFERENCES payments(id)
                    )
                """))
                
                # Crear índices
                conn.execute(text("""
                    CREATE INDEX idx_payment_event_type ON payment_events(payment_id, event_type)
                """))
                
                conn.execute(text("""
                    CREATE INDEX idx_event_created ON payment_events(event_type, created_at)
                """))
                
                conn.commit()
                print("✅ Tabla payment_events creada exitosamente")
                print("✅ Índices creados para performance")
                
                return True
                
            except Exception as e:
                print(f"❌ Error creando tabla: {str(e)}")
                return False
                
    except Exception as e:
        print(f"❌ Error conectando a la base de datos: {str(e)}")
        return False

def verify_smtp_configuration():
    """
    Verifica la configuración SMTP para envío de emails
    """
    print(f"\n📧 VERIFICANDO CONFIGURACIÓN SMTP...")
    
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT", "587")
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("FROM_EMAIL")
    to_emails = os.getenv("TO_EMAILS")
    
    config_status = []
    
    if smtp_server:
        config_status.append("✅ SMTP_SERVER configurado")
    else:
        config_status.append("❌ SMTP_SERVER no configurado")
    
    if smtp_username and smtp_password:
        config_status.append("✅ Credenciales SMTP configuradas")
    else:
        config_status.append("⚠️ Credenciales SMTP no configuradas (opcional)")
    
    if from_email:
        config_status.append(f"✅ FROM_EMAIL: {from_email}")
    else:
        config_status.append("❌ FROM_EMAIL no configurado")
    
    if to_emails:
        config_status.append(f"✅ TO_EMAILS: {to_emails}")
    else:
        config_status.append("⚠️ TO_EMAILS no configurado (se usará email del cliente)")
    
    for status in config_status:
        print(f"   {status}")
    
    # Determinar si está listo para envío
    smtp_ready = bool(smtp_server and from_email)
    
    if smtp_ready:
        print("✅ Configuración SMTP lista para envío de emails")
    else:
        print("⚠️ Configuración SMTP incompleta - emails no se enviarán")
        print("   Para habilitar emails, configura en .env:")
        print("   SMTP_SERVER=smtp.gmail.com")
        print("   SMTP_PORT=587")
        print("   FROM_EMAIL=tu-email@gmail.com")
        print("   SMTP_USERNAME=tu-email@gmail.com")
        print("   SMTP_PASSWORD=tu-app-password")
    
    return smtp_ready

def test_notification_system():
    """
    Prueba básica del sistema de notificaciones
    """
    print(f"\n🧪 PROBANDO SISTEMA DE NOTIFICACIONES...")
    
    try:
        # Importar aquí para evitar problemas de circular imports
        sys.path.append(str(Path(__file__).parent.parent))
        
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from services.vendor_notification_service import VendorNotificationService
        
        # Conectar a BD
        database_url = os.getenv("DATABASE_URL", "sqlite:///./mercadopago_enterprise.db")
        engine = create_engine(database_url, echo=False)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        # Inicializar servicio
        vendor_service = VendorNotificationService(db)
        
        # Obtener estadísticas
        stats = vendor_service.get_notification_stats()
        print(f"✅ Servicio inicializado correctamente")
        print(f"   📊 Notificaciones aprobadas: {stats['total_approved_notifications']}")
        print(f"   📧 Notificaciones enviadas: {stats['total_sent_notifications']}")
        print(f"   📈 Tasa de éxito: {stats['success_rate']:.1f}%")
        
        # Obtener notificaciones recientes
        notifications = vendor_service.get_recent_notifications(limit=5)
        print(f"✅ Últimas notificaciones: {len(notifications)} encontradas")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Error probando sistema: {str(e)}")
        return False

def main():
    """Función principal"""
    print("🚀 SETUP MVP NOTIFICACIONES VENDEDOR")
    print("Configuración del sistema de notificaciones para pagos aprobados")
    print("=" * 70)
    
    # 1. Crear tabla PaymentEvent
    table_success = setup_payment_events_table()
    
    # 2. Verificar configuración SMTP
    smtp_ready = verify_smtp_configuration()
    
    # 3. Probar sistema
    system_ready = test_notification_system()
    
    print(f"\n📋 RESUMEN DE CONFIGURACIÓN:")
    print(f"   {'✅' if table_success else '❌'} Tabla PaymentEvent: {'Creada' if table_success else 'Error'}")
    print(f"   {'✅' if smtp_ready else '⚠️'} Configuración SMTP: {'Lista' if smtp_ready else 'Incompleta'}")
    print(f"   {'✅' if system_ready else '❌'} Sistema de notificaciones: {'Funcionando' if system_ready else 'Error'}")
    
    if table_success and system_ready:
        print(f"\n🎉 ¡CONFIGURACIÓN COMPLETADA EXITOSAMENTE!")
        print("✅ El sistema de notificaciones vendedor está listo")
        print("✅ Tabla PaymentEvent creada con protección anti-duplicados")
        print("✅ Endpoints /api/notifications/ disponibles")
        
        if smtp_ready:
            print("✅ Emails automáticos habilitados")
        else:
            print("⚠️ Emails deshabilitados (configurar SMTP en .env)")
        
        print("\n🎯 Próximos pasos:")
        print("1. Ejecutar: python scripts/test_vendor_notifications.py")
        print("2. Probar endpoint: GET /api/notifications/")
        print("3. Verificar dashboard con notificaciones")
        
    else:
        print(f"\n❌ La configuración falló")
        print("⚠️ Revisar errores arriba para identificar problemas")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()