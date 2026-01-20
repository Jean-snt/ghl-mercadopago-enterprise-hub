#!/usr/bin/env python3
"""
Script para resolver alertas de seguridad desde la terminal
Permite marcar alertas como resueltas para que el dashboard vuelva a verde
"""
import sys
import os
import requests
import json
from datetime import datetime
from pathlib import Path

# Agregar el directorio raíz al path para imports
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

def get_admin_token():
    """Obtiene el token de administrador"""
    token = os.getenv("ADMIN_API_KEY")
    if not token:
        print("❌ Error: ADMIN_API_KEY no está configurado en .env")
        return None
    return token

def get_active_alerts(base_url: str, token: str):
    """Obtiene alertas activas (no resueltas)"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{base_url}/security/alerts?is_resolved=false", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("alerts", [])
        else:
            print(f"❌ Error obteniendo alertas: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error de conexión: {str(e)}")
        return []

def resolve_alert(base_url: str, token: str, alert_id: int, resolution_notes: str):
    """Resuelve una alerta específica"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        params = {"resolution_notes": resolution_notes}
        
        response = requests.put(
            f"{base_url}/security/alerts/{alert_id}/resolve",
            headers=headers,
            params=params
        )
        
        if response.status_code == 200:
            return True, "Alerta resuelta exitosamente"
        else:
            return False, f"Error {response.status_code}: {response.text}"
    except Exception as e:
        return False, f"Error de conexión: {str(e)}"

def check_dashboard_status(base_url: str, token: str):
    """Verifica el estado actual del dashboard"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{base_url}/api/v1/dashboard/overview", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            security = data.get("data", {}).get("security", {})
            threat_level = security.get("threat_level", "unknown")
            top_threats = security.get("top_threats", [])
            
            return threat_level, len(top_threats)
        else:
            return "error", 0
    except Exception as e:
        return "error", 0

def main():
    """Función principal del script"""
    print("🔧 Resolver Alertas de Seguridad - MercadoPago Enterprise")
    print("=" * 60)
    
    # Configuración
    base_url = "http://localhost:8000"
    token = get_admin_token()
    
    if not token:
        return 1
    
    # Verificar estado actual del dashboard
    print("📊 Verificando estado actual del dashboard...")
    threat_level, threat_count = check_dashboard_status(base_url, token)
    
    print(f"   Nivel de amenaza: {threat_level}")
    print(f"   Amenazas activas: {threat_count}")
    
    if threat_level == "low" and threat_count == 0:
        print("✅ El dashboard ya está en verde. No hay alertas activas.")
        return 0
    
    # Obtener alertas activas
    print("\n🚨 Obteniendo alertas activas...")
    alerts = get_active_alerts(base_url, token)
    
    if not alerts:
        print("✅ No hay alertas activas para resolver.")
        return 0
    
    print(f"📋 Encontradas {len(alerts)} alertas activas:")
    print("-" * 60)
    
    for alert in alerts:
        print(f"   ID: {alert['id']}")
        print(f"   Tipo: {alert['alert_type']}")
        print(f"   Severidad: {alert['severity']}")
        print(f"   Título: {alert['title']}")
        print(f"   Creada: {alert['created_at']}")
        print("-" * 60)
    
    # Modo interactivo o automático
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        # Modo automático: resolver todas las alertas
        print("\n🤖 Modo automático: Resolviendo todas las alertas...")
        
        for alert in alerts:
            resolution_notes = f"Auto-resolved by script at {datetime.utcnow().isoformat()}"
            success, message = resolve_alert(base_url, token, alert['id'], resolution_notes)
            
            if success:
                print(f"   ✅ Alerta {alert['id']} resuelta")
            else:
                print(f"   ❌ Error resolviendo alerta {alert['id']}: {message}")
    
    else:
        # Modo interactivo
        print("\n🔧 Modo interactivo:")
        print("Opciones:")
        print("  1. Resolver todas las alertas")
        print("  2. Resolver alerta específica")
        print("  3. Salir")
        
        try:
            choice = input("\nSelecciona una opción (1-3): ").strip()
            
            if choice == "1":
                # Resolver todas
                resolution_notes = input("Notas de resolución (opcional): ").strip()
                if not resolution_notes:
                    resolution_notes = f"Bulk resolution at {datetime.utcnow().isoformat()}"
                
                print("\n🔄 Resolviendo todas las alertas...")
                for alert in alerts:
                    success, message = resolve_alert(base_url, token, alert['id'], resolution_notes)
                    
                    if success:
                        print(f"   ✅ Alerta {alert['id']} ({alert['alert_type']}) resuelta")
                    else:
                        print(f"   ❌ Error resolviendo alerta {alert['id']}: {message}")
            
            elif choice == "2":
                # Resolver específica
                alert_id = input("ID de la alerta a resolver: ").strip()
                resolution_notes = input("Notas de resolución: ").strip()
                
                if not resolution_notes:
                    resolution_notes = f"Manual resolution at {datetime.utcnow().isoformat()}"
                
                try:
                    alert_id = int(alert_id)
                    success, message = resolve_alert(base_url, token, alert_id, resolution_notes)
                    
                    if success:
                        print(f"✅ {message}")
                    else:
                        print(f"❌ {message}")
                        
                except ValueError:
                    print("❌ ID de alerta inválido")
            
            elif choice == "3":
                print("👋 Saliendo...")
                return 0
            
            else:
                print("❌ Opción inválida")
                return 1
                
        except KeyboardInterrupt:
            print("\n👋 Operación cancelada")
            return 0
    
    # Verificar estado final
    print("\n📊 Verificando estado final del dashboard...")
    threat_level, threat_count = check_dashboard_status(base_url, token)
    
    print(f"   Nivel de amenaza: {threat_level}")
    print(f"   Amenazas activas: {threat_count}")
    
    if threat_level == "low" and threat_count == 0:
        print("🎉 ¡Dashboard vuelto a verde exitosamente!")
    else:
        print("⚠️  El dashboard aún muestra amenazas. Verifica si hay alertas adicionales.")
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)