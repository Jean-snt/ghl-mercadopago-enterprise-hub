#!/usr/bin/env python3
"""
Script para simular el callback OAuth de GoHighLevel
Simula el flujo completo sin necesidad de subcuenta GHL activa
"""
import sys
import os
import requests
import json
import time
from pathlib import Path

# Agregar el directorio raíz al path para imports
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# Configuración
BASE_URL = "http://localhost:8000"
ADMIN_TOKEN = os.getenv("ADMIN_API_KEY", "junior123")

def simulate_ghl_oauth_callback():
    """
    Simula el callback OAuth de GoHighLevel con datos mock
    """
    print("🚀 SIMULACIÓN CALLBACK OAUTH GOHIGHLEVEL")
    print("="*60)
    
    # Datos de simulación
    client_id = "cliente_prueba_oficial"
    mock_auth_code = "mock_auth_code_12345_ghl_simulation"
    state = client_id
    
    print(f"📋 Datos de simulación:")
    print(f"   Client ID: {client_id}")
    print(f"   Auth Code: {mock_auth_code}")
    print(f"   State: {state}")
    print(f"   Callback URL: {BASE_URL}/oauth/callback/callback")
    
    # 1. Verificar que el servidor esté corriendo
    print(f"\n🔍 1. Verificando servidor...")
    try:
        response = requests.get(f"{BASE_URL}/dashboard", timeout=5)
        if response.status_code == 200:
            print("   ✅ Servidor corriendo correctamente")
        else:
            print("   ⚠️  Servidor responde pero con error")
    except Exception as e:
        print(f"   ❌ Servidor no disponible: {str(e)}")
        print("   💡 Ejecuta: python -m uvicorn main:app --reload --port 8000")
        return False
    
    # 2. Simular callback OAuth (GET request como hace GHL)
    print(f"\n📞 2. Simulando callback OAuth...")
    
    callback_params = {
        "code": mock_auth_code,
        "state": state
    }
    
    try:
        print(f"   🔗 Enviando GET a /oauth/callback/callback")
        print(f"   📊 Parámetros: {callback_params}")
        
        response = requests.get(
            f"{BASE_URL}/oauth/callback/callback",
            params=callback_params,
            timeout=10
        )
        
        print(f"   📈 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            callback_data = response.json()
            print(f"   ✅ Callback procesado exitosamente")
            print(f"   🎯 Cliente: {callback_data.get('client_id')}")
            print(f"   🏢 Location ID: {callback_data.get('location_id')}")
            print(f"   🔑 Scope: {callback_data.get('scope')}")
            print(f"   ⏰ Expira: {callback_data.get('expires_at')}")
        else:
            print(f"   ❌ Error en callback: {response.status_code}")
            print(f"   📄 Respuesta: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error simulando callback: {str(e)}")
        return False
    
    # 3. Verificar que el cliente se creó correctamente
    print(f"\n🔍 3. Verificando cliente creado...")
    
    try:
        headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
        response = requests.get(
            f"{BASE_URL}/oauth/ghl/status/{client_id}",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            status_data = response.json()
            print(f"   ✅ Cliente encontrado en base de datos")
            print(f"   👤 Nombre: {status_data.get('client_name')}")
            print(f"   🏢 Empresa: {status_data.get('company_name')}")
            print(f"   🔗 GHL conectado: {status_data['ghl_integration']['connected']}")
            print(f"   🏢 Location ID: {status_data['ghl_integration']['location_id']}")
            print(f"   ⏰ Token expira: {status_data['ghl_integration']['expires_at']}")
            print(f"   🔄 Necesita refresh: {status_data['ghl_integration']['needs_refresh']}")
        else:
            print(f"   ❌ Cliente no encontrado: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error verificando cliente: {str(e)}")
        return False
    
    # 4. Probar conexión GHL (debería funcionar con tokens mock)
    print(f"\n🧪 4. Probando conexión GHL...")
    
    try:
        headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
        response = requests.post(
            f"{BASE_URL}/oauth/ghl/test/{client_id}",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            test_data = response.json()
            if test_data.get("success"):
                print(f"   ✅ Conexión GHL simulada exitosa")
                print(f"   📊 Mensaje: {test_data.get('message')}")
            else:
                print(f"   ⚠️  Conexión falló: {test_data.get('error')}")
        else:
            print(f"   ❌ Error probando conexión: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error en prueba de conexión: {str(e)}")
    
    # 5. Verificar dashboard (debería mostrar GHL como HEALTHY)
    print(f"\n📊 5. Verificando estado del dashboard...")
    
    try:
        headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
        response = requests.get(
            f"{BASE_URL}/api/v1/dashboard/overview",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            dashboard_data = response.json()
            print(f"   ✅ Dashboard accesible")
            print(f"   🔒 Threat Level: {dashboard_data.get('threat_level', 'N/A')}")
            print(f"   📊 Total Payments: {dashboard_data.get('total_payments', 0)}")
            print(f"   💰 Total Amount: ${dashboard_data.get('total_amount', 0)}")
            
            # Verificar métricas en tiempo real
            response = requests.get(
                f"{BASE_URL}/api/v1/dashboard/metrics/realtime",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                metrics_data = response.json()
                ghl_status = metrics_data.get('integrations', {}).get('ghl_status', 'UNKNOWN')
                print(f"   🔗 GHL Status: {ghl_status}")
                
                if ghl_status == "HEALTHY":
                    print(f"   🎉 ¡GHL ahora aparece como HEALTHY!")
                elif ghl_status == "DEGRADED":
                    print(f"   ⚠️  GHL aún aparece como DEGRADED")
                else:
                    print(f"   ❓ Estado GHL desconocido: {ghl_status}")
            
        else:
            print(f"   ❌ Error accediendo dashboard: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error verificando dashboard: {str(e)}")
    
    return True

def show_next_steps():
    """
    Muestra los próximos pasos después de la simulación
    """
    print(f"\n🎯 PRÓXIMOS PASOS")
    print("="*60)
    print("✅ Simulación OAuth completada exitosamente")
    print("✅ Cliente mock creado en base de datos")
    print("✅ Tokens mock generados y guardados")
    print("✅ Dashboard debería mostrar GHL como HEALTHY")
    
    print(f"\n📋 Para verificar manualmente:")
    print(f"   🌐 Dashboard: http://localhost:8000/dashboard")
    print(f"   📊 Métricas: http://localhost:8000/api/v1/dashboard/metrics/realtime")
    print(f"   👤 Estado cliente: http://localhost:8000/oauth/ghl/status/cliente_prueba_oficial")
    
    print(f"\n🔧 Comandos útiles:")
    print(f"   # Ver estado del cliente")
    print(f"   curl -H 'Authorization: Bearer junior123' \\")
    print(f"     'http://localhost:8000/oauth/ghl/status/cliente_prueba_oficial'")
    print(f"")
    print(f"   # Probar conexión GHL")
    print(f"   curl -X POST -H 'Authorization: Bearer junior123' \\")
    print(f"     'http://localhost:8000/oauth/ghl/test/cliente_prueba_oficial'")
    
    print(f"\n🚀 Para producción:")
    print("   1. Obtener subcuenta GHL activa")
    print("   2. Usar URL de autorización real")
    print("   3. Completar flujo OAuth real")
    print("   4. Reemplazar tokens mock con tokens reales")

def main():
    """Función principal"""
    print("🚀 MercadoPago Enterprise - Simulación OAuth GoHighLevel")
    print("="*70)
    
    success = simulate_ghl_oauth_callback()
    
    if success:
        show_next_steps()
        print(f"\n🎉 SIMULACIÓN COMPLETADA EXITOSAMENTE")
        return 0
    else:
        print(f"\n❌ SIMULACIÓN FALLÓ")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)