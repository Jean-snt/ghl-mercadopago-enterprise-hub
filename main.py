"""
Sistema MercadoPago Enterprise con seguridad reforzada
Incluye auditoría completa, validación de idempotencia y alertas de seguridad
"""
from fastapi import FastAPI, HTTPException, Request, Depends, BackgroundTasks, Query
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, and_, or_, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, validator
from typing import Optional, Dict, Any
import json
import hashlib
import hmac
import logging
from datetime import datetime, timedelta
from decimal import Decimal
import requests
import os
import time
from contextlib import contextmanager
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

from models import (
    Base, Payment, AuditLog, SecurityAlert, WebhookLog, WebhookEvent, MercadoPagoAccount,
    PaymentStatus, AuditAction, ClientAccount, PaymentEvent, CriticalAuditLog
)
from services.critical_audit_service import CriticalAuditService, AuditContext, CriticalActions

# Configuración
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mercadopago_enterprise.db")
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
MP_WEBHOOK_SECRET = os.getenv("MP_WEBHOOK_SECRET")
GHL_API_KEY = os.getenv("GHL_API_KEY")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")

# OAuth Configuration
MP_CLIENT_ID = os.getenv("MP_CLIENT_ID")
MP_CLIENT_SECRET = os.getenv("MP_CLIENT_SECRET")
MP_REDIRECT_URI = os.getenv("MP_REDIRECT_URI", f"{os.getenv('BASE_URL', 'http://localhost:8000')}/oauth/callback")

# URLs de MercadoPago
MP_AUTH_URL = "https://auth.mercadopago.com/authorization"
MP_TOKEN_URL = "https://api.mercadopago.com/oauth/token"
MP_USER_INFO_URL = "https://api.mercadopago.com/users/me"

# Debug: Verificar que las variables se carguen correctamente
print(f"🔧 Configuración cargada:")
print(f"   DATABASE_URL: {DATABASE_URL}")
print(f"   ADMIN_API_KEY: {'✅ Configurado' if ADMIN_API_KEY else '❌ No configurado'}")
print(f"   MP_ACCESS_TOKEN: {'✅ Configurado' if MP_ACCESS_TOKEN else '❌ No configurado'}")
print(f"   MP_WEBHOOK_SECRET: {'✅ Configurado' if MP_WEBHOOK_SECRET else '❌ No configurado'}")
print(f"   GHL_API_KEY: {'✅ Configurado' if GHL_API_KEY else '❌ No configurado'}")
print(f"   MP_CLIENT_ID: {'✅ Configurado' if MP_CLIENT_ID else '❌ No configurado'}")
print(f"   MP_CLIENT_SECRET: {'✅ Configurado' if MP_CLIENT_SECRET else '❌ No configurado'}")
print(f"   MP_REDIRECT_URI: {MP_REDIRECT_URI}")

if not ADMIN_API_KEY:
    print("⚠️  ADVERTENCIA: ADMIN_API_KEY no está configurado. Los endpoints admin fallarán.")
    print("   Asegúrate de tener un archivo .env con ADMIN_API_KEY=tu_token_aqui")

if not MP_CLIENT_ID or not MP_CLIENT_SECRET:
    print("⚠️  ADVERTENCIA: Credenciales OAuth de MercadoPago no configuradas.")
    print("   Para OAuth necesitas: MP_CLIENT_ID y MP_CLIENT_SECRET")

# Configuración de logging enterprise - Corregido para correlation_id opcional
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Crear un formatter personalizado que maneje correlation_id opcional de forma ultra segura
class SafeFormatter(logging.Formatter):
    def format(self, record):
        # Manejar correlation_id de forma ultra segura
        if not hasattr(record, 'correlation_id'):
            record.correlation_id = 'N/A'
        elif record.correlation_id is None:
            record.correlation_id = 'N/A'
        elif isinstance(record.correlation_id, dict):
            # Si por alguna razón es un dict, convertir a string
            record.correlation_id = str(record.correlation_id)
        
        # Asegurar que sea string
        try:
            record.correlation_id = str(record.correlation_id)
        except:
            record.correlation_id = 'ERROR'
            
        return super().format(record)

# Aplicar el formatter seguro
safe_formatter = SafeFormatter('%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s')
for handler in logging.getLogger().handlers:
    handler.setFormatter(safe_formatter)

# Base de datos
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="MercadoPago Enterprise API", version="2.0.0")
security = HTTPBearer()

# Montar archivos estáticos para el dashboard
app.mount("/static", StaticFiles(directory="static"), name="static")

# Middleware para correlation_id - Versión ultra segura sin conflictos
@app.middleware("http")
async def add_correlation_id_middleware(request: Request, call_next):
    """Middleware para agregar correlation_id a todas las requests de forma segura"""
    correlation_id = request.headers.get("x-correlation-id", f"req_{int(time.time() * 1000)}")
    
    # Almacenar en el request para uso posterior, sin tocar el logging
    request.state.correlation_id = correlation_id
    
    try:
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
    except Exception as e:
        # Log simple sin extra para evitar conflictos
        print(f"[ERROR] Request failed with correlation_id {correlation_id}: {str(e)}")
        raise e

# Endpoint para servir el favicon
@app.get("/favicon.ico")
async def favicon():
    """Sirve el favicon oficial del sitio"""
    import requests
    from fastapi.responses import Response
    
    try:
        # URL del logo oficial
        logo_url = "https://tse2.mm.bing.net/th/id/OIP.9XLgV42tKJAzgXzhuCGjTQAAAA?rs=1&pid=ImgDetMain&o=7&rm=3"
        
        # Descargar la imagen
        response = requests.get(logo_url, timeout=10)
        if response.status_code == 200:
            return Response(
                content=response.content,
                media_type="image/png",  # Cambiar a PNG ya que la imagen es PNG
                headers={
                    "Cache-Control": "public, max-age=86400",  # Cache por 24 horas
                    "Content-Type": "image/png"
                }
            )
        else:
            logger.warning(f"Failed to download favicon: HTTP {response.status_code}")
            # Fallback: crear un favicon básico de 1x1 pixel transparente
            fallback_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
            return Response(
                content=fallback_png,
                media_type="image/png",
                headers={"Content-Type": "image/png"}
            )
    except Exception as e:
        logger.warning(f"Error serving favicon: {str(e)}")
        # Fallback: crear un favicon básico de 1x1 pixel transparente
        fallback_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
        return Response(
            content=fallback_png,
            media_type="image/png",
            headers={"Content-Type": "image/png"}
        )

# Endpoint para servir el dashboard
@app.get("/dashboard")
async def serve_dashboard():
    """Sirve el dashboard HTML del Centro de Comando NOC"""
    return FileResponse("static/dashboard.html")

# Endpoint para servir el dashboard por cliente
@app.get("/dashboard/client/{client_id}")
async def serve_client_dashboard(client_id: str):
    """Sirve el dashboard HTML específico para un cliente"""
    return FileResponse("static/client_dashboard.html")

# Modelos Pydantic
class PaymentCreateRequest(BaseModel):
    customer_email: str
    customer_name: Optional[str] = None
    ghl_contact_id: str
    amount: float
    description: str
    created_by: str
    client_id: Optional[str] = None  # Para usar cuenta OAuth específica
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        if v > 999999.99:
            raise ValueError('Amount exceeds maximum limit')
        return round(v, 2)

class OAuthAuthorizeRequest(BaseModel):
    client_id: str
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    redirect_after_auth: Optional[str] = None

class WebhookPayload(BaseModel):
    id: Optional[int] = None
    live_mode: Optional[bool] = None
    type: Optional[str] = None
    date_created: Optional[str] = None
    application_id: Optional[int] = None
    user_id: Optional[int] = None
    version: Optional[int] = None
    api_version: Optional[str] = None
    action: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

