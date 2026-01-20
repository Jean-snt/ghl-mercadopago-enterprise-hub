"""
Script para aprobar manualmente pagos mock en desarrollo
Útil para testing y cerrar el flujo completo sin API real de MercadoPago
"""
import sqlite3
import os
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def get_db_path():
    """Obtiene la ruta de la base de datos"""
    database_url = os.getenv("DATABASE_URL", "sqlite:///./mercadopago_enterprise.db")
    
    if database_url.startswith("sqlite:///"):
        db_path = database_url.replace("sqlite:///", "")
    elif database_url.startswith("sqlite://"):
        db_path = database_url.replace("sqlite://", "")
    else:
        db_path = "./mercadopago_enterprise.db"
    
    return db_path

def approve_payment(preference_id=None, payment_id=None, amount=None):
    """Aprueba un pago manualmente"""
    db_path = get_db_path()
    
    print(f"🔧 Conectando a base de datos: {db_path}\n")
    
    if not os.path.exists(db_path):
        print(f"❌ Error: Base de datos no encontrada en {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Buscar el pago
        if preference_id:
            print(f"🔍 Buscando pago con preference_id: {preference_id}")
            cursor.execute("""
                SELECT id, internal_uuid, customer_email, expected_amount, status, 
                       mp_preference_id, mp_payment_id, is_processed
                FROM payments 
                WHERE mp_preference_id = ?
            """, (preference_id,))
        elif payment_id:
            print(f"🔍 Buscando pago con payment_id: {payment_id}")
            cursor.execute("""
                SELECT id, internal_uuid, customer_email, expected_amount, status, 
                       mp_preference_id, mp_payment_id, is_processed
                FROM payments 
                WHERE id = ?
            """, (payment_id,))
        else:
            print("❌ Error: Debes proporcionar preference_id o payment_id")
            conn.close()
            return False
        
        payment = cursor.fetchone()
        
        if not payment:
            print("❌ Pago no encontrado")
            conn.close()
            return False
        
        # Extraer datos del pago
        pay_id, internal_uuid, customer_email, expected_amount, current_status, \
            mp_pref_id, mp_pay_id, is_processed = payment
        
        print(f"\n✅ Pago encontrado:")
        print(f"   ID: {pay_id}")
        print(f"   UUID: {internal_uuid}")
        print(f"   Email: {customer_email}")
        print(f"   Monto esperado: ${expected_amount}")
        print(f"   Estado actual: {current_status}")
        print(f"   Preference ID: {mp_pref_id}")
        print(f"   Payment ID: {mp_pay_id or 'N/A'}")
        print(f"   Procesado: {'Sí' if is_processed else 'No'}")
        
        # Si ya está aprobado
        if current_status == 'approved' and is_processed:
            print(f"\n⚠️  El pago ya está aprobado y procesado")
            conn.close()
            return True
        
        # Generar mock payment ID si no existe
        if not mp_pay_id:
            mp_pay_id = f"mock_payment_{pay_id}_{int(datetime.utcnow().timestamp())}"
            print(f"\n🆔 Generando mock payment ID: {mp_pay_id}")
        
        # Determinar monto pagado
        paid_amount = amount if amount else expected_amount
        
        # Actualizar el pago
        print(f"\n🔄 Aprobando pago...")
        
        cursor.execute("""
            UPDATE payments 
            SET status = 'approved',
                mp_payment_id = ?,
                paid_amount = ?,
                is_processed = 1,
                processed_at = ?,
                updated_at = ?
            WHERE id = ?
        """, (mp_pay_id, paid_amount, datetime.utcnow(), datetime.utcnow(), pay_id))
        
        # Registrar en audit_logs
        cursor.execute("""
            INSERT INTO audit_logs 
            (payment_id, action, description, performed_by, timestamp, request_data)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            pay_id,
            'payment_approved',
            f'Payment manually approved via force_approve.py for testing',
            'System-ForceApprove',
            datetime.utcnow(),
            f'{{"preference_id": "{mp_pref_id}", "payment_id": "{mp_pay_id}", "amount": {paid_amount}}}'
        ))
        
        conn.commit()
        
        # Verificar actualización
        cursor.execute("""
            SELECT status, mp_payment_id, paid_amount, is_processed, processed_at
            FROM payments 
            WHERE id = ?
        """, (pay_id,))
        
        updated = cursor.fetchone()
        new_status, new_mp_id, new_amount, new_processed, new_processed_at = updated
        
        print(f"\n✅ ¡PAGO APROBADO EXITOSAMENTE!")
        print(f"\n📊 Estado actualizado:")
        print(f"   Estado: {new_status}")
        print(f"   Payment ID: {new_mp_id}")
        print(f"   Monto pagado: ${new_amount}")
        print(f"   Procesado: {'Sí' if new_processed else 'No'}")
        print(f"   Fecha procesamiento: {new_processed_at}")
        
        print(f"\n🎉 Día 2 completado: Pago aprobado y listo para integración con GHL")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Error de SQLite: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {str(e)}")
        return False

def list_pending_payments():
    """Lista todos los pagos pendientes"""
    db_path = get_db_path()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, mp_preference_id, customer_email, expected_amount, status, created_at
            FROM payments 
            WHERE status != 'approved' OR is_processed = 0
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        payments = cursor.fetchall()
        
        if not payments:
            print("✅ No hay pagos pendientes")
            conn.close()
            return
        
        print(f"\n📋 Pagos pendientes ({len(payments)}):\n")
        for payment in payments:
            pay_id, pref_id, email, amount, status, created = payment
            print(f"   ID: {pay_id}")
            print(f"   Preference: {pref_id}")
            print(f"   Email: {email}")
            print(f"   Monto: ${amount}")
            print(f"   Estado: {status}")
            print(f"   Creado: {created}")
            print(f"   ---")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error listando pagos: {str(e)}")

if __name__ == "__main__":
    import sys
    
    print("Force Approve - Aprobacion manual de pagos mock\n")
    
    # Si se pasa un argumento, usarlo como preference_id
    if len(sys.argv) > 1:
        preference_id = sys.argv[1]
        print(f"Preference ID desde argumento: {preference_id}\n")
        success = approve_payment(preference_id=preference_id)
    else:
        # Buscar el pago específico mencionado
        preference_id = "mock_pref_3_1768452317.878706"
        print(f"Aprobando pago: {preference_id}\n")
        success = approve_payment(preference_id=preference_id)
    
    if success:
        print("\n" + "="*60)
        print("OPERACION EXITOSA")
        print("="*60)
        
        # Mostrar pagos pendientes restantes
        print("\nVerificando otros pagos pendientes...")
        list_pending_payments()
        
        print("\nProximos pasos:")
        print("   1. El pago esta aprobado en la BD")
        print("   2. Puedes verificar con: python test_quick_payment.py")
        print("   3. Listo para integracion con GoHighLevel")
        print("   4. Dia 2 completado")
        
        exit(0)
    else:
        print("\nLa operacion fallo")
        print("\nOpciones:")
        print("   - Verifica que el preference_id sea correcto")
        print("   - Lista pagos pendientes para ver IDs disponibles")
        print("   - Usa: python force_approve.py <preference_id>")
        
        exit(1)