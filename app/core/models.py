"""
Modelos SQLAlchemy para sistema MercadoPago Enterprise
Incluye auditoría completa y seguridad reforzada
"""
from sqlalchemy import Column, Integer, String, DateTime, Numeric, Boolean, Text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timedelta
from enum import Enum
import uuid

Base = declarative_base()

class PaymentStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved" 
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    IN_PROCESS = "in_process"

class AuditAction(Enum):
    PAYMENT_LINK_GENERATED = "payment_link_generated"
    WEBHOOK_RECEIVED = "webhook_received"
    WEBHOOK_PROCESSED = "webhook_processed"
    WEBHOOK_FAILED = "webhook_failed"
    PAYMENT_APPROVED = "payment_approved"
    PAYMENT_REJECTED = "payment_rejected"
    GHL_UPDATE_SUCCESS = "ghl_update_success"
    GHL_UPDATE_FAILED = "ghl_update_failed"
    GHL_TAG_APPLIED = "ghl_tag_applied"
    SECURITY_ALERT = "security_alert"
    AMOUNT_MISMATCH = "amount_mismatch"
    DUPLICATE_PAYMENT_ATTEMPT = "duplicate_payment_attempt"

class PaymentEvent(Base):
    """Tabla para tracking de eventos de pagos y prevención de duplicados"""
    __tablename__ = 'payment_events'
    
    id = Column(Integer, primary_key=True)
    payment_id = Column(Integer, ForeignKey('payments.id'), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)  # payment_approved, notification_sent, etc.
    event_data = Column(Text, nullable=True)  # JSON con datos del evento
    created_at = Column(DateTime, nullable=False, default=func.now())
    processed_at = Column(DateTime, nullable=True)
    
    # Relaciones
    payment = relationship("Payment", back_populates="payment_events")
    
    # Índices para prevenir duplicados y performance
    __table_args__ = (
        Index('idx_payment_event_type', 'payment_id', 'event_type'),
        Index('idx_event_created', 'event_type', 'created_at'),
    )
    
    def __repr__(self):
        return f"<PaymentEvent(id={self.id}, payment_id={self.payment_id}, event_type={self.event_type})>"

