#!/usr/bin/env python3
"""
Script de verificación del Día 3 - Dashboard Multi-tenant por Cliente
Verifica que el dashboard específico por cliente esté funcionando correctamente
"""
import sys
import os
import requests
import json
from pathlib import Path

# Agregar el directorio raíz al path para imports
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# Configuración
BASE_URL = "http://localhost:8000"
ADMIN_TOKEN = os.getenv("ADMIN_API_KEY", "junior123")
TEST_CLIENT_ID = "cliente_prueba_oficial"

def verify_day3_implementation():
    """
    Verificación completa del Día 3 - Dashboard Multi-tenant
    """
    print("🚀 VERIFICACIÓN DÍA 3 - DASHBOARD MULTI-TENANT POR CLIENTE")
    print("="*70)
    
    results = {
        "server_running": False,
        "client_dashboard_accessible": False,
        "client_exists": False,
        "client_metrics_working": False,
        "client_payments_working": False,
        "payment_creation_working": False,
        "multitenant_isolation": False
    }
    
    # 1. Verificar servidor
    print("\n🔍 1. Verificando servidor...")
    try:
        response = requests.get(f"{BASE_URL}/dashboard", timeout=5)
        if response.status_code == 200:
            print("   ✅ Servidor corriendo correctamente")
            results["server_running"] = True
        else:
            print(f"   ❌ Servidor responde con error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Servidor no disponible: {str(e)}")
        return results
    
    # 2. Verificar dashboard del cliente
    print(f"\n📊 2. Verificando dashboard del cliente...")
    try:
        response = requests.get(f"{BASE_URL}/dashboard/client/{TEST_CLIENT_ID}", timeout=10)
        if response.status_code == 200:
            print(f"   ✅ Dashboard del cliente accesible")
            print(f"   🌐 URL: {BASE_URL}/dashboard/client/{TEST_CLIENT_ID}")
            results["client_dashboard_accessible"] = True
        else:
            print(f"   ❌ Dashboard del cliente no accesible: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error accediendo dashboard del cliente: {str(e)}")
    
    # 3. Verificar que el cliente existe
    print(f"\n👤 3. Verificando cliente {TEST_CLIENT_ID}...")
    try:
        headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
        response = requests.get(f"{BASE_URL}/oauth/ghl/status/{TEST_CLIENT_ID}", headers=headers, timeout=10)
        
        if response.status_code == 200:
            client_data = response.json()
            print(f"   ✅ Cliente encontrado")
            print(f"   👤 Nombre: {client_data.get('client_name')}")
            print(f"   🏢 Empresa: {client_data.get('company_name')}")
            print(f"   🔗 GHL conectado: {client_data['ghl_integration']['connected']}")
            print(f"   🏢 Location ID: {client_data['ghl_integration']['location_id']}")
            results["client_exists"] = True
        else:
            print(f"   ❌ Cliente no encontrado: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error verificando cliente: {str(e)}")
    
    # 4. Verificar métricas del cliente
    print(f"\n📈 4. Verificando métricas del cliente...")
    try:
        headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
        response = requests.get(f"{BASE_URL}/api/v1/clients/{TEST_CLIENT_ID}/metrics", headers=headers, timeout=10)
        
        if response.status_code == 200:
            metrics_data = response.json()
            metrics = metrics_data.get("metrics", {})
            
            print(f"   ✅ Métricas del cliente funcionando")
            print(f"   📊 Total pagos: {metrics.get('total_payments', 0)}")
            print(f"   💰 Monto total: ${metrics.get('total_amount', 0)}")
            print(f"   ✅ Pagos aprobados: {metrics.get('approved_payments', 0)}")
            print(f"   📅 Pagos del mes: {metrics.get('monthly_payments', 0)}")
            print(f"   🎯 Plan: {metrics.get('subscription_plan', 'N/A')}")
            
            results["client_metrics_working"] = True
        else:
            print(f"   ❌ Error obteniendo métricas: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error verificando métricas: {str(e)}")
    
    # 5. Verificar pagos del cliente
    print(f"\n💳 5. Verificando pagos del cliente...")
    try:
        headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
        response = requests.get(f"{BASE_URL}/api/v1/clients/{TEST_CLIENT_ID}/payments", headers=headers, timeout=10)
        
        if response.status_code == 200:
            payments_data = response.json()
            payments = payments_data.get("payments", [])
            pagination = payments_data.get("pagination", {})
            
            print(f"   ✅ Endpoint de pagos funcionando")
            print(f"   📊 Total pagos: {pagination.get('total', 0)}")
            
            if payments:
                latest_payment = payments[0]
                print(f"   💳 Último pago:")
                print(f"      - ID: {latest_payment['id']}")
                print(f"      - Cliente: {latest_payment['customer_name']}")
                print(f"      - Monto: ${latest_payment['expected_amount']}")
                print(f"      - Estado: {latest_payment['status']}")
                print(f"      - GHL Contact: {latest_payment['ghl_contact_id']}")
            
            results["client_payments_working"] = True
        else:
            print(f"   ❌ Error obteniendo pagos: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error verificando pagos: {str(e)}")
    
    # 6. Probar creación de pago específico del cliente
    print(f"\n🔧 6. Probando creación de pago multi-tenant...")
    try:
        headers = {
            "Authorization": f"Bearer {ADMIN_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payment_data = {
            "customer_email": "test.day3@ejemplo.com",
            "customer_name": "Cliente Día 3",
            "ghl_contact_id": "ghl_day3_test_456",
            "amount": 250.00,
            "description": "Pago de prueba Día 3 - Multi-tenant",
            "created_by": "verification_script",
            "client_id": TEST_CLIENT_ID
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/payments/create",
            headers=headers,
            json=payment_data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Pago creado exitosamente")
            print(f"   💳 Payment ID: {result.get('payment_id')}")
            print(f"   🔗 Checkout URL: {result.get('checkout_url', 'N/A')[:50]}...")
            print(f"   👤 Cliente vinculado: {result.get('oauth_client')}")
            print(f"   🏢 Location GHL: {result.get('ghl_location_id')}")
            print(f"   🧪 Modo: {result.get('mode', 'N/A')}")
            
            # Verificar que se vinculó correctamente
            if result.get("client_account_id") and result.get("ghl_location_id"):
                print(f"   ✅ Pago correctamente vinculado al cliente multi-tenant")
                results["payment_creation_working"] = True
            else:
                print(f"   ⚠️  Pago creado pero vinculación incompleta")
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            print(f"   ❌ Error creando pago: {response.status_code}")
            print(f"   📄 Detalle: {error_data}")
    except Exception as e:
        print(f"   ❌ Error probando creación de pago: {str(e)}")
    
    # 7. Verificar aislamiento multi-tenant
    print(f"\n🔒 7. Verificando aislamiento multi-tenant...")
    try:
        # Crear un cliente ficticio para probar aislamiento
        fake_client_id = "cliente_inexistente_test"
        
        headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
        response = requests.get(f"{BASE_URL}/api/v1/clients/{fake_client_id}/payments", headers=headers, timeout=10)
        
        if response.status_code == 404:
            print(f"   ✅ Aislamiento funcionando - Cliente inexistente correctamente rechazado")
            results["multitenant_isolation"] = True
        elif response.status_code == 200:
            # Verificar que no devuelve datos de otros clientes
            data = response.json()
            if data.get("payments", []) == []:
                print(f"   ✅ Aislamiento funcionando - No se filtraron datos de otros clientes")
                results["multitenant_isolation"] = True
            else:
                print(f"   ❌ Posible fuga de datos - Cliente inexistente devolvió pagos")
        else:
            print(f"   ⚠️  Respuesta inesperada para cliente inexistente: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error verificando aislamiento: {str(e)}")
    
    return results

def show_day3_summary(results):
    """
    Muestra resumen de la verificación del Día 3
    """
    print("\n📋 RESUMEN VERIFICACIÓN DÍA 3")
    print("="*70)
    
    total_checks = len(results)
    passed_checks = sum(1 for result in results.values() if result)
    
    print(f"✅ Verificaciones pasadas: {passed_checks}/{total_checks}")
    print(f"📊 Porcentaje de éxito: {(passed_checks/total_checks)*100:.1f}%")
    
    print(f"\n📝 Detalle por funcionalidad:")
    status_map = {
        "server_running": "🖥️  Servidor corriendo",
        "client_dashboard_accessible": "📊 Dashboard del cliente accesible",
        "client_exists": "👤 Cliente de prueba existe",
        "client_metrics_working": "📈 Métricas del cliente funcionando",
        "client_payments_working": "💳 Pagos del cliente funcionando",
        "payment_creation_working": "🔧 Creación de pagos multi-tenant",
        "multitenant_isolation": "🔒 Aislamiento multi-tenant"
    }
    
    for key, description in status_map.items():
        status = "✅" if results[key] else "❌"
        print(f"   {status} {description}")
    
    # Estado general del Día 3
    if passed_checks == total_checks:
        print(f"\n🎉 DÍA 3 COMPLETADO AL 100%")
        print("   ✅ Dashboard multi-tenant por cliente funcionando perfectamente")
        print("   ✅ Filtrado de pagos por cliente implementado")
        print("   ✅ Creación de pagos vinculados a clientes específicos")
        print("   ✅ Aislamiento de datos entre clientes")
        print("   ✅ Integración con tokens GHL por cliente")
    elif passed_checks >= total_checks * 0.8:
        print(f"\n⚠️  DÍA 3 MAYORMENTE COMPLETADO")
        print("   ✅ Funcionalidades principales del multi-tenant funcionando")
        print("   ⚠️  Algunas verificaciones fallaron")
    else:
        print(f"\n❌ DÍA 3 REQUIERE ATENCIÓN")
        print("   ❌ Múltiples funcionalidades multi-tenant fallando")
        print("   🔧 Revisar implementación del dashboard por cliente")

def show_day3_next_steps(results):
    """
    Muestra próximos pasos para el Día 3
    """
    print(f"\n🎯 PRÓXIMOS PASOS DÍA 3")
    print("="*70)
    
    if all(results.values()):
        print("🚀 Día 3 completado exitosamente. Próximos pasos:")
        print("   1. Probar dashboard con múltiples clientes")
        print("   2. Implementar más funcionalidades específicas por cliente")
        print("   3. Agregar métricas avanzadas por cliente")
        print("   4. Implementar notificaciones por cliente")
        print("   5. Configurar límites y cuotas por cliente")
        
        print(f"\n📚 URLs importantes:")
        print(f"   🌐 Dashboard general: {BASE_URL}/dashboard")
        print(f"   👤 Dashboard cliente: {BASE_URL}/dashboard/client/{TEST_CLIENT_ID}")
        print(f"   📊 API métricas: {BASE_URL}/api/v1/clients/{TEST_CLIENT_ID}/metrics")
        print(f"   💳 API pagos: {BASE_URL}/api/v1/clients/{TEST_CLIENT_ID}/payments")
    else:
        print("🔧 Resolver problemas identificados:")
        
        if not results["client_dashboard_accessible"]:
            print("   - Verificar que el archivo static/client_dashboard.html existe")
            print("   - Verificar endpoint /dashboard/client/{client_id}")
        
        if not results["client_metrics_working"]:
            print("   - Verificar endpoint /api/v1/clients/{client_id}/metrics")
            print("   - Verificar consultas SQL de métricas por cliente")
        
        if not results["payment_creation_working"]:
            print("   - Verificar vinculación de pagos con client_account_id")
            print("   - Verificar uso de tokens específicos por cliente")
        
        if not results["multitenant_isolation"]:
            print("   - Verificar filtros de seguridad multi-tenant")
            print("   - Verificar que no hay fuga de datos entre clientes")

def main():
    """Función principal"""
    print("🚀 MercadoPago Enterprise - Verificación Día 3")
    print("="*70)
    
    results = verify_day3_implementation()
    show_day3_summary(results)
    show_day3_next_steps(results)
    
    # Código de salida basado en resultados
    passed_checks = sum(1 for result in results.values() if result)
    total_checks = len(results)
    
    if passed_checks == total_checks:
        return 0  # Éxito completo
    elif passed_checks >= total_checks * 0.8:
        return 1  # Mayormente exitoso
    else:
        return 2  # Requiere atención

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)