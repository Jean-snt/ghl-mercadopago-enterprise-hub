"""
Script para aprobar manualmente pagos mock - Version sin emojis para Windows
"""
import sqlite3
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def get_db_path():
    database_url = os.getenv("DATABASE_URL", "sqlite:///./mercadopago_enterprise.db")
    if database_url.startswith("sqlite:///"):
        return database_url.replace("sqlite:///", "")
    elif database_url.startswith("sqlite://"):
        return database_url.replace("sqlite://", "")
    return "./mercadopago_enterprise.db"

def approve_payment(preference_id):
    db_path = get_db_path()
    print(f"\n[*] Conectando a: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"[ERROR] Base de datos no encontrada")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"[*] Buscando pago: {preference_id}")
        cursor.execute("""
            SELECT id, customer_email, expected_amount, status, mp_payment_id, is_processed
            FROM payments WHERE mp_preference_id = ?
        """, (preference_id,))
        
        payment = cursor.fetchone()
        if not payment:
            print("[ERROR] Pago no encontrado")
            return False
        
        pay_id, email, amount, status, mp_id, processed = payment
        print(f"[OK] Pago encontrado - ID: {pay_id}, Email: {email}, Monto: ${amount}")
        
        if status == 'approved' and processed:
            print("[INFO] Pago ya esta aprobado")
            return True
        
        if not mp_id:
            mp_id = f"mock_payment_{pay_id}_{int(datetime.utcnow().timestamp())}"
        
        print(f"[*] Aprobando pago...")
        cursor.execute("""
            UPDATE payments 
            SET status = 'approved', mp_payment_id = ?, paid_amount = ?,
                is_processed = 1, processed_at = ?, updated_at = ?
            WHERE id = ?
        """, (mp_id, amount, datetime.utcnow(), datetime.utcnow(), pay_id))
        
        cursor.execute("""
            INSERT INTO audit_logs (payment_id, action, description, performed_by, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (pay_id, 'payment_approved', 'Manually approved via script', 'System', datetime.utcnow()))
        
        conn.commit()
        print(f"[SUCCESS] Pago aprobado exitosamente!")
        print(f"[INFO] Payment ID: {mp_id}")
        print(f"[INFO] Estado: approved")
        print(f"[INFO] Procesado: Si")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return False

if __name__ == "__main__":
    print("\n" + "="*60)
    print("FORCE APPROVE - Aprobacion manual de pagos")
    print("="*60)
    
    pref_id = sys.argv[1] if len(sys.argv) > 1 else "mock_pref_3_1768452317.878706"
    print(f"\nPreference ID: {pref_id}")
    
    if approve_payment(pref_id):
        print("\n" + "="*60)
        print("[SUCCESS] Operacion completada")
        print("="*60)
        exit(0)
    else:
        print("\n[ERROR] Operacion fallida")
        exit(1)