class Payment(Base):
    """Modelo principal de pagos con seguridad reforzada y soporte multi-tenant"""
    __tablename__ = 'payments'
    
    id = Column(Integer, primary_key=True)
    # UUID interno para mayor seguridad
    internal_uuid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    
    # Datos de MercadoPago
    mp_payment_id = Column(String(50), unique=True, nullable=True, index=True)
    mp_preference_id = Column(String(50), nullable=True, index=True)
    
    # Datos del cliente y negocio
    customer_email = Column(String(255), nullable=False)
    customer_name = Column(String(255), nullable=True)
    ghl_contact_id = Column(String(100), nullable=False, index=True)
    
    # Relaciones multi-tenant
    client_account_id = Column(Integer, ForeignKey('client_accounts.id'), nullable=True, index=True)
    mp_account_id = Column(Integer, ForeignKey('mercadopago_accounts.id'), nullable=True, index=True)
    
    # Montos y validación
    expected_amount = Column(Numeric(10, 2), nullable=False)
    paid_amount = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(3), nullable=False, default='ARS')
    
    # Estados y control
    status = Column(String(20), nullable=False, default=PaymentStatus.PENDING.value)
    is_processed = Column(Boolean, default=False, nullable=False)
    webhook_processed_count = Column(Integer, default=0, nullable=False)
    
    # Seguridad y auditoría
    created_by = Column(String(100), nullable=False)  # Admin que generó el link
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    processed_at = Column(DateTime, nullable=True)
    
    # Datos adicionales para auditoría
    mp_payment_method = Column(String(50), nullable=True)
    mp_status_detail = Column(String(100), nullable=True)
    client_ip = Column(String(45), nullable=True)
    
    # Relaciones
    audit_logs = relationship("AuditLog", back_populates="payment", cascade="all, delete-orphan")
    security_alerts = relationship("SecurityAlert", back_populates="payment", cascade="all, delete-orphan")
    payment_events = relationship("PaymentEvent", back_populates="payment", cascade="all, delete-orphan")
    mp_account = relationship("MercadoPagoAccount", back_populates="payments")
    client_account = relationship("ClientAccount", back_populates="payments")
    
    # Índices para performance multi-tenant
    __table_args__ = (
        Index('idx_payment_status_created', 'status', 'created_at'),
        Index('idx_payment_ghl_contact', 'ghl_contact_id', 'status'),
        Index('idx_payment_mp_id_status', 'mp_payment_id', 'status'),
        Index('idx_payment_client_account', 'client_account_id', 'status'),
        Index('idx_payment_client_created', 'client_account_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Payment(id={self.id}, mp_payment_id={self.mp_payment_id}, status={self.status})>"

class CriticalAuditLog(Base):
    """Módulo de Auditoría de Acciones Críticas según documento oficial"""
    __tablename__ = 'critical_audit_logs'
    
    id = Column(Integer, primary_key=True)
    
    # Campos según especificación del documento oficial
    tenant_id = Column(String(100), nullable=True, index=True)  # ID del tenant/cliente
    user_email = Column(String(255), nullable=False, index=True)  # Email del usuario que ejecuta la acción
    action = Column(String(50), nullable=False, index=True)  # login, config_change, link_generated
    entity = Column(String(100), nullable=True)  # Tipo de entidad afectada
    entity_id = Column(String(255), nullable=True)  # ID de la entidad (usar IDs de negocio, no UUIDs internos)
    ip_address = Column(String(45), nullable=False, index=True)  # IP del usuario
    
    # Campos adicionales para contexto
    user_agent = Column(String(500), nullable=True)  # Browser/client info
    details = Column(Text, nullable=True)  # Detalles adicionales en JSON
    old_values = Column(Text, nullable=True)  # Valores anteriores (para config_change)
    new_values = Column(Text, nullable=True)  # Valores nuevos (para config_change)
    
    # Timestamp
    created_at = Column(DateTime, nullable=False, default=func.now(), index=True)
    
    # Índices para queries de auditoría
    __table_args__ = (
        Index('idx_critical_audit_tenant_action', 'tenant_id', 'action'),
        Index('idx_critical_audit_user_action', 'user_email', 'action'),
        Index('idx_critical_audit_entity', 'entity', 'entity_id'),
        Index('idx_critical_audit_ip_time', 'ip_address', 'created_at'),
        Index('idx_critical_audit_action_time', 'action', 'created_at'),
    )
    
    def __repr__(self):
        return f"<CriticalAuditLog(id={self.id}, user={self.user_email}, action={self.action})>"

class AuditLog(Base):
    """Registro completo de auditoría para todas las acciones del sistema con blockchain inmutable"""
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    payment_id = Column(Integer, ForeignKey('payments.id'), nullable=True, index=True)
    
    # Acción y contexto
    action = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=False)
    
    # Datos del usuario/sistema
    performed_by = Column(String(100), nullable=False)  # Admin, System, Webhook, etc.
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)
    
    # Datos técnicos (filtrados por @sensitive_data_filter)
    request_data = Column(Text, nullable=True)  # JSON de la request
    response_data = Column(Text, nullable=True)  # JSON de la response
    error_message = Column(Text, nullable=True)
    
    # Metadatos
    timestamp = Column(DateTime, nullable=False, default=func.now(), index=True)
    session_id = Column(String(100), nullable=True)
    correlation_id = Column(String(100), nullable=True)  # Para tracking de requests
    
    # Blockchain Inmutable - Certificación Bancaria (según esquema real)
    previous_hash = Column(Text, nullable=True, index=True)  # SHA-256 del registro anterior
    current_hash = Column(Text, nullable=True, index=True)  # SHA-256 de este registro
    block_number = Column(Integer, nullable=True, default=0, index=True)  # Número secuencial del bloque
    
    # Campos adicionales de blockchain según esquema real
    signature = Column(Text, nullable=True)  # Firma digital
    merkle_root = Column(Text, nullable=True)  # Raíz del árbol Merkle
    nonce = Column(Integer, nullable=True, default=0)  # Nonce para proof-of-work
    difficulty = Column(Integer, nullable=True, default=1)  # Dificultad del bloque
    
    # Integridad y verificación (según esquema real)
    is_verified = Column(Boolean, default=True, nullable=True)  # Estado de verificación
    blockchain_enabled = Column(Boolean, default=False, nullable=True)  # Si blockchain está activo
    
    # Relaciones
    payment = relationship("Payment", back_populates="audit_logs")
    
    # Índices para queries de auditoría y blockchain
    __table_args__ = (
        Index('idx_audit_action_timestamp', 'action', 'timestamp'),
        Index('idx_audit_payment_action', 'payment_id', 'action'),
        Index('idx_audit_performed_by', 'performed_by', 'timestamp'),
        Index('idx_audit_blockchain', 'block_number', 'current_hash'),
        Index('idx_audit_hash_chain', 'previous_hash', 'current_hash'),
        Index('idx_audit_correlation', 'correlation_id', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, block={self.block_number}, action={self.action}, hash={self.current_hash[:8] if self.current_hash else 'None'}...)>"

class SecurityAlert(Base):
    """Alertas de seguridad para monitoreo enterprise"""
    __tablename__ = 'security_alerts'
    
    id = Column(Integer, primary_key=True)
    payment_id = Column(Integer, ForeignKey('payments.id'), nullable=True, index=True)
    
    # Tipo y severidad de alerta
    alert_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, default='MEDIUM')  # LOW, MEDIUM, HIGH, CRITICAL
    
    # Descripción y detalles
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    
    # Datos técnicos
    expected_value = Column(String(255), nullable=True)
    actual_value = Column(String(255), nullable=True)
    source_ip = Column(String(45), nullable=True)
    
    # Estado de la alerta
    is_resolved = Column(Boolean, default=False, nullable=False)
    resolved_by = Column(String(100), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Metadatos
    created_at = Column(DateTime, nullable=False, default=func.now(), index=True)
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    # Relaciones
    payment = relationship("Payment", back_populates="security_alerts")
    
    # Índices para monitoreo
    __table_args__ = (
        Index('idx_alert_type_severity', 'alert_type', 'severity'),
        Index('idx_alert_unresolved', 'is_resolved', 'created_at'),
        Index('idx_alert_payment_type', 'payment_id', 'alert_type'),
    )
    
    def __repr__(self):
        return f"<SecurityAlert(id={self.id}, type={self.alert_type}, severity={self.severity})>"

class WebhookLog(Base):
    """Log específico para webhooks de MercadoPago"""
    __tablename__ = 'webhook_logs'
    
    id = Column(Integer, primary_key=True)
    
    # Identificadores
    mp_payment_id = Column(String(50), nullable=True, index=True)
    webhook_id = Column(String(100), nullable=True)  # ID del webhook de MP
    
    # Datos del webhook
    event_type = Column(String(50), nullable=False)
    raw_payload = Column(Text, nullable=False)
    headers = Column(Text, nullable=True)
    
    # Procesamiento
    is_processed = Column(Boolean, default=False, nullable=False)
    processing_attempts = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)
    
    # Validación de seguridad
    signature_valid = Column(Boolean, nullable=True)
    ip_whitelisted = Column(Boolean, nullable=True)
    source_ip = Column(String(45), nullable=True)
    
    # Timestamps
    received_at = Column(DateTime, nullable=False, default=func.now(), index=True)
    processed_at = Column(DateTime, nullable=True)
    
    # Índices para performance
    __table_args__ = (
        Index('idx_webhook_mp_payment', 'mp_payment_id', 'received_at'),
        Index('idx_webhook_processed', 'is_processed', 'received_at'),
        Index('idx_webhook_event_type', 'event_type', 'received_at'),
    )
    
    def __repr__(self):
        return f"<WebhookLog(id={self.id}, mp_payment_id={self.mp_payment_id}, event_type={self.event_type})>"