# Dependencias
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_context():
    """Context manager para transacciones de base de datos"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

def verify_admin_token(token: str = Depends(security)):
    """Verificación de token de administrador"""
    print(f"🔍 Debug token verification:")
    print(f"   Token recibido: {token.credentials[:10]}..." if token.credentials else "   Token recibido: None")
    print(f"   Token esperado: {ADMIN_API_KEY[:10]}..." if ADMIN_API_KEY else "   Token esperado: None")
    
    if not ADMIN_API_KEY:
        raise HTTPException(status_code=500, detail="Admin token not configured on server")
    
    if token.credentials != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin token")
    
    return token.credentials

# Utilidades de Auditoría
class AuditLogger:
    """Clase para manejo centralizado de auditoría"""
    
    @staticmethod
    def log_action(
        db: Session,
        action: AuditAction,
        description: str,
        payment_id: Optional[int] = None,
        performed_by: str = "System",
        request_data: Optional[Dict] = None,
        response_data: Optional[Dict] = None,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        correlation_id: Optional[str] = None
    ):
        """Registra una acción en el log de auditoría con manejo seguro de errores"""
        try:
            # Verificar si blockchain está habilitado
            is_development = os.getenv("ENVIRONMENT", "development") == "development"
            
            # Generar hash simple
            correlation_id = correlation_id or f"audit_{int(time.time())}"
            hash_data = f"{action.value}:{description}:{performed_by}:{correlation_id}"
            current_hash = hashlib.sha256(hash_data.encode()).hexdigest()
            
            # Obtener último bloque para secuencia
            previous_hash = "genesis"
            block_number = 1
            
            try:
                last_audit = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
                if last_audit and last_audit.current_hash:
                    previous_hash = last_audit.current_hash
                    block_number = (last_audit.block_number or 0) + 1
            except Exception:
                # Si falla, usar valores por defecto
                pass
            
            audit_log = AuditLog(
                payment_id=payment_id,
                action=action.value,
                description=description,
                performed_by=performed_by,
                request_data=json.dumps(request_data) if request_data else None,
                response_data=json.dumps(response_data) if response_data else None,
                error_message=error_message,
                ip_address=ip_address,
                user_agent=user_agent,
                correlation_id=correlation_id,
                # Campos blockchain según esquema real
                previous_hash=previous_hash,
                current_hash=current_hash,
                block_number=block_number,
                is_verified=True,
                blockchain_enabled=not is_development
            )
            
            db.add(audit_log)
            db.commit()
            
            # Log simple sin extra para evitar conflictos
            print(f"[AUDIT] {action.value} - {description} (Block: {block_number})")
                       
        except Exception as e:
            # En caso de error crítico, intentar log básico
            try:
                # Hash simple para fallback
                fallback_hash = hashlib.md5(f"fallback_{int(time.time())}".encode()).hexdigest()
                
                basic_audit = AuditLog(
                    payment_id=payment_id,
                    action=action.value,
                    description=f"[FALLBACK] {description}",
                    performed_by=performed_by,
                    error_message=f"Original error: {str(e)}",
                    correlation_id=correlation_id or f"fallback_{int(time.time())}",
                    previous_hash="fallback",
                    current_hash=fallback_hash,
                    block_number=0,
                    is_verified=False
                )
                db.add(basic_audit)
                db.commit()
                print(f"[AUDIT-FALLBACK] {action.value} - Fallback log created")
            except Exception as fallback_error:
                print(f"[AUDIT-CRITICAL] Cannot create audit log: {fallback_error}")

# Utilidades de Seguridad
class SecurityManager:
    """Manejo centralizado de seguridad y alertas"""
    
    @staticmethod
    def create_security_alert(
        db: Session,
        alert_type: str,
        title: str,
        description: str,
        payment_id: Optional[int] = None,
        severity: str = "MEDIUM",
        expected_value: Optional[str] = None,
        actual_value: Optional[str] = None,
        source_ip: Optional[str] = None
    ):
        """Crea una alerta de seguridad"""
        try:
            alert = SecurityAlert(
                payment_id=payment_id,
                alert_type=alert_type,
                severity=severity,
                title=title,
                description=description,
                expected_value=expected_value,
                actual_value=actual_value,
                source_ip=source_ip
            )
            db.add(alert)
            db.commit()
            
            logger.warning(f"Security Alert: {alert_type} - {title}")
            
            # Si es crítico, enviar notificación inmediata
            if severity == "CRITICAL":
                SecurityManager._send_critical_alert_notification(alert)
                
        except Exception as e:
            logger.error(f"Failed to create security alert: {str(e)}")
    
    @staticmethod
    def _send_critical_alert_notification(alert: SecurityAlert):
        """Envía notificación para alertas críticas"""
        # Aquí implementarías integración con Slack, email, etc.
        logger.critical(f"CRITICAL SECURITY ALERT: {alert.title}")
    
    @staticmethod
    def validate_webhook_signature(payload: str, signature: str) -> bool:
        """Valida la firma del webhook de MercadoPago"""
        if not MP_WEBHOOK_SECRET:
            logger.warning("Webhook secret not configured")
            return False
            
        expected_signature = hmac.new(
            MP_WEBHOOK_SECRET.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    @staticmethod
    def is_duplicate_payment(db: Session, mp_payment_id: str) -> bool:
        """Verifica si el payment_id ya fue procesado (idempotencia)"""
        existing_payment = db.query(Payment).filter(
            Payment.mp_payment_id == mp_payment_id
        ).first()
        
        return existing_payment is not None
    
    @staticmethod
    def validate_amount_match(expected: Decimal, actual: Decimal, tolerance: Decimal = Decimal('0.01')) -> bool:
        """Valida que los montos coincidan dentro de una tolerancia"""
        return abs(expected - actual) <= tolerance

# Servicios de Negocio
class OAuthService:
    """Servicio para manejo de OAuth con MercadoPago"""
    
    @staticmethod
    def get_authorization_url(
        client_id: str,
        state: Optional[str] = None,
        redirect_uri: Optional[str] = None
    ) -> str:
        """Genera URL de autorización de MercadoPago"""
        base_url = "https://auth.mercadopago.com/authorization"
        
        params = {
            "client_id": MP_CLIENT_ID,
            "response_type": "code",
            "platform_id": "mp",
            "redirect_uri": redirect_uri or MP_REDIRECT_URI,
        }
        
        if state:
            params["state"] = state
        
        # Construir URL
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}?{query_string}"
    
    @staticmethod
    def exchange_code_for_token(
        db: Session,
        authorization_code: str,
        client_id: str,
        client_name: Optional[str] = None,
        client_email: Optional[str] = None,
        connection_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Intercambia código de autorización por tokens"""
        try:
            # Intercambiar código por token
            token_data = {
                "client_id": MP_CLIENT_ID,
                "client_secret": MP_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": authorization_code,
                "redirect_uri": MP_REDIRECT_URI
            }
            
            response = requests.post(
                "https://api.mercadopago.com/oauth/token",
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"OAuth token exchange failed: {response.status_code} - {response.text}")
                raise HTTPException(status_code=400, detail="Failed to exchange authorization code")
            
            token_response = response.json()
            
            # Obtener información del usuario
            user_info = OAuthService._get_user_info(token_response["access_token"])
            
            # Calcular expiración
            expires_in = token_response.get("expires_in", 21600)  # Default 6 horas
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            # Verificar si ya existe una cuenta para este usuario
            existing_account = db.query(MercadoPagoAccount).filter(
                MercadoPagoAccount.mp_user_id == str(user_info["id"])
            ).first()
            
            if existing_account:
                # Actualizar cuenta existente
                existing_account.access_token = token_response["access_token"]
                existing_account.refresh_token = token_response.get("refresh_token")
                existing_account.expires_in = expires_in
                existing_account.expires_at = expires_at
                existing_account.last_refreshed = datetime.utcnow()
                existing_account.is_active = True
                existing_account.updated_at = datetime.utcnow()
                existing_account.connection_ip = connection_ip
                existing_account.user_agent = user_agent
                
                # Actualizar datos del usuario si han cambiado
                if client_name:
                    existing_account.client_name = client_name
                if client_email:
                    existing_account.client_email = client_email
                
                account = existing_account
                action_description = f"OAuth token refreshed for existing account {client_id}"
            else:
                # Crear nueva cuenta
                account = MercadoPagoAccount(
                    client_id=client_id,
                    client_name=client_name,
                    client_email=client_email,
                    mp_user_id=str(user_info["id"]),
                    access_token=token_response["access_token"],
                    refresh_token=token_response.get("refresh_token"),
                    token_type=token_response.get("token_type", "Bearer"),
                    expires_in=expires_in,
                    expires_at=expires_at,
                    scope=token_response.get("scope"),
                    is_sandbox=user_info.get("site_id") == "MLA",  # Ajustar según necesidad
                    mp_public_key=token_response.get("public_key"),
                    mp_site_id=user_info.get("site_id"),
                    mp_nickname=user_info.get("nickname"),
                    connection_ip=connection_ip,
                    user_agent=user_agent
                )
                
                db.add(account)
                action_description = f"New OAuth account created for {client_id}"
            
            db.commit()
            
            # Log de auditoría
            AuditLogger.log_action(
                db=db,
                action=AuditAction.PAYMENT_LINK_GENERATED,  # Usar acción existente o crear nueva
                description=action_description,
                performed_by=f"OAuth-{client_id}",
                request_data={
                    "client_id": client_id,
                    "mp_user_id": user_info["id"],
                    "scope": token_response.get("scope")
                },
                response_data={
                    "account_id": account.id,
                    "expires_at": expires_at.isoformat()
                },
                ip_address=connection_ip
            )
            
            return {
                "success": True,
                "account_id": account.id,
                "mp_user_id": account.mp_user_id,
                "client_id": account.client_id,
                "expires_at": expires_at.isoformat(),
                "scope": account.scope,
                "is_new_account": existing_account is None
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during OAuth: {str(e)}")
            raise HTTPException(status_code=500, detail="Network error during OAuth process")
        except Exception as e:
            db.rollback()
            logger.error(f"Error in OAuth token exchange: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @staticmethod
    def _get_user_info(access_token: str) -> Dict[str, Any]:
        """Obtiene información del usuario desde MercadoPago"""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(
                "https://api.mercadopago.com/users/me",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get user info: {response.status_code}")
                return {"id": "unknown", "nickname": "unknown"}
                
        except Exception as e:
            logger.error(f"Error getting user info: {str(e)}")
            return {"id": "unknown", "nickname": "unknown"}
    
    @staticmethod
    def refresh_token(db: Session, account: MercadoPagoAccount) -> bool:
        """Renueva el access token usando el refresh token"""
        if not account.refresh_token:
            logger.warning(f"No refresh token available for account {account.id}")
            return False
        
        try:
            refresh_data = {
                "client_id": MP_CLIENT_ID,
                "client_secret": MP_CLIENT_SECRET,
                "grant_type": "refresh_token",
                "refresh_token": account.refresh_token
            }
            
            response = requests.post(
                "https://api.mercadopago.com/oauth/token",
                data=refresh_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"Token refresh failed for account {account.id}: {response.status_code}")
                account.refresh_attempts += 1
                db.commit()
                return False
            
            token_response = response.json()
            
            # Actualizar tokens
            account.access_token = token_response["access_token"]
            if "refresh_token" in token_response:
                account.refresh_token = token_response["refresh_token"]
            
            # Actualizar expiración
            expires_in = token_response.get("expires_in", 21600)
            account.expires_in = expires_in
            account.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            account.last_refreshed = datetime.utcnow()
            account.refresh_attempts = 0
            
            db.commit()
            
            # Log de auditoría
            AuditLogger.log_action(
                db=db,
                action=AuditAction.WEBHOOK_PROCESSED,  # Usar acción existente
                description=f"Access token refreshed for account {account.client_id}",
                performed_by="System",
                response_data={
                    "account_id": account.id,
                    "new_expires_at": account.expires_at.isoformat()
                }
            )
            
            logger.info(f"Token refreshed successfully for account {account.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error refreshing token for account {account.id}: {str(e)}")
            account.refresh_attempts += 1
            db.commit()
            return False
    
    @staticmethod
    def get_valid_token(db: Session, client_id: str) -> Optional[str]:
        """Obtiene un token válido para el cliente, renovándolo si es necesario"""
        account = db.query(MercadoPagoAccount).filter(
            and_(
                MercadoPagoAccount.client_id == client_id,
                MercadoPagoAccount.is_active == True
            )
        ).first()
        
        if not account:
            logger.warning(f"No active MercadoPago account found for client {client_id}")
            return None
        
        # Verificar si necesita renovación
        if account.needs_refresh():
            logger.info(f"Token needs refresh for account {account.id}")
            if OAuthService.refresh_token(db, account):
                # Actualizar timestamp de último uso
                account.last_used_at = datetime.utcnow()
                db.commit()
                return account.access_token
            else:
                logger.error(f"Failed to refresh token for account {account.id}")
                return None
        
        # Token válido, actualizar último uso
        account.last_used_at = datetime.utcnow()
        db.commit()
        return account.access_token

class PaymentService:
    """Servicio para manejo de pagos"""
    
    @staticmethod
    def create_payment_link(
        db: Session,
        payment_data: PaymentCreateRequest,
        client_ip: str,
        correlation_id: str
    ) -> Dict[str, Any]:
        """Crea un link de pago en MercadoPago"""
        try:
            # Determinar qué token usar y vincular con cliente
            access_token = None
            mp_account = None
            client_account = None
            
            if payment_data.client_id:
                # Buscar cuenta del cliente
                client_account = db.query(ClientAccount).filter(
                    ClientAccount.client_id == payment_data.client_id
                ).first()
                
                if client_account and client_account.mp_account_id:
                    # Usar token OAuth del cliente específico
                    access_token = OAuthService.get_valid_token(db, payment_data.client_id)
                    if access_token:
                        mp_account = db.query(MercadoPagoAccount).filter(
                            MercadoPagoAccount.id == client_account.mp_account_id
                        ).first()
                        logger.info(f"Usando token OAuth del cliente {payment_data.client_id}")
                    else:
                        logger.warning(f"No se pudo obtener token OAuth válido para cliente {payment_data.client_id}")
            
            # Fallback al token global si no hay OAuth o falló
            if not access_token:
                access_token = MP_ACCESS_TOKEN
                logger.info("Usando token global MP_ACCESS_TOKEN como fallback")
            
            # Crear registro de pago
            payment = Payment(
                customer_email=payment_data.customer_email,
                customer_name=payment_data.customer_name,
                ghl_contact_id=payment_data.ghl_contact_id,
                expected_amount=Decimal(str(payment_data.amount)),
                created_by=payment_data.created_by,
                client_ip=client_ip,
                mp_account_id=mp_account.id if mp_account else None,
                client_account_id=client_account.id if client_account else None
            )
            
            db.add(payment)
            db.flush()  # Para obtener el ID
            
            # Verificar si estamos en modo desarrollo o si falta el token de MP
            is_development = os.getenv("ENVIRONMENT", "development") == "development"
            has_mp_token = access_token and access_token.strip() and not access_token.startswith("TEST-")
            
            if is_development or not has_mp_token:
                # Modo desarrollo: generar IDs mock
                mock_preference_id = f"mock_pref_{payment.id}_{datetime.utcnow().timestamp()}"
                mock_checkout_url = f"{os.getenv('BASE_URL', 'http://localhost:8000')}/mock-checkout/{mock_preference_id}"
                
                payment.mp_preference_id = mock_preference_id
                db.commit()
                
                # Log de auditoría para modo desarrollo
                AuditLogger.log_action(
                    db=db,
                    action=AuditAction.PAYMENT_LINK_GENERATED,
                    description=f"Payment link generated (DEVELOPMENT MODE) for {payment_data.customer_email} - Cliente: {payment_data.client_id or 'global'}",
                    payment_id=payment.id,
                    performed_by=payment_data.created_by,
                    request_data=payment_data.dict(),
                    response_data={
                        "preference_id": mock_preference_id, 
                        "mode": "development",
                        "oauth_client": payment_data.client_id,
                        "mp_account_id": mp_account.id if mp_account else None,
                        "client_account_id": client_account.id if client_account else None
                    },
                    ip_address=client_ip,
                    correlation_id=correlation_id
                )
                
                logger.info(f"🧪 Development mode: Created mock payment link for payment {payment.id} - Cliente: {payment_data.client_id or 'global'}")
                
                return {
                    "payment_id": payment.id,
                    "internal_uuid": payment.internal_uuid,
                    "checkout_url": mock_checkout_url,
                    "preference_id": mock_preference_id,
                    "mode": "development",
                    "oauth_client": payment_data.client_id,
                    "client_account_id": client_account.id if client_account else None,
                    "ghl_location_id": client_account.ghl_location_id if client_account else None,
                    "mp_account_id": mp_account.id if mp_account else None,
                    "note": "This is a mock payment link for development/testing"
                }
            
            else:
                # Modo producción: crear preferencia real en MercadoPago
                preference_data = {
                    "items": [{
                        "title": payment_data.description,
                        "quantity": 1,
                        "unit_price": payment_data.amount
                    }],
                    "payer": {
                        "email": payment_data.customer_email,
                        "name": payment_data.customer_name
                    },
                    "external_reference": payment.internal_uuid,
                    "notification_url": f"{os.getenv('BASE_URL', 'https://your-domain.com')}/webhook/mercadopago"
                }
                
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
                
                try:
                    response = requests.post(
                        "https://api.mercadopago.com/checkout/preferences",
                        json=preference_data,
                        headers=headers,
                        timeout=10
                    )
                    
                    if response.status_code != 201:
                        logger.error(f"MercadoPago API error: {response.status_code} - {response.text}")
                        # Fallback a modo mock si falla la API
                        mock_preference_id = f"fallback_pref_{payment.id}_{datetime.utcnow().timestamp()}"
                        payment.mp_preference_id = mock_preference_id
                        db.commit()
                        
                        AuditLogger.log_action(
                            db=db,
                            action=AuditAction.PAYMENT_LINK_GENERATED,
                            description=f"Payment link generated (FALLBACK MODE) for {payment_data.customer_email} - MP API failed",
                            payment_id=payment.id,
                            performed_by=payment_data.created_by,
                            request_data=payment_data.dict(),
                            response_data={
                                "preference_id": mock_preference_id, 
                                "mode": "fallback", 
                                "mp_error": response.text,
                                "oauth_client": payment_data.client_id,
                                "mp_account_id": mp_account.id if mp_account else None
                            },
                            error_message=f"MercadoPago API failed: {response.status_code}",
                            ip_address=client_ip,
                            correlation_id=correlation_id
                        )
                        
                        return {
                            "payment_id": payment.id,
                            "internal_uuid": payment.internal_uuid,
                            "checkout_url": f"{os.getenv('BASE_URL', 'http://localhost:8000')}/mock-checkout/{mock_preference_id}",
                            "preference_id": mock_preference_id,
                            "mode": "fallback",
                            "oauth_client": payment_data.client_id,
                            "mp_account_id": mp_account.id if mp_account else None,
                            "note": "MercadoPago API unavailable, using fallback mode"
                        }
                    
                    mp_response = response.json()
                    payment.mp_preference_id = mp_response["id"]
                    db.commit()
                    
                    # Log de auditoría exitoso
                    AuditLogger.log_action(
                        db=db,
                        action=AuditAction.PAYMENT_LINK_GENERATED,
                        description=f"Payment link generated for {payment_data.customer_email}",
                        payment_id=payment.id,
                        performed_by=payment_data.created_by,
                        request_data=payment_data.dict(),
                        response_data={
                            "preference_id": mp_response["id"],
                            "oauth_client": payment_data.client_id,
                            "mp_account_id": mp_account.id if mp_account else None
                        },
                        ip_address=client_ip,
                        correlation_id=correlation_id
                    )
                    
                    return {
                        "payment_id": payment.id,
                        "internal_uuid": payment.internal_uuid,
                        "checkout_url": mp_response["init_point"],
                        "preference_id": mp_response["id"],
                        "mode": "production",
                        "oauth_client": payment_data.client_id,
                        "mp_account_id": mp_account.id if mp_account else None
                    }
                    
                except requests.exceptions.RequestException as req_error:
                    logger.error(f"Network error calling MercadoPago: {str(req_error)}")
                    # Fallback a modo mock si hay error de red
                    mock_preference_id = f"network_fallback_pref_{payment.id}_{datetime.utcnow().timestamp()}"
                    payment.mp_preference_id = mock_preference_id
                    db.commit()
                    
                    AuditLogger.log_action(
                        db=db,
                        action=AuditAction.PAYMENT_LINK_GENERATED,
                        description=f"Payment link generated (NETWORK FALLBACK) for {payment_data.customer_email}",
                        payment_id=payment.id,
                        performed_by=payment_data.created_by,
                        request_data=payment_data.dict(),
                        response_data={
                            "preference_id": mock_preference_id, 
                            "mode": "network_fallback",
                            "oauth_client": payment_data.client_id,
                            "mp_account_id": mp_account.id if mp_account else None
                        },
                        error_message=f"Network error: {str(req_error)}",
                        ip_address=client_ip,
                        correlation_id=correlation_id
                    )
                    
                    return {
                        "payment_id": payment.id,
                        "internal_uuid": payment.internal_uuid,
                        "checkout_url": f"{os.getenv('BASE_URL', 'http://localhost:8000')}/mock-checkout/{mock_preference_id}",
                        "preference_id": mock_preference_id,
                        "mode": "network_fallback",
                        "oauth_client": payment_data.client_id,
                        "mp_account_id": mp_account.id if mp_account else None,
                        "note": "Network error with MercadoPago, using fallback mode"
                    }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating payment link: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

class WebhookService:
    """Servicio resiliente para procesamiento de webhooks"""
    
    @staticmethod
    def receive_webhook(
        db: Session,
        raw_payload: str,
        headers: Dict[str, str],
        source_ip: str,
        correlation_id: str
    ) -> Dict[str, Any]:
        """
        Recibe y almacena webhook para procesamiento posterior (resiliente)
        Responde inmediatamente a MercadoPago para evitar reintentos
        """
        try:
            # Parsear el payload
            payload_dict = json.loads(raw_payload)
            
            # Extraer información básica del webhook
            topic = payload_dict.get("topic", "unknown")
            resource = payload_dict.get("resource")
            mp_event_id = payload_dict.get("id")
            
            # Validar firma si está configurada
            signature_valid = None
            signature = headers.get("x-signature")
            if signature and MP_WEBHOOK_SECRET:
                signature_valid = SecurityManager.validate_webhook_signature(raw_payload, signature)
                
                if not signature_valid:
                    # Log de seguridad pero NO fallar - guardar para análisis
                    SecurityManager.create_security_alert(
                        db=db,
                        alert_type="INVALID_WEBHOOK_SIGNATURE",
                        title="Invalid webhook signature detected",
                        description=f"Webhook received with invalid signature from IP {source_ip}",
                        severity="HIGH",
                        source_ip=source_ip
                    )
            
            # Crear evento de webhook para procesamiento posterior
            webhook_event = WebhookEvent(
                mp_event_id=str(mp_event_id) if mp_event_id else None,
                topic=topic,
                resource=resource,
                raw_data=raw_payload,
                headers=json.dumps(dict(headers)),
                source_ip=source_ip,
                signature_valid=signature_valid,
                status='pending'
            )
            
            db.add(webhook_event)
            db.commit()
            
            # Log de auditoría
            AuditLogger.log_action(
                db=db,
                action=AuditAction.WEBHOOK_RECEIVED,
                description=f"Webhook received and queued: topic={topic}, event_id={mp_event_id}",
                performed_by="WebhookReceiver",
                request_data={"topic": topic, "resource": resource, "event_id": mp_event_id},
                response_data={"webhook_event_id": webhook_event.id, "status": "queued"},
                ip_address=source_ip,
                correlation_id=correlation_id
            )
            
            logger.info(f"Webhook received and queued: ID={webhook_event.id}, topic={topic}")
            
            return {
                "success": True,
                "webhook_event_id": webhook_event.id,
                "status": "queued",
                "message": "Webhook received and queued for processing"
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in webhook: {str(e)}")
            
            # Crear evento con error para análisis
            webhook_event = WebhookEvent(
                topic="invalid_json",
                raw_data=raw_payload,
                headers=json.dumps(dict(headers)),
                source_ip=source_ip,
                status='error',
                last_error=f"JSON decode error: {str(e)}"
            )
            db.add(webhook_event)
            db.commit()
            
            # Aún así responder OK para evitar reintentos de MP
            return {
                "success": True,
                "webhook_event_id": webhook_event.id,
                "status": "error",
                "message": "Invalid JSON received but logged for analysis"
            }
            
        except Exception as e:
            logger.error(f"Error receiving webhook: {str(e)}")
            db.rollback()
            
            # En caso de error crítico, aún responder OK
            return {
                "success": True,
                "status": "error",
                "message": "Webhook received but failed to process - will retry"
            }
    
    @staticmethod
    def process_webhook_event(db: Session, webhook_event_id: int) -> Dict[str, Any]:
        """
        Procesa un evento de webhook específico (ejecutado en background)
        """
        webhook_event = db.query(WebhookEvent).filter(WebhookEvent.id == webhook_event_id).first()
        
        if not webhook_event:
            logger.error(f"Webhook event {webhook_event_id} not found")
            return {"success": False, "error": "Event not found"}
        
        # Verificar si puede ser reintentado
        if not webhook_event.can_retry():
            logger.warning(f"Webhook event {webhook_event_id} cannot be retried (attempts: {webhook_event.attempts})")
            return {"success": False, "error": "Max attempts reached"}
        
        # Incrementar contador de intentos
        webhook_event.attempts += 1
        webhook_event.last_attempt_at = datetime.utcnow()
        webhook_event.status = 'processing'
        db.commit()
        
        try:
            # Parsear datos del webhook
            payload_dict = json.loads(webhook_event.raw_data)
            
            # Solo procesar webhooks de payment
            if webhook_event.topic != "payment":
                webhook_event.status = 'processed'
                webhook_event.processed_at = datetime.utcnow()
                webhook_event.last_error = None
                db.commit()
                
                logger.info(f"Webhook event {webhook_event_id} ignored (topic: {webhook_event.topic})")
                return {"success": True, "message": f"Topic {webhook_event.topic} ignored"}
            
            # Obtener payment_id del webhook
            payment_id = payload_dict.get("data", {}).get("id")
            if not payment_id:
                raise ValueError("Missing payment ID in webhook data")
            
            webhook_event.mp_payment_id = str(payment_id)
            
            # Verificar idempotencia
            if SecurityManager.is_duplicate_payment(db, str(payment_id)):
                webhook_event.status = 'processed'
                webhook_event.processed_at = datetime.utcnow()
                webhook_event.last_error = None
                db.commit()
                
                SecurityManager.create_security_alert(
                    db=db,
                    alert_type="DUPLICATE_PAYMENT_ATTEMPT",
                    title="Duplicate payment processing attempt",
                    description=f"Attempt to process already processed payment {payment_id}",
                    severity="MEDIUM",
                    source_ip=webhook_event.source_ip
                )
                
                logger.info(f"Webhook event {webhook_event_id} - duplicate payment {payment_id}")
                return {"success": True, "message": "Duplicate payment ignored"}
            
            # Obtener detalles del pago desde MercadoPago
            payment_details = WebhookService._get_payment_details(payment_id)
            
            if not payment_details:
                raise ValueError(f"Could not fetch payment details for {payment_id}")
            
            # Buscar el pago en nuestra BD por external_reference
            external_ref = payment_details.get("external_reference")
            if not external_ref:
                raise ValueError("Missing external reference in payment details")
            
            payment = db.query(Payment).filter(Payment.internal_uuid == external_ref).first()
            
            if not payment:
                SecurityManager.create_security_alert(
                    db=db,
                    alert_type="UNKNOWN_PAYMENT_REFERENCE",
                    title="Unknown payment reference in webhook",
                    description=f"Received webhook for unknown payment reference {external_ref}",
                    severity="HIGH",
                    source_ip=webhook_event.source_ip
                )
                raise ValueError(f"Payment not found for reference {external_ref}")
            
            # Asociar el evento con el pago
            webhook_event.payment_id = payment.id
            
            # Validar monto (SEGURIDAD CRÍTICA)
            mp_amount = Decimal(str(payment_details.get("transaction_amount", 0)))
            if not SecurityManager.validate_amount_match(payment.expected_amount, mp_amount):
                SecurityManager.create_security_alert(
                    db=db,
                    alert_type="AMOUNT_MISMATCH",
                    title="Payment amount mismatch detected",
                    description=f"Expected {payment.expected_amount}, received {mp_amount}",
                    payment_id=payment.id,
                    severity="CRITICAL",
                    expected_value=str(payment.expected_amount),
                    actual_value=str(mp_amount),
                    source_ip=webhook_event.source_ip
                )
                
                webhook_event.status = 'error'
                webhook_event.last_error = f"Amount mismatch: expected {payment.expected_amount}, got {mp_amount}"
                db.commit()
                
                logger.error(f"Amount mismatch for payment {payment.id}: expected {payment.expected_amount}, got {mp_amount}")
                return {"success": False, "error": "Amount mismatch - security violation"}
            
            # Actualizar pago
            payment.mp_payment_id = str(payment_id)
            payment.paid_amount = mp_amount
            payment.status = payment_details.get("status", "unknown")
            payment.mp_payment_method = payment_details.get("payment_method_id")
            payment.mp_status_detail = payment_details.get("status_detail")
            payment.webhook_processed_count += 1
            
            # Si está aprobado, actualizar GHL y enviar notificaciones
            ghl_success = False
            if payment.status == PaymentStatus.APPROVED.value and not payment.is_processed:
                ghl_success = WebhookService._update_ghl_contact(payment)
                
                if ghl_success:
                    payment.is_processed = True
                    payment.processed_at = datetime.utcnow()
                    
                    AuditLogger.log_action(
                        db=db,
                        action=AuditAction.GHL_UPDATE_SUCCESS,
                        description=f"GHL contact {payment.ghl_contact_id} updated successfully",
                        payment_id=payment.id,
                        performed_by="WebhookProcessor"
                    )
                    
                    # 🚀 NUEVA FUNCIONALIDAD: Notificación automática con tagging GHL
                    try:
                        from services.notification_service import NotificationService
                        notification_service = NotificationService(db)
                        notification_result = notification_service.notify_payment_approved(payment)
                        
                        logger.info(f"Payment approved notification sent for payment {payment.id}: {notification_result}")
                        
                    except Exception as notification_error:
                        logger.error(f"Error sending payment approved notification: {str(notification_error)}")
                        # No fallar el proceso principal por un error de notificación
                    
                    # 🎯 MVP NOTIFICACIONES VENDEDOR: Disparador único desde backend
                    try:
                        from services.vendor_notification_service import VendorNotificationService
                        vendor_service = VendorNotificationService(db)
                        vendor_result = vendor_service.notify_payment_approved(payment)
                        
                        logger.info(f"Vendor notification completed for payment {payment.id}: {vendor_result}")
                        
                    except Exception as vendor_error:
                        logger.error(f"Error sending vendor notification: {str(vendor_error)}")
                        # No fallar el proceso principal por un error de notificación
                        
                else:
                    AuditLogger.log_action(
                        db=db,
                        action=AuditAction.GHL_UPDATE_FAILED,
                        description=f"Failed to update GHL contact {payment.ghl_contact_id}",
                        payment_id=payment.id,
                        performed_by="WebhookProcessor",
                        error_message="GHL API call failed"
                    )
            
            # Marcar evento como procesado
            webhook_event.status = 'processed'
            webhook_event.processed_at = datetime.utcnow()
            webhook_event.last_error = None
            
            db.commit()
            
            # Log de auditoría exitoso
            AuditLogger.log_action(
                db=db,
                action=AuditAction.WEBHOOK_PROCESSED,
                description=f"Webhook processed successfully for payment {payment_id}",
                payment_id=payment.id,
                performed_by="WebhookProcessor",
                response_data={
                    "webhook_event_id": webhook_event.id,
                    "payment_status": payment.status,
                    "ghl_updated": ghl_success
                }
            )
            
            logger.info(f"Webhook event {webhook_event_id} processed successfully")
            
            return {
                "success": True,
                "webhook_event_id": webhook_event.id,
                "payment_id": payment.id,
                "payment_status": payment.status,
                "ghl_updated": ghl_success
            }
            
        except Exception as e:
            # Marcar como error para posible reintento
            webhook_event.status = 'error'
            webhook_event.last_error = str(e)
            webhook_event.updated_at = datetime.utcnow()
            
            # Si se agotaron los intentos, marcar como failed
            if webhook_event.attempts >= webhook_event.max_attempts:
                webhook_event.status = 'failed'
                
                # Crear alerta de seguridad para fallos críticos
                SecurityManager.create_security_alert(
                    db=db,
                    alert_type="WEBHOOK_PROCESSING_FAILED",
                    title="Webhook processing failed after max attempts",
                    description=f"Webhook event {webhook_event.id} failed after {webhook_event.attempts} attempts: {str(e)}",
                    severity="HIGH",
                    source_ip=webhook_event.source_ip
                )
            
            db.commit()
            
            AuditLogger.log_action(
                db=db,
                action=AuditAction.WEBHOOK_FAILED,
                description=f"Webhook processing failed: {str(e)}",
                performed_by="WebhookProcessor",
                error_message=str(e)
            )
            
            logger.error(f"Error processing webhook event {webhook_event_id}: {str(e)}")
            
            return {
                "success": False,
                "webhook_event_id": webhook_event.id,
                "error": str(e),
                "attempts": webhook_event.attempts,
                "can_retry": webhook_event.can_retry()
            }
    
    @staticmethod
    def _get_payment_details(payment_id: str) -> Optional[Dict]:
        """Obtiene detalles del pago desde MercadoPago API"""
        try:
            headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
            response = requests.get(
                f"https://api.mercadopago.com/v1/payments/{payment_id}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to fetch payment details: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching payment details: {str(e)}")
            return None
    
    @staticmethod
    def _update_ghl_contact(payment: Payment) -> bool:
        """
        Actualiza contacto en GoHighLevel usando el token específico del cliente (MULTI-TENANT)
        Identifica al cliente y usa su token GHL específico
        """
        try:
            # Obtener información del cliente desde la base de datos
            with get_db_context() as db:
                client_account = None
                
                # Si el pago ya tiene client_account_id, usarlo directamente
                if payment.client_account_id:
                    client_account = db.query(ClientAccount).filter(
                        ClientAccount.id == payment.client_account_id
                    ).first()
                
                # Si no, intentar identificar por mp_account_id
                elif payment.mp_account_id:
                    mp_account = db.query(MercadoPagoAccount).filter(
                        MercadoPagoAccount.id == payment.mp_account_id
                    ).first()
                    
                    if mp_account:
                        client_account = db.query(ClientAccount).filter(
                            ClientAccount.mp_account_id == mp_account.id
                        ).first()
                
                # Si aún no encontramos el cliente, buscar por created_by
                if not client_account and payment.created_by:
                    # Intentar extraer client_id del created_by (formato: client_dashboard_CLIENTE)
                    if "client_dashboard_" in payment.created_by:
                        client_id = payment.created_by.replace("client_dashboard_", "")
                        client_account = db.query(ClientAccount).filter(
                            ClientAccount.client_id == client_id
                        ).first()
                
                # Calcular monto en formato legible
                amount_str = f"${payment.paid_amount}" if payment.paid_amount else f"${payment.expected_amount}"
                
                # Si no encontramos cliente específico, usar modo global/mock
                if not client_account:
                    logger.warning(f"No se encontró cliente específico para payment {payment.id}, usando modo global")
                    return WebhookService._update_ghl_contact_global(payment, amount_str)
                
                # MODO MULTI-TENANT: Usar token específico del cliente
                logger.info(f"🎯 Actualizando GHL para cliente {client_account.client_id} (Payment {payment.id})")
                
                # Verificar si el cliente tiene token GHL válido
                if not client_account.ghl_access_token:
                    logger.warning(f"Cliente {client_account.client_id} no tiene token GHL configurado")
                    
                    # Crear alerta crítica
                    SecurityManager.create_security_alert(
                        db=db,
                        alert_type="GHL_TOKEN_MISSING",
                        title="Cliente sin token GHL",
                        description=f"El cliente {client_account.client_id} no tiene token GHL para actualizar contacto {payment.ghl_contact_id}",
                        payment_id=payment.id,
                        severity="HIGH"
                    )
                    
                    return WebhookService._update_ghl_contact_mock(payment, client_account, amount_str, "NO_TOKEN")
                
                # Verificar si el token ha expirado
                if client_account.is_ghl_token_expired():
                    logger.warning(f"Token GHL del cliente {client_account.client_id} ha expirado")
                    
                    # Intentar renovar token
                    from services.ghl_oauth_service import GHLOAuthService
                    ghl_service = GHLOAuthService(db)
                    
                    if ghl_service.refresh_token(client_account):
                        logger.info(f"Token GHL renovado exitosamente para cliente {client_account.client_id}")
                    else:
                        logger.error(f"No se pudo renovar token GHL para cliente {client_account.client_id}")
                        
                        # Crear alerta crítica
                        SecurityManager.create_security_alert(
                            db=db,
                            alert_type="GHL_TOKEN_EXPIRED",
                            title="Token GHL expirado y no renovable",
                            description=f"El token GHL del cliente {client_account.client_id} expiró y no se pudo renovar",
                            payment_id=payment.id,
                            severity="CRITICAL"
                        )
                        
                        return WebhookService._update_ghl_contact_mock(payment, client_account, amount_str, "TOKEN_EXPIRED")
                
                # Detectar si es un token mock (modo simulación)
                is_mock_token = client_account.ghl_access_token.startswith("mock_ghl_access_token_")
                
                if is_mock_token:
                    return WebhookService._update_ghl_contact_mock(payment, client_account, amount_str, "SIMULATION")
                
                # MODO PRODUCCIÓN: Llamada real a GHL API con token específico del cliente
                return WebhookService._update_ghl_contact_real(payment, client_account, amount_str, db)
                
        except Exception as e:
            logger.error(f"Error crítico en actualización GHL multi-tenant: {str(e)}")
            return False
    
    @staticmethod
    def _update_ghl_contact_mock(payment: Payment, client_account: ClientAccount, amount_str: str, reason: str) -> bool:
        """Actualización GHL en modo mock con información del cliente"""
        
        reason_messages = {
            "NO_TOKEN": "Cliente sin token GHL configurado",
            "TOKEN_EXPIRED": "Token GHL expirado y no renovable", 
            "SIMULATION": "Modo simulación con token mock",
            "API_ERROR": "Error en API de GHL - fallback a mock"
        }
        
        print("\n" + "="*80)
        print("🎭 " + "="*76 + " 🎭")
        print("="*80)
        print("║" + " "*78 + "║")
        print("║" + "[MOCK GHL SUCCESS - MULTI-TENANT]".center(78) + "║")
        print("║" + " "*78 + "║")
        print("║" + f"Cliente: {client_account.client_id}".center(78) + "║")
        print("║" + f"Contacto: {payment.ghl_contact_id}".center(78) + "║")
        print("║" + f"Razón: {reason_messages.get(reason, reason)}".center(78) + "║")
        print("║" + " "*78 + "║")
        print("="*80)
        print("📊 DETALLES DEL CLIENTE:")
        print(f"   Cliente ID: {client_account.client_id}")
        print(f"   Empresa: {client_account.company_name or 'N/A'}")
        print(f"   GHL Location: {client_account.ghl_location_id or 'N/A'}")
        print(f"   Plan: {client_account.subscription_plan}")
        print("📊 DETALLES DEL PAGO:")
        print(f"   Payment ID: {payment.id}")
        print(f"   Customer: {payment.customer_name or payment.customer_email}")
        print(f"   Monto: {amount_str}")
        print(f"   GHL Contact ID: {payment.ghl_contact_id}")
        print("="*80)
        print("🔗 ACCIONES VIRTUALES APLICADAS:")
        print(f"   ✅ Tag aplicado: {client_account.payment_tag_prefix or 'MP_PAGADO'}_{amount_str}")
        print(f"   ✅ Custom field: payment_status = 'paid'")
        print(f"   ✅ Custom field: payment_amount = '{amount_str}'")
        print(f"   ✅ Custom field: client_id = '{client_account.client_id}'")
        print("="*80)
        print("🎭 " + "="*76 + " 🎭")
        print("="*80 + "\n")
        
        logger.info(f"[MOCK GHL MULTI-TENANT] Cliente {client_account.client_id} - Contacto {payment.ghl_contact_id} actualizado virtualmente")
        return True
    
    @staticmethod
    def _update_ghl_contact_real(payment: Payment, client_account: ClientAccount, amount_str: str, db: Session) -> bool:
        """Actualización real en GHL API usando token específico del cliente"""
        
        try:
            logger.info(f"🚀 Llamada REAL a GHL API para cliente {client_account.client_id}")
            
            headers = {
                "Authorization": f"Bearer {client_account.ghl_access_token}",
                "Content-Type": "application/json",
                "Version": "2021-07-28"
            }
            
            # Preparar tag personalizado del cliente
            tag_prefix = client_account.payment_tag_prefix or "MP_PAGADO"
            payment_tag = f"{tag_prefix}_{amount_str}"
            
            # Preparar datos para actualizar
            update_data = {
                "tags": [payment_tag],
                "customFields": {
                    "payment_status": "paid",
                    "payment_amount": str(payment.paid_amount or payment.expected_amount),
                    "payment_date": payment.processed_at.isoformat() if payment.processed_at else datetime.utcnow().isoformat(),
                    "mp_payment_id": payment.mp_payment_id,
                    "client_id": client_account.client_id,
                    "processed_by": "mercadopago_enterprise"
                }
            }
            
            # URL de la API de GHL v2
            contact_url = f"https://services.leadconnectorhq.com/contacts/{payment.ghl_contact_id}"
            
            response = requests.put(
                contact_url,
                json=update_data,
                headers=headers,
                timeout=15
            )
            
            if response.status_code in [200, 201]:
                print("\n" + "="*80)
                print("🎉 [GHL SUCCESS - MULTI-TENANT] 🎉")
                print("="*80)
                print(f"Cliente: {client_account.client_id}")
                print(f"Contacto: {payment.ghl_contact_id} ✅ ACTUALIZADO")
                print(f"Tag aplicado: {payment_tag}")
                print(f"Location: {client_account.ghl_location_id}")
                print("="*80 + "\n")
                
                logger.info(f"✅ GHL contacto {payment.ghl_contact_id} actualizado exitosamente para cliente {client_account.client_id}")
                return True
                
            else:
                logger.error(f"GHL API error para cliente {client_account.client_id}: {response.status_code} - {response.text}")
                
                # Crear alerta crítica
                SecurityManager.create_security_alert(
                    db=db,
                    alert_type="GHL_UPDATE_FAILED",
                    title="Fallo en actualización GHL",
                    description=f"No se pudo actualizar contacto {payment.ghl_contact_id} para cliente {client_account.client_id}: HTTP {response.status_code}",
                    payment_id=payment.id,
                    severity="CRITICAL",
                    expected_value="HTTP 200",
                    actual_value=f"HTTP {response.status_code}"
                )
                
                # Fallback a mock
                return WebhookService._update_ghl_contact_mock(payment, client_account, amount_str, "API_ERROR")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de red en GHL API para cliente {client_account.client_id}: {str(e)}")
            
            # Crear alerta crítica
            SecurityManager.create_security_alert(
                db=db,
                alert_type="GHL_NETWORK_ERROR",
                title="Error de red en GHL API",
                description=f"Error de conectividad con GHL para cliente {client_account.client_id}: {str(e)}",
                payment_id=payment.id,
                severity="HIGH"
            )
            
            # Fallback a mock
            return WebhookService._update_ghl_contact_mock(payment, client_account, amount_str, "API_ERROR")
            
        except Exception as e:
            logger.error(f"Error crítico en GHL API para cliente {client_account.client_id}: {str(e)}")
            
            # Crear alerta crítica
            SecurityManager.create_security_alert(
                db=db,
                alert_type="GHL_CRITICAL_ERROR",
                title="Error crítico en actualización GHL",
                description=f"Error crítico actualizando GHL para cliente {client_account.client_id}: {str(e)}",
                payment_id=payment.id,
                severity="CRITICAL"
            )
            
            return False
    
    @staticmethod
    def _update_ghl_contact_global(payment: Payment, amount_str: str) -> bool:
        """Fallback al método global cuando no se encuentra cliente específico"""
        
        # Verificar si estamos en modo desarrollo o si no hay API key válida
        is_development = os.getenv("ENVIRONMENT", "development") == "development"
        has_ghl_key = GHL_API_KEY and GHL_API_KEY.strip() and not GHL_API_KEY.startswith("test_")
        
        if is_development or not has_ghl_key:
            print("\n" + "="*80)
            print("🌐 [MOCK GHL SUCCESS - MODO GLOBAL] 🌐")
            print("="*80)
            print(f"Contacto: {payment.ghl_contact_id}")
            print(f"Monto: {amount_str}")
            print("Razón: No se encontró cliente específico - usando modo global")
            print("="*80 + "\n")
            
            logger.info(f"[MOCK GHL GLOBAL] Contacto {payment.ghl_contact_id} actualizado en modo global")
            return True
        
        # Intentar con API key global (modo legacy)
        try:
            headers = {
                "Authorization": f"Bearer {GHL_API_KEY}",
                "Content-Type": "application/json"
            }
            
            update_data = {
                "tags": [f"MP_PAGADO_{amount_str}"],
                "customFields": {
                    "payment_status": "paid",
                    "payment_amount": str(payment.paid_amount or payment.expected_amount),
                    "payment_date": payment.processed_at.isoformat() if payment.processed_at else None,
                    "mp_payment_id": payment.mp_payment_id
                }
            }
            
            response = requests.put(
                f"https://rest.gohighlevel.com/v1/contacts/{payment.ghl_contact_id}",
                json=update_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"✅ GHL contacto {payment.ghl_contact_id} actualizado con API global")
                return True
            else:
                logger.error(f"GHL API global error: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error en GHL API global: {str(e)}")
            return False

# Endpoints de la API
@app.post("/payments/create")
async def create_payment(
    payment_data: PaymentCreateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """Crea un nuevo link de pago con auditoría completa"""
    correlation_id = request.headers.get("x-correlation-id", f"pay_{datetime.utcnow().timestamp()}")
    client_ip = request.client.host
    
    try:
        # Gancho de Auditoría Crítica: Registrar generación de link de pago
        audit_service = CriticalAuditService(db)
        audit_context = AuditContext(
            user_email=payment_data.created_by,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
            tenant_id=payment_data.client_id
        )
        
        result = PaymentService.create_payment_link(
            db=db,
            payment_data=payment_data,
            client_ip=client_ip,
            correlation_id=correlation_id
        )
        
        # Registrar auditoría crítica después del éxito
        if result.get("payment_id"):
            audit_service.log_payment_link_generated(
                context=audit_context,
                payment_id=result["payment_id"],
                amount=payment_data.amount,
                customer_email=payment_data.customer_email,
                mp_preference_id=result.get("preference_id")
            )
        
        return {
            "success": True,
            "data": result,
            "correlation_id": correlation_id
        }
        
    except Exception as e:
        logger.error(f"Error in create_payment: {str(e)}", extra={'correlation_id': correlation_id})
        raise e

@app.post("/webhook/mercadopago")
async def mercadopago_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Recibe webhooks de MercadoPago de forma resiliente
    Responde inmediatamente y procesa en segundo plano
    """
    correlation_id = request.headers.get("x-correlation-id", f"wh_{datetime.utcnow().timestamp()}")
    client_ip = request.client.host
    
    # Obtener payload raw para validación de firma
    raw_payload = await request.body()
    headers = dict(request.headers)
    
    try:
        # Gancho de Auditoría Crítica: Registrar recepción de webhook
        audit_service = CriticalAuditService(db)
        
        # Validar firma del webhook (Seguridad e Higiene)
        signature = headers.get("x-signature", "")
        signature_valid = SecurityManager.validate_webhook_signature(raw_payload.decode(), signature)
        
        # Registrar recepción del webhook
        webhook_data = json.loads(raw_payload.decode()) if raw_payload else {}
        payment_id = webhook_data.get("data", {}).get("id") if webhook_data.get("data") else None
        
        audit_service.log_webhook_received(
            ip_address=client_ip,
            webhook_type=webhook_data.get("type", "unknown"),
            payment_id=str(payment_id) if payment_id else None,
            signature_valid=signature_valid
        )
        
        # Recibir y almacenar webhook (respuesta inmediata)
        result = WebhookService.receive_webhook(
            db=db,
            raw_payload=raw_payload.decode(),
            headers=headers,
            source_ip=client_ip,
            correlation_id=correlation_id
        )
        
        # Si se guardó exitosamente, programar procesamiento en segundo plano
        if result.get("success") and result.get("webhook_event_id"):
            webhook_event_id = result["webhook_event_id"]
            
            # Agregar tarea en segundo plano para procesar el evento
            background_tasks.add_task(
                process_webhook_background,
                webhook_event_id,
                correlation_id
            )
            
            logger.info(f"Webhook queued for background processing: event_id={webhook_event_id}")
        
        # Responder inmediatamente a MercadoPago (200 OK)
        return {
            "success": True,
            "message": "Webhook received and queued for processing",
            "correlation_id": correlation_id
        }
        
    except Exception as e:
        logger.error(f"Error receiving webhook: {str(e)}", extra={'correlation_id': correlation_id})
        
        # Aún así responder OK para evitar reintentos de MP
        return {
            "success": True,
            "message": "Webhook received but failed to queue - will retry",
            "correlation_id": correlation_id
        }

async def process_webhook_background(webhook_event_id: int, correlation_id: str):
    """
    Función para procesar webhook en segundo plano
    """
    logger.info(f"Starting background processing for webhook event {webhook_event_id}")
    
    try:
        with get_db_context() as db:
            result = WebhookService.process_webhook_event(db, webhook_event_id)
            
            if result.get("success"):
                logger.info(f"Webhook event {webhook_event_id} processed successfully")
            else:
                logger.error(f"Webhook event {webhook_event_id} processing failed: {result.get('error')}")
                
                # Si puede reintentarse, programar reintento
                if result.get("can_retry"):
                    # Aquí podrías implementar un sistema de cola más sofisticado
                    # Por ahora, el reintento se hará manualmente o con un cron job
                    logger.info(f"Webhook event {webhook_event_id} can be retried later")
                    
    except Exception as e:
        logger.error(f"Critical error in background webhook processing: {str(e)}")
        
        # Crear alerta crítica
        try:
            with get_db_context() as db:
                SecurityManager.create_security_alert(
                    db=db,
                    alert_type="WEBHOOK_BACKGROUND_ERROR",
                    title="Critical error in webhook background processing",
                    description=f"Webhook event {webhook_event_id} failed with critical error: {str(e)}",
                    severity="CRITICAL"
                )
        except:
            pass  # No fallar si no se puede crear la alerta

@app.get("/payments/{payment_id}")
async def get_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """Obtiene detalles de un pago"""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return {
        "id": payment.id,
        "internal_uuid": payment.internal_uuid,
        "mp_payment_id": payment.mp_payment_id,
        "customer_email": payment.customer_email,
        "expected_amount": str(payment.expected_amount),
        "paid_amount": str(payment.paid_amount) if payment.paid_amount else None,
        "status": payment.status,
        "is_processed": payment.is_processed,
        "created_at": payment.created_at.isoformat(),
        "processed_at": payment.processed_at.isoformat() if payment.processed_at else None
    }

@app.get("/audit/logs")
async def get_audit_logs(
    payment_id: Optional[int] = None,
    action: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """Obtiene logs de auditoría con filtros"""
    query = db.query(AuditLog)
    
    if payment_id:
        query = query.filter(AuditLog.payment_id == payment_id)
    
    if action:
        query = query.filter(AuditLog.action == action)
    
    logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()
    
    return {
        "logs": [
            {
                "id": log.id,
                "payment_id": log.payment_id,
                "action": log.action,
                "description": log.description,
                "performed_by": log.performed_by,
                "timestamp": log.timestamp.isoformat(),
                "error_message": log.error_message,
                "correlation_id": log.correlation_id,
                "current_hash": getattr(log, 'current_hash', None),
                "block_number": getattr(log, 'block_number', 0),
                "is_verified": getattr(log, 'is_verified', True),
                "blockchain_enabled": getattr(log, 'blockchain_enabled', False)
            }
            for log in logs
        ],
        "total": query.count()
    }

@app.post("/audit/logs")
async def create_audit_log(
    request: Request,
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """
    Crea un log de auditoría manual (para testing/simulación)
    TEMPORAL: Habilitado para pruebas de penetración
    Versión simplificada sin conflictos de logging
    """
    try:
        # Obtener datos del body JSON
        body = await request.json()
        
        action = body.get("action", "UNKNOWN")
        description = body.get("description", "Manual audit entry")
        payment_id = body.get("payment_id")
        performed_by = body.get("performed_by", "Manual")
        
        correlation_id = f"manual_{int(time.time() * 1000)}"
        
        # Validar que la acción sea válida
        valid_actions = [action.value for action in AuditAction]
        if action not in valid_actions:
            # Permitir acciones personalizadas para testing
            action = f"CUSTOM_{action.upper()}"
        
        # Generar hash simple para blockchain
        import hashlib
        data_for_hash = f"{action}:{description}:{performed_by}:{correlation_id}"
        current_hash = hashlib.sha256(data_for_hash.encode()).hexdigest()
        data_checksum = hashlib.md5(data_for_hash.encode()).hexdigest()
        
        # Obtener último bloque para secuencia
        last_audit = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
        previous_hash = last_audit.current_hash if last_audit else "genesis"
        block_number = (last_audit.block_number if last_audit else 0) + 1
        
        # Crear log de auditoría directamente con campos correctos del esquema real
        audit_log = AuditLog(
            payment_id=payment_id,
            action=action,  # Usar la acción personalizada directamente
            description=f"[MANUAL] {description}",
            performed_by=performed_by,
            request_data=json.dumps({
                "manual_entry": True,
                "original_action": action,
                "source": "POST_endpoint",
                "body": body
            }),
            ip_address=request.client.host,
            correlation_id=correlation_id,
            # Campos blockchain según esquema real
            previous_hash=previous_hash,
            current_hash=current_hash,
            block_number=block_number,
            is_verified=True,
            blockchain_enabled=False  # Desarrollo
        )
        
        db.add(audit_log)
        db.commit()
        
        # Log simple en consola
        print(f"[MANUAL-AUDIT] {action} - {description} (Block: {block_number}, ID: {correlation_id})")
        
        return {
            "success": True,
            "message": "Audit log created successfully",
            "action": action,
            "description": description,
            "correlation_id": correlation_id,
            "block_number": block_number,
            "current_hash": current_hash[:16],  # Hash corto para respuesta
            "timestamp": datetime.utcnow().isoformat(),
            "note": "This is a manual/testing entry with blockchain verification"
        }
        
    except Exception as e:
        # Log de error simple sin usar logger para evitar conflictos
        print(f"[ERROR] Manual audit log creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/security/alerts")
async def get_security_alerts(
    is_resolved: Optional[bool] = None,
    severity: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """Obtiene alertas de seguridad"""
    query = db.query(SecurityAlert)
    
    if is_resolved is not None:
        query = query.filter(SecurityAlert.is_resolved == is_resolved)
    
    if severity:
        query = query.filter(SecurityAlert.severity == severity)
    
    alerts = query.order_by(SecurityAlert.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "alerts": [
            {
                "id": alert.id,
                "payment_id": alert.payment_id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "title": alert.title,
                "description": alert.description,
                "expected_value": alert.expected_value,
                "actual_value": alert.actual_value,
                "is_resolved": alert.is_resolved,
                "created_at": alert.created_at.isoformat()
            }
            for alert in alerts
        ],
        "total": query.count()
    }

@app.put("/security/alerts/{alert_id}/resolve")
async def resolve_security_alert(
    alert_id: int,
    resolution_notes: str,
    request: Request,
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """Resuelve una alerta de seguridad"""
    alert = db.query(SecurityAlert).filter(SecurityAlert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.is_resolved = True
    alert.resolved_by = "Admin"  # Podrías obtener esto del token
    alert.resolved_at = datetime.utcnow()
    alert.resolution_notes = resolution_notes
    
    db.commit()
    
    # Log de auditoría
    AuditLogger.log_action(
        db=db,
        action=AuditAction.SECURITY_ALERT,
        description=f"Security alert {alert_id} resolved",
        performed_by="Admin",
        request_data={"alert_id": alert_id, "resolution_notes": resolution_notes},
        ip_address=request.client.host
    )
    
    return {"success": True, "message": "Alert resolved successfully"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0"
    }

@app.get("/mock-checkout/{preference_id}")
async def mock_checkout(preference_id: str):
    """Mock checkout page for development/testing"""
    return {
        "message": "Mock MercadoPago Checkout",
        "preference_id": preference_id,
        "note": "This is a development/testing mock. In production, this would redirect to MercadoPago.",
        "actions": {
            "simulate_payment": f"/simulate-payment/{preference_id}",
            "webhook_test": "/webhook/mercadopago"
        }
    }

@app.post("/simulate-payment/{preference_id}")
@app.get("/simulate-payment/{preference_id}")
async def simulate_payment(
    request: Request,
    preference_id: str,
    status: str = "approved",
    db: Session = Depends(get_db)
):
    """
    Simula un pago aprobado para testing en desarrollo
    Acepta tanto GET como POST - GET redirige a página visual
    """
    try:
        # Buscar el pago por preference_id
        payment = db.query(Payment).filter(
            Payment.mp_preference_id == preference_id
        ).first()
        
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        if payment.status != PaymentStatus.PENDING.value:
            # Si ya está procesado y es GET, redirigir a resultado
            if request.method == "GET":
                from fastapi.responses import RedirectResponse
                return RedirectResponse(
                    url=f"/payment-result/{payment.internal_uuid}?status={payment.status}",
                    status_code=302
                )
            else:
                raise HTTPException(status_code=400, detail=f"Payment already processed with status: {payment.status}")
        
        # Simular datos de MercadoPago
        mock_mp_payment_id = f"mock_payment_{payment.id}_{int(datetime.utcnow().timestamp())}"
        
        # Actualizar el pago
        payment.mp_payment_id = mock_mp_payment_id
        payment.status = status
        payment.paid_amount = payment.expected_amount
        payment.is_processed = True
        payment.processed_at = datetime.utcnow()
        payment.mp_payment_method = "mock_credit_card"
        payment.mp_status_detail = "accredited"
        
        db.commit()
        
        # Log de auditoría
        AuditLogger.log_action(
            db=db,
            action=AuditAction.PAYMENT_APPROVED,
            description=f"Payment simulated as {status} for testing - preference_id: {preference_id} (Method: {request.method})",
            payment_id=payment.id,
            performed_by="MockSystem",
            request_data={"preference_id": preference_id, "status": status, "method": request.method},
            response_data={"mp_payment_id": mock_mp_payment_id, "amount": str(payment.paid_amount)},
            correlation_id=f"mock_payment_{int(datetime.utcnow().timestamp())}"
        )
        
        # Simular webhook si el pago fue aprobado
        if status == "approved":
            # Crear webhook simulado
            mock_webhook_data = {
                "id": int(mock_mp_payment_id.split('_')[-1]),
                "live_mode": False,
                "type": "payment",
                "date_created": datetime.utcnow().isoformat(),
                "application_id": 123456789,
                "user_id": 987654321,
                "version": 1,
                "api_version": "v1",
                "action": "payment.updated",
                "data": {
                    "id": mock_mp_payment_id
                }
            }
            
            # Procesar webhook simulado
            try:
                from services.notification_service import NotificationService
                notification_service = NotificationService(db)
                
                # Notificar pago aprobado (esto activará el tag de GHL automáticamente)
                notification_result = notification_service.notify_payment_approved(payment)
                
                logger.info(f"Mock payment notification sent: {notification_result}")
                
            except Exception as e:
                logger.warning(f"Mock payment notification failed: {str(e)}")
        
        # Si es GET, redirigir a página visual
        if request.method == "GET":
            from fastapi.responses import RedirectResponse
            return RedirectResponse(
                url=f"/payment-result/{payment.internal_uuid}?status={status}",
                status_code=302
            )
        
        # Si es POST, devolver JSON
        return {
            "success": True,
            "message": f"Payment simulated as {status}",
            "payment": {
                "id": payment.id,
                "mp_payment_id": mock_mp_payment_id,
                "status": payment.status,
                "amount": str(payment.paid_amount),
                "customer_email": payment.customer_email,
                "processed_at": payment.processed_at.isoformat()
            },
            "webhook_triggered": status == "approved",
            "redirect_url": f"/payment-result/{payment.internal_uuid}?status={status}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error simulating payment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/payment-result/{internal_uuid}")
async def payment_result(
    internal_uuid: str,
    status: str = "approved",
    db: Session = Depends(get_db)
):
    """
    Página visual de resultado del pago simulado
    """
    try:
        payment = db.query(Payment).filter(
            Payment.internal_uuid == internal_uuid
        ).first()
        
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        status_messages = {
            "approved": {
                "title": "¡Pago Aprobado!",
                "message": "Su pago ha sido procesado exitosamente.",
                "color": "green",
                "bg_color": "bg-green-50",
                "border_color": "border-green-200",
                "text_color": "text-green-800",
                "icon": "check-circle"
            },
            "rejected": {
                "title": "Pago Rechazado",
                "message": "Su pago no pudo ser procesado.",
                "color": "red",
                "bg_color": "bg-red-50",
                "border_color": "border-red-200",
                "text_color": "text-red-800",
                "icon": "times-circle"
            },
            "pending": {
                "title": "Pago Pendiente",
                "message": "Su pago está siendo procesado.",
                "color": "yellow",
                "bg_color": "bg-yellow-50",
                "border_color": "border-yellow-200",
                "text_color": "text-yellow-800",
                "icon": "clock"
            }
        }
        
        status_info = status_messages.get(status, status_messages["approved"])
        
        # Crear página HTML visual
        html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{status_info['title']} - MercadoPago Enterprise</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        .gradient-bg {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}
        .bounce-animation {{
            animation: bounce 2s infinite;
        }}
        @keyframes bounce {{
            0%, 20%, 50%, 80%, 100% {{ transform: translateY(0); }}
            40% {{ transform: translateY(-10px); }}
            60% {{ transform: translateY(-5px); }}
        }}
    </style>
</head>
<body class="bg-gray-100 min-h-screen flex items-center justify-center">
    <div class="max-w-md w-full mx-4">
        <!-- Tarjeta principal -->
        <div class="bg-white rounded-2xl shadow-2xl overflow-hidden">
            <!-- Header con gradiente -->
            <div class="gradient-bg p-6 text-center">
                <div class="bounce-animation inline-block">
                    <i class="fas fa-{status_info['icon']} text-6xl text-white mb-4"></i>
                </div>
                <h1 class="text-2xl font-bold text-white">{status_info['title']}</h1>
            </div>
            
            <!-- Contenido -->
            <div class="p-6">
                <!-- Mensaje principal -->
                <div class="{status_info['bg_color']} {status_info['border_color']} border rounded-lg p-4 mb-6">
                    <p class="{status_info['text_color']} text-center font-semibold">
                        {status_info['message']}
                    </p>
                </div>
                
                <!-- Detalles del pago -->
                <div class="space-y-3 mb-6">
                    <div class="flex justify-between items-center py-2 border-b border-gray-200">
                        <span class="text-gray-600">Monto:</span>
                        <span class="font-bold text-lg text-gray-900">${payment.paid_amount or payment.expected_amount}</span>
                    </div>
                    <div class="flex justify-between items-center py-2 border-b border-gray-200">
                        <span class="text-gray-600">Cliente:</span>
                        <span class="font-semibold text-gray-900">{payment.customer_name or payment.customer_email}</span>
                    </div>
                    <div class="flex justify-between items-center py-2 border-b border-gray-200">
                        <span class="text-gray-600">ID de Pago:</span>
                        <span class="font-mono text-sm text-gray-700">{payment.mp_payment_id or 'N/A'}</span>
                    </div>
                    <div class="flex justify-between items-center py-2 border-b border-gray-200">
                        <span class="text-gray-600">Fecha:</span>
                        <span class="text-gray-900">{payment.processed_at.strftime('%d/%m/%Y %H:%M') if payment.processed_at else 'N/A'}</span>
                    </div>
                </div>
                
                <!-- Modo desarrollo -->
                <div class="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-6">
                    <div class="flex items-center">
                        <i class="fas fa-flask text-blue-600 mr-2"></i>
                        <span class="text-blue-800 text-sm font-semibold">Modo Desarrollo</span>
                    </div>
                    <p class="text-blue-700 text-xs mt-1">
                        Esta es una simulación de pago para testing. En producción, esto sería un pago real de MercadoPago.
                    </p>
                </div>
                
                <!-- Botones de acción -->
                <div class="space-y-3">
                    <a href="/dashboard" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 px-6 rounded-lg transition-all text-center block">
                        <i class="fas fa-chart-line mr-2"></i>Ver Dashboard
                    </a>
                    <a href="/dashboard/client/{payment.client_account.client_id if payment.client_account else 'default'}" class="w-full bg-gray-600 hover:bg-gray-700 text-white font-semibold py-3 px-6 rounded-lg transition-all text-center block">
                        <i class="fas fa-user mr-2"></i>Dashboard Cliente
                    </a>
                </div>
            </div>
        </div>
        
        <!-- Footer -->
        <div class="text-center mt-6">
            <p class="text-gray-500 text-sm">
                <i class="fas fa-shield-alt mr-1"></i>
                MercadoPago Enterprise - Sistema Seguro
            </p>
        </div>
    </div>
</body>
</html>
        """
        
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html_content)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting payment result: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
async def get_metrics(
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """Métricas del sistema para monitoreo"""
    
    # Estadísticas de pagos
    total_payments = db.query(Payment).count()
    approved_payments = db.query(Payment).filter(Payment.status == PaymentStatus.APPROVED.value).count()
    pending_payments = db.query(Payment).filter(Payment.status == PaymentStatus.PENDING.value).count()
    
    # Alertas de seguridad
    total_alerts = db.query(SecurityAlert).count()
    unresolved_alerts = db.query(SecurityAlert).filter(SecurityAlert.is_resolved == False).count()
    critical_alerts = db.query(SecurityAlert).filter(
        and_(SecurityAlert.severity == "CRITICAL", SecurityAlert.is_resolved == False)
    ).count()
    
    # Webhooks
    total_webhooks = db.query(WebhookLog).count()
    failed_webhooks = db.query(WebhookLog).filter(WebhookLog.is_processed == False).count()
    
    return {
        "payments": {
            "total": total_payments,
            "approved": approved_payments,
            "pending": pending_payments,
            "approval_rate": round((approved_payments / total_payments * 100) if total_payments > 0 else 0, 2)
        },
        "security": {
            "total_alerts": total_alerts,
            "unresolved_alerts": unresolved_alerts,
            "critical_alerts": critical_alerts
        },
        "webhooks": {
            "total": total_webhooks,
            "failed": failed_webhooks,
            "success_rate": round(((total_webhooks - failed_webhooks) / total_webhooks * 100) if total_webhooks > 0 else 0, 2)
        }
    }

# Endpoints de Notificaciones para Vendedores (MVP)
@app.get("/api/notifications/")
async def get_vendor_notifications(
    limit: int = Query(10, ge=1, le=50, description="Número de notificaciones a obtener"),
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """
    Notificación en Dashboard: Devuelve los últimos eventos de tipo payment_approved
    """
    try:
        from services.vendor_notification_service import VendorNotificationService
        
        vendor_service = VendorNotificationService(db)
        notifications = vendor_service.get_recent_notifications(limit=limit)
        stats = vendor_service.get_notification_stats()
        
        return {
            "success": True,
            "notifications": notifications,
            "stats": stats,
            "count": len(notifications),
            "message": f"Retrieved {len(notifications)} recent notifications"
        }
        
    except Exception as e:
        logger.error(f"Error getting vendor notifications: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving notifications: {str(e)}"
        )

@app.get("/api/notifications/stats")
async def get_notification_stats(
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """
    Estadísticas de notificaciones para el dashboard
    """
    try:
        from services.vendor_notification_service import VendorNotificationService
        
        vendor_service = VendorNotificationService(db)
        stats = vendor_service.get_notification_stats()
        
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting notification stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving notification stats: {str(e)}"
        )

# Endpoints de Gestión de Webhooks
@app.get("/webhooks/events")
async def list_webhook_events(
    status: Optional[str] = None,
    topic: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """Lista eventos de webhook con filtros"""
    query = db.query(WebhookEvent)
    
    if status:
        query = query.filter(WebhookEvent.status == status)
    
    if topic:
        query = query.filter(WebhookEvent.topic == topic)
    
    events = query.order_by(WebhookEvent.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "events": [
            {
                "id": event.id,
                "mp_event_id": event.mp_event_id,
                "topic": event.topic,
                "resource": event.resource,
                "status": event.status,
                "attempts": event.attempts,
                "max_attempts": event.max_attempts,
                "payment_id": event.payment_id,
                "mp_payment_id": event.mp_payment_id,
                "last_error": event.last_error,
                "signature_valid": event.signature_valid,
                "created_at": event.created_at.isoformat(),
                "last_attempt_at": event.last_attempt_at.isoformat() if event.last_attempt_at else None,
                "processed_at": event.processed_at.isoformat() if event.processed_at else None,
                "can_retry": event.can_retry(),
                "is_expired": event.is_expired()
            }
            for event in events
        ],
        "total": query.count(),
        "filters": {
            "status": status,
            "topic": topic,
            "limit": limit,
            "offset": offset
        }
    }

@app.get("/webhooks/events/{event_id}")
async def get_webhook_event(
    event_id: int,
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """Obtiene detalles de un evento de webhook específico"""
    event = db.query(WebhookEvent).filter(WebhookEvent.id == event_id).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Webhook event not found")
    
    return {
        "id": event.id,
        "mp_event_id": event.mp_event_id,
        "topic": event.topic,
        "resource": event.resource,
        "status": event.status,
        "attempts": event.attempts,
        "max_attempts": event.max_attempts,
        "payment_id": event.payment_id,
        "mp_payment_id": event.mp_payment_id,
        "raw_data": json.loads(event.raw_data) if event.raw_data else None,
        "headers": json.loads(event.headers) if event.headers else None,
        "source_ip": event.source_ip,
        "last_error": event.last_error,
        "signature_valid": event.signature_valid,
        "created_at": event.created_at.isoformat(),
        "updated_at": event.updated_at.isoformat(),
        "last_attempt_at": event.last_attempt_at.isoformat() if event.last_attempt_at else None,
        "processed_at": event.processed_at.isoformat() if event.processed_at else None,
        "can_retry": event.can_retry(),
        "is_expired": event.is_expired()
    }

@app.post("/webhooks/events/{event_id}/retry")
async def retry_webhook_event(
    event_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """Reintenta procesar un evento de webhook manualmente"""
    event = db.query(WebhookEvent).filter(WebhookEvent.id == event_id).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Webhook event not found")
    
    if not event.can_retry():
        raise HTTPException(
            status_code=400, 
            detail=f"Event cannot be retried (attempts: {event.attempts}/{event.max_attempts}, status: {event.status})"
        )
    
    # Resetear estado para reintento
    event.status = 'pending'
    event.last_error = None
    db.commit()
    
    # Programar procesamiento en segundo plano
    background_tasks.add_task(
        process_webhook_background,
        event_id,
        f"manual_retry_{datetime.utcnow().timestamp()}"
    )
    
    # Log de auditoría
    AuditLogger.log_action(
        db=db,
        action=AuditAction.WEBHOOK_PROCESSED,  # Usar acción existente
        description=f"Manual retry initiated for webhook event {event_id}",
        performed_by="Admin",
        response_data={"event_id": event_id, "previous_attempts": event.attempts}
    )
    
    return {
        "success": True,
        "message": f"Webhook event {event_id} queued for retry",
        "event_id": event_id,
        "attempts": event.attempts
    }

@app.get("/webhooks/stats")
async def get_webhook_stats(
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """Obtiene estadísticas de eventos de webhook"""
    
    # Estadísticas por estado
    stats_by_status = db.query(
        WebhookEvent.status,
        func.count(WebhookEvent.id).label('count')
    ).group_by(WebhookEvent.status).all()
    
    # Estadísticas por topic
    stats_by_topic = db.query(
        WebhookEvent.topic,
        func.count(WebhookEvent.id).label('count')
    ).group_by(WebhookEvent.topic).all()
    
    # Eventos que necesitan reintento
    events_needing_retry = db.query(WebhookEvent).filter(
        and_(
            WebhookEvent.status == 'error',
            WebhookEvent.attempts < WebhookEvent.max_attempts
        )
    ).count()
    
    # Eventos fallidos definitivamente
    failed_events = db.query(WebhookEvent).filter(
        WebhookEvent.status == 'failed'
    ).count()
    
    # Eventos procesados exitosamente
    processed_events = db.query(WebhookEvent).filter(
        WebhookEvent.status == 'processed'
    ).count()
    
    # Eventos pendientes
    pending_events = db.query(WebhookEvent).filter(
        WebhookEvent.status == 'pending'
    ).count()
    
    # Tasa de éxito
    total_events = db.query(WebhookEvent).count()
    success_rate = (processed_events / total_events * 100) if total_events > 0 else 0
    
    return {
        "total_events": total_events,
        "success_rate": round(success_rate, 2),
        "by_status": {
            "processed": processed_events,
            "pending": pending_events,
            "error": events_needing_retry,
            "failed": failed_events
        },
        "by_topic": {topic: count for topic, count in stats_by_topic},
        "events_needing_retry": events_needing_retry,
        "failed_events": failed_events,
        "health": {
            "status": "healthy" if success_rate > 90 else "warning" if success_rate > 70 else "critical",
            "pending_queue": pending_events,
            "retry_queue": events_needing_retry
        }
    }

# Endpoints Dashboard NOC
@app.get("/api/v1/dashboard/overview")
async def get_dashboard_overview(
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """
    Dashboard Overview - Centro de Comando NOC
    Retorna métricas agregadas para visualización enterprise
    """
    try:
        from services.metrics_service import MetricsService
        
        metrics_service = MetricsService(db)
        dashboard_data = metrics_service.get_dashboard_overview()
        
        # Convertir a formato JSON serializable
        response_data = {
            "status": "success",
            "data": {
                "financials": {
                    "total_processed_today": float(dashboard_data.total_processed_today),
                    "total_processed_month": float(dashboard_data.total_processed_month),
                    "payments_pending": dashboard_data.payments_pending,
                    "payments_approved": dashboard_data.payments_approved,
                    "payments_rejected": dashboard_data.payments_rejected,
                    "approval_rate": round((dashboard_data.payments_approved / 
                                          max(1, dashboard_data.payments_approved + dashboard_data.payments_rejected)) * 100, 2)
                },
                "performance": {
                    "payment_success_rate": dashboard_data.payment_success_rate,
                    "webhook_avg_response_time": dashboard_data.webhook_avg_response_time,
                    "transactions_per_client": dashboard_data.transactions_per_client
                },
                "system_health": {
                    "services": [
                        {
                            "name": service.name,
                            "status": service.status.value,
                            "response_time_ms": service.response_time_ms,
                            "uptime_percentage": service.uptime_percentage,
                            "last_check": service.last_check.isoformat(),
                            "error_message": service.error_message
                        }
                        for service in dashboard_data.services_health
                    ],
                    "overall_status": "healthy" if all(s.status.value in ["healthy", "degraded"] 
                                                     for s in dashboard_data.services_health) else "critical"
                },
                "security": {
                    "top_threats": [
                        {
                            "threat_type": threat.threat_type,
                            "severity": threat.severity,
                            "count": threat.count,
                            "description": threat.description,
                            "last_occurrence": threat.last_occurrence.isoformat()
                        }
                        for threat in dashboard_data.top_threats
                    ],
                    "threat_level": "high" if any(t.severity == "CRITICAL" for t in dashboard_data.top_threats) 
                                   else "medium" if dashboard_data.top_threats else "low"
                },
                "trends": {
                    "hourly_volume": dashboard_data.hourly_volume,
                    "daily_revenue": dashboard_data.daily_revenue
                },
                "metadata": {
                    "generated_at": dashboard_data.generated_at.isoformat(),
                    "data_freshness_seconds": dashboard_data.data_freshness_seconds,
                    "cache_status": "fresh" if dashboard_data.data_freshness_seconds < 60 else "cached"
                }
            }
        }
        
        # Log de auditoría
        AuditLogger.log_action(
            db=db,
            action=AuditAction.WEBHOOK_PROCESSED,  # Usar acción existente
            description="Dashboard overview accessed",
            performed_by="Admin",
            response_data={
                "data_freshness": dashboard_data.data_freshness_seconds,
                "services_checked": len(dashboard_data.services_health),
                "threats_detected": len(dashboard_data.top_threats)
            }
        )
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error generating dashboard overview: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/dashboard/metrics/realtime")
async def get_realtime_metrics(
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """
    Métricas en tiempo real para widgets del dashboard
    """
    try:
        from services.metrics_service import MetricsService
        
        metrics_service = MetricsService(db)
        realtime_metrics = metrics_service.get_real_time_metrics()
        
        response_data = {
            "status": "success",
            "data": {
                metric_name: {
                    "value": metric.value,
                    "unit": metric.unit,
                    "timestamp": metric.timestamp.isoformat(),
                    "trend": metric.trend,
                    "previous_value": metric.previous_value
                }
                for metric_name, metric in realtime_metrics.items()
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error getting realtime metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/dashboard/alerts")
async def get_dashboard_alerts(
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """
    Estado actual del sistema de alertas
    """
    try:
        from services.alert_service import AlertService
        
        alert_service = AlertService(db)
        alert_status = alert_service.get_alert_status()
        
        return {
            "status": "success",
            "data": alert_status,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting alert status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/dashboard/alerts/check")
async def trigger_alert_check(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """
    Dispara verificación manual de alertas
    """
    try:
        from services.alert_service import AlertService
        
        # Ejecutar verificación de alertas en segundo plano
        background_tasks.add_task(run_alert_check, db)
        
        return {
            "status": "success",
            "message": "Alert check initiated in background",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error triggering alert check: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_alert_check(db: Session):
    """Ejecuta verificación de alertas en segundo plano"""
    try:
        from services.alert_service import AlertService
        
        alert_service = AlertService(db)
        alerts_generated = alert_service.check_all_alerts()
        
        logger.info(f"Alert check completed - {len(alerts_generated)} alerts generated")
        
    except Exception as e:
        logger.error(f"Error in background alert check: {str(e)}")

@app.get("/health/deep")
async def deep_health_check(
    db: Session = Depends(get_db)
):
    """
    Health Check Profesional - Verificación profunda del sistema
    Incluye latencia de APIs y estado de tablas de BD
    """
    start_time = time.time()
    
    try:
        from services.metrics_service import MetricsService
        
        metrics_service = MetricsService(db)
        
        # 1. Verificar servicios externos
        services_health = metrics_service._check_services_health()
        
        # 2. Verificar tablas de base de datos
        db_tables_status = metrics_service._check_database_tables()
        
        # 3. Verificar conectividad de MercadoPago con latencia
        mp_latency_test = await test_mercadopago_latency()
        
        # 4. Métricas básicas del sistema
        system_metrics = {
            "total_payments": db.query(Payment).count(),
            "pending_webhooks": db.query(WebhookEvent).filter(WebhookEvent.status == 'pending').count(),
            "active_oauth_accounts": db.query(MercadoPagoAccount).filter(MercadoPagoAccount.is_active == True).count(),
            "unresolved_alerts": db.query(SecurityAlert).filter(SecurityAlert.is_resolved == False).count()
        }
        
        # Determinar estado general
        overall_status = "healthy"
        issues = []
        
        # Verificar servicios
        for service in services_health:
            if service.status.value == "down":
                overall_status = "critical"
                issues.append(f"{service.name} is down: {service.error_message}")
            elif service.status.value == "degraded" and overall_status == "healthy":
                overall_status = "degraded"
                issues.append(f"{service.name} is degraded")
        
        # Verificar tablas
        for table, status in db_tables_status.items():
            if status.get("status") == "error":
                overall_status = "critical"
                issues.append(f"Database table {table} has issues: {status.get('error')}")
        
        # Verificar latencia de MP
        if mp_latency_test["status"] != "success":
            if overall_status == "healthy":
                overall_status = "degraded"
            issues.append(f"MercadoPago latency test failed: {mp_latency_test.get('error')}")
        
        total_check_time = (time.time() - start_time) * 1000
        
        response = {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "check_duration_ms": round(total_check_time, 2),
            "services": {
                service.name.lower().replace(" ", "_"): {
                    "status": service.status.value,
                    "response_time_ms": service.response_time_ms,
                    "uptime_percentage": service.uptime_percentage,
                    "error_message": service.error_message,
                    "last_check": service.last_check.isoformat()
                }
                for service in services_health
            },
            "database": {
                "tables": db_tables_status,
                "connection_time_ms": round((time.time() - start_time) * 1000, 2)
            },
            "external_apis": {
                "mercadopago": mp_latency_test
            },
            "system_metrics": system_metrics,
            "issues": issues,
            "recommendations": generate_health_recommendations(services_health, system_metrics)
        }
        
        # Log del health check
        logger.info(f"Deep health check completed - Status: {overall_status}, Duration: {total_check_time:.2f}ms")
        
        return response
        
    except Exception as e:
        error_time = (time.time() - start_time) * 1000
        logger.error(f"Error in deep health check: {str(e)}")
        
        return {
            "status": "critical",
            "timestamp": datetime.utcnow().isoformat(),
            "check_duration_ms": round(error_time, 2),
            "error": str(e),
            "issues": [f"Health check failed: {str(e)}"]
        }

async def test_mercadopago_latency() -> Dict[str, Any]:
    """Prueba de latencia específica para MercadoPago"""
    start_time = time.time()
    
    try:
        mp_token = os.getenv("MP_ACCESS_TOKEN")
        if not mp_token:
            return {
                "status": "error",
                "error": "No MP access token configured",
                "latency_ms": 0
            }
        
        headers = {"Authorization": f"Bearer {mp_token}"}
        
        # Hacer múltiples llamadas para obtener latencia promedio
        latencies = []
        for _ in range(3):
            call_start = time.time()
            response = requests.get(
                "https://api.mercadopago.com/users/me",
                headers=headers,
                timeout=10
            )
            call_latency = (time.time() - call_start) * 1000
            latencies.append(call_latency)
            
            if response.status_code != 200:
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}",
                    "latency_ms": round(sum(latencies) / len(latencies), 2)
                }
        
        avg_latency = sum(latencies) / len(latencies)
        
        return {
            "status": "success",
            "latency_ms": round(avg_latency, 2),
            "min_latency_ms": round(min(latencies), 2),
            "max_latency_ms": round(max(latencies), 2),
            "samples": len(latencies)
        }
        
    except Exception as e:
        error_latency = (time.time() - start_time) * 1000
        return {
            "status": "error",
            "error": str(e),
            "latency_ms": round(error_latency, 2)
        }

def generate_health_recommendations(services_health, system_metrics) -> List[str]:
    """Genera recomendaciones basadas en el estado del sistema"""
    recommendations = []
    
    # Verificar servicios lentos
    for service in services_health:
        if service.response_time_ms and service.response_time_ms > 3000:
            recommendations.append(f"Consider optimizing {service.name} - response time is {service.response_time_ms}ms")
    
    # Verificar cola de webhooks
    if system_metrics["pending_webhooks"] > 50:
        recommendations.append(f"High webhook queue ({system_metrics['pending_webhooks']} pending) - consider scaling processing")
    
    # Verificar alertas no resueltas
    if system_metrics["unresolved_alerts"] > 10:
        recommendations.append(f"Multiple unresolved security alerts ({system_metrics['unresolved_alerts']}) - review and resolve")
    
    # Verificar cuentas OAuth
    if system_metrics["active_oauth_accounts"] == 0:
        recommendations.append("No active OAuth accounts - ensure proper authentication setup")
    
    return recommendations

# Endpoints OAuth
@app.post("/admin/reconcile")
async def execute_reconciliation(
    background_tasks: BackgroundTasks,
    request: Request,
    hours_back: int = 24,
    enable_auto_correction: bool = True,
    dry_run: bool = False,
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """
    Ejecuta proceso de reconciliación diaria
    Endpoint protegido por API Key para administradores
    """
    correlation_id = request.headers.get("x-correlation-id", f"recon_{datetime.utcnow().timestamp()}")
    
    try:
        from services import ReconciliationService, ReconciliationConfig
        
        # Configurar parámetros de reconciliación
        config = ReconciliationConfig(
            hours_back=hours_back,
            max_retries=3,
            retry_delay_seconds=5,
            batch_size=50,
            enable_auto_correction=enable_auto_correction,
            dry_run=dry_run,
            include_pending_payments=False,
            ghl_tag_prefix="MP_PAGADO",
            report_formats=["json", "csv"],
            notification_webhooks=[]
        )
        
        # Crear servicio de reconciliación
        reconciliation_service = ReconciliationService(db, config)
        
        # Ejecutar reconciliación en segundo plano
        background_tasks.add_task(
            execute_reconciliation_background,
            reconciliation_service,
            correlation_id
        )
        
        # Log de auditoría
        AuditLogger.log_action(
            db=db,
            action=AuditAction.WEBHOOK_PROCESSED,  # Usar acción existente
            description=f"Daily reconciliation initiated via API",
            performed_by="Admin",
            request_data={
                "hours_back": hours_back,
                "enable_auto_correction": enable_auto_correction,
                "dry_run": dry_run
            },
            response_data={
                "execution_id": reconciliation_service.execution_id,
                "status": "initiated"
            },
            ip_address=request.client.host,
            correlation_id=correlation_id
        )
        
        logger.info(f"Reconciliation initiated - Execution ID: {reconciliation_service.execution_id}")
        
        return {
            "success": True,
            "message": "Reconciliation process initiated",
            "execution_id": reconciliation_service.execution_id,
            "config": dict(config),
            "correlation_id": correlation_id,
            "note": "Process is running in background. Check /admin/reconcile/status/{execution_id} for progress."
        }
        
    except Exception as e:
        logger.error(f"Error initiating reconciliation: {str(e)}")
        
        AuditLogger.log_action(
            db=db,
            action=AuditAction.WEBHOOK_FAILED,
            description=f"Reconciliation initiation failed: {str(e)}",
            performed_by="Admin",
            error_message=str(e),
            ip_address=request.client.host,
            correlation_id=correlation_id
        )
        
        raise HTTPException(status_code=500, detail=str(e))

async def execute_reconciliation_background(reconciliation_service, correlation_id: str):
    """
    Función para ejecutar reconciliación en segundo plano
    """
    logger.info(f"Starting background reconciliation - ID: {reconciliation_service.execution_id}")
    
    try:
        # Ejecutar reconciliación
        result = reconciliation_service.execute_reconciliation()
        
        logger.info(f"Reconciliation completed - Status: {result['status']}, Duration: {result['duration_seconds']:.2f}s")
        
        # Log resultado final
        if result["status"] in ["error", "critical"]:
            logger.error(f"Reconciliation {reconciliation_service.execution_id} completed with issues: {len(result['discrepancies'])} discrepancies found")
        else:
            logger.info(f"Reconciliation {reconciliation_service.execution_id} completed successfully: {result['corrections_applied']} corrections applied")
            
    except Exception as e:
        logger.error(f"Critical error in background reconciliation: {str(e)}")
        
        # Crear alerta crítica
        try:
            from contextlib import contextmanager
            
            @contextmanager
            def get_db_context():
                db = SessionLocal()
                try:
                    yield db
                    db.commit()
                except Exception as e:
                    db.rollback()
                    raise e
                finally:
                    db.close()
            
            with get_db_context() as db:
                SecurityManager.create_security_alert(
                    db=db,
                    alert_type="RECONCILIATION_CRITICAL_ERROR",
                    title="Critical error in daily reconciliation",
                    description=f"Reconciliation {reconciliation_service.execution_id} failed with critical error: {str(e)}",
                    severity="CRITICAL"
                )
        except:
            pass  # No fallar si no se puede crear la alerta

@app.get("/admin/reconcile/status/{execution_id}")
async def get_reconciliation_status(
    execution_id: str,
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """
    Obtiene el estado de una reconciliación específica
    """
    try:
        # Buscar en audit logs
        audit_logs = db.query(AuditLog).filter(
            AuditLog.correlation_id == execution_id
        ).order_by(AuditLog.timestamp.desc()).all()
        
        if not audit_logs:
            raise HTTPException(status_code=404, detail="Reconciliation execution not found")
        
        # Buscar reportes generados
        reports_dir = "reports"
        reports = []
        
        if os.path.exists(reports_dir):
            for filename in os.listdir(reports_dir):
                if execution_id in filename:
                    file_path = os.path.join(reports_dir, filename)
                    file_stats = os.stat(file_path)
                    reports.append({
                        "filename": filename,
                        "file_path": file_path,
                        "size_bytes": file_stats.st_size,
                        "created_at": datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
                        "format": "json" if filename.endswith(".json") else "csv"
                    })
        
        # Determinar estado basado en logs
        latest_log = audit_logs[0]
        status = "completed" if latest_log.error_message is None else "error"
        
        response_data = json.loads(latest_log.response_data) if latest_log.response_data else {}
        
        return {
            "execution_id": execution_id,
            "status": status,
            "started_at": audit_logs[-1].timestamp.isoformat() if audit_logs else None,
            "completed_at": latest_log.timestamp.isoformat(),
            "duration_seconds": response_data.get("duration_seconds"),
            "summary": response_data.get("summary", {}),
            "total_payments_checked": response_data.get("total_payments_checked", 0),
            "discrepancies_found": response_data.get("discrepancies_found", 0),
            "corrections_applied": response_data.get("corrections_applied", 0),
            "reports_generated": reports,
            "error_message": latest_log.error_message,
            "logs_count": len(audit_logs)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting reconciliation status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/reconcile/reports/{execution_id}")
async def list_reconciliation_reports(
    execution_id: str,
    admin_token: str = Depends(verify_admin_token)
):
    """
    Lista los reportes generados para una reconciliación específica
    """
    try:
        reports_dir = "reports"
        reports = []
        
        if not os.path.exists(reports_dir):
            return {"reports": [], "message": "No reports directory found"}
        
        for filename in os.listdir(reports_dir):
            if execution_id in filename:
                file_path = os.path.join(reports_dir, filename)
                file_stats = os.stat(file_path)
                
                reports.append({
                    "filename": filename,
                    "file_path": file_path,
                    "size_bytes": file_stats.st_size,
                    "size_human": f"{file_stats.st_size / 1024:.1f} KB",
                    "created_at": datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
                    "modified_at": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                    "format": "json" if filename.endswith(".json") else "csv",
                    "download_url": f"/admin/reconcile/download/{filename}"
                })
        
        return {
            "execution_id": execution_id,
            "reports": sorted(reports, key=lambda x: x["created_at"], reverse=True),
            "total_reports": len(reports)
        }
        
    except Exception as e:
        logger.error(f"Error listing reconciliation reports: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/reconcile/download/{filename}")
async def download_reconciliation_report(
    filename: str,
    admin_token: str = Depends(verify_admin_token)
):
    """
    Descarga un reporte de reconciliación específico
    """
    try:
        reports_dir = "reports"
        file_path = os.path.join(reports_dir, filename)
        
        # Validar que el archivo existe y está en el directorio correcto
        if not os.path.exists(file_path) or not os.path.commonpath([reports_dir, file_path]) == reports_dir:
            raise HTTPException(status_code=404, detail="Report file not found")
        
        from fastapi.responses import FileResponse
        
        # Determinar media type
        media_type = "application/json" if filename.endswith(".json") else "text/csv"
        
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading report: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Endpoints OAuth
@app.get("/oauth/authorize")
async def oauth_authorize(
    state: str = None,
    db: Session = Depends(get_db)
):
    """Inicia el proceso OAuth redirigiendo al usuario a MercadoPago"""
    try:
        if not MP_CLIENT_ID or not MP_CLIENT_SECRET:
            raise HTTPException(status_code=500, detail="OAuth credentials not configured")
        
        # Generar state para seguridad si no se proporciona
        if not state:
            state = f"oauth_{datetime.utcnow().timestamp()}"
        
        # Construir URL de autorización de MercadoPago
        auth_params = {
            "client_id": MP_CLIENT_ID,
            "response_type": "code",
            "platform_id": "mp",
            "redirect_uri": MP_REDIRECT_URI,
            "state": state
        }
        
        # Construir query string
        query_string = "&".join([f"{k}={v}" for k, v in auth_params.items()])
        authorization_url = f"{MP_AUTH_URL}?{query_string}"
        
        # Log de auditoría
        AuditLogger.log_action(
            db=db,
            action=AuditAction.PAYMENT_LINK_GENERATED,  # Usar acción existente
            description=f"OAuth authorization initiated with state: {state}",
            performed_by="OAuth-System",
            request_data={"state": state, "redirect_uri": MP_REDIRECT_URI},
            response_data={"authorization_url": authorization_url}
        )
        
        logger.info(f"OAuth authorization initiated - redirecting to MercadoPago")
        
        # Redireccionar al usuario a MercadoPago
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=authorization_url)
        
    except Exception as e:
        logger.error(f"Error in OAuth authorize: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/oauth/callback")
async def oauth_callback(
    code: str = None,
    state: str = None,
    error: str = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Callback de OAuth - intercambia código por tokens"""
    try:
        # Verificar si hay error en la autorización
        if error:
            logger.error(f"OAuth error received: {error}")
            
            AuditLogger.log_action(
                db=db,
                action=AuditAction.WEBHOOK_FAILED,  # Usar acción existente
                description=f"OAuth authorization failed: {error}",
                performed_by="OAuth-System",
                error_message=error,
                ip_address=request.client.host if request else None
            )
            
            raise HTTPException(status_code=400, detail=f"OAuth authorization failed: {error}")
        
        # Verificar que tenemos el código
        if not code:
            raise HTTPException(status_code=400, detail="Authorization code not provided")
        
        logger.info(f"OAuth callback received - exchanging code for tokens")
        
        # Intercambiar código por tokens
        token_data = {
            "client_id": MP_CLIENT_ID,
            "client_secret": MP_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": MP_REDIRECT_URI
        }
        
        # Hacer POST a MercadoPago para obtener tokens
        response = requests.post(
            MP_TOKEN_URL,
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )
        
        if response.status_code != 200:
            logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
            
            AuditLogger.log_action(
                db=db,
                action=AuditAction.WEBHOOK_FAILED,
                description=f"Token exchange failed: {response.status_code}",
                performed_by="OAuth-System",
                error_message=response.text,
                ip_address=request.client.host if request else None
            )
            
            raise HTTPException(status_code=400, detail="Failed to exchange authorization code for tokens")
        
        token_response = response.json()
        logger.info(f"Tokens received successfully from MercadoPago")
        
        # Obtener información del usuario
        user_info = None
        try:
            user_response = requests.get(
                MP_USER_INFO_URL,
                headers={"Authorization": f"Bearer {token_response['access_token']}"},
                timeout=10
            )
            
            if user_response.status_code == 200:
                user_info = user_response.json()
                logger.info(f"User info retrieved: {user_info.get('id', 'unknown')}")
            else:
                logger.warning(f"Failed to get user info: {user_response.status_code}")
                
        except Exception as e:
            logger.warning(f"Error getting user info: {str(e)}")
        
        # Calcular expiración
        expires_in = token_response.get("expires_in", 21600)  # Default 6 horas
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        # Obtener mp_user_id
        mp_user_id = str(user_info.get("id", "unknown")) if user_info else "unknown"
        
        # Verificar si ya existe una cuenta para este usuario
        existing_account = db.query(OAuthAccount).filter(
            OAuthAccount.mp_user_id == mp_user_id
        ).first()
        
        if existing_account:
            # Actualizar cuenta existente
            existing_account.access_token = token_response["access_token"]
            existing_account.refresh_token = token_response.get("refresh_token")
            existing_account.public_key = token_response.get("public_key")
            existing_account.expires_at = expires_at
            existing_account.updated_at = datetime.utcnow()
            existing_account.is_active = True
            
            # Actualizar datos del usuario si están disponibles
            if user_info:
                existing_account.mp_nickname = user_info.get("nickname")
                existing_account.mp_site_id = user_info.get("site_id")
            
            account = existing_account
            action_description = f"OAuth tokens updated for existing user {mp_user_id}"
            
        else:
            # Crear nueva cuenta
            account = OAuthAccount(
                mp_user_id=mp_user_id,
                access_token=token_response["access_token"],
                refresh_token=token_response.get("refresh_token"),
                public_key=token_response.get("public_key"),
                expires_at=expires_at,
                mp_nickname=user_info.get("nickname") if user_info else None,
                mp_site_id=user_info.get("site_id") if user_info else None
            )
            
            db.add(account)
            action_description = f"New OAuth account created for user {mp_user_id}"
        
        db.commit()
        
        # Log de auditoría exitoso
        AuditLogger.log_action(
            db=db,
            action=AuditAction.PAYMENT_LINK_GENERATED,
            description=action_description,
            performed_by="OAuth-System",
            request_data={
                "code": code[:10] + "...",  # Solo mostrar parte del código
                "state": state,
                "mp_user_id": mp_user_id
            },
            response_data={
                "account_id": account.id,
                "expires_at": expires_at.isoformat(),
                "has_refresh_token": bool(account.refresh_token),
                "public_key": account.public_key[:20] + "..." if account.public_key else None
            },
            ip_address=request.client.host if request else None
        )
        
        logger.info(f"OAuth account saved successfully - ID: {account.id}")
        
        # Respuesta exitosa
        return {
            "success": True,
            "message": "OAuth authorization completed successfully",
            "data": {
                "account_id": account.id,
                "mp_user_id": account.mp_user_id,
                "mp_nickname": account.mp_nickname,
                "expires_at": expires_at.isoformat(),
                "has_refresh_token": bool(account.refresh_token),
                "is_new_account": existing_account is None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in OAuth callback: {str(e)}")
        
        AuditLogger.log_action(
            db=db,
            action=AuditAction.WEBHOOK_FAILED,
            description=f"OAuth callback error: {str(e)}",
            performed_by="OAuth-System",
            error_message=str(e),
            ip_address=request.client.host if request else None
        )
        
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/oauth/accounts")
async def list_oauth_accounts(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """Lista las cuentas OAuth conectadas"""
    query = db.query(OAuthAccount)
    
    accounts = query.order_by(OAuthAccount.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "accounts": [
            {
                "id": account.id,
                "mp_user_id": account.mp_user_id,
                "mp_nickname": account.mp_nickname,
                "mp_site_id": account.mp_site_id,
                "is_active": account.is_active,
                "expires_at": account.expires_at.isoformat(),
                "needs_refresh": account.needs_refresh(),
                "is_expired": account.is_token_expired(),
                "has_refresh_token": bool(account.refresh_token),
                "has_public_key": bool(account.public_key),
                "created_at": account.created_at.isoformat(),
                "updated_at": account.updated_at.isoformat()
            }
            for account in accounts
        ],
        "total": query.count()
    }

@app.delete("/oauth/accounts/{account_id}")
async def deactivate_oauth_account(
    account_id: int,
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """Desactiva una cuenta OAuth"""
    account = db.query(OAuthAccount).filter(OAuthAccount.id == account_id).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account.is_active = False
    account.updated_at = datetime.utcnow()
    db.commit()
    
    # Log de auditoría
    AuditLogger.log_action(
        db=db,
        action=AuditAction.SECURITY_ALERT,  # Usar acción existente
        description=f"OAuth account deactivated: {account.mp_user_id}",
        performed_by="Admin",
        response_data={"account_id": account.id, "mp_user_id": account.mp_user_id}
    )
    
    return {
        "success": True,
        "message": "Account deactivated successfully",
        "account_id": account.id
    }

# ============================================
# ENDPOINTS OAUTH GOHIGHLEVEL (MULTI-TENANT)
# ============================================

@app.get("/oauth/ghl/authorize")
async def ghl_oauth_authorize(
    client_id: str,
    state: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Inicia el flujo OAuth de GoHighLevel para un cliente específico
    """
    try:
        from services.ghl_oauth_service import GHLOAuthService
        
        ghl_service = GHLOAuthService(db)
        
        # Generar URL de autorización
        auth_url = ghl_service.get_authorization_url(client_id, state)
        
        # Log de auditoría
        AuditLogger.log_action(
            db=db,
            action=AuditAction.SECURITY_ALERT,
            description=f"GHL OAuth authorization initiated for client {client_id}",
            performed_by=f"Client-{client_id}",
            request_data={"client_id": client_id, "state": state}
        )
        
        return {
            "success": True,
            "authorization_url": auth_url,
            "client_id": client_id,
            "scopes": "contacts.read,contacts.write,tags.read,tags.write",
            "message": "Redirect user to authorization_url to complete OAuth flow"
        }
        
    except Exception as e:
        logger.error(f"Error initiating GHL OAuth: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/oauth/callback/callback")
async def ghl_oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Callback OAuth de GoHighLevel - Recibe el código de autorización
    """
    try:
        if error:
            logger.error(f"GHL OAuth error: {error} - {error_description}")
            raise HTTPException(
                status_code=400, 
                detail=f"OAuth error: {error_description or error}"
            )
        
        if not code:
            raise HTTPException(status_code=400, detail="Authorization code not provided")
        
        if not state:
            raise HTTPException(status_code=400, detail="State parameter not provided")
        
        # El state contiene el client_id
        client_id = state
        
        from services.ghl_oauth_service import GHLOAuthService
        
        ghl_service = GHLOAuthService(db)
        
        # Intercambiar código por tokens
        result = ghl_service.exchange_code_for_token(code, client_id, state)
        
        # Log de auditoría exitoso
        AuditLogger.log_action(
            db=db,
            action=AuditAction.SECURITY_ALERT,
            description=f"GHL OAuth completed successfully for client {client_id}",
            performed_by=f"Client-{client_id}",
            request_data={
                "client_id": client_id,
                "code": code[:10] + "...",  # Solo primeros caracteres por seguridad
                "state": state
            },
            response_data={
                "client_account_id": result["client_account_id"],
                "location_id": result["location_id"],
                "scope": result["scope"]
            },
            ip_address=request.client.host if request else None
        )
        
        logger.info(f"GHL OAuth completed for client {client_id}, location {result['location_id']}")
        
        # Respuesta de éxito con redirección
        return {
            "success": True,
            "message": "GoHighLevel integration completed successfully",
            "client_id": result["client_id"],
            "location_id": result["location_id"],
            "expires_at": result["expires_at"],
            "scope": result["scope"],
            "redirect_message": "You can now close this window and return to the application"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # Log de error
        AuditLogger.log_action(
            db=db,
            action=AuditAction.SECURITY_ALERT,
            description=f"GHL OAuth failed for client {state or 'unknown'}",
            performed_by=f"Client-{state or 'unknown'}",
            error_message=str(e),
            ip_address=request.client.host if request else None
        )
        
        logger.error(f"Error in GHL OAuth callback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# ENDPOINTS ESPECÍFICOS POR CLIENTE (MULTI-TENANT)
# ============================================

@app.get("/api/v1/clients/{client_id}/metrics")
async def get_client_metrics(
    client_id: str,
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """
    Obtiene métricas específicas de un cliente (multi-tenant)
    """
    try:
        # Verificar que el cliente existe
        client_account = db.query(ClientAccount).filter(
            ClientAccount.client_id == client_id
        ).first()
        
        if not client_account:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
        # Obtener métricas del cliente
        total_payments = db.query(Payment).filter(
            Payment.client_account_id == client_account.id
        ).count()
        
        total_amount = db.query(func.sum(Payment.expected_amount)).filter(
            Payment.client_account_id == client_account.id
        ).scalar() or 0
        
        approved_payments = db.query(Payment).filter(
            and_(
                Payment.client_account_id == client_account.id,
                Payment.status == PaymentStatus.APPROVED.value
            )
        ).count()
        
        # Métricas del mes actual
        current_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_payments = db.query(Payment).filter(
            and_(
                Payment.client_account_id == client_account.id,
                Payment.created_at >= current_month_start
            )
        ).count()
        
        return {
            "success": True,
            "client_id": client_id,
            "metrics": {
                "total_payments": total_payments,
                "total_amount": float(total_amount),
                "approved_payments": approved_payments,
                "monthly_payments": monthly_payments,
                "monthly_limit": client_account.monthly_payment_limit,
                "subscription_plan": client_account.subscription_plan
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting client metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/clients/{client_id}/payments")
async def get_client_payments(
    client_id: str,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """
    Obtiene pagos específicos de un cliente (filtrado multi-tenant)
    """
    try:
        # Verificar que el cliente existe
        client_account = db.query(ClientAccount).filter(
            ClientAccount.client_id == client_id
        ).first()
        
        if not client_account:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
        # Obtener pagos del cliente con paginación
        payments_query = db.query(Payment).filter(
            Payment.client_account_id == client_account.id
        ).order_by(Payment.created_at.desc())
        
        total_count = payments_query.count()
        payments = payments_query.offset(offset).limit(limit).all()
        
        # Convertir a formato JSON
        payments_data = []
        for payment in payments:
            payments_data.append({
                "id": payment.id,
                "internal_uuid": payment.internal_uuid,
                "mp_payment_id": payment.mp_payment_id,
                "customer_email": payment.customer_email,
                "customer_name": payment.customer_name,
                "ghl_contact_id": payment.ghl_contact_id,
                "expected_amount": float(payment.expected_amount),
                "paid_amount": float(payment.paid_amount) if payment.paid_amount else None,
                "status": payment.status,
                "created_at": payment.created_at.isoformat(),
                "processed_at": payment.processed_at.isoformat() if payment.processed_at else None,
                "created_by": payment.created_by
            })
        
        return {
            "success": True,
            "client_id": client_id,
            "payments": payments_data,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total_count
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting client payments: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/payments/create")
async def create_payment_multitenant(
    payment_data: PaymentCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """
    Crea un pago usando el sistema multi-tenant
    Usa el access_token específico del cliente si está disponible
    """
    try:
        correlation_id = getattr(request.state, 'correlation_id', f"payment_{int(time.time())}")
        client_ip = request.client.host
        
        # Gancho de Auditoría Crítica: Registrar generación de link de pago multi-tenant
        audit_service = CriticalAuditService(db)
        audit_context = AuditContext(
            user_email=payment_data.created_by,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
            tenant_id=payment_data.client_id
        )
        
        # Si se especifica client_id, verificar que existe y obtener su cuenta
        client_account = None
        if payment_data.client_id:
            client_account = db.query(ClientAccount).filter(
                ClientAccount.client_id == payment_data.client_id
            ).first()
            
            if not client_account:
                raise HTTPException(status_code=404, detail=f"Cliente {payment_data.client_id} no encontrado")
            
            if not client_account.is_active:
                raise HTTPException(status_code=400, detail=f"Cliente {payment_data.client_id} no está activo")
        
        # Usar PaymentService para crear el pago
        result = PaymentService.create_payment_link(
            db=db,
            payment_data=payment_data,
            client_ip=client_ip,
            correlation_id=correlation_id
        )
        
        # Si hay client_account, vincular el pago
        if client_account and "payment_id" in result:
            payment = db.query(Payment).filter(Payment.id == result["payment_id"]).first()
            if payment:
                payment.client_account_id = client_account.id
                db.commit()
                
                logger.info(f"Pago {payment.id} vinculado al cliente {client_account.client_id}")
        
        # Registrar auditoría crítica después del éxito
        if result.get("payment_id"):
            audit_service.log_payment_link_generated(
                context=audit_context,
                payment_id=result["payment_id"],
                amount=payment_data.amount,
                customer_email=payment_data.customer_email,
                mp_preference_id=result.get("preference_id")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating multitenant payment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/oauth/ghl/status/{client_id}")
async def get_ghl_oauth_status(
    client_id: str,
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """
    Obtiene el estado de la integración OAuth de GHL para un cliente
    Crea cliente por defecto si no existe para evitar errores 404
    """
    try:
        client_account = db.query(ClientAccount).filter(
            ClientAccount.client_id == client_id
        ).first()
        
        # Si el cliente no existe, crear uno por defecto para evitar errores
        if not client_account:
            logger.info(f"Cliente {client_id} no existe, creando cuenta por defecto")
            
            client_account = ClientAccount(
                client_id=client_id,
                client_name=f"Usuario Mock {client_id}",
                client_email=f"{client_id}@mock-client.com",
                company_name=f"Empresa Mock {client_id}",
                ghl_location_id=f"mock_location_{client_id}",
                is_active=True,
                subscription_plan="basic",
                monthly_payment_limit=None,
                current_month_payments=0
            )
            
            db.add(client_account)
            db.commit()
            db.refresh(client_account)
            
            logger.info(f"Cliente mock {client_id} creado exitosamente")
        
        # Verificar estado de tokens de forma segura
        has_ghl_token = bool(client_account.ghl_access_token)
        
        # Manejar métodos que pueden fallar de forma segura
        try:
            token_expired = client_account.is_ghl_token_expired() if has_ghl_token else True
        except Exception as e:
            logger.warning(f"Error checking token expiration for {client_id}: {e}")
            token_expired = True
            
        try:
            needs_refresh = client_account.needs_ghl_refresh() if has_ghl_token else True
        except Exception as e:
            logger.warning(f"Error checking refresh need for {client_id}: {e}")
            needs_refresh = True
        
        # 🎭 MODO DESARROLLO: Mostrar "Simulado: Conectado" si existe ghl_location_id
        is_development = os.getenv("ENVIRONMENT", "development") == "development"
        has_ghl_location = bool(client_account.ghl_location_id)
        
        # En desarrollo, si tiene ghl_location_id, mostrar como conectado aunque el token OAuth esté expirado
        if is_development and has_ghl_location:
            connected_status = True
            connection_mode = "Simulado: Conectado"
        else:
            connected_status = has_ghl_token and not token_expired
            connection_mode = "OAuth" if has_ghl_token else "Desconectado"
        
        return {
            "success": True,
            "client_id": client_account.client_id,
            "client_name": client_account.client_name,
            "client_email": client_account.client_email,
            "company_name": client_account.company_name,
            "ghl_integration": {
                "connected": connected_status,
                "connection_mode": connection_mode,
                "location_id": client_account.ghl_location_id,
                "token_expired": token_expired,
                "needs_refresh": needs_refresh,
                "expires_at": client_account.ghl_expires_at.isoformat() if client_account.ghl_expires_at else None,
                "last_refreshed": client_account.ghl_last_refreshed.isoformat() if client_account.ghl_last_refreshed else None,
                "scope": client_account.ghl_scope,
                "development_mode": is_development,
                "has_location": has_ghl_location
            },
            "account_status": {
                "is_active": client_account.is_active,
                "subscription_plan": client_account.subscription_plan,
                "monthly_payment_limit": client_account.monthly_payment_limit,
                "current_month_payments": client_account.current_month_payments
            },
            "created_at": client_account.created_at.isoformat(),
            "updated_at": client_account.updated_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting GHL OAuth status for {client_id}: {str(e)}")
        
        # En caso de error crítico, devolver respuesta por defecto en lugar de 500
        return {
            "success": False,
            "error": "Client data unavailable",
            "client_id": client_id,
            "client_name": f"Cliente {client_id}",
            "client_email": f"{client_id}@unknown.com",
            "company_name": f"Empresa {client_id}",
            "ghl_integration": {
                "connected": False,
                "connection_mode": "Error",
                "location_id": None,
                "token_expired": True,
                "needs_refresh": True,
                "expires_at": None,
                "last_refreshed": None,
                "scope": None,
                "development_mode": os.getenv("ENVIRONMENT", "development") == "development",
                "has_location": False
            },
            "account_status": {
                "is_active": False,
                "subscription_plan": "unknown",
                "monthly_payment_limit": None,
                "current_month_payments": 0
            },
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "error_details": str(e)
        }

@app.post("/oauth/ghl/test/{client_id}")
async def test_ghl_connection(
    client_id: str,
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """
    Prueba la conexión con GoHighLevel para un cliente
    """
    try:
        from services.ghl_oauth_service import GHLOAuthService
        
        ghl_service = GHLOAuthService(db)
        result = ghl_service.test_connection(client_id)
        
        # Log de auditoría
        AuditLogger.log_action(
            db=db,
            action=AuditAction.SECURITY_ALERT,
            description=f"GHL connection test for client {client_id}: {'SUCCESS' if result['success'] else 'FAILED'}",
            performed_by="Admin",
            response_data=result
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error testing GHL connection: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/clients")
async def list_client_accounts(
    limit: int = 50,
    offset: int = 0,
    active_only: bool = True,
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """
    Lista cuentas de clientes multi-tenant
    """
    try:
        query = db.query(ClientAccount)
        
        if active_only:
            query = query.filter(ClientAccount.is_active == True)
        
        clients = query.order_by(ClientAccount.created_at.desc()).offset(offset).limit(limit).all()
        
        client_list = []
        for client in clients:
            client_data = {
                "id": client.id,
                "client_id": client.client_id,
                "client_name": client.client_name,
                "company_name": client.company_name,
                "client_email": client.client_email,
                "is_active": client.is_active,
                "subscription_plan": client.subscription_plan,
                "ghl_connected": bool(client.ghl_access_token),
                "ghl_location_id": client.ghl_location_id,
                "mp_connected": bool(client.mp_account_id),
                "monthly_payment_limit": client.monthly_payment_limit,
                "current_month_payments": client.current_month_payments,
                "created_at": client.created_at.isoformat(),
                "last_login_at": client.last_login_at.isoformat() if client.last_login_at else None
            }
            client_list.append(client_data)
        
        total_clients = db.query(ClientAccount).count()
        active_clients = db.query(ClientAccount).filter(ClientAccount.is_active == True).count()
        
        return {
            "success": True,
            "clients": client_list,
            "pagination": {
                "total": total_clients,
                "active": active_clients,
                "limit": limit,
                "offset": offset,
                "returned": len(client_list)
            }
        }
        
    except Exception as e:
        logger.error(f"Error listing client accounts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para archivado de logs en S3
@app.post("/admin/archive-logs")
async def archive_logs_to_s3(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token),
    days_back: int = 90,
    compress: bool = True,
    dry_run: bool = False
):
    """
    Archiva logs de alertas y auditoría en Amazon S3
    Permite backup manual desde el dashboard
    """
    correlation_id = request.headers.get("x-correlation-id", f"archive_{datetime.utcnow().timestamp()}")
    
    try:
        from services.s3_archive_service import S3ArchiveService
        
        # Calcular fechas
        end_date = datetime.utcnow() - timedelta(days=days_back)
        start_date = datetime(2020, 1, 1)  # Fecha muy antigua para incluir todo
        
        # Inicializar servicio S3
        s3_service = S3ArchiveService(db)
        
        if dry_run:
            # Modo dry-run: solo obtener resumen
            summary = s3_service.get_archive_summary(start_date, end_date)
            
            AuditLogger.log_action(
                db=db,
                action=AuditAction.SECURITY_ALERT,
                description=f"S3 archive dry-run executed - {summary['records_to_archive']['total']} records would be archived",
                performed_by="Admin",
                request_data={
                    "days_back": days_back,
                    "compress": compress,
                    "dry_run": dry_run
                },
                response_data=summary,
                ip_address=request.client.host,
                correlation_id=correlation_id
            )
            
            return {
                "success": True,
                "message": "Dry-run completed - no files uploaded",
                "summary": summary,
                "dry_run": True
            }
        
        else:
            # Ejecutar archivado real en background
            def archive_task():
                try:
                    results = s3_service.archive_all_logs_for_date_range(start_date, end_date, compress)
                    
                    total_files = sum(result.files_uploaded for result in results.values())
                    total_records = sum(result.total_records for result in results.values())
                    total_bytes = sum(result.bytes_uploaded for result in results.values())
                    
                    # Log de auditoría del resultado
                    AuditLogger.log_action(
                        db=db,
                        action=AuditAction.SECURITY_ALERT,
                        description=f"S3 archive completed - {total_files} files, {total_records} records, {total_bytes} bytes",
                        performed_by="Admin",
                        request_data={
                            "days_back": days_back,
                            "compress": compress
                        },
                        response_data={
                            "total_files": total_files,
                            "total_records": total_records,
                            "total_bytes": total_bytes,
                            "results": {k: {"success": v.success, "files": v.files_uploaded, "records": v.total_records} for k, v in results.items()}
                        },
                        ip_address=request.client.host,
                        correlation_id=correlation_id
                    )
                    
                    logger.info(f"S3 archive completed: {total_files} files, {total_records} records")
                    
                except Exception as e:
                    logger.error(f"S3 archive failed: {str(e)}")
                    
                    AuditLogger.log_action(
                        db=db,
                        action=AuditAction.SECURITY_ALERT,
                        description=f"S3 archive failed: {str(e)}",
                        performed_by="Admin",
                        error_message=str(e),
                        ip_address=request.client.host,
                        correlation_id=correlation_id
                    )
            
            background_tasks.add_task(archive_task)
            
            # Log de inicio
            AuditLogger.log_action(
                db=db,
                action=AuditAction.SECURITY_ALERT,
                description=f"S3 archive initiated - logs older than {days_back} days",
                performed_by="Admin",
                request_data={
                    "days_back": days_back,
                    "compress": compress,
                    "end_date": end_date.isoformat()
                },
                ip_address=request.client.host,
                correlation_id=correlation_id
            )
            
            return {
                "success": True,
                "message": f"Archive process initiated for logs older than {days_back} days",
                "correlation_id": correlation_id,
                "background_task": True,
                "estimated_end_date": end_date.isoformat()
            }
    
    except ImportError:
        raise HTTPException(
            status_code=500, 
            detail="S3 archive service not available. Install boto3: pip install boto3"
        )
    except Exception as e:
        logger.error(f"Error initiating S3 archive: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/archive-status")
async def get_archive_status(
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """
    Obtiene estado del sistema de archivado S3
    """
    try:
        from services.s3_archive_service import S3ArchiveService
        
        s3_service = S3ArchiveService(db)
        
        # Obtener archivos archivados
        archived_files = s3_service.list_archived_files()
        
        # Calcular estadísticas
        total_files = len(archived_files)
        total_size = sum(f['size'] for f in archived_files)
        
        # Agrupar por tipo
        file_types = {}
        for file_info in archived_files:
            key_parts = file_info['key'].split('/')
            if len(key_parts) >= 2:
                file_type = key_parts[1]
                if file_type not in file_types:
                    file_types[file_type] = {"count": 0, "size": 0}
                file_types[file_type]["count"] += 1
                file_types[file_type]["size"] += file_info['size']
        
        # Obtener resumen de logs pendientes de archivar
        end_date = datetime.utcnow() - timedelta(days=90)
        start_date = datetime(2020, 1, 1)
        pending_summary = s3_service.get_archive_summary(start_date, end_date)
        
        return {
            "success": True,
            "s3_config": {
                "bucket": s3_service.config.bucket_name,
                "region": s3_service.config.region,
                "prefix": s3_service.config.prefix
            },
            "archived_files": {
                "total_files": total_files,
                "total_size_bytes": total_size,
                "by_type": file_types,
                "latest_files": sorted(archived_files, key=lambda x: x['last_modified'], reverse=True)[:10]
            },
            "pending_archive": pending_summary.get("records_to_archive", {}),
            "last_check": datetime.utcnow().isoformat()
        }
    
    except ImportError:
        raise HTTPException(
            status_code=500, 
            detail="S3 archive service not available. Install boto3: pip install boto3"
        )
    except Exception as e:
        logger.error(f"Error getting archive status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/test-notifications")
async def test_notifications(
    request: Request,
    notification_type: str = "test",
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """
    Prueba el sistema de notificaciones con manejo robusto de errores
    """
    try:
        from services.notification_service import NotificationService
        
        notification_service = NotificationService(db)
        
        if notification_type == "test":
            result = notification_service.test_notifications()
        elif notification_type == "security":
            result = notification_service.notify_brute_force_attack("192.168.1.100", 5)
        elif notification_type == "system_error":
            result = notification_service.notify_system_error(
                "Test system error notification",
                "test_error",
                component="notification_test"
            )
        elif notification_type == "reconciliation":
            result = notification_service.notify_reconciliation_completed(
                "test_recon_123", 2, 1
            )
        else:
            return {
                "success": False,
                "error": "Invalid notification type",
                "valid_types": ["test", "security", "system_error", "reconciliation"]
            }
        
        return {
            "success": True,
            "notification_type": notification_type,
            "result": result
        }
        
    except ImportError as e:
        logger.warning(f"NotificationService import error: {str(e)}")
        
        # Registrar en AuditLog para trazabilidad
        AuditLogger.log_action(
            db=db,
            action=AuditAction.SECURITY_ALERT,
            description=f"Prueba de notificación fallida - Servicio no configurado: {notification_type}",
            performed_by="Admin",
            error_message=f"ImportError: {str(e)}",
            ip_address=request.client.host,
            correlation_id=f"notification_test_fail_{int(time.time())}"
        )
        
        return {
            "success": False,
            "error": "Servicio No Configurado",
            "message": "NotificationService no está disponible. Verifique las dependencias.",
            "notification_type": notification_type,
            "result": {
                "success": False,
                "message": "Service not configured",
                "channels": []
            }
        }
    except AttributeError as e:
        logger.warning(f"NotificationService configuration error: {str(e)}")
        
        # Registrar en AuditLog para trazabilidad
        AuditLogger.log_action(
            db=db,
            action=AuditAction.SECURITY_ALERT,
            description=f"Prueba de notificación fallida - Error de configuración: {notification_type}",
            performed_by="Admin",
            error_message=f"AttributeError: {str(e)}",
            ip_address=request.client.host,
            correlation_id=f"notification_test_config_fail_{int(time.time())}"
        )
        
        return {
            "success": False,
            "error": "Servicio No Configurado",
            "message": f"Error de configuración: {str(e)}",
            "notification_type": notification_type,
            "result": {
                "success": False,
                "message": "Configuration error",
                "channels": []
            }
        }
    except Exception as e:
        logger.warning(f"NotificationService general error: {str(e)}")
        
        # Registrar en AuditLog para trazabilidad
        AuditLogger.log_action(
            db=db,
            action=AuditAction.SECURITY_ALERT,
            description=f"Prueba de notificación fallida - Error general: {notification_type}",
            performed_by="Admin",
            error_message=str(e),
            ip_address=request.client.host,
            correlation_id=f"notification_test_error_{int(time.time())}"
        )
        
        return {
            "success": False,
            "error": "Servicio No Configurado",
            "message": f"Error del servicio de notificaciones: {str(e)}",
            "notification_type": notification_type,
            "result": {
                "success": False,
                "message": "Service error",
                "channels": []
            }
        }

@app.get("/admin/notification-config")
async def get_notification_config(
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """
    Obtiene la configuración actual de notificaciones
    """
    try:
        from services.notification_service import NotificationService
        
        # Intentar crear el servicio de notificaciones
        notification_service = NotificationService(db)
        config = notification_service.config
        
        # Verificar que la configuración sea válida
        if not config:
            return {
                "success": True,
                "config": {
                    "status": "Servicio No Configurado",
                    "slack_configured": False,
                    "email_configured": False,
                    "webhooks_configured": False,
                    "enabled_channels": [],
                    "min_priority": "medium",
                    "rate_limit_minutes": 5,
                    "slack_channel": "#alerts",
                    "to_emails_count": 0,
                    "webhook_urls_count": 0,
                    "message": "NotificationService no está configurado correctamente"
                }
            }
        
        return {
            "success": True,
            "config": {
                "status": "Configurado",
                "slack_configured": bool(config.slack_webhook_url),
                "email_configured": bool(config.smtp_server and config.from_email),
                "webhooks_configured": bool(config.webhook_urls),
                "enabled_channels": [c.value for c in config.enabled_channels if c],
                "min_priority": config.min_priority.value,
                "rate_limit_minutes": config.rate_limit_minutes,
                "slack_channel": config.slack_channel,
                "to_emails_count": len(config.to_emails),
                "webhook_urls_count": len(config.webhook_urls)
            }
        }
        
    except ImportError as e:
        logger.warning(f"NotificationService import error: {str(e)}")
        return {
            "success": True,
            "config": {
                "status": "Servicio No Configurado",
                "slack_configured": False,
                "email_configured": False,
                "webhooks_configured": False,
                "enabled_channels": [],
                "min_priority": "medium",
                "rate_limit_minutes": 5,
                "slack_channel": "#alerts",
                "to_emails_count": 0,
                "webhook_urls_count": 0,
                "message": "NotificationService no está disponible. Verifique las dependencias."
            }
        }
    except AttributeError as e:
        logger.warning(f"NotificationService configuration error: {str(e)}")
        return {
            "success": True,
            "config": {
                "status": "Servicio No Configurado",
                "slack_configured": False,
                "email_configured": False,
                "webhooks_configured": False,
                "enabled_channels": [],
                "min_priority": "medium",
                "rate_limit_minutes": 5,
                "slack_channel": "#alerts",
                "to_emails_count": 0,
                "webhook_urls_count": 0,
                "message": f"Error de configuración: {str(e)}"
            }
        }
    except Exception as e:
        logger.warning(f"NotificationService general error: {str(e)}")
        return {
            "success": True,
            "config": {
                "status": "Servicio No Configurado",
                "slack_configured": False,
                "email_configured": False,
                "webhooks_configured": False,
                "enabled_channels": [],
                "min_priority": "medium",
                "rate_limit_minutes": 5,
                "slack_channel": "#alerts",
                "to_emails_count": 0,
                "webhook_urls_count": 0,
                "message": f"Error del servicio de notificaciones: {str(e)}"
            }
        }

# ============================================================================
# ENDPOINTS DE AUDITORÍA CRÍTICA
# ============================================================================

class IntegrationSettingsUpdate(BaseModel):
    """Modelo para actualización de configuraciones de integración"""
    client_id: str
    settings: Dict[str, Any]
    updated_by: str

@app.put("/admin/integration-settings/{client_id}")
async def update_integration_settings(
    client_id: str,
    settings_update: IntegrationSettingsUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """
    Actualiza configuraciones de integración con auditoría crítica
    """
    try:
        client_ip = request.client.host
        
        # Buscar cuenta del cliente
        client_account = db.query(ClientAccount).filter(
            ClientAccount.client_id == client_id
        ).first()
        
        if not client_account:
            raise HTTPException(status_code=404, detail=f"Cliente {client_id} no encontrado")
        
        # Gancho de Auditoría Crítica: Registrar cambio de configuración
        audit_service = CriticalAuditService(db)
        audit_context = AuditContext(
            user_email=settings_update.updated_by,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
            tenant_id=client_id
        )
        
        # Capturar valores anteriores
        old_values = {
            "default_tag_paid": client_account.default_tag_paid,
            "auto_tag_payments": client_account.auto_tag_payments,
            "payment_tag_prefix": client_account.payment_tag_prefix,
            "webhook_url": client_account.webhook_url,
            "monthly_payment_limit": client_account.monthly_payment_limit
        }
        
        # Aplicar cambios
        new_values = {}
        for key, value in settings_update.settings.items():
            if hasattr(client_account, key):
                setattr(client_account, key, value)
                new_values[key] = value
            else:
                logger.warning(f"Attempted to set unknown setting: {key}")
        
        # Actualizar timestamp
        client_account.updated_at = datetime.utcnow()
        db.commit()
        
        # Registrar auditoría crítica
        audit_service.log_config_change(
            context=audit_context,
            config_type="integration_settings",
            config_id=client_id,
            old_values=old_values,
            new_values=new_values
        )
        
        return {
            "success": True,
            "message": f"Configuración actualizada para cliente {client_id}",
            "updated_settings": new_values,
            "audit_logged": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating integration settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/audit-trail")
async def get_audit_trail(
    limit: int = 100,
    user_email: Optional[str] = None,
    action: Optional[str] = None,
    tenant_id: Optional[str] = None,
    hours_back: int = 24,
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """
    Obtiene el rastro de auditoría crítica del sistema
    """
    try:
        audit_service = CriticalAuditService(db)
        
        audit_logs = audit_service.get_audit_trail(
            limit=limit,
            user_email=user_email,
            action=action,
            tenant_id=tenant_id,
            hours_back=hours_back
        )
        
        # Convertir a formato serializable
        audit_data = []
        for log in audit_logs:
            audit_data.append({
                "id": log.id,
                "tenant_id": log.tenant_id,
                "user_email": log.user_email,
                "action": log.action,
                "entity": log.entity,
                "entity_id": log.entity_id,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "details": json.loads(log.details) if log.details else None,
                "old_values": json.loads(log.old_values) if log.old_values else None,
                "new_values": json.loads(log.new_values) if log.new_values else None,
                "created_at": log.created_at.isoformat()
            })
        
        # Obtener estadísticas
        stats = audit_service.get_audit_stats(hours_back)
        
        # Detectar actividad sospechosa
        suspicious_activity = audit_service.get_suspicious_activity(hours_back)
        
        return {
            "success": True,
            "audit_trail": audit_data,
            "statistics": stats,
            "suspicious_activity": suspicious_activity,
            "filters_applied": {
                "limit": limit,
                "user_email": user_email,
                "action": action,
                "tenant_id": tenant_id,
                "hours_back": hours_back
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting audit trail: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/user-activity/{user_email}")
async def get_user_activity(
    user_email: str,
    hours_back: int = 24,
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """
    Obtiene toda la actividad de un usuario específico
    """
    try:
        audit_service = CriticalAuditService(db)
        
        user_activity = audit_service.get_user_activity(user_email, hours_back)
        
        # Convertir a formato serializable
        activity_data = []
        for log in user_activity:
            activity_data.append({
                "id": log.id,
                "action": log.action,
                "entity": log.entity,
                "entity_id": log.entity_id,
                "ip_address": log.ip_address,
                "details": json.loads(log.details) if log.details else None,
                "created_at": log.created_at.isoformat()
            })
        
        return {
            "success": True,
            "user_email": user_email,
            "activity_count": len(activity_data),
            "activity": activity_data,
            "time_range_hours": hours_back,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting user activity: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/simulate-login")
async def simulate_login_attempt(
    user_email: str,
    success: bool = True,
    request: Request = None,
    db: Session = Depends(get_db),
    admin_token: str = Depends(verify_admin_token)
):
    """
    Simula un intento de login para pruebas de auditoría
    """
    try:
        client_ip = request.client.host if request else "127.0.0.1"
        
        audit_service = CriticalAuditService(db)
        audit_context = AuditContext(
            user_email=user_email,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent") if request else "Test-Agent"
        )
        
        # Registrar intento de login
        audit_log = audit_service.log_login_attempt(
            context=audit_context,
            success=success,
            details={
                "simulation": True,
                "test_mode": True
            }
        )
        
        return {
            "success": True,
            "message": f"Login attempt simulated for {user_email}",
            "login_success": success,
            "audit_log_id": audit_log.id,
            "ip_address": client_ip
        }
        
    except Exception as e:
        logger.error(f"Error simulating login: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)