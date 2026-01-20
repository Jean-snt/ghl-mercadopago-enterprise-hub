"""
Script simple para verificar la configuración del token
"""
import os
from dotenv import load_dotenv
import requests

# Cargar variables de entorno
load_dotenv()

# Obtener configuración
ADMIN_TOKEN = os.getenv("ADMIN_API_KEY")
BASE_URL = "http://localhost:8000"

print("🔧 Verificación de configuración:")
print(f"   ADMIN_API_KEY desde .env: {ADMIN_TOKEN}")
print(f"   BASE_URL: {BASE_URL}")
print()

if not ADMIN_TOKEN:
    print("❌ Error: ADMIN_API_KEY no está configurado en .env")
    exit(1)

# Test simple del health endpoint (no requiere auth)
print("🏥 Testing health endpoint...")
try:
    response = requests.get(f"{BASE_URL}/health")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print("   ✅ Servidor funcionando")
    else:
        print("   ❌ Servidor no responde correctamente")
        exit(1)
except Exception as e:
    print(f"   ❌ Error conectando al servidor: {e}")
    exit(1)

# Test del endpoint con autenticación
print("\n🔐 Testing endpoint con autenticación...")
headers = {
    "Authorization": f"Bearer {ADMIN_TOKEN}",
    "Content-Type": "application/json"
}

try:
    response = requests.get(f"{BASE_URL}/metrics", headers=headers)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        print("   ✅ Autenticación exitosa")
        data = response.json()
        print(f"   📊 Total pagos: {data.get('payments', {}).get('total', 0)}")
    elif response.status_code == 401:
        print("   ❌ Token inválido")
        print(f"   Response: {response.text}")
    else:
        print(f"   ❌ Error inesperado: {response.text}")
        
except Exception as e:
    print(f"   ❌ Error en request: {e}")

print("\n📋 Si ves errores:")
print("   1. Verifica que el servidor esté corriendo: uvicorn main:app --reload")
print("   2. Verifica que el archivo .env tenga ADMIN_API_KEY=test_admin_token_123")
print("   3. Reinicia el servidor después de cambiar .env")