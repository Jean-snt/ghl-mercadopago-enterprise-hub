#!/usr/bin/env python3
"""
Script para crear un cliente de prueba para auditoría crítica
"""
import os
import sys
from datetime import datetime

# Agregar el directorio padre al path para importar modelos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import ClientAccount
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mercadopago_enterprise.db")

def create_test_client():
    """Crea un cliente de prueba para testing de auditoría"""
    try:
        engine = create_engine(DATABASE_URL, echo=False)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        db = SessionLocal()
        
        # Verificar si ya existe
        existing_client = db.query(ClientAccount).filter(
            ClientAccount.client_id == "test_client_001"
        ).first()
        
        if existing_client:
            print("✅ Cliente test_client_001 ya existe")
            return existing_client
        
        # Crear nuevo cliente
        test_client = ClientAccount(
            client_id="test_client_001",
            client_name="Cliente de Prueba Auditoría",
            client_email="test@audit.com",
            company_name="Test Audit Company",
            is_active=True,
            default_tag_paid="Pago confirmado",
            auto_tag_payments=True,
            monthly_payment_limit=500
        )
        
        db.add(test_client)
        db.commit()
        
        print("✅ Cliente test_client_001 creado exitosamente")
        print(f"   ID: {test_client.id}")
        print(f"   Nombre: {test_client.client_name}")
        print(f"   Email: {test_client.client_email}")
        
        db.close()
        return test_client
        
    except Exception as e:
        print(f"❌ Error creando cliente: {str(e)}")
        return None

if __name__ == "__main__":
    create_test_client()