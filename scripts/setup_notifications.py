#!/usr/bin/env python3
"""
Setup Notifications - Configuración del Sistema de Notificaciones
Configura Slack, Email y Webhooks para alertas en tiempo real
"""
import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from services.notification_service import NotificationService, NotificationConfig, NotificationMessage, NotificationPriority, NotificationChannel
from models import Base

def create_sample_env_file():
    """Crea archivo .env.example con configuración de notificaciones"""
    env_content = """
# ============================================
# CONFIGURACIÓN DE NOTIFICACIONES
# ============================================

# Slack Notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
SLACK_CHANNEL=#alerts
SLACK_USERNAME=MercadoPago-Bot

# Email Notifications (Gmail example)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=your-email@gmail.com
TO_EMAILS=admin1@company.com,admin2@company.com,security@company.com

# Webhook Notifications
WEBHOOK_URLS=https://your-webhook-endpoint.com/alerts,https://backup-webhook.com/notifications

# Notification Settings
MIN_NOTIFICATION_PRIORITY=medium  # low, medium, high, critical
NOTIFICATION_RATE_LIMIT=5  # minutes between same event type notifications

# Existing MercadoPago Configuration
ADMIN_API_KEY=junior123
DATABASE_URL=sqlite:///./mercadopago_enterprise.db
MP_ACCESS_TOKEN=TEST-your-mp-access-token
MP_WEBHOOK_SECRET=your-webhook-secret
GHL_API_KEY=test_ghl_key_for_development
ENVIRONMENT=development
BASE_URL=http://localhost:8000
"""
    
    with open('.env.notifications.example', 'w') as f:
        f.write(env_content.strip())
    
    print("✅ Archivo .env.notifications.example creado")
    print("📝 Copia este archivo a .env y configura tus credenciales reales")

