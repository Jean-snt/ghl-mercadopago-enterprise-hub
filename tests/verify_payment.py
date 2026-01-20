"""
Script para verificar el estado de un pago
"""
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_path():
    database_url = os.getenv("DATABASE_URL", "sqlite:///./mercadopago_enterprise.db")
    if database_url.startswith("sqlite:///"):
        return database_url.replace("sqlite:///", "")
    elif database_url.startswith("sqlite://"):
        return database_url.replace("sqlite://", "")
    return "./mercadopago_enterprise.db"

def verify_payment(preference_id):
    db_path = get_db_path()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, internal_uuid, customer_email, expected_amount, paid_amount,
                   status, mp_payment_id, is_processed, processed_at, created_at
            FROM payments 
            WHERE mp_preference_id = ?
        """, (preference_id,))
        
        payment = cursor.fetchone()
        
        if not payment:
            print(f"❌ Pago no encontrado: {preference_id}")
            return False
        
        pay_id, uuid, email, expected, paid, status, mp_id, processed, proc_at, created = payment
        
        print(f"\n✅ Pago verificado:")
        print(f"   ID: {pay_id}")
        print(f"   UUID: {uuid}")
        print(f"   Email: {email}")
        print(f"   Monto esperado: ${expected}")
        print(f"   Monto pagado: ${paid}")
        print(f"   Estado: {status}")
        print(f"   Payment ID: {mp_id}")
        print(f"   Procesado: {'✅ Sí' if processed else '❌ No'}")
        print(f"   Fecha procesamiento: {proc_at or 'N/A'}")
        print(f"   Fecha creación: {created}")
        
        if status == 'approved' and processed:
            print(f"\n🎉 ¡Pago aprobado y procesado!")
            print(f"   ✅ Listo para integración con GoHighLevel")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    import sys
    pref_id = sys.argv[1] if len(sys.argv) > 1 else "mock_pref_3_1768452317.878706"
    verify_payment(pref_id)