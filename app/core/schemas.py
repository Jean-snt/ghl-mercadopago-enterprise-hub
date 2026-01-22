"""
Esquemas Pydantic para validación de datos
"""
from pydantic import BaseModel, validator
from typing import Optional, Dict, Any

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