def test_notification_service():
    """Prueba el servicio de notificaciones"""
    print("\n🧪 PROBANDO SISTEMA DE NOTIFICACIONES")
    print("=" * 50)
    
    # Configurar base de datos
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mercadopago_enterprise.db")
    engine = create_engine(DATABASE_URL, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    with SessionLocal() as db:
        # Crear servicio de notificaciones
        notification_service = NotificationService(db)
        
        print(f"📋 Configuración cargada:")
        print(f"   Slack: {'✅' if notification_service.config.slack_webhook_url else '❌'}")
        print(f"   Email: {'✅' if notification_service.config.smtp_server else '❌'}")
        print(f"   Webhooks: {'✅' if notification_service.config.webhook_urls else '❌'}")
        print(f"   Canales habilitados: {[c.value for c in notification_service.config.enabled_channels if c]}")
        
        # Probar notificación de prueba
        print(f"\n📤 Enviando notificación de prueba...")
        result = notification_service.test_notifications()
        
        print(f"📊 Resultado:")
        print(f"   Éxito: {'✅' if result['success'] else '❌'}")
        print(f"   Canales enviados: {result.get('channels', [])}")
        
        if result.get('results'):
            for channel, channel_result in result['results'].items():
                status = '✅' if channel_result.get('success') else '❌'
                message = channel_result.get('message', channel_result.get('error', 'Unknown'))
                print(f"   {channel}: {status} {message}")
        
        return result['success']

def test_specific_notifications():
    """Prueba notificaciones específicas"""
    print("\n🎯 PROBANDO NOTIFICACIONES ESPECÍFICAS")
    print("=" * 50)
    
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mercadopago_enterprise.db")
    engine = create_engine(DATABASE_URL, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    with SessionLocal() as db:
        notification_service = NotificationService(db)
        
        # 1. Notificación de alerta de seguridad
        print("🚨 Probando alerta de seguridad...")
        security_result = notification_service.notify_brute_force_attack("192.168.1.100", 5)
        print(f"   Resultado: {'✅' if security_result['success'] else '❌'}")
        
        # 2. Notificación de error del sistema
        print("⚠️ Probando error del sistema...")
        error_result = notification_service.notify_system_error(
            "Base de datos temporalmente no disponible",
            "database_error",
            error_code="DB_CONN_TIMEOUT",
            affected_services=["payments", "webhooks"]
        )
        print(f"   Resultado: {'✅' if error_result['success'] else '❌'}")
        
        # 3. Notificación de reconciliación
        print("📊 Probando reconciliación completada...")
        recon_result = notification_service.notify_reconciliation_completed(
            "recon_20260120_test", 3, 2
        )
        print(f"   Resultado: {'✅' if recon_result['success'] else '❌'}")
        
        return all([security_result['success'], error_result['success'], recon_result['success']])

def setup_slack_integration():
    """Guía para configurar Slack"""
    print("\n🔧 CONFIGURACIÓN DE SLACK")
    print("=" * 50)
    print("""
Para configurar notificaciones de Slack:

1. Ve a https://api.slack.com/apps
2. Crea una nueva app o selecciona una existente
3. Ve a "Incoming Webhooks" y actívalo
4. Crea un nuevo webhook para tu canal
5. Copia la URL del webhook
6. Agrega la URL a tu archivo .env:
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK

Ejemplo de configuración:
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXXX/YYYY/ZZZZ
SLACK_CHANNEL=#alerts
SLACK_USERNAME=MercadoPago-Bot
""")

def setup_email_integration():
    """Guía para configurar Email"""
    print("\n📧 CONFIGURACIÓN DE EMAIL")
    print("=" * 50)
    print("""
Para configurar notificaciones por email:

Gmail (recomendado):
1. Habilita autenticación de 2 factores en tu cuenta Gmail
2. Genera una "App Password" en tu cuenta Google
3. Configura las variables:
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=tu-email@gmail.com
   SMTP_PASSWORD=tu-app-password-generado
   FROM_EMAIL=tu-email@gmail.com
   TO_EMAILS=admin1@company.com,admin2@company.com

Outlook/Hotmail:
   SMTP_SERVER=smtp-mail.outlook.com
   SMTP_PORT=587

Servidor SMTP personalizado:
   SMTP_SERVER=mail.tu-empresa.com
   SMTP_PORT=587 (o 465 para SSL)
""")

def create_notification_test_script():
    """Crea script para probar notificaciones"""
    script_content = '''#!/usr/bin/env python3
"""
Test Notifications - Script para probar notificaciones manualmente
"""
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from services.notification_service import NotificationService, NotificationMessage, NotificationPriority
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def main():
    print("🧪 PROBADOR DE NOTIFICACIONES")
    print("=" * 40)
    
    # Configurar DB
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mercadopago_enterprise.db")
    engine = create_engine(DATABASE_URL, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    with SessionLocal() as db:
        service = NotificationService(db)
        
        while True:
            print("\\nOpciones:")
            print("1. Probar notificación básica")
            print("2. Simular alerta de seguridad")
            print("3. Simular error del sistema")
            print("4. Simular ataque brute force")
            print("5. Ver configuración actual")
            print("0. Salir")
            
            choice = input("\\nSelecciona una opción: ").strip()
            
            if choice == "1":
                result = service.test_notifications()
                print(f"Resultado: {'✅ Éxito' if result['success'] else '❌ Error'}")
                
            elif choice == "2":
                result = service.notify_security_alert_custom(
                    "Test Security Alert",
                    "Esta es una alerta de seguridad de prueba",
                    "HIGH"
                )
                print(f"Resultado: {'✅ Éxito' if result['success'] else '❌ Error'}")
                
            elif choice == "3":
                result = service.notify_system_error(
                    "Error de prueba del sistema",
                    "test_error",
                    component="test_module"
                )
                print(f"Resultado: {'✅ Éxito' if result['success'] else '❌ Error'}")
                
            elif choice == "4":
                result = service.notify_brute_force_attack("192.168.1.999", 10)
                print(f"Resultado: {'✅ Éxito' if result['success'] else '❌ Error'}")
                
            elif choice == "5":
                config = service.config
                print(f"\\n📋 Configuración:")
                print(f"   Slack: {'✅' if config.slack_webhook_url else '❌'}")
                print(f"   Email: {'✅' if config.smtp_server else '❌'}")
                print(f"   Webhooks: {'✅' if config.webhook_urls else '❌'}")
                print(f"   Canales: {[c.value for c in config.enabled_channels if c]}")
                
            elif choice == "0":
                break
                
            else:
                print("Opción inválida")

if __name__ == "__main__":
    main()
'''
    
    with open('scripts/test_notifications.py', 'w') as f:
        f.write(script_content)
    
    # Hacer ejecutable en sistemas Unix
    os.chmod('scripts/test_notifications.py', 0o755)
    
    print("✅ Script de prueba creado: scripts/test_notifications.py")

def main():
    """Función principal"""
    print("🚀 CONFIGURADOR DE NOTIFICACIONES - MERCADOPAGO ENTERPRISE")
    print("=" * 60)
    
    # Cargar variables de entorno si existen
    from dotenv import load_dotenv
    load_dotenv()
    
    while True:
        print(f"\n📋 OPCIONES:")
        print("1. Crear archivo de configuración (.env.example)")
        print("2. Probar sistema de notificaciones")
        print("3. Probar notificaciones específicas")
        print("4. Guía configuración Slack")
        print("5. Guía configuración Email")
        print("6. Crear script de pruebas")
        print("0. Salir")
        
        choice = input("\nSelecciona una opción: ").strip()
        
        if choice == "1":
            create_sample_env_file()
            
        elif choice == "2":
            success = test_notification_service()
            if not success:
                print("\n⚠️ Algunas notificaciones fallaron. Verifica tu configuración.")
                
        elif choice == "3":
            success = test_specific_notifications()
            if success:
                print("\n✅ Todas las notificaciones específicas funcionaron correctamente")
            else:
                print("\n⚠️ Algunas notificaciones específicas fallaron")
                
        elif choice == "4":
            setup_slack_integration()
            
        elif choice == "5":
            setup_email_integration()
            
        elif choice == "6":
            create_notification_test_script()
            
        elif choice == "0":
            print("\n👋 ¡Hasta luego!")
            break
            
        else:
            print("❌ Opción inválida")

if __name__ == "__main__":
    main()