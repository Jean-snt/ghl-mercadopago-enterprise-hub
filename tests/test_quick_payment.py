"""
Test rápido para verificar que el endpoint POST /payments/create funciona
"""
import requests
import json
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
ADMIN_TOKEN = os.getenv("ADMIN_API_KEY")

print("🧪 Test rápido: POST /payments/create")
print(f"📡 URL: {BASE_URL}/payments/create")
print(f"🔑 Token: {'✅ Configurado' if ADMIN_TOKEN else '❌ No configurado'}\n")

if not ADMIN_TOKEN:
    print("❌ Error: ADMIN_API_KEY no configurado en .env")
    exit(1)

# Datos del pago
payment_data = {
    "customer_email": "cliente@test.com",
    "customer_name": "Cliente Test",
    "ghl_contact_id": "ghl_123456",
    "amount": 100.50,
    "description": "Pago de prueba MVP",
    "created_by": "TestAdmin"
}

headers = {
    "Authorization": f"Bearer {ADMIN_TOKEN}",
    "Content-Type": "application/json"
}

print("📤 Enviando request...")
print(f"   Datos: {json.dumps(payment_data, indent=2)}\n")

try:
    response = requests.post(
        f"{BASE_URL}/payments/create",
        json=payment_data,
        headers=headers,
        timeout=10
    )
    
    print(f"📥 Response Status: {response.status_code}\n")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ ¡ÉXITO! Pago creado correctamente")
        print(f"\n📊 Datos del pago:")
        print(f"   Payment ID: {data['data']['payment_id']}")
        print(f"   Internal UUID: {data['data']['internal_uuid']}")
        print(f"   Checkout URL: {data['data']['checkout_url']}")
        print(f"   Preference ID: {data['data']['preference_id']}")
        print(f"   Mode: {data['data']['mode']}")
        
        if 'note' in data['data']:
            print(f"   Note: {data['data']['note']}")
        
        print(f"\n🎉 MVP Día 1 completado: El endpoint devuelve el init_point exitosamente")
        
    elif response.status_code == 500:
        print("❌ Error 500 - Error interno del servidor")
        error_data = response.json()
        print(f"   Detalle: {error_data.get('detail', 'No detail provided')}")
        print("\n🔍 Verifica:")
        print("   1. Que el servidor esté corriendo: uvicorn main:app --reload")
        print("   2. Que la base de datos esté inicializada: python recreate_db.py")
        print("   3. Los logs del servidor para más detalles")
        
    else:
        print(f"❌ Error {response.status_code}")
        print(f"   Response: {response.text}")
        
except requests.exceptions.ConnectionError:
    print("❌ Error de conexión")
    print("   El servidor no está corriendo en", BASE_URL)
    print("   Ejecuta: uvicorn main:app --reload")
    
except Exception as e:
    print(f"❌ Error inesperado: {str(e)}")

print("\n" + "="*60)