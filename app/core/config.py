"""
Configuración centralizada del sistema MercadoPago Enterprise
"""
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de Base de Datos
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mercadopago_enterprise.db")

# Configuración de MercadoPago
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
MP_WEBHOOK_SECRET = os.getenv("MP_WEBHOOK_SECRET")
MP_CLIENT_ID = os.getenv("MP_CLIENT_ID")
MP_CLIENT_SECRET = os.getenv("MP_CLIENT_SECRET")
MP_REDIRECT_URI = os.getenv("MP_REDIRECT_URI", f"{os.getenv('BASE_URL', 'http://localhost:8000')}/oauth/callback")

# URLs de MercadoPago
MP_AUTH_URL = "https://auth.mercadopago.com/authorization"
MP_TOKEN_URL = "https://api.mercadopago.com/oauth/token"
MP_USER_INFO_URL = "https://api.mercadopago.com/users/me"

# Configuración de GoHighLevel
GHL_API_KEY = os.getenv("GHL_API_KEY")

# Configuración de Administración
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")

# Configuración de Servidor
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8003"))

# Debug: Verificar configuración
def print_config_status():
    """Imprime el estado de la configuración al iniciar"""
    print(f"🔧 Configuración cargada:")
    print(f"   DATABASE_URL: {DATABASE_URL}")
    print(f"   ADMIN_API_KEY: {'✅ Configurado' if ADMIN_API_KEY else '❌ No configurado'}")
    print(f"   MP_ACCESS_TOKEN: {'✅ Configurado' if MP_ACCESS_TOKEN else '❌ No configurado'}")
    print(f"   MP_WEBHOOK_SECRET: {'✅ Configurado' if MP_WEBHOOK_SECRET else '❌ No configurado'}")
    print(f"   GHL_API_KEY: {'✅ Configurado' if GHL_API_KEY else '❌ No configurado'}")
    print(f"   MP_CLIENT_ID: {'✅ Configurado' if MP_CLIENT_ID else '❌ No configurado'}")
    print(f"   MP_CLIENT_SECRET: {'✅ Configurado' if MP_CLIENT_SECRET else '❌ No configurado'}")
    print(f"   MP_REDIRECT_URI: {MP_REDIRECT_URI}")
    
    if not ADMIN_API_KEY:
        print("⚠️  ADVERTENCIA: ADMIN_API_KEY no está configurado. Los endpoints admin fallarán.")
        print("   Asegúrate de tener un archivo .env con ADMIN_API_KEY=tu_token_aqui")
    
    if not MP_CLIENT_ID or not MP_CLIENT_SECRET:
        print("⚠️  ADVERTENCIA: Credenciales OAuth de MercadoPago no configuradas.")
        print("   Para OAuth necesitas: MP_CLIENT_ID y MP_CLIENT_SECRET")