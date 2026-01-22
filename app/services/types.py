"""
Tipos de datos para el sistema de reconciliación
Implementa TypedDict para type hinting estricto
"""
from typing import TypedDict, Optional, List, Dict, Any, Literal
from datetime import datetime
from decimal import Decimal

# Tipos de estado para reconciliación
ReconciliationStatus = Literal["success", "warning", "error", "critical"]
DiscrepancyType = Literal["missing_tag", "amount_mismatch", "status_mismatch", "missing_payment", "orphan_payment"]
ReportFormat = Literal["json", "csv"]

class PaymentDiscrepancy(TypedDict):
    """Estructura para discrepancias encontradas en pagos"""
    payment_id: int
    mp_payment_id: str
    ghl_contact_id: str
    discrepancy_type: DiscrepancyType
    description: str
    expected_value: Optional[str]
    actual_value: Optional[str]
    severity: Literal["low", "medium", "high", "critical"]
    auto_correctable: bool
    correction_attempted: bool
    correction_successful: Optional[bool]
    timestamp: datetime

class MPPaymentData(TypedDict):
    """Datos de pago desde MercadoPago API"""
    id: str
    status: str
    status_detail: str
    transaction_amount: Decimal
    currency_id: str
    date_created: str
    date_approved: Optional[str]
    external_reference: Optional[str]
    payment_method_id: Optional[str]
    payer_email: Optional[str]

class GHLContactData(TypedDict):
    """Datos de contacto desde GoHighLevel API"""
    id: str
    email: Optional[str]
    tags: List[str]
    custom_fields: Dict[str, Any]
    date_added: str
    last_activity: Optional[str]

class ReconciliationResult(TypedDict):
    """Resultado de un proceso de reconciliación"""
    execution_id: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    status: ReconciliationStatus
    summary: Dict[str, int]
    discrepancies: List[PaymentDiscrepancy]
    corrections_applied: int
    total_payments_checked: int
    mp_api_calls: int
    ghl_api_calls: int
    errors: List[str]
    warnings: List[str]

class ReconciliationReport(TypedDict):
    """Estructura del reporte de reconciliación"""
    report_id: str
    execution_id: str
    generated_at: datetime
    format: ReportFormat
    file_path: str
    summary: Dict[str, Any]
    discrepancies_count: int
    corrections_count: int
    status: ReconciliationStatus

class ReconciliationConfig(TypedDict):
    """Configuración para el proceso de reconciliación"""
    hours_back: int
    max_retries: int
    retry_delay_seconds: int
    batch_size: int
    enable_auto_correction: bool
    dry_run: bool
    include_pending_payments: bool
    ghl_tag_prefix: str
    report_formats: List[ReportFormat]
    notification_webhooks: List[str]

class APICallResult(TypedDict):
    """Resultado de llamada a API externa"""
    success: bool
    status_code: Optional[int]
    data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    retry_count: int
    duration_ms: float

class BackoffConfig(TypedDict):
    """Configuración para backoff exponencial"""
    initial_delay: float
    max_delay: float
    multiplier: float
    max_retries: int
    jitter: bool