class WebhookEvent(Base):
    """Tabla para manejo resiliente de eventos de webhook"""
    __tablename__ = 'webhook_events'
    
    id = Column(Integer, primary_key=True)
    
    # Identificadores del evento
    mp_event_id = Column(String(100), nullable=True, index=True)  # ID del evento de MP
    topic = Column(String(50), nullable=False, index=True)  # payment, merchant_order, etc.
    resource = Column(String(200), nullable=True)  # URL del recurso
    
    # Datos del webhook
    raw_data = Column(Text, nullable=False)  # JSON completo del webhook
    headers = Column(Text, nullable=True)  # Headers HTTP
    source_ip = Column(String(45), nullable=True)
    
    # Estado del procesamiento
    status = Column(String(20), nullable=False, default='pending', index=True)  # pending, processed, error, failed
    attempts = Column(Integer, default=0, nullable=False)  # Contador de reintentos
    max_attempts = Column(Integer, default=3, nullable=False)  # Máximo de reintentos
    
    # Información de procesamiento
    last_attempt_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    
    # Datos relacionados (se llenan durante el procesamiento)
    payment_id = Column(Integer, ForeignKey('payments.id'), nullable=True, index=True)
    mp_payment_id = Column(String(50), nullable=True, index=True)
    
    # Validación de seguridad
    signature_valid = Column(Boolean, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=func.now(), index=True)
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    # Relaciones
    payment = relationship("Payment", foreign_keys=[payment_id])
    
    # Índices para performance y consultas
    __table_args__ = (
        Index('idx_webhook_event_status_created', 'status', 'created_at'),
        Index('idx_webhook_event_topic_status', 'topic', 'status'),
        Index('idx_webhook_event_attempts', 'attempts', 'status'),
        Index('idx_webhook_event_mp_payment', 'mp_payment_id', 'status'),
    )
    
    def can_retry(self) -> bool:
        """Verifica si el evento puede ser reintentado"""
        return self.attempts < self.max_attempts and self.status in ['pending', 'error']
    
    def is_expired(self, max_age_hours: int = 24) -> bool:
        """Verifica si el evento ha expirado (muy viejo para procesar)"""
        if not self.created_at:
            return False
        age = datetime.utcnow() - self.created_at
        return age.total_seconds() > (max_age_hours * 3600)
    
    def __repr__(self):
        return f"<WebhookEvent(id={self.id}, topic={self.topic}, status={self.status}, attempts={self.attempts})>"

class OAuthAccount(Base):
    """Cuentas OAuth de MercadoPago"""
    __tablename__ = 'oauth_accounts'
    
    id = Column(Integer, primary_key=True)
    
    # Identificador único de MercadoPago
    mp_user_id = Column(String(50), nullable=False, unique=True, index=True)
    
    # Tokens OAuth
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    public_key = Column(String(100), nullable=True)
    
    # Expiración y timestamps
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    # Estado de la cuenta
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Datos adicionales de MercadoPago
    mp_nickname = Column(String(100), nullable=True)
    mp_site_id = Column(String(10), nullable=True)  # MLA, MLB, etc.
    
    # Índices para performance
    __table_args__ = (
        Index('idx_oauth_user_active', 'mp_user_id', 'is_active'),
        Index('idx_oauth_expires', 'expires_at', 'is_active'),
    )
    
    def is_token_expired(self) -> bool:
        """Verifica si el token ha expirado"""
        return datetime.utcnow() >= self.expires_at
    
    def needs_refresh(self, buffer_minutes: int = 10) -> bool:
        """Verifica si el token necesita renovación (con buffer de tiempo)"""
        buffer_time = timedelta(minutes=buffer_minutes)
        return datetime.utcnow() >= (self.expires_at - buffer_time)
    
    def __repr__(self):
        return f"<OAuthAccount(id={self.id}, mp_user_id={self.mp_user_id}, active={self.is_active})>"

class MercadoPagoAccount(Base):
    """Cuentas OAuth de MercadoPago conectadas"""
    __tablename__ = 'mercadopago_accounts'
    
    id = Column(Integer, primary_key=True)
    
    # Identificadores del cliente
    client_id = Column(String(100), nullable=False, index=True)  # ID interno del cliente
    client_name = Column(String(255), nullable=True)
    client_email = Column(String(255), nullable=True)
    
    # Datos OAuth de MercadoPago
    mp_user_id = Column(String(50), nullable=False, unique=True, index=True)
    access_token = Column(Text, nullable=False)  # Token de acceso
    refresh_token = Column(Text, nullable=True)  # Token de renovación
    token_type = Column(String(20), nullable=False, default='Bearer')
    
    # Expiración y renovación
    expires_in = Column(Integer, nullable=False)  # Segundos hasta expiración
    expires_at = Column(DateTime, nullable=False, index=True)  # Timestamp de expiración
    last_refreshed = Column(DateTime, nullable=True)
    refresh_attempts = Column(Integer, default=0, nullable=False)
    
    # Scopes y permisos
    scope = Column(String(500), nullable=True)  # Permisos otorgados
    
    # Estado de la cuenta
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_sandbox = Column(Boolean, default=False, nullable=False)  # Sandbox vs Production
    
    # Datos adicionales de MercadoPago
    mp_public_key = Column(String(100), nullable=True)
    mp_site_id = Column(String(10), nullable=True)  # MLA, MLB, etc.
    mp_nickname = Column(String(100), nullable=True)
    
    # Auditoría
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    last_used_at = Column(DateTime, nullable=True, index=True)
    
    # Metadatos de conexión
    connection_ip = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Relaciones
    payments = relationship("Payment", back_populates="mp_account", foreign_keys="Payment.mp_account_id")
    
    # Índices para performance
    __table_args__ = (
        Index('idx_mp_account_client_active', 'client_id', 'is_active'),
        Index('idx_mp_account_expires', 'expires_at', 'is_active'),
        Index('idx_mp_account_user_active', 'mp_user_id', 'is_active'),
    )
    
    def is_token_expired(self) -> bool:
        """Verifica si el token ha expirado"""
        return datetime.utcnow() >= self.expires_at
    
    def needs_refresh(self, buffer_minutes: int = 10) -> bool:
        """Verifica si el token necesita renovación (con buffer de tiempo)"""
        buffer_time = timedelta(minutes=buffer_minutes)
        return datetime.utcnow() >= (self.expires_at - buffer_time)
    
    def __repr__(self):
        return f"<MercadoPagoAccount(id={self.id}, client_id={self.client_id}, mp_user_id={self.mp_user_id})>"

class ClientAccount(Base):
    """Tabla Multi-tenant para cuentas de clientes con integración MP + GHL"""
    __tablename__ = 'client_accounts'
    
    id = Column(Integer, primary_key=True)
    
    # Identificación del cliente
    client_id = Column(String(100), nullable=False, unique=True, index=True)  # ID único del cliente
    client_name = Column(String(255), nullable=False)
    client_email = Column(String(255), nullable=True)
    client_phone = Column(String(50), nullable=True)
    
    # Información de la empresa/agencia
    company_name = Column(String(255), nullable=True)
    industry = Column(String(100), nullable=True)
    website = Column(String(255), nullable=True)
    
    # Configuración GoHighLevel
    ghl_location_id = Column(String(100), nullable=True, index=True)  # Location ID de GHL
    ghl_access_token = Column(Text, nullable=True)  # Token de acceso GHL
    ghl_refresh_token = Column(Text, nullable=True)  # Token de renovación GHL
    ghl_token_type = Column(String(20), nullable=True, default='Bearer')
    ghl_expires_at = Column(DateTime, nullable=True, index=True)  # Expiración token GHL
    ghl_scope = Column(String(500), nullable=True)  # Scopes otorgados
    ghl_last_refreshed = Column(DateTime, nullable=True)
    
    # Configuración MercadoPago (referencia)
    mp_account_id = Column(Integer, ForeignKey('mercadopago_accounts.id'), nullable=True, index=True)
    
    # Estado y configuración
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_sandbox = Column(Boolean, default=False, nullable=False)  # Modo sandbox
    subscription_plan = Column(String(50), nullable=True, default='basic')  # Plan de suscripción
    
    # Configuración de integración
    auto_tag_payments = Column(Boolean, default=True, nullable=False)  # Auto-taggear pagos
    payment_tag_prefix = Column(String(50), nullable=True, default='MP_PAGADO')  # Prefijo para tags
    default_tag_paid = Column(String(100), nullable=True, default='Pago confirmado')  # Tag por defecto para pagos aprobados
    webhook_url = Column(String(500), nullable=True)  # URL webhook personalizada
    
    # Límites y cuotas
    monthly_payment_limit = Column(Integer, nullable=True)  # Límite mensual de pagos
    current_month_payments = Column(Integer, default=0, nullable=False)  # Pagos del mes actual
    
    # Auditoría y metadatos
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime, nullable=True)
    
    # Datos de conexión
    registration_ip = Column(String(45), nullable=True)
    last_ip = Column(String(45), nullable=True)
    
    # Relaciones
    mp_account = relationship("MercadoPagoAccount", foreign_keys=[mp_account_id])
    payments = relationship("Payment", back_populates="client_account", foreign_keys="Payment.client_account_id")
    
    # Índices para performance multi-tenant
    __table_args__ = (
        Index('idx_client_active', 'is_active', 'created_at'),
        Index('idx_client_ghl_location', 'ghl_location_id', 'is_active'),
        Index('idx_client_subscription', 'subscription_plan', 'is_active'),
        Index('idx_client_mp_account', 'mp_account_id', 'is_active'),
    )
    
    def is_ghl_token_expired(self) -> bool:
        """Verifica si el token de GHL ha expirado"""
        if not self.ghl_expires_at:
            return True
        return datetime.utcnow() >= self.ghl_expires_at
    
    def needs_ghl_refresh(self, buffer_minutes: int = 10) -> bool:
        """Verifica si el token de GHL necesita renovación"""
        if not self.ghl_expires_at:
            return True
        buffer_time = timedelta(minutes=buffer_minutes)
        return datetime.utcnow() >= (self.ghl_expires_at - buffer_time)
    
    def get_payment_count_this_month(self) -> int:
        """Obtiene el conteo de pagos del mes actual"""
        # Esto se actualizará en tiempo real desde la lógica de negocio
        return self.current_month_payments
    
    def is_within_payment_limit(self) -> bool:
        """Verifica si está dentro del límite mensual de pagos"""
        if not self.monthly_payment_limit:
            return True
        return self.current_month_payments < self.monthly_payment_limit
    
    def __repr__(self):
        return f"<ClientAccount(id={self.id}, client_id={self.client_id}, company={self.company_name})>"