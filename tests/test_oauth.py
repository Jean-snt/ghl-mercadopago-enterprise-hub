"""
Script de testing para funcionalidades OAuth de MercadoPago
"""
import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de testing
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
ADMIN_TOKEN = os.getenv("ADMIN_API_KEY")

def test_oauth_flow():
    """Test completo del flujo OAuth"""
    print("🔐 Testing OAuth Flow MercadoPago\n")
    
    if not ADMIN_TOKEN:
        print("❌ Error: ADMIN_API_KEY no configurado")
        return
    
    headers = {
        "Authorization": f"Bearer {ADMIN_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # 1. Iniciar autorización OAuth
    print("1️⃣ Iniciando autorización OAuth...")
    
    oauth_request = {
        "client_id": "test_client_123",
        "client_name": "Test Company",
        "client_email": "test@company.com"
    }
    
    response = requests.post(f"{BASE_URL}/oauth/authorize", json=oauth_request, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Autorización iniciada exitosamente")
        print(f"   Client ID: {data['client_id']}")
        print(f"   Authorization URL: {data['authorization_url']}")
        print(f"   State: {data['state']}")
        
        print("\n📋 Pasos siguientes:")
        print("   1. El usuario debe visitar la authorization_url")
        print("   2. Autorizar la aplicación en MercadoPago")
        print("   3. MercadoPago redirigirá a /oauth/callback con el código")
        
        return data
    else:
        print(f"❌ Error iniciando OAuth: {response.status_code}")
        print(response.text)
        return None

def test_oauth_accounts():
    """Test de listado de cuentas OAuth"""
    print("\n2️⃣ Listando cuentas OAuth...")
    
    headers = {
        "Authorization": f"Bearer {ADMIN_TOKEN}"
    }
    
    response = requests.get(f"{BASE_URL}/oauth/accounts", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Cuentas encontradas: {len(data['accounts'])}")
        
        for account in data['accounts']:
            print(f"   📱 Account ID: {account['id']}")
            print(f"      Client ID: {account['client_id']}")
            print(f"      MP User ID: {account['mp_user_id']}")
            print(f"      Active: {account['is_active']}")
            print(f"      Expires: {account['expires_at']}")
            print(f"      Needs Refresh: {account['needs_refresh']}")
            print()
    else:
        print(f"❌ Error listando cuentas: {response.status_code}")
        print(response.text)

def test_payment_with_oauth():
    """Test de creación de pago usando OAuth"""
    print("3️⃣ Testing pago con OAuth...")
    
    headers = {
        "Authorization": f"Bearer {ADMIN_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payment_data = {
        "customer_email": "customer@test.com",
        "customer_name": "Test Customer",
        "ghl_contact_id": "ghl_contact_456",
        "amount": 150.75,
        "description": "Test Payment with OAuth",
        "created_by": "TestAdmin",
        "client_id": "test_client_123"  # Usar OAuth de este cliente
    }
    
    response = requests.post(f"{BASE_URL}/payments/create", json=payment_data, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Pago creado con OAuth")
        print(f"   Payment ID: {data['data']['payment_id']}")
        print(f"   OAuth Client: {data['data'].get('oauth_client', 'N/A')}")
        print(f"   MP Account ID: {data['data'].get('mp_account_id', 'N/A')}")
        print(f"   Mode: {data['data']['mode']}")
        return data['data']
    else:
        print(f"❌ Error creando pago: {response.status_code}")
        print(response.text)
        return None

def test_token_refresh():
    """Test de renovación manual de token"""
    print("\n4️⃣ Testing renovación de token...")
    
    # Primero obtener una cuenta para renovar
    headers = {
        "Authorization": f"Bearer {ADMIN_TOKEN}"
    }
    
    response = requests.get(f"{BASE_URL}/oauth/accounts", headers=headers)
    
    if response.status_code == 200:
        accounts = response.json()['accounts']
        if accounts:
            account_id = accounts[0]['id']
            print(f"   Renovando token para account ID: {account_id}")
            
            refresh_response = requests.post(
                f"{BASE_URL}/oauth/refresh/{account_id}", 
                headers=headers
            )
            
            if refresh_response.status_code == 200:
                data = refresh_response.json()
                print(f"✅ Token renovado: {data['success']}")
                if data['success']:
                    print(f"   Nueva expiración: {data['expires_at']}")
                else:
                    print(f"   Razón del fallo: {data['message']}")
            else:
                print(f"❌ Error renovando token: {refresh_response.status_code}")
        else:
            print("⚠️  No hay cuentas OAuth para renovar")
    else:
        print(f"❌ Error obteniendo cuentas: {response.status_code}")

def simulate_oauth_callback():
    """Simula un callback OAuth (solo para testing)"""
    print("\n🧪 Simulando OAuth callback...")
    print("   (En producción, esto vendría desde MercadoPago)")
    
    # Esto es solo para mostrar cómo funcionaría
    callback_url = f"{BASE_URL}/oauth/callback"
    params = {
        "code": "MOCK_AUTHORIZATION_CODE_123",
        "state": "test_client_123:1234567890"
    }
    
    print(f"   Callback URL: {callback_url}")
    print(f"   Parámetros: {params}")
    print("   ⚠️  Nota: Esto requiere credenciales reales de MercadoPago para funcionar")

if __name__ == "__main__":
    print("🚀 Iniciando tests OAuth MercadoPago Enterprise\n")
    print(f"📡 Base URL: {BASE_URL}")
    print(f"🔑 Admin Token: {'✅ Configurado' if ADMIN_TOKEN else '❌ No configurado'}")
    print()
    
    if not ADMIN_TOKEN:
        print("❌ Configure ADMIN_API_KEY en .env para continuar")
        exit(1)
    
    # Ejecutar tests
    oauth_data = test_oauth_flow()
    test_oauth_accounts()
    test_payment_with_oauth()
    test_token_refresh()
    simulate_oauth_callback()
    
    print("\n✅ Tests OAuth completados")
    print("\n📋 Para usar OAuth en producción:")
    print("   1. Registra tu aplicación en MercadoPago Developers")
    print("   2. Configura MP_CLIENT_ID y MP_CLIENT_SECRET")
    print("   3. Configura MP_REDIRECT_URI apuntando a tu dominio")
    print("   4. Usa /oauth/authorize para iniciar el flujo")
    print("   5. Los usuarios autorizarán en MercadoPago")
    print("   6. El callback procesará automáticamente los tokens")
    print("   7. Usa client_id en payments/create para usar tokens OAuth")