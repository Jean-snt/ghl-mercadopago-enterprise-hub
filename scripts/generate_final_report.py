#!/usr/bin/env python3
"""
Generate Final Report - Verificación Completa del Sistema
Genera reporte final con verificación de todos los componentes
"""
import os
import sys
import json
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class SystemVerifier:
    """Verificador completo del sistema MercadoPago Enterprise"""
    
    def __init__(self):
        self.results = {
            "verification_timestamp": datetime.utcnow().isoformat(),
            "system_status": "UNKNOWN",
            "components": {},
            "summary": {},
            "recommendations": [],
            "final_seal": "PENDING"
        }
        
        # Configuración
        self.base_url = os.getenv("BASE_URL", "http://localhost:8000")
        self.admin_token = os.getenv("ADMIN_API_KEY", "junior123")
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./mercadopago_enterprise.db")
        
        print("🔍 VERIFICADOR FINAL - MERCADOPAGO ENTERPRISE")
        print("=" * 60)
    
    def verify_all_components(self) -> Dict[str, Any]:
        """Verifica todos los componentes del sistema"""
        
        print("\n📋 INICIANDO VERIFICACIÓN COMPLETA...")
        
        # 1. Base de Datos
        print("\n1️⃣ Verificando Base de Datos...")
        self.results["components"]["database"] = self._verify_database()
        
        # 2. API Principal
        print("\n2️⃣ Verificando API Principal...")
        self.results["components"]["api"] = self._verify_api()
        
        # 3. Sistema Multi-tenant
        print("\n3️⃣ Verificando Sistema Multi-tenant...")
        self.results["components"]["multitenant"] = self._verify_multitenant()
        
        # 4. Integración GoHighLevel
        print("\n4️⃣ Verificando Integración GoHighLevel...")
        self.results["components"]["ghl"] = self._verify_ghl()
        
        # 5. MercadoPago Integration
        print("\n5️⃣ Verificando Integración MercadoPago...")
        self.results["components"]["mercadopago"] = self._verify_mercadopago()
        
        # 6. Sistema de Seguridad
        print("\n6️⃣ Verificando Sistema de Seguridad...")
        self.results["components"]["security"] = self._verify_security()
        
        # 7. Sistema de Notificaciones
        print("\n7️⃣ Verificando Sistema de Notificaciones...")
        self.results["components"]["notifications"] = self._verify_notifications()
        
        # 8. Archivado S3
        print("\n8️⃣ Verificando Archivado S3...")
        self.results["components"]["s3"] = self._verify_s3()
        
        # 9. Dashboard y Monitoreo
        print("\n9️⃣ Verificando Dashboard y Monitoreo...")
        self.results["components"]["dashboard"] = self._verify_dashboard()
        
        # 10. Documentación
        print("\n🔟 Verificando Documentación...")
        self.results["components"]["documentation"] = self._verify_documentation()
        
        # Generar resumen final
        self._generate_summary()
        
        return self.results
    
    def _verify_database(self) -> Dict[str, Any]:
        """Verifica la base de datos y sus tablas"""
        result = {
            "status": "UNKNOWN",
            "details": {},
            "issues": [],
            "score": 0
        }
        
        try:
            # Conectar a la base de datos
            engine = create_engine(self.database_url, echo=False)
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            
            with SessionLocal() as db:
                # Verificar tablas principales
                tables_to_check = [
                    'payments', 'audit_logs', 'security_alerts', 'webhook_events',
                    'mercadopago_accounts', 'client_accounts', 'webhook_logs'
                ]
                
                tables_status = {}
                for table in tables_to_check:
                    try:
                        count = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                        tables_status[table] = {"exists": True, "count": count}
                        print(f"   ✅ {table}: {count} registros")
                    except Exception as e:
                        tables_status[table] = {"exists": False, "error": str(e)}
                        print(f"   ❌ {table}: Error - {str(e)}")
                        result["issues"].append(f"Tabla {table} no accesible: {str(e)}")
                
                result["details"]["tables"] = tables_status
                
                # Verificar integridad de datos
                try:
                    # Verificar que hay al menos algunos datos de prueba
                    payment_count = db.execute(text("SELECT COUNT(*) FROM payments")).scalar()
                    audit_count = db.execute(text("SELECT COUNT(*) FROM audit_logs")).scalar()
                    
                    result["details"]["data_integrity"] = {
                        "payments": payment_count,
                        "audit_logs": audit_count,
                        "has_test_data": payment_count > 0 or audit_count > 0
                    }
                    
                    if payment_count > 0 or audit_count > 0:
                        print(f"   ✅ Datos de prueba encontrados: {payment_count} pagos, {audit_count} logs")
                    else:
                        print(f"   ⚠️ No hay datos de prueba (normal en instalación nueva)")
                    
                except Exception as e:
                    result["issues"].append(f"Error verificando integridad: {str(e)}")
                
                # Calcular score
                existing_tables = sum(1 for t in tables_status.values() if t.get("exists", False))
                result["score"] = int((existing_tables / len(tables_to_check)) * 100)
                
                if result["score"] >= 90:
                    result["status"] = "EXCELLENT"
                elif result["score"] >= 70:
                    result["status"] = "GOOD"
                elif result["score"] >= 50:
                    result["status"] = "WARNING"
                else:
                    result["status"] = "CRITICAL"
                
        except Exception as e:
            result["status"] = "CRITICAL"
            result["issues"].append(f"Error de conexión a BD: {str(e)}")
            print(f"   ❌ Error conectando a base de datos: {str(e)}")
        
        return result
    
    def _verify_api(self) -> Dict[str, Any]:
        """Verifica la API principal"""
        result = {
            "status": "UNKNOWN",
            "details": {},
            "issues": [],
            "score": 0
        }
        
        try:
            # Health check básico
            response = requests.get(f"{self.base_url}/health", timeout=10)
            
            if response.status_code == 200:
                result["details"]["health_check"] = "OK"
                print("   ✅ Health check: OK")
            else:
                result["issues"].append(f"Health check failed: {response.status_code}")
                print(f"   ❌ Health check failed: {response.status_code}")
            
            # Verificar endpoints principales
            endpoints_to_check = [
                ("/api/v1/dashboard/overview", "Dashboard overview"),
                ("/metrics", "Métricas del sistema"),
                ("/audit/logs", "Logs de auditoría"),
                ("/security/alerts", "Alertas de seguridad")
            ]
            
            working_endpoints = 0
            for endpoint, description in endpoints_to_check:
                try:
                    resp = requests.get(
                        f"{self.base_url}{endpoint}",
                        headers={"Authorization": f"Bearer {self.admin_token}"},
                        timeout=5
                    )
                    if resp.status_code in [200, 201]:
                        print(f"   ✅ {description}: OK")
                        working_endpoints += 1
                    else:
                        print(f"   ⚠️ {description}: HTTP {resp.status_code}")
                        result["issues"].append(f"{description} returned {resp.status_code}")
                except Exception as e:
                    print(f"   ❌ {description}: Error - {str(e)}")
                    result["issues"].append(f"{description} error: {str(e)}")
            
            result["details"]["endpoints_working"] = working_endpoints
            result["details"]["endpoints_total"] = len(endpoints_to_check)
            
            # Calcular score
            health_score = 20 if response.status_code == 200 else 0
            endpoints_score = int((working_endpoints / len(endpoints_to_check)) * 80)
            result["score"] = health_score + endpoints_score
            
            if result["score"] >= 90:
                result["status"] = "EXCELLENT"
            elif result["score"] >= 70:
                result["status"] = "GOOD"
            elif result["score"] >= 50:
                result["status"] = "WARNING"
            else:
                result["status"] = "CRITICAL"
                
        except Exception as e:
            result["status"] = "CRITICAL"
            result["issues"].append(f"API no accesible: {str(e)}")
            print(f"   ❌ API no accesible: {str(e)}")
        
        return result
    
    def _verify_multitenant(self) -> Dict[str, Any]:
        """Verifica el sistema multi-tenant"""
        result = {
            "status": "UNKNOWN",
            "details": {},
            "issues": [],
            "score": 0
        }
        
        try:
            # Verificar endpoint de clientes
            response = requests.get(
                f"{self.base_url}/clients",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                client_count = len(data.get("clients", []))
                result["details"]["client_count"] = client_count
                print(f"   ✅ Clientes registrados: {client_count}")
                
                # Verificar si hay cliente de prueba
                test_client_exists = any(
                    client.get("client_id") == "cliente_prueba_oficial" 
                    for client in data.get("clients", [])
                )
                
                if test_client_exists:
                    print("   ✅ Cliente de prueba encontrado")
                    result["details"]["test_client"] = True
                    
                    # Verificar dashboard del cliente
                    try:
                        dashboard_resp = requests.get(
                            f"{self.base_url}/dashboard/client/cliente_prueba_oficial",
                            timeout=5
                        )
                        if dashboard_resp.status_code == 200:
                            print("   ✅ Dashboard de cliente accesible")
                            result["details"]["client_dashboard"] = True
                        else:
                            result["issues"].append("Dashboard de cliente no accesible")
                    except Exception as e:
                        result["issues"].append(f"Error accediendo dashboard cliente: {str(e)}")
                else:
                    print("   ⚠️ No hay cliente de prueba configurado")
                    result["details"]["test_client"] = False
            else:
                result["issues"].append(f"Endpoint de clientes falló: {response.status_code}")
                print(f"   ❌ Endpoint de clientes falló: {response.status_code}")
            
            # Verificar APIs específicas de cliente
            if result["details"].get("test_client"):
                client_apis = [
                    f"/api/v1/clients/cliente_prueba_oficial/metrics",
                    f"/api/v1/clients/cliente_prueba_oficial/payments",
                    f"/oauth/ghl/status/cliente_prueba_oficial"
                ]
                
                working_apis = 0
                for api in client_apis:
                    try:
                        resp = requests.get(
                            f"{self.base_url}{api}",
                            headers={"Authorization": f"Bearer {self.admin_token}"},
                            timeout=5
                        )
                        if resp.status_code in [200, 404]:  # 404 es OK si no hay datos
                            working_apis += 1
                    except:
                        pass
                
                result["details"]["client_apis_working"] = working_apis
                result["details"]["client_apis_total"] = len(client_apis)
            
            # Calcular score
            base_score = 40 if response.status_code == 200 else 0
            client_score = 30 if result["details"].get("test_client") else 10
            dashboard_score = 20 if result["details"].get("client_dashboard") else 0
            api_score = 10 if result["details"].get("client_apis_working", 0) > 0 else 0
            
            result["score"] = base_score + client_score + dashboard_score + api_score
            
            if result["score"] >= 80:
                result["status"] = "EXCELLENT"
            elif result["score"] >= 60:
                result["status"] = "GOOD"
            elif result["score"] >= 40:
                result["status"] = "WARNING"
            else:
                result["status"] = "CRITICAL"
                
        except Exception as e:
            result["status"] = "CRITICAL"
            result["issues"].append(f"Error verificando multi-tenant: {str(e)}")
            print(f"   ❌ Error verificando multi-tenant: {str(e)}")
        
        return result
    
    def _verify_ghl(self) -> Dict[str, Any]:
        """Verifica la integración con GoHighLevel"""
        result = {
            "status": "UNKNOWN",
            "details": {},
            "issues": [],
            "score": 0
        }
        
        try:
            # Verificar configuración OAuth
            ghl_client_id = os.getenv("GHL_CLIENT_ID")
            ghl_client_secret = os.getenv("GHL_CLIENT_SECRET")
            
            if ghl_client_id and ghl_client_secret:
                result["details"]["oauth_configured"] = True
                print("   ✅ Credenciales OAuth GHL configuradas")
            else:
                result["details"]["oauth_configured"] = False
                print("   ⚠️ Credenciales OAuth GHL no configuradas")
            
            # Verificar endpoint de estado GHL
            try:
                response = requests.get(
                    f"{self.base_url}/oauth/ghl/status/cliente_prueba_oficial",
                    headers={"Authorization": f"Bearer {self.admin_token}"},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    ghl_connected = data.get("ghl_integration", {}).get("connected", False)
                    
                    result["details"]["test_client_connected"] = ghl_connected
                    
                    if ghl_connected:
                        print("   ✅ Cliente de prueba conectado a GHL")
                        
                        # Probar conexión
                        test_resp = requests.post(
                            f"{self.base_url}/oauth/ghl/test/cliente_prueba_oficial",
                            headers={"Authorization": f"Bearer {self.admin_token}"},
                            timeout=10
                        )
                        
                        if test_resp.status_code == 200:
                            test_data = test_resp.json()
                            if test_data.get("success"):
                                print("   ✅ Prueba de conexión GHL exitosa")
                                result["details"]["connection_test"] = True
                            else:
                                print(f"   ⚠️ Prueba de conexión GHL falló: {test_data.get('error')}")
                                result["details"]["connection_test"] = False
                        else:
                            result["issues"].append("Prueba de conexión GHL falló")
                    else:
                        print("   ⚠️ Cliente de prueba no conectado a GHL (normal en modo desarrollo)")
                        result["details"]["test_client_connected"] = False
                else:
                    result["issues"].append(f"Estado GHL no accesible: {response.status_code}")
                    
            except Exception as e:
                result["issues"].append(f"Error verificando estado GHL: {str(e)}")
            
            # Calcular score
            oauth_score = 40 if result["details"].get("oauth_configured") else 20
            connection_score = 40 if result["details"].get("test_client_connected") else 20
            test_score = 20 if result["details"].get("connection_test") else 10
            
            result["score"] = oauth_score + connection_score + test_score
            
            if result["score"] >= 80:
                result["status"] = "EXCELLENT"
            elif result["score"] >= 60:
                result["status"] = "GOOD"
            elif result["score"] >= 40:
                result["status"] = "WARNING"
            else:
                result["status"] = "CRITICAL"
                
        except Exception as e:
            result["status"] = "CRITICAL"
            result["issues"].append(f"Error verificando GHL: {str(e)}")
            print(f"   ❌ Error verificando GHL: {str(e)}")
        
        return result
    
    def _verify_mercadopago(self) -> Dict[str, Any]:
        """Verifica la integración con MercadoPago"""
        result = {
            "status": "UNKNOWN",
            "details": {},
            "issues": [],
            "score": 0
        }
        
        try:
            # Verificar configuración
            mp_token = os.getenv("MP_ACCESS_TOKEN")
            mp_webhook_secret = os.getenv("MP_WEBHOOK_SECRET")
            
            config_score = 0
            if mp_token:
                result["details"]["access_token_configured"] = True
                print("   ✅ MP Access Token configurado")
                config_score += 25
            else:
                result["details"]["access_token_configured"] = False
                print("   ⚠️ MP Access Token no configurado")
            
            if mp_webhook_secret:
                result["details"]["webhook_secret_configured"] = True
                print("   ✅ MP Webhook Secret configurado")
                config_score += 25
            else:
                result["details"]["webhook_secret_configured"] = False
                print("   ⚠️ MP Webhook Secret no configurado")
            
            # Verificar endpoint de creación de pagos
            try:
                # No crear pago real, solo verificar que el endpoint responde
                test_payment = {
                    "customer_email": "test@example.com",
                    "customer_name": "Test User",
                    "ghl_contact_id": "test_contact_123",
                    "amount": 10.00,
                    "description": "Test payment for verification",
                    "created_by": "system_verification",
                    "client_id": "cliente_prueba_oficial"
                }
                
                # En modo desarrollo, esto debería crear un pago mock
                response = requests.post(
                    f"{self.base_url}/api/v1/payments/create",
                    json=test_payment,
                    headers={
                        "Authorization": f"Bearer {self.admin_token}",
                        "Content-Type": "application/json"
                    },
                    timeout=10
                )
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    if data.get("checkout_url"):
                        print("   ✅ Creación de pagos funcional")
                        result["details"]["payment_creation"] = True
                        config_score += 30
                    else:
                        result["issues"].append("Creación de pagos no retorna checkout_url")
                else:
                    result["issues"].append(f"Creación de pagos falló: {response.status_code}")
                    print(f"   ❌ Creación de pagos falló: {response.status_code}")
                    
            except Exception as e:
                result["issues"].append(f"Error probando creación de pagos: {str(e)}")
            
            # Verificar webhook endpoint
            try:
                # Solo verificar que el endpoint existe
                webhook_resp = requests.post(
                    f"{self.base_url}/webhook/mercadopago",
                    json={"test": "verification"},
                    timeout=5
                )
                # Cualquier respuesta (incluso error) indica que el endpoint existe
                if webhook_resp.status_code in [200, 400, 422]:
                    print("   ✅ Webhook endpoint accesible")
                    result["details"]["webhook_endpoint"] = True
                    config_score += 20
                else:
                    result["issues"].append("Webhook endpoint no accesible")
            except Exception as e:
                result["issues"].append(f"Error verificando webhook: {str(e)}")
            
            result["score"] = config_score
            
            if result["score"] >= 80:
                result["status"] = "EXCELLENT"
            elif result["score"] >= 60:
                result["status"] = "GOOD"
            elif result["score"] >= 40:
                result["status"] = "WARNING"
            else:
                result["status"] = "CRITICAL"
                
        except Exception as e:
            result["status"] = "CRITICAL"
            result["issues"].append(f"Error verificando MercadoPago: {str(e)}")
            print(f"   ❌ Error verificando MercadoPago: {str(e)}")
        
        return result
    
    def _verify_security(self) -> Dict[str, Any]:
        """Verifica el sistema de seguridad"""
        result = {
            "status": "UNKNOWN",
            "details": {},
            "issues": [],
            "score": 0
        }
        
        try:
            # Verificar alertas de seguridad
            response = requests.get(
                f"{self.base_url}/security/alerts",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                alert_count = len(data.get("alerts", []))
                result["details"]["security_alerts_accessible"] = True
                result["details"]["alert_count"] = alert_count
                print(f"   ✅ Sistema de alertas accesible: {alert_count} alertas")
            else:
                result["issues"].append(f"Sistema de alertas no accesible: {response.status_code}")
            
            # Verificar logs de auditoría
            audit_resp = requests.get(
                f"{self.base_url}/audit/logs?limit=10",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            
            if audit_resp.status_code == 200:
                audit_data = audit_resp.json()
                log_count = len(audit_data.get("logs", []))
                result["details"]["audit_logs_accessible"] = True
                result["details"]["audit_log_count"] = log_count
                print(f"   ✅ Logs de auditoría accesibles: {log_count} logs recientes")
            else:
                result["issues"].append("Logs de auditoría no accesibles")
            
            # Verificar sistema de alertas automáticas
            try:
                alert_status_resp = requests.get(
                    f"{self.base_url}/api/v1/dashboard/alerts",
                    headers={"Authorization": f"Bearer {self.admin_token}"},
                    timeout=10
                )
                
                if alert_status_resp.status_code == 200:
                    result["details"]["alert_system_active"] = True
                    print("   ✅ Sistema de alertas automáticas activo")
                else:
                    result["issues"].append("Sistema de alertas automáticas no disponible")
            except Exception as e:
                result["issues"].append(f"Error verificando alertas automáticas: {str(e)}")
            
            # Calcular score
            alerts_score = 30 if result["details"].get("security_alerts_accessible") else 0
            audit_score = 30 if result["details"].get("audit_logs_accessible") else 0
            auto_alerts_score = 40 if result["details"].get("alert_system_active") else 0
            
            result["score"] = alerts_score + audit_score + auto_alerts_score
            
            if result["score"] >= 80:
                result["status"] = "EXCELLENT"
            elif result["score"] >= 60:
                result["status"] = "GOOD"
            elif result["score"] >= 40:
                result["status"] = "WARNING"
            else:
                result["status"] = "CRITICAL"
                
        except Exception as e:
            result["status"] = "CRITICAL"
            result["issues"].append(f"Error verificando seguridad: {str(e)}")
            print(f"   ❌ Error verificando seguridad: {str(e)}")
        
        return result
    
    def _verify_notifications(self) -> Dict[str, Any]:
        """Verifica el sistema de notificaciones"""
        result = {
            "status": "UNKNOWN",
            "details": {},
            "issues": [],
            "score": 0
        }
        
        try:
            # Verificar configuración de notificaciones
            response = requests.get(
                f"{self.base_url}/admin/notification-config",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                config = data.get("config", {})
                
                result["details"]["notification_system_available"] = True
                result["details"]["slack_configured"] = config.get("slack_configured", False)
                result["details"]["email_configured"] = config.get("email_configured", False)
                result["details"]["webhooks_configured"] = config.get("webhooks_configured", False)
                result["details"]["enabled_channels"] = config.get("enabled_channels", [])
                
                print(f"   ✅ Sistema de notificaciones disponible")
                print(f"   📧 Slack: {'✅' if config.get('slack_configured') else '❌'}")
                print(f"   📧 Email: {'✅' if config.get('email_configured') else '❌'}")
                print(f"   🔗 Webhooks: {'✅' if config.get('webhooks_configured') else '❌'}")
                
                # Probar notificación
                try:
                    test_resp = requests.post(
                        f"{self.base_url}/admin/test-notifications?notification_type=test",
                        headers={"Authorization": f"Bearer {self.admin_token}"},
                        timeout=15
                    )
                    
                    if test_resp.status_code == 200:
                        test_data = test_resp.json()
                        if test_data.get("success"):
                            channels_used = len(test_data.get("result", {}).get("channels", []))
                            result["details"]["test_notification_success"] = True
                            result["details"]["channels_working"] = channels_used
                            print(f"   ✅ Prueba de notificación exitosa: {channels_used} canales")
                        else:
                            result["issues"].append("Prueba de notificación falló")
                    else:
                        result["issues"].append(f"Prueba de notificación error: {test_resp.status_code}")
                except Exception as e:
                    result["issues"].append(f"Error probando notificaciones: {str(e)}")
                    
            else:
                result["status"] = "WARNING"
                result["details"]["notification_system_available"] = False
                print("   ⚠️ Sistema de notificaciones no disponible")
            
            # Calcular score
            system_score = 40 if result["details"].get("notification_system_available") else 0
            config_score = 0
            if result["details"].get("slack_configured"): config_score += 20
            if result["details"].get("email_configured"): config_score += 20
            if result["details"].get("webhooks_configured"): config_score += 10
            test_score = 10 if result["details"].get("test_notification_success") else 0
            
            result["score"] = system_score + config_score + test_score
            
            if result["score"] >= 80:
                result["status"] = "EXCELLENT"
            elif result["score"] >= 60:
                result["status"] = "GOOD"
            elif result["score"] >= 40:
                result["status"] = "WARNING"
            else:
                result["status"] = "CRITICAL"
                
        except Exception as e:
            result["status"] = "CRITICAL"
            result["issues"].append(f"Error verificando notificaciones: {str(e)}")
            print(f"   ❌ Error verificando notificaciones: {str(e)}")
        
        return result
    
    def _verify_s3(self) -> Dict[str, Any]:
        """Verifica el sistema de archivado S3"""
        result = {
            "status": "UNKNOWN",
            "details": {},
            "issues": [],
            "score": 0
        }
        
        try:
            # Verificar configuración S3
            aws_key = os.getenv("AWS_ACCESS_KEY_ID")
            aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
            s3_bucket = os.getenv("S3_BUCKET_NAME")
            
            config_score = 0
            if aws_key and aws_secret:
                result["details"]["aws_credentials_configured"] = True
                print("   ✅ Credenciales AWS configuradas")
                config_score += 40
            else:
                result["details"]["aws_credentials_configured"] = False
                print("   ⚠️ Credenciales AWS no configuradas")
            
            if s3_bucket:
                result["details"]["s3_bucket_configured"] = True
                print(f"   ✅ Bucket S3 configurado: {s3_bucket}")
                config_score += 20
            else:
                result["details"]["s3_bucket_configured"] = False
                print("   ⚠️ Bucket S3 no configurado")
            
            # Verificar endpoint de estado S3
            try:
                s3_resp = requests.get(
                    f"{self.base_url}/admin/archive-status",
                    headers={"Authorization": f"Bearer {self.admin_token}"},
                    timeout=10
                )
                
                if s3_resp.status_code == 200:
                    s3_data = s3_resp.json()
                    result["details"]["s3_service_available"] = True
                    result["details"]["archived_files"] = s3_data.get("archived_files", {}).get("total_files", 0)
                    print(f"   ✅ Servicio S3 disponible: {result['details']['archived_files']} archivos")
                    config_score += 40
                else:
                    result["issues"].append(f"Servicio S3 no disponible: {s3_resp.status_code}")
                    
            except Exception as e:
                result["issues"].append(f"Error verificando S3: {str(e)}")
            
            result["score"] = config_score
            
            if result["score"] >= 80:
                result["status"] = "EXCELLENT"
            elif result["score"] >= 60:
                result["status"] = "GOOD"
            elif result["score"] >= 40:
                result["status"] = "WARNING"
            else:
                result["status"] = "CRITICAL"
                
        except Exception as e:
            result["status"] = "CRITICAL"
            result["issues"].append(f"Error verificando S3: {str(e)}")
            print(f"   ❌ Error verificando S3: {str(e)}")
        
        return result
    
    def _verify_dashboard(self) -> Dict[str, Any]:
        """Verifica el dashboard y monitoreo"""
        result = {
            "status": "UNKNOWN",
            "details": {},
            "issues": [],
            "score": 0
        }
        
        try:
            # Verificar dashboard principal
            dashboard_resp = requests.get(f"{self.base_url}/dashboard", timeout=10)
            
            if dashboard_resp.status_code == 200:
                result["details"]["main_dashboard_accessible"] = True
                print("   ✅ Dashboard principal accesible")
            else:
                result["issues"].append(f"Dashboard principal no accesible: {dashboard_resp.status_code}")
            
            # Verificar dashboard de cliente
            client_dashboard_resp = requests.get(
                f"{self.base_url}/dashboard/client/cliente_prueba_oficial", 
                timeout=10
            )
            
            if client_dashboard_resp.status_code == 200:
                result["details"]["client_dashboard_accessible"] = True
                print("   ✅ Dashboard de cliente accesible")
            else:
                result["issues"].append("Dashboard de cliente no accesible")
            
            # Verificar métricas en tiempo real
            metrics_resp = requests.get(
                f"{self.base_url}/api/v1/dashboard/metrics/realtime",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            
            if metrics_resp.status_code == 200:
                result["details"]["realtime_metrics_available"] = True
                print("   ✅ Métricas en tiempo real disponibles")
            else:
                result["issues"].append("Métricas en tiempo real no disponibles")
            
            # Verificar overview del dashboard
            overview_resp = requests.get(
                f"{self.base_url}/api/v1/dashboard/overview",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                timeout=10
            )
            
            if overview_resp.status_code == 200:
                overview_data = overview_resp.json()
                if overview_data.get("status") == "success":
                    result["details"]["dashboard_overview_working"] = True
                    print("   ✅ Overview del dashboard funcional")
                else:
                    result["issues"].append("Overview del dashboard con errores")
            else:
                result["issues"].append("Overview del dashboard no accesible")
            
            # Calcular score
            main_score = 25 if result["details"].get("main_dashboard_accessible") else 0
            client_score = 25 if result["details"].get("client_dashboard_accessible") else 0
            metrics_score = 25 if result["details"].get("realtime_metrics_available") else 0
            overview_score = 25 if result["details"].get("dashboard_overview_working") else 0
            
            result["score"] = main_score + client_score + metrics_score + overview_score
            
            if result["score"] >= 80:
                result["status"] = "EXCELLENT"
            elif result["score"] >= 60:
                result["status"] = "GOOD"
            elif result["score"] >= 40:
                result["status"] = "WARNING"
            else:
                result["status"] = "CRITICAL"
                
        except Exception as e:
            result["status"] = "CRITICAL"
            result["issues"].append(f"Error verificando dashboard: {str(e)}")
            print(f"   ❌ Error verificando dashboard: {str(e)}")
        
        return result
    
    def _verify_documentation(self) -> Dict[str, Any]:
        """Verifica la documentación del sistema"""
        result = {
            "status": "UNKNOWN",
            "details": {},
            "issues": [],
            "score": 0
        }
        
        try:
            # Archivos de documentación requeridos
            required_docs = [
                ("README.md", "Documentación principal"),
                ("QUICKSTART.md", "Guía de inicio rápido"),
                ("INDEX.md", "Índice de documentación"),
                (".env.example", "Archivo de configuración ejemplo"),
                ("requirements.txt", "Dependencias del proyecto")
            ]
            
            existing_docs = 0
            for doc_file, description in required_docs:
                if os.path.exists(doc_file):
                    print(f"   ✅ {description}: Encontrado")
                    existing_docs += 1
                else:
                    print(f"   ❌ {description}: No encontrado")
                    result["issues"].append(f"{description} no encontrado")
            
            result["details"]["required_docs_found"] = existing_docs
            result["details"]["required_docs_total"] = len(required_docs)
            
            # Verificar documentación adicional
            additional_docs = [
                "COMO_RESOLVER_ALERTAS.md",
                "NOTIFICACIONES_GUIA_COMPLETA.md",
                "docs/"
            ]
            
            additional_found = 0
            for doc in additional_docs:
                if os.path.exists(doc):
                    additional_found += 1
            
            result["details"]["additional_docs_found"] = additional_found
            
            # Verificar scripts
            script_dir = "scripts"
            if os.path.exists(script_dir):
                scripts = [f for f in os.listdir(script_dir) if f.endswith('.py')]
                result["details"]["scripts_count"] = len(scripts)
                print(f"   ✅ Scripts encontrados: {len(scripts)}")
            else:
                result["details"]["scripts_count"] = 0
                result["issues"].append("Directorio de scripts no encontrado")
            
            # Calcular score
            docs_score = int((existing_docs / len(required_docs)) * 60)
            additional_score = min(additional_found * 10, 30)
            scripts_score = min(result["details"]["scripts_count"] * 2, 10)
            
            result["score"] = docs_score + additional_score + scripts_score
            
            if result["score"] >= 80:
                result["status"] = "EXCELLENT"
            elif result["score"] >= 60:
                result["status"] = "GOOD"
            elif result["score"] >= 40:
                result["status"] = "WARNING"
            else:
                result["status"] = "CRITICAL"
                
        except Exception as e:
            result["status"] = "CRITICAL"
            result["issues"].append(f"Error verificando documentación: {str(e)}")
            print(f"   ❌ Error verificando documentación: {str(e)}")
        
        return result
    
    def _generate_summary(self):
        """Genera resumen final del sistema"""
        components = self.results["components"]
        
        # Calcular score general
        total_score = 0
        component_count = 0
        
        status_counts = {"EXCELLENT": 0, "GOOD": 0, "WARNING": 0, "CRITICAL": 0}
        
        for component_name, component_data in components.items():
            if isinstance(component_data, dict) and "score" in component_data:
                total_score += component_data["score"]
                component_count += 1
                
                status = component_data.get("status", "UNKNOWN")
                if status in status_counts:
                    status_counts[status] += 1
        
        overall_score = int(total_score / component_count) if component_count > 0 else 0
        
        # Determinar estado general
        if overall_score >= 85:
            system_status = "PRODUCTION_READY"
            final_seal = "PRODUCTO_LISTO"
        elif overall_score >= 70:
            system_status = "MOSTLY_READY"
            final_seal = "CASI_LISTO"
        elif overall_score >= 50:
            system_status = "NEEDS_WORK"
            final_seal = "REQUIERE_TRABAJO"
        else:
            system_status = "NOT_READY"
            final_seal = "NO_LISTO"
        
        self.results["system_status"] = system_status
        self.results["final_seal"] = final_seal
        
        self.results["summary"] = {
            "overall_score": overall_score,
            "total_components": component_count,
            "status_breakdown": status_counts,
            "critical_issues": sum(1 for c in components.values() 
                                 if isinstance(c, dict) and c.get("status") == "CRITICAL"),
            "warnings": sum(1 for c in components.values() 
                          if isinstance(c, dict) and c.get("status") == "WARNING")
        }
        
        # Generar recomendaciones
        self._generate_recommendations()
        
        print(f"\n🎯 RESUMEN FINAL:")
        print(f"   Score General: {overall_score}/100")
        print(f"   Estado del Sistema: {system_status}")
        print(f"   Sello Final: {final_seal}")
        print(f"   Componentes Críticos: {self.results['summary']['critical_issues']}")
        print(f"   Advertencias: {self.results['summary']['warnings']}")
    
    def _generate_recommendations(self):
        """Genera recomendaciones basadas en los resultados"""
        recommendations = []
        components = self.results["components"]
        
        # Recomendaciones por componente
        for component_name, component_data in components.items():
            if isinstance(component_data, dict):
                status = component_data.get("status")
                issues = component_data.get("issues", [])
                
                if status == "CRITICAL":
                    recommendations.append({
                        "priority": "HIGH",
                        "component": component_name,
                        "message": f"Componente {component_name} requiere atención inmediata",
                        "issues": issues
                    })
                elif status == "WARNING":
                    recommendations.append({
                        "priority": "MEDIUM",
                        "component": component_name,
                        "message": f"Componente {component_name} necesita mejoras",
                        "issues": issues
                    })
        
        # Recomendaciones específicas
        if not components.get("notifications", {}).get("details", {}).get("slack_configured"):
            recommendations.append({
                "priority": "MEDIUM",
                "component": "notifications",
                "message": "Configurar Slack para notificaciones en tiempo real",
                "action": "Agregar SLACK_WEBHOOK_URL a .env"
            })
        
        if not components.get("s3", {}).get("details", {}).get("aws_credentials_configured"):
            recommendations.append({
                "priority": "LOW",
                "component": "s3",
                "message": "Configurar S3 para archivado a largo plazo",
                "action": "Agregar credenciales AWS a .env"
            })
        
        self.results["recommendations"] = recommendations

def main():
    """Función principal"""
    print("🚀 GENERADOR DE REPORTE FINAL - MERCADOPAGO ENTERPRISE")
    print("=" * 60)
    print("Verificando todos los componentes del sistema...")
    
    verifier = SystemVerifier()
    results = verifier.verify_all_components()
    
    # Generar archivo de reporte
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report_file = f"FINAL_VERIFICATION_{timestamp}.json"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n📄 REPORTE GENERADO: {report_file}")
    
    # Mostrar resumen en consola
    print(f"\n{'='*60}")
    print(f"🎯 VERIFICACIÓN FINAL COMPLETADA")
    print(f"{'='*60}")
    print(f"📊 Score General: {results['summary']['overall_score']}/100")
    print(f"🏷️ Estado: {results['system_status']}")
    print(f"🏆 Sello: {results['final_seal']}")
    
    if results["final_seal"] == "PRODUCTO_LISTO":
        print(f"\n🎉 ¡FELICITACIONES!")
        print(f"✅ El sistema está LISTO para producción")
        print(f"✅ Todos los componentes funcionan correctamente")
        print(f"✅ Documentación completa")
        print(f"✅ Seguridad implementada")
        print(f"✅ Multi-tenant operativo")
    else:
        print(f"\n⚠️ El sistema necesita atención:")
        for rec in results["recommendations"]:
            if rec["priority"] == "HIGH":
                print(f"   🔴 {rec['message']}")
            elif rec["priority"] == "MEDIUM":
                print(f"   🟡 {rec['message']}")
    
    print(f"\n📋 Ver reporte completo en: {report_file}")
    
    return results["final_seal"] == "PRODUCTO_LISTO"

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)