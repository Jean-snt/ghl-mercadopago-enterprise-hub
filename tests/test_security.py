"""
Script de testing para validar las funcionalidades de seguridad
"""
import requests
import json
import hmac
import hashlib
import os
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de testing
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
ADMIN_TOKEN = os.getenv("ADMIN_API_KEY")
WEBHOOK_SECRET = os.getenv("MP_WEBHOOK_SECRET")

# Validar que las variables estén configuradas
if not ADMIN_TOKEN:
    print("❌ Error: ADMIN_API_KEY no está configurado en las variables de entorno")
    print("   Por favor, configura tu archivo .env con:")
    print("   ADMIN_API_KEY=tu_token_admin_aqui")
    exit(1)

if not WEBHOOK_SECRET:
    print("⚠️  Advertencia: MP_WEBHOOK_SECRET no está configurado")
    print("   Los tests de webhook con firma HMAC fallarán")
    WEBHOOK_SECRET = "test_secret"  # Fallback para testing básico

def test_payment_creation():
    """Test de creación de pago con auditoría"""
    print("🧪 Testing: Creación de pago...")
    
    headers = {
        "Authorization": f"Bearer {ADMIN_TOKEN}",
        "Content-Type": "application/json",
        "x-correlation-id": f"test_{datetime.now().timestamp()}"
    }
    
    payload = {
        "customer_email": "test@example.com",
        "customer_name": "Test Customer",
        "ghl_contact_id": "test_contact_123",
        "amount": 100.50,
        "description": "Test Payment",
        "created_by": "TestAdmin"
    }
    
    response = requests.post(f"{BASE_URL}/payments/create", json=payload, headers=headers)
    
    if response.status_code == 200:
        print("✅ Pago creado exitosamente")
        data = response.json()
        print(f"   Payment ID: {data['data']['payment_id']}")
        print(f"   Internal UUID: {data['data']['internal_uuid']}")
        return data['data']
    else:
        print(f"❌ Error creando pago: {response.status_code}")
        print(response.text)
        return None

def test_webhook_security(payment_data):
    """Test de seguridad de webhook"""
    print("\n🧪 Testing: Seguridad de webhook...")
    
    # Simular webhook de MercadoPago
    webhook_payload = {
        "id": 12345,
        "live_mode": True,
        "type": "payment",
        "date_created": "2024-01-15T10:00:00.000-04:00",
        "application_id": 123456789,
        "user_id": 987654321,
        "version": 1,
        "api_version": "v1",
        "action": "payment.updated",
        "data": {
            "id": "67890"  # Este será el MP payment ID
        }
    }
    
    payload_str = json.dumps(webhook_payload)
    
    # Generar firma HMAC
    signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload_str.encode(),
        hashlib.sha256
    ).hexdigest()
    
    headers = {
        "Content-Type": "application/json",
        "x-signature": signature,
        "x-correlation-id": f"webhook_test_{datetime.now().timestamp()}"
    }
    
    response = requests.post(f"{BASE_URL}/webhook/mercadopago", 
                           data=payload_str, headers=headers)
    
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        print("✅ Webhook procesado")
        print(f"   Response: {response.json()}")
    else:
        print(f"❌ Error en webhook: {response.text}")

def test_duplicate_webhook():
    """Test de protección contra webhooks duplicados"""
    print("\n🧪 Testing: Protección contra duplicados...")
    
    # Simular el mismo webhook dos veces
    webhook_payload = {
        "id": 12345,
        "type": "payment",
        "data": {"id": "67890"}  # Mismo payment ID
    }
    
    payload_str = json.dumps(webhook_payload)
    signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload_str.encode(),
        hashlib.sha256
    ).hexdigest()
    
    headers = {
        "Content-Type": "application/json",
        "x-signature": signature
    }
    
    # Primera llamada
    response1 = requests.post(f"{BASE_URL}/webhook/mercadopago", 
                            data=payload_str, headers=headers)
    
    # Segunda llamada (duplicada)
    response2 = requests.post(f"{BASE_URL}/webhook/mercadopago", 
                            data=payload_str, headers=headers)
    
    print(f"   Primera llamada: {response1.status_code}")
    print(f"   Segunda llamada: {response2.status_code}")
    
    if response2.status_code == 200:
        data = response2.json()
        if data.get('data', {}).get('status') == 'duplicate':
            print("✅ Duplicado detectado correctamente")
        else:
            print("❌ Duplicado no detectado")

def test_amount_mismatch():
    """Test de validación de montos"""
    print("\n🧪 Testing: Validación de montos...")
    
    # Este test requeriría mockear la respuesta de MercadoPago API
    # para simular un monto diferente al esperado
    print("   (Requiere mock de MercadoPago API para testing completo)")

def test_audit_logs():
    """Test de consulta de logs de auditoría"""
    print("\n🧪 Testing: Logs de auditoría...")
    
    headers = {
        "Authorization": f"Bearer {ADMIN_TOKEN}"
    }
    
    response = requests.get(f"{BASE_URL}/audit/logs?limit=10", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Logs obtenidos: {len(data['logs'])} registros")
        if data['logs']:
            print(f"   Último log: {data['logs'][0]['action']} - {data['logs'][0]['description']}")
    else:
        print(f"❌ Error obteniendo logs: {response.status_code}")

def test_security_alerts():
    """Test de consulta de alertas de seguridad"""
    print("\n🧪 Testing: Alertas de seguridad...")
    
    headers = {
        "Authorization": f"Bearer {ADMIN_TOKEN}"
    }
    
    response = requests.get(f"{BASE_URL}/security/alerts", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Alertas obtenidas: {len(data['alerts'])} registros")
        critical_alerts = [a for a in data['alerts'] if a['severity'] == 'CRITICAL']
        print(f"   Alertas críticas: {len(critical_alerts)}")
    else:
        print(f"❌ Error obteniendo alertas: {response.status_code}")

def test_metrics():
    """Test de métricas del sistema"""
    print("\n🧪 Testing: Métricas del sistema...")
    
    headers = {
        "Authorization": f"Bearer {ADMIN_TOKEN}"
    }
    
    response = requests.get(f"{BASE_URL}/metrics", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Métricas obtenidas:")
        print(f"   Total pagos: {data['payments']['total']}")
        print(f"   Pagos aprobados: {data['payments']['approved']}")
        print(f"   Alertas no resueltas: {data['security']['unresolved_alerts']}")
        print(f"   Alertas críticas: {data['security']['critical_alerts']}")
    else:
        print(f"❌ Error obteniendo métricas: {response.status_code}")

if __name__ == "__main__":
    print("🚀 Iniciando tests de seguridad MercadoPago Enterprise\n")
    print(f"📡 Base URL: {BASE_URL}")
    print(f"🔑 Admin Token: {ADMIN_TOKEN[:10]}..." if ADMIN_TOKEN else "❌ No configurado")
    print(f"🔐 Webhook Secret: {'✅ Configurado' if WEBHOOK_SECRET else '❌ No configurado'}")
    print()
    
    # Ejecutar tests
    payment_data = test_payment_creation()
    
    if payment_data:
        test_webhook_security(payment_data)
        test_duplicate_webhook()
        test_amount_mismatch()
        test_audit_logs()
        test_security_alerts()
        test_metrics()
    
    print("\n✅ Tests de seguridad completados")
    print("\n📋 Para producción, asegúrate de:")
    print("   - Configurar todas las variables de entorno")
    print("   - Usar PostgreSQL en lugar de SQLite")
    print("   - Implementar HTTPS")
    print("   - Configurar monitoreo de alertas críticas")
    print("   - Establecer backup automático de logs")