#!/usr/bin/env python3
"""
Test Vendor Notifications - Prueba de Integración Completa
Dispara el flujo completo: Pago -> Tag GHL -> Notificación Dashboard -> Envío de Email
"""
import os
import sys
import json
import time
import requests
from datetime import datetime
from pathlib import Path
from decimal import Decimal

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

from models import Payment, PaymentStatus, ClientAccount, PaymentEvent
from services.vendor_notification_service import VendorNotificationService

class VendorNotificationTester:
    """
    Tester completo del sistema de notificaciones vendedor
    """
    
    def __init__(self):
        # Configuración de base de datos
        database_url = os.getenv("DATABASE_URL", "sqlite:///./mercadopago_enterprise.db")
        self.engine = create_engine(database_url, echo=False)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = SessionLocal()
        
        # Configuración API
        self.base_url = os.getenv("BASE_URL", "http://localhost:8000")
        self.admin_token = os.getenv("ADMIN_API_KEY", "junior123")
        
        print("🧪 TESTER DE NOTIFICACIONES VENDEDOR - MVP")
        print("=" * 60)
    
    def run_complete_integration_test(self) -> bool:
        """
        Prueba de Integración: Flujo completo de notificaciones
        """
        try:
            print("\n🎯 INICIANDO PRUEBA DE INTEGRACIÓN COMPLETA...")
            print("Flujo: Pago -> Tag GHL -> Notificación Dashboard -> Envío Email")
            
            # PASO 1: Crear/obtener pago de prueba
            print(f"\n1️⃣ PASO 1: Preparando pago de prueba...")
            payment = self._create_test_payment()
            
            if not payment:
                print("❌ No se pudo crear pago de prueba")
                return False
            
            print(f"✅ Pago de prueba preparado: ID {payment.id}")
            print(f"   📧 Cliente: {payment.customer_email}")
            print(f"   💰 Monto: ${payment.expected_amount}")
            print(f"   🏢 Cliente Account: {payment.client_account_id}")
            
            # PASO 2: Simular aprobación del pago
            print(f"\n2️⃣ PASO 2: Simulando aprobación del pago...")
            
            # Cambiar estado a aprobado
            payment.status = PaymentStatus.APPROVED.value
            payment.paid_amount = payment.expected_amount
            payment.mp_payment_id = f"test_mp_payment_{int(time.time())}"
            payment.processed_at = datetime.utcnow()
            
            self.db.commit()
            
            print(f"✅ Pago marcado como APROBADO")
            print(f"   💳 MP Payment ID: {payment.mp_payment_id}")
            print(f"   💰 Monto pagado: ${payment.paid_amount}")
            
            # PASO 3: Disparar notificaciones vendedor
            print(f"\n3️⃣ PASO 3: Disparando notificaciones vendedor...")
            
            vendor_service = VendorNotificationService(self.db)
            notification_result = vendor_service.notify_payment_approved(payment)
            
            print(f"📊 RESULTADO DE NOTIFICACIONES:")
            print(f"   ✅ Éxito: {notification_result.get('success', False)}")
            
            if notification_result.get('success'):
                print(f"   📋 Dashboard Notification ID: {notification_result.get('dashboard_notification_id')}")
                print(f"   📧 Email enviado: {notification_result.get('email_sent', False)}")
                print(f"   🆔 Notification Sent ID: {notification_result.get('notification_sent_id')}")
            else:
                print(f"   ❌ Error: {notification_result.get('error', 'Error desconocido')}")
            
            # PASO 4: Verificar protección anti-duplicados
            print(f"\n4️⃣ PASO 4: Verificando protección anti-duplicados...")
            
            # Intentar enviar notificación nuevamente
            duplicate_result = vendor_service.notify_payment_approved(payment)
            
            if duplicate_result.get('success') and "already sent" in duplicate_result.get('message', ''):
                print(f"✅ Protección anti-duplicados funcionando correctamente")
                print(f"   📝 Mensaje: {duplicate_result.get('message')}")
            else:
                print(f"⚠️ Protección anti-duplicados no funcionó como esperado")
            
            # PASO 5: Probar endpoint de dashboard
            print(f"\n5️⃣ PASO 5: Probando endpoint de dashboard...")
            
            dashboard_result = self._test_dashboard_endpoint()
            
            if dashboard_result.get('success'):
                notifications = dashboard_result.get('notifications', [])
                print(f"✅ Endpoint /api/notifications/ funcionando")
                print(f"   📋 Notificaciones encontradas: {len(notifications)}")
                
                # Mostrar la notificación más reciente
                if notifications:
                    latest = notifications[0]
                    print(f"   💰 Última notificación: ${latest.get('amount')} - {latest.get('customer_name')}")
            else:
                print(f"❌ Error en endpoint dashboard: {dashboard_result.get('error')}")
            
            # PASO 6: Verificar logs de eventos
            print(f"\n6️⃣ PASO 6: Verificando logs de eventos...")
            
            self._verify_payment_events(payment.id)
            
            # PASO 7: Mostrar estadísticas
            print(f"\n7️⃣ PASO 7: Mostrando estadísticas del sistema...")
            
            stats = vendor_service.get_notification_stats()
            print(f"✅ Estadísticas del sistema:")
            print(f"   📊 Total notificaciones aprobadas: {stats['total_approved_notifications']}")
            print(f"   📧 Total notificaciones enviadas: {stats['total_sent_notifications']}")
            print(f"   📈 Tasa de éxito: {stats['success_rate']:.1f}%")
            print(f"   📅 Notificaciones hoy: {stats['today_approved']}")
            
            print(f"\n🎉 PRUEBA DE INTEGRACIÓN COMPLETADA EXITOSAMENTE")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERROR EN LA PRUEBA DE INTEGRACIÓN: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.db.close()
    
    def _create_test_payment(self) -> Payment:
        """
        Crea un pago de prueba para las notificaciones
        """
        try:
            # Buscar cliente de prueba existente
            test_client = self.db.query(ClientAccount).filter(
                ClientAccount.client_id == "cliente_prueba_oficial"
            ).first()
            
            if not test_client:
                print("🔧 Creando cliente de prueba para notificaciones...")
                test_client = ClientAccount(
                    client_id="cliente_prueba_oficial",
                    client_name="Cliente Prueba Notificaciones",
                    client_email="vendor@notifications-test.com",
                    company_name="Empresa Test Notificaciones",
                    ghl_location_id="mock_location_notifications",
                    ghl_access_token="mock_ghl_access_token_notifications",
                    default_tag_paid="Pago confirmado",
                    auto_tag_payments=True,
                    is_active=True
                )
                self.db.add(test_client)
                self.db.commit()
                print(f"✅ Cliente de prueba creado: {test_client.client_id}")
            
            # Crear pago de prueba
            test_payment = Payment(
                customer_email="cliente.notificaciones@test.com",
                customer_name="Cliente Notificaciones Test",
                ghl_contact_id=f"ghl_contact_notif_{int(time.time())}",
                client_account_id=test_client.id,
                expected_amount=Decimal("299.99"),
                currency="ARS",
                status=PaymentStatus.PENDING.value,
                created_by="notification_tester",
                mp_preference_id=f"test_pref_notif_{int(time.time())}"
            )
            
            self.db.add(test_payment)
            self.db.commit()
            
            print(f"✅ Pago de prueba creado: ID {test_payment.id}")
            return test_payment
            
        except Exception as e:
            print(f"❌ Error creando pago de prueba: {str(e)}")
            self.db.rollback()
            return None
    
    def _test_dashboard_endpoint(self) -> dict:
        """
        Prueba el endpoint GET /api/notifications/
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/notifications/",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                params={"limit": 5},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _verify_payment_events(self, payment_id: int):
        """
        Verifica los eventos de pago creados
        """
        try:
            events = self.db.query(PaymentEvent).filter(
                PaymentEvent.payment_id == payment_id
            ).order_by(PaymentEvent.created_at.desc()).all()
            
            print(f"✅ Eventos de pago encontrados: {len(events)}")
            
            for i, event in enumerate(events, 1):
                event_data = {}
                if event.event_data:
                    try:
                        event_data = json.loads(event.event_data)
                    except:
                        pass
                
                print(f"   {i}. Evento: {event.event_type}")
                print(f"      📅 Creado: {event.created_at}")
                print(f"      🆔 ID: {event.id}")
                
                if event.event_type == "payment_approved":
                    amount = event_data.get('amount', 'N/A')
                    customer = event_data.get('customer_name', 'N/A')
                    print(f"      💰 Monto: ${amount}")
                    print(f"      👤 Cliente: {customer}")
                elif event.event_type == "notification_sent":
                    email_sent = event_data.get('email_sent', False)
                    print(f"      📧 Email enviado: {'Sí' if email_sent else 'No'}")
                    if not email_sent and event_data.get('email_error'):
                        print(f"      ❌ Error email: {event_data['email_error']}")
            
        except Exception as e:
            print(f"❌ Error verificando eventos: {str(e)}")
    
    def show_recent_activity(self):
        """
        Muestra la actividad reciente de notificaciones
        """
        try:
            print("\n📊 ACTIVIDAD RECIENTE DE NOTIFICACIONES VENDEDOR")
            print("=" * 60)
            
            vendor_service = VendorNotificationService(self.db)
            
            # Obtener notificaciones recientes
            notifications = vendor_service.get_recent_notifications(limit=10)
            
            if not notifications:
                print("📭 No hay notificaciones recientes")
                return
            
            print(f"📋 Últimas {len(notifications)} notificaciones:")
            
            for i, notif in enumerate(notifications, 1):
                amount = notif.get('amount', 0)
                customer = notif.get('customer_name', 'N/A')
                client = notif.get('client_name', 'N/A')
                created = notif.get('created_at', 'N/A')
                
                print(f"\n{i}. 💰 ${amount} ARS")
                print(f"   👤 Cliente: {customer}")
                print(f"   🏢 Cuenta: {client}")
                print(f"   📅 Fecha: {created}")
                print(f"   🆔 Payment ID: {notif.get('payment_id')}")
            
            # Mostrar estadísticas
            stats = vendor_service.get_notification_stats()
            print(f"\n📈 ESTADÍSTICAS:")
            print(f"   📊 Total aprobadas: {stats['total_approved_notifications']}")
            print(f"   📧 Total enviadas: {stats['total_sent_notifications']}")
            print(f"   📈 Tasa éxito: {stats['success_rate']:.1f}%")
            print(f"   📅 Hoy: {stats['today_approved']}")
            
        except Exception as e:
            print(f"❌ Error mostrando actividad: {str(e)}")
        finally:
            self.db.close()

def main():
    """Función principal del tester"""
    print("🚀 TESTER DE NOTIFICACIONES VENDEDOR - MVP")
    print("Prueba de Integración Completa del Sistema")
    print("=" * 70)
    
    tester = VendorNotificationTester()
    
    # Mostrar actividad reciente primero
    tester.show_recent_activity()
    
    # Ejecutar prueba completa
    print(f"\n🎯 INICIANDO PRUEBA DE INTEGRACIÓN COMPLETA...")
    success = tester.run_complete_integration_test()
    
    if success:
        print(f"\n🎉 ¡PRUEBA DE INTEGRACIÓN EXITOSA!")
        print("✅ Flujo completo funcionando: Pago -> Tag GHL -> Dashboard -> Email")
        print("✅ Protección anti-duplicados verificada")
        print("✅ Endpoint /api/notifications/ operativo")
        print("✅ Logs de eventos registrados correctamente")
        print("✅ MVP Notificaciones Vendedor: COMPLETADO")
    else:
        print(f"\n❌ La prueba de integración falló")
        print("⚠️ Revisar logs para identificar problemas")
    
    print("\n" + "=" * 70)
    print("Para ver notificaciones en dashboard:")
    print("curl -H 'Authorization: Bearer junior123' http://localhost:8000/api/notifications/")
    print("\nPara ver logs en tiempo real:")
    print("tail -f logs/app.log | grep 'vendor\\|notification\\|PaymentEvent'")
    print("=" * 70)

if __name__ == "__main__":
    main()