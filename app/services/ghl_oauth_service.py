"""
GHLOAuthService - Servicio OAuth para GoHighLevel Multi-tenant
Maneja autorización, tokens y renovación para múltiples clientes
"""
import os
import requests
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from urllib.parse import urlencode

from models import ClientAccount

logger = logging.getLogger("ghl_oauth_service")

class GHLOAuthService:
    """
    Servicio OAuth para GoHighLevel con soporte multi-tenant
    Maneja autorización y tokens por cliente
    """
    
    def __init__(self, db: Session):
        self.db = db
        
        # Configuración OAuth de GHL
        self.client_id = os.getenv("GHL_CLIENT_ID")
        self.client_secret = os.getenv("GHL_CLIENT_SECRET")
        self.redirect_uri = os.getenv("GHL_REDIRECT_URI", f"{os.getenv('BASE_URL', 'http://localhost:8000')}/oauth/callback/callback")
        self.scopes = os.getenv("GHL_SCOPES", "contacts.read,contacts.write,tags.read,tags.write")
        
        # URLs de GoHighLevel
        self.auth_url = "https://marketplace.gohighlevel.com/oauth/chooselocation"
        self.token_url = "https://services.leadconnectorhq.com/oauth/token"
        self.user_info_url = "https://services.leadconnectorhq.com/oauth/userinfo"
        
        logger.info("GHLOAuthService initialized")
    
    def get_authorization_url(self, client_id: str, state: Optional[str] = None) -> str:
        """
        Genera URL de autorización de GoHighLevel
        """
        if not self.client_id or not self.client_secret:
            raise ValueError("GHL OAuth credentials not configured")
        
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self.scopes,
            "state": state or client_id  # Usar client_id como state por defecto
        }
        
        auth_url = f"{self.auth_url}?{urlencode(params)}"
        
        logger.info(f"Generated GHL auth URL for client {client_id}")
        return auth_url
    
    def exchange_code_for_token(
        self,
        authorization_code: str,
        client_id: str,
        state: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Intercambia código de autorización por tokens de GHL
        Soporta modo simulación para desarrollo
        """
        try:
            # Detectar si es una simulación
            is_simulation = authorization_code.startswith("mock_auth_code_")
            
            if is_simulation:
                logger.info(f"🧪 Modo simulación detectado para cliente {client_id}")
                
                # Generar tokens mock para simulación
                mock_tokens = {
                    "access_token": f"mock_ghl_access_token_{client_id}_{int(time.time())}",
                    "refresh_token": f"mock_ghl_refresh_token_{client_id}_{int(time.time())}",
                    "token_type": "Bearer",
                    "expires_in": 3600,  # 1 hora
                    "scope": self.scopes
                }
                
                # Información mock del usuario
                mock_user_info = {
                    "locationId": f"mock_location_{client_id}",
                    "name": f"Usuario Mock {client_id}",
                    "email": f"{client_id}@mock-ghl.com",
                    "companyName": f"Empresa Mock {client_id}"
                }
                
                logger.info(f"🎭 Tokens mock generados para {client_id}")
                
            else:
                # Flujo OAuth real
                # Preparar datos para intercambio de token
                token_data = {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "authorization_code",
                    "code": authorization_code,
                    "redirect_uri": self.redirect_uri
                }
                
                # Realizar intercambio
                response = requests.post(
                    self.token_url,
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=10
                )
                
                if response.status_code != 200:
                    logger.error(f"GHL token exchange failed: {response.status_code} - {response.text}")
                    raise Exception(f"Token exchange failed: {response.status_code}")
                
                mock_tokens = response.json()
                
                # Obtener información del usuario/location
                mock_user_info = self._get_user_info(mock_tokens["access_token"])
            
            # Buscar o crear cuenta de cliente
            client_account = self.db.query(ClientAccount).filter(
                ClientAccount.client_id == client_id
            ).first()
            
            if not client_account:
                # Crear nueva cuenta de cliente
                client_account = ClientAccount(
                    client_id=client_id,
                    client_name=mock_user_info.get("name", f"Cliente {client_id}"),
                    client_email=mock_user_info.get("email"),
                    company_name=mock_user_info.get("companyName", f"Empresa {client_id}"),
                    ghl_location_id=mock_user_info.get("locationId"),
                    is_active=True
                )
                self.db.add(client_account)
            
            # Actualizar tokens de GHL
            client_account.ghl_access_token = mock_tokens["access_token"]
            client_account.ghl_refresh_token = mock_tokens.get("refresh_token")
            client_account.ghl_token_type = mock_tokens.get("token_type", "Bearer")
            client_account.ghl_scope = mock_tokens.get("scope", self.scopes)
            
            # Calcular expiración
            expires_in = mock_tokens.get("expires_in", 3600)  # Default 1 hora
            client_account.ghl_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            client_account.ghl_last_refreshed = datetime.utcnow()
            
            # Actualizar información del usuario
            if not client_account.ghl_location_id:
                client_account.ghl_location_id = mock_user_info.get("locationId")
            
            client_account.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            mode_text = "SIMULACIÓN" if is_simulation else "PRODUCCIÓN"
            logger.info(f"GHL OAuth completado ({mode_text}) para cliente {client_id}, location {client_account.ghl_location_id}")
            
            return {
                "success": True,
                "client_account_id": client_account.id,
                "client_id": client_account.client_id,
                "location_id": client_account.ghl_location_id,
                "expires_at": client_account.ghl_expires_at.isoformat(),
                "scope": client_account.ghl_scope,
                "user_info": mock_user_info,
                "simulation_mode": is_simulation
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during GHL OAuth: {str(e)}")
            raise Exception(f"Network error: {str(e)}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error in GHL OAuth token exchange: {str(e)}")
            raise e
    
    def _get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Obtiene información del usuario desde GoHighLevel
        """
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(
                self.user_info_url,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get GHL user info: {response.status_code}")
                return {"locationId": "unknown", "name": "Unknown User"}
                
        except Exception as e:
            logger.error(f"Error getting GHL user info: {str(e)}")
            return {"locationId": "unknown", "name": "Unknown User"}
    
    def refresh_token(self, client_account: ClientAccount) -> bool:
        """
        Renueva el access token de GHL usando el refresh token
        """
        if not client_account.ghl_refresh_token:
            logger.warning(f"No GHL refresh token available for client {client_account.client_id}")
            return False
        
        try:
            refresh_data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": client_account.ghl_refresh_token
            }
            
            response = requests.post(
                self.token_url,
                data=refresh_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"GHL token refresh failed for client {client_account.client_id}: {response.status_code}")
                return False
            
            token_response = response.json()
            
            # Actualizar tokens
            client_account.ghl_access_token = token_response["access_token"]
            if "refresh_token" in token_response:
                client_account.ghl_refresh_token = token_response["refresh_token"]
            
            # Actualizar expiración
            expires_in = token_response.get("expires_in", 3600)
            client_account.ghl_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            client_account.ghl_last_refreshed = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"GHL token refreshed successfully for client {client_account.client_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error refreshing GHL token for client {client_account.client_id}: {str(e)}")
            return False
    
    def get_valid_token(self, client_id: str) -> Optional[str]:
        """
        Obtiene un token válido de GHL para el cliente, renovándolo si es necesario
        """
        client_account = self.db.query(ClientAccount).filter(
            ClientAccount.client_id == client_id,
            ClientAccount.is_active == True
        ).first()
        
        if not client_account or not client_account.ghl_access_token:
            logger.warning(f"No GHL account found for client {client_id}")
            return None
        
        # Verificar si necesita renovación
        if client_account.needs_ghl_refresh():
            logger.info(f"GHL token needs refresh for client {client_id}")
            if self.refresh_token(client_account):
                return client_account.ghl_access_token
            else:
                logger.error(f"Failed to refresh GHL token for client {client_id}")
                return None
        
        return client_account.ghl_access_token
    
    def get_client_location_id(self, client_id: str) -> Optional[str]:
        """
        Obtiene el location_id de GHL para un cliente
        """
        client_account = self.db.query(ClientAccount).filter(
            ClientAccount.client_id == client_id,
            ClientAccount.is_active == True
        ).first()
        
        return client_account.ghl_location_id if client_account else None
    
    def update_contact_with_payment(
        self,
        client_id: str,
        contact_id: str,
        payment_amount: float,
        payment_id: str
    ) -> bool:
        """
        Actualiza un contacto en GHL con información de pago
        """
        try:
            # Obtener token válido
            access_token = self.get_valid_token(client_id)
            if not access_token:
                logger.error(f"No valid GHL token for client {client_id}")
                return False
            
            # Obtener location_id
            location_id = self.get_client_location_id(client_id)
            if not location_id:
                logger.error(f"No location_id for client {client_id}")
                return False
            
            # Obtener configuración del cliente
            client_account = self.db.query(ClientAccount).filter(
                ClientAccount.client_id == client_id
            ).first()
            
            if not client_account:
                return False
            
            # Preparar datos de actualización
            tag_prefix = client_account.payment_tag_prefix or "MP_PAGADO"
            payment_tag = f"{tag_prefix}_{payment_amount}"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Version": "2021-07-28"
            }
            
            # Actualizar contacto con tag
            update_data = {
                "tags": [payment_tag],
                "customFields": {
                    "payment_status": "paid",
                    "payment_amount": str(payment_amount),
                    "payment_date": datetime.utcnow().isoformat(),
                    "mp_payment_id": payment_id
                }
            }
            
            # URL de la API de GHL v2
            contact_url = f"https://services.leadconnectorhq.com/contacts/{contact_id}"
            
            response = requests.put(
                contact_url,
                json=update_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"GHL contact {contact_id} updated successfully for client {client_id}")
                return True
            else:
                logger.error(f"GHL contact update failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating GHL contact: {str(e)}")
            return False
    
    def test_connection(self, client_id: str) -> Dict[str, Any]:
        """
        Prueba la conexión con GHL para un cliente
        Soporta modo simulación para desarrollo
        """
        try:
            access_token = self.get_valid_token(client_id)
            if not access_token:
                return {
                    "success": False,
                    "error": "No valid access token"
                }
            
            # Detectar si es un token mock
            is_mock = access_token.startswith("mock_ghl_access_token_")
            
            if is_mock:
                # Simulación exitosa
                return {
                    "success": True,
                    "message": "GHL connection successful (SIMULATION MODE)",
                    "mode": "simulation",
                    "client_id": client_id,
                    "token_type": "mock",
                    "data": {
                        "locations": [
                            {
                                "id": f"mock_location_{client_id}",
                                "name": f"Location Mock {client_id}",
                                "status": "active"
                            }
                        ]
                    }
                }
            else:
                # Hacer una llamada real a la API
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Version": "2021-07-28"
                }
                
                response = requests.get(
                    "https://services.leadconnectorhq.com/locations/",
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": "GHL connection successful",
                        "mode": "production",
                        "data": response.json()
                    }
                else:
                    return {
                        "success": False,
                        "error": f"API call failed: {response.status_code}"
                    }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }