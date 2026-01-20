#!/usr/bin/env python3
"""
Script de verificación completa del Proyecto Integrador Multi-tenant
Verifica que todas las funcionalidades estén operativas
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

def verify_multitenant_system():
    """
    Verificación completa del sistema multi-tenant
    """
    print("🚀 VERIFICACIÓN PROYECTO INTEGRADOR MULTI-TENANT")
    print("="*70)
    
    results = {
        "server_running": False,
        "database_migrated": False,
        "ghl_oauth_working": False,
        "client_created": False,
        "integrations_healthy": False,
        "dashboard_accessible": False
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
    
    # 2. Verificar migración de base de datos
    print("\n🗄️  2. Verificando migración multi-tenant...")
    try:
        headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
        response = requests.get(f"{BASE_URL}/api/v1/dashboard/overview", headers=headers, timeout=10)
        
        if response.status_code == 200:
            print("   ✅ Base de datos multi-tenant funcionando")
            results["database_migrated"] = True
        else:
            print(f"   ❌ Error accediendo base de datos: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error verificando base de datos: {str(e)}")
    
    # 3. Verificar OAuth GHL
    print("\n🔐 3. Verificando OAuth GoHighLevel...")
    try:
        response = requests.get(
            f"{BASE_URL}/oauth/ghl/authorize?client_id=test_verification",
            timeout=10
        )
        
        if response.status_code == 200:
            auth_data = response.json()
            if "authorization_url" in auth_data:
                print("   ✅ OAuth GHL generando URLs correctamente")
                print(f"   🔗 Client ID configurado: {auth_data.get('client_id')}")
                results["ghl_oauth_working"] = True
            else:
                print("   ❌ OAuth GHL no retorna URL válida")
        else:
            print(f"   ❌ Error en OAuth GHL: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error verificando OAuth GHL: {str(e)}")
    
    # 4. Verificar cliente simulado
    print("\n👤 4. Verificando cliente simulado...")
    try:
        headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
        response = requests.get(
            f"{BASE_URL}/oauth/ghl/status/cliente_prueba_oficial",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            client_data = response.json()
            if client_data.get("ghl_integration", {}).get("connected"):
                print("   ✅ Cliente simulado creado y conectado")
                print(f"   👤 Nombre: {client_data.get('client_name')}")
                print(f"   🏢 Location: {client_data['ghl_integration']['location_id']}")
                results["client_created"] = True
            else:
                print("   ⚠️  Cliente existe pero no está conectado a GHL")
        elif response.status_code == 404:
            print("   ⚠️  Cliente simulado no encontrado")
            print("   💡 Ejecuta: python scripts/simulate_ghl_oauth_callback.py")
        else:
            print(f"   ❌ Error verificando cliente: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error verificando cliente: {str(e)}")
    
    # 5. Verificar integraciones
    print("\n🔗 5. Verificando estado de integraciones...")
    try:
        headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
        response = requests.get(
            f"{BASE_URL}/api/v1/dashboard/metrics/realtime",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            metrics_data = response.json()
            integrations = metrics_data.get("data", {}).get("integrations", {}).get("value", {})
            
            ghl_status = integrations.get("ghl_status", "UNKNOWN")
            mp_status = integrations.get("mercadopago_status", "UNKNOWN")
            db_status = integrations.get("database_status", "UNKNOWN")
            active_clients = integrations.get("active_ghl_clients", 0)
            
            print(f"   🔗 GoHighLevel: {ghl_status}")
            print(f"   💳 MercadoPago: {mp_status}")
            print(f"   🗄️  Base de Datos: {db_status}")
            print(f"   👥 Clientes GHL Activos: {active_clients}")
            
            if ghl_status == "HEALTHY" and mp_status == "HEALTHY" and db_status == "HEALTHY":
                print("   ✅ Todas las integraciones están HEALTHY")
                results["integrations_healthy"] = True
            else:
                print("   ⚠️  Algunas integraciones no están HEALTHY")
        else:
            print(f"   ❌ Error obteniendo métricas: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error verificando integraciones: {str(e)}")
    
    # 6. Verificar dashboard
    print("\n📊 6. Verificando dashboard...")
    try:
        response = requests.get(f"{BASE_URL}/dashboard", timeout=10)
        if response.status_code == 200:
            print("   ✅ Dashboard accesible")
            print(f"   🌐 URL: {BASE_URL}/dashboard")
            results["dashboard_accessible"] = True
        else:
            print(f"   ❌ Dashboard no accesible: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error accediendo dashboard: {str(e)}")
    
    return results

def show_verification_summary(results):
    """
    Muestra resumen de la verificación
    """
    print("\n📋 RESUMEN DE VERIFICACIÓN")
    print("="*70)
    
    total_checks = len(results)
    passed_checks = sum(1 for result in results.values() if result)
    
    print(f"✅ Verificaciones pasadas: {passed_checks}/{total_checks}")
    print(f"📊 Porcentaje de éxito: {(passed_checks/total_checks)*100:.1f}%")
    
    print("\n📝 Detalle por componente:")
    status_map = {
        "server_running": "🖥️  Servidor corriendo",
        "database_migrated": "🗄️  Base de datos multi-tenant",
        "ghl_oauth_working": "🔐 OAuth GoHighLevel",
        "client_created": "👤 Cliente simulado",
        "integrations_healthy": "🔗 Integraciones HEALTHY",
        "dashboard_accessible": "📊 Dashboard accesible"
    }
    
    for key, description in status_map.items():
        status = "✅" if results[key] else "❌"
        print(f"   {status} {description}")
    
    # Estado general
    if passed_checks == total_checks:
        print(f"\n🎉 SISTEMA COMPLETAMENTE OPERATIVO")
        print("   ✅ Proyecto Integrador Multi-tenant funcionando al 100%")
        print("   ✅ Listo para producción con credenciales reales")
    elif passed_checks >= total_checks * 0.8:
        print(f"\n⚠️  SISTEMA MAYORMENTE OPERATIVO")
        print("   ✅ Funcionalidades principales funcionando")
        print("   ⚠️  Algunas verificaciones fallaron")
    else:
        print(f"\n❌ SISTEMA REQUIERE ATENCIÓN")
        print("   ❌ Múltiples componentes fallando")
        print("   🔧 Revisar configuración y dependencias")

def show_next_steps(results):
    """
    Muestra próximos pasos según el estado
    """
    print(f"\n🎯 PRÓXIMOS PASOS")
    print("="*70)
    
    if not results["server_running"]:
        print("🔧 Iniciar servidor:")
        print("   python -m uvicorn main:app --reload --port 8000")
        return
    
    if not results["client_created"]:
        print("🧪 Crear cliente simulado:")
        print("   python scripts/simulate_ghl_oauth_callback.py")
    
    if all(results.values()):
        print("🚀 Para usar en producción:")
        print("   1. Obtener subcuenta GoHighLevel activa")
        print("   2. Configurar credenciales reales en .env")
        print("   3. Usar URL de autorización real:")
        print("      GET /oauth/ghl/authorize?client_id=tu_cliente_real")
        print("   4. Completar flujo OAuth real con GHL")
        print("   5. Probar integración con contactos reales")
        
        print(f"\n📚 Documentación completa:")
        print("   - PROYECTO_INTEGRADOR_MULTITENANT_COMPLETADO.md")
        print("   - README.md")
        print("   - INDEX.md")
    else:
        print("🔧 Resolver problemas identificados arriba")
        print("🧪 Ejecutar verificación nuevamente")

def main():
    """Función principal"""
    print("🚀 MercadoPago Enterprise - Verificación Multi-tenant")
    print("="*70)
    
    results = verify_multitenant_system()
    show_verification_summary(results)
    show_next_steps(results)
    
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