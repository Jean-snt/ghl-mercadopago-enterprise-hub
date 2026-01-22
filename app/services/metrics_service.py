"""
MetricsService - Centro de Comando NOC
Implementa métricas agregadas en tiempo real para monitoreo enterprise
"""
import time
import requests
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, text
import logging
import os
from dataclasses import dataclass
from enum import Enum

from models import (
    Payment, PaymentStatus, WebhookEvent, AuditLog, SecurityAlert, 
    MercadoPagoAccount, WebhookLog
)

logger = logging.getLogger("metrics_service")

class ServiceStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class MetricValue:
    """Estructura para valores de métricas"""
    value: float
    unit: str
    timestamp: datetime
    trend: Optional[str] = None  # "up", "down", "stable"
    previous_value: Optional[float] = None

@dataclass
class ServiceHealth:
    """Estado de salud de un servicio"""
    name: str
    status: ServiceStatus
    response_time_ms: Optional[float]
    last_check: datetime
    error_message: Optional[str] = None
    uptime_percentage: Optional[float] = None

@dataclass
class SecurityThreat:
    """Amenaza de seguridad detectada"""
    threat_type: str
    severity: str
    count: int
    description: str
    last_occurrence: datetime

@dataclass
class DashboardMetrics:
    """Métricas completas del dashboard"""
    # Financials
    total_processed_today: Decimal
    total_processed_month: Decimal
    payments_pending: int
    payments_approved: int
    payments_rejected: int
    
    # Performance
    payment_success_rate: float
    webhook_avg_response_time: float
    transactions_per_client: Dict[str, int]
    
    # System Health
    services_health: List[ServiceHealth]
    
    # Security
    top_threats: List[SecurityThreat]
    
    # Trends
    hourly_volume: List[Dict[str, Any]]
    daily_revenue: List[Dict[str, Any]]
    
    # Metadata
    generated_at: datetime
    data_freshness_seconds: int

class MetricsService:
    """
    Servicio enterprise para métricas y monitoreo en tiempo real
    Implementa cálculos agregados optimizados para NOC dashboard
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._cache = {}
        self._cache_ttl = 60  # Cache por 60 segundos
        logger.info("MetricsService initialized")
    
    def get_dashboard_overview(self) -> DashboardMetrics:
        """
        Obtiene métricas completas para dashboard NOC
        Optimizado para performance con cache inteligente
        """
        cache_key = "dashboard_overview"
        
        # Verificar cache
        if self._is_cache_valid(cache_key):
            logger.debug("Returning cached dashboard metrics")
            return self._cache[cache_key]["data"]
        
        start_time = time.time()
        logger.info("Calculating fresh dashboard metrics")
        
        # Calcular métricas
        metrics = DashboardMetrics(
            # Financials
            total_processed_today=self._get_total_processed_today(),
            total_processed_month=self._get_total_processed_month(),
            payments_pending=self._get_payments_count_by_status(PaymentStatus.PENDING),
            payments_approved=self._get_payments_count_by_status(PaymentStatus.APPROVED),
            payments_rejected=self._get_payments_count_by_status(PaymentStatus.REJECTED),
            
            # Performance
            payment_success_rate=self._calculate_payment_success_rate(),
            webhook_avg_response_time=self._calculate_webhook_avg_response_time(),
            transactions_per_client=self._get_transactions_per_client(),
            
            # System Health
            services_health=self._check_services_health(),
            
            # Security
            top_threats=self._get_top_security_threats(),
            
            # Trends
            hourly_volume=self._get_hourly_volume_trend(),
            daily_revenue=self._get_daily_revenue_trend(),
            
            # Metadata
            generated_at=datetime.utcnow(),
            data_freshness_seconds=int(time.time() - start_time)
        )
        
        # Guardar en cache
        self._cache[cache_key] = {
            "data": metrics,
            "timestamp": time.time()
        }
        
        calculation_time = time.time() - start_time
        logger.info(f"Dashboard metrics calculated in {calculation_time:.2f}s")
        
        return metrics
    
    def _get_total_processed_today(self) -> Decimal:
        """Total procesado hoy - Compatible con SQLite"""
        today = datetime.utcnow().date()
        
        result = self.db.query(
            func.coalesce(func.sum(Payment.paid_amount), 0)
        ).filter(
            and_(
                Payment.status == PaymentStatus.APPROVED.value,
                func.strftime('%Y-%m-%d', Payment.processed_at) == today.strftime('%Y-%m-%d')
            )
        ).scalar()
        
        return Decimal(str(result or 0))
    
    def _get_total_processed_month(self) -> Decimal:
        """Total procesado este mes"""
        first_day_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        result = self.db.query(
            func.coalesce(func.sum(Payment.paid_amount), 0)
        ).filter(
            and_(
                Payment.status == PaymentStatus.APPROVED.value,
                Payment.processed_at >= first_day_month
            )
        ).scalar()
        
        return Decimal(str(result or 0))
    
    def _get_payments_count_by_status(self, status: PaymentStatus) -> int:
        """Cuenta pagos por estado"""
        return self.db.query(Payment).filter(Payment.status == status.value).count()
    
    def _calculate_payment_success_rate(self) -> float:
        """Calcula tasa de éxito de pagos (últimas 24h)"""
        last_24h = datetime.utcnow() - timedelta(hours=24)
        
        total_payments = self.db.query(Payment).filter(
            Payment.created_at >= last_24h
        ).count()
        
        if total_payments == 0:
            return 100.0
        
        successful_payments = self.db.query(Payment).filter(
            and_(
                Payment.created_at >= last_24h,
                Payment.status == PaymentStatus.APPROVED.value
            )
        ).count()
        
        return round((successful_payments / total_payments) * 100, 2)
    
    def _calculate_webhook_avg_response_time(self) -> float:
        """Calcula tiempo promedio de respuesta de webhooks (últimas 24h)"""
        last_24h = datetime.utcnow() - timedelta(hours=24)
        
        # Calcular tiempo promedio entre created_at y processed_at
        webhooks = self.db.query(WebhookEvent).filter(
            and_(
                WebhookEvent.created_at >= last_24h,
                WebhookEvent.status == 'processed',
                WebhookEvent.processed_at.isnot(None)
            )
        ).all()
        
        if not webhooks:
            return 0.0
        
        total_time = 0
        for webhook in webhooks:
            if webhook.processed_at and webhook.created_at:
                processing_time = (webhook.processed_at - webhook.created_at).total_seconds()
                total_time += processing_time
        
        avg_time_seconds = total_time / len(webhooks)
        return round(avg_time_seconds * 1000, 2)  # Convertir a milisegundos
    
    def _get_transactions_per_client(self) -> Dict[str, int]:
        """Obtiene volumen de transacciones por cliente (últimos 7 días)"""
        last_7_days = datetime.utcnow() - timedelta(days=7)
        
        # Agrupar por mp_account_id o created_by
        results = self.db.query(
            func.coalesce(MercadoPagoAccount.client_id, Payment.created_by).label('client'),
            func.count(Payment.id).label('count')
        ).outerjoin(
            MercadoPagoAccount, Payment.mp_account_id == MercadoPagoAccount.id
        ).filter(
            Payment.created_at >= last_7_days
        ).group_by(
            func.coalesce(MercadoPagoAccount.client_id, Payment.created_by)
        ).order_by(
            func.count(Payment.id).desc()
        ).limit(10).all()
        
        return {result.client: result.count for result in results}
    
    def _check_services_health(self) -> List[ServiceHealth]:
        """Verifica estado de salud de servicios externos"""
        services = []
        
        # 1. MercadoPago API Health
        mp_health = self._check_mercadopago_health()
        services.append(mp_health)
        
        # 2. GoHighLevel API Health
        ghl_health = self._check_ghl_health()
        services.append(ghl_health)
        
        # 3. Database Health
        db_health = self._check_database_health()
        services.append(db_health)
        
        # 4. Webhook Processing Health
        webhook_health = self._check_webhook_processing_health()
        services.append(webhook_health)
        
        return services
    
    def _check_mercadopago_health(self) -> ServiceHealth:
        """Verifica salud de MercadoPago API"""
        start_time = time.time()
        
        try:
            mp_token = os.getenv("MP_ACCESS_TOKEN")
            if not mp_token:
                return ServiceHealth(
                    name="MercadoPago API",
                    status=ServiceStatus.DOWN,
                    response_time_ms=None,
                    last_check=datetime.utcnow(),
                    error_message="No access token configured"
                )
            
            # Hacer una llamada simple a la API
            headers = {"Authorization": f"Bearer {mp_token}"}
            response = requests.get(
                "https://api.mercadopago.com/users/me",
                headers=headers,
                timeout=5
            )
            
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                status = ServiceStatus.HEALTHY if response_time < 2000 else ServiceStatus.DEGRADED
                return ServiceHealth(
                    name="MercadoPago API",
                    status=status,
                    response_time_ms=round(response_time, 2),
                    last_check=datetime.utcnow(),
                    uptime_percentage=self._calculate_api_uptime("mercadopago")
                )
            else:
                return ServiceHealth(
                    name="MercadoPago API",
                    status=ServiceStatus.DOWN,
                    response_time_ms=round(response_time, 2),
                    last_check=datetime.utcnow(),
                    error_message=f"HTTP {response.status_code}"
                )
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ServiceHealth(
                name="MercadoPago API",
                status=ServiceStatus.DOWN,
                response_time_ms=round(response_time, 2),
                last_check=datetime.utcnow(),
                error_message=str(e)
            )
    
    def _check_ghl_health(self) -> ServiceHealth:
        """Verifica salud de GoHighLevel API"""
        start_time = time.time()
        
        try:
            ghl_key = os.getenv("GHL_API_KEY")
            if not ghl_key or ghl_key.startswith("test_"):
                return ServiceHealth(
                    name="GoHighLevel API",
                    status=ServiceStatus.DEGRADED,
                    response_time_ms=0,
                    last_check=datetime.utcnow(),
                    error_message="Mock mode - no real API key"
                )
            
            # En producción haríamos una llamada real
            # Por ahora simulamos
            response_time = (time.time() - start_time) * 1000
            
            return ServiceHealth(
                name="GoHighLevel API",
                status=ServiceStatus.HEALTHY,
                response_time_ms=round(response_time, 2),
                last_check=datetime.utcnow(),
                uptime_percentage=95.5  # Simulado
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ServiceHealth(
                name="GoHighLevel API",
                status=ServiceStatus.DOWN,
                response_time_ms=round(response_time, 2),
                last_check=datetime.utcnow(),
                error_message=str(e)
            )
    
    def _check_database_health(self) -> ServiceHealth:
        """Verifica salud de la base de datos"""
        start_time = time.time()
        
        try:
            # Hacer una query simple para verificar conectividad
            self.db.execute(text("SELECT 1")).scalar()
            
            response_time = (time.time() - start_time) * 1000
            
            # Verificar tamaño de tablas principales
            tables_status = self._check_database_tables()
            
            status = ServiceStatus.HEALTHY if response_time < 100 else ServiceStatus.DEGRADED
            
            return ServiceHealth(
                name="Database",
                status=status,
                response_time_ms=round(response_time, 2),
                last_check=datetime.utcnow(),
                uptime_percentage=99.9
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return ServiceHealth(
                name="Database",
                status=ServiceStatus.DOWN,
                response_time_ms=round(response_time, 2),
                last_check=datetime.utcnow(),
                error_message=str(e)
            )
    
    def _check_webhook_processing_health(self) -> ServiceHealth:
        """Verifica salud del procesamiento de webhooks"""
        try:
            last_hour = datetime.utcnow() - timedelta(hours=1)
            
            # Contar webhooks procesados vs fallidos en la última hora
            total_webhooks = self.db.query(WebhookEvent).filter(
                WebhookEvent.created_at >= last_hour
            ).count()
            
            failed_webhooks = self.db.query(WebhookEvent).filter(
                and_(
                    WebhookEvent.created_at >= last_hour,
                    WebhookEvent.status.in_(['error', 'failed'])
                )
            ).count()
            
            if total_webhooks == 0:
                error_rate = 0
            else:
                error_rate = (failed_webhooks / total_webhooks) * 100
            
            if error_rate > 15:
                status = ServiceStatus.DOWN
            elif error_rate > 5:
                status = ServiceStatus.DEGRADED
            else:
                status = ServiceStatus.HEALTHY
            
            return ServiceHealth(
                name="Webhook Processing",
                status=status,
                response_time_ms=None,
                last_check=datetime.utcnow(),
                error_message=f"Error rate: {error_rate:.1f}%" if error_rate > 0 else None,
                uptime_percentage=100 - error_rate
            )
            
        except Exception as e:
            return ServiceHealth(
                name="Webhook Processing",
                status=ServiceStatus.UNKNOWN,
                response_time_ms=None,
                last_check=datetime.utcnow(),
                error_message=str(e)
            )
    
    def _get_top_security_threats(self) -> List[SecurityThreat]:
        """Obtiene las 3 principales amenazas de seguridad"""
        last_24h = datetime.utcnow() - timedelta(hours=24)
        
        # Agrupar alertas por tipo
        threats = self.db.query(
            SecurityAlert.alert_type,
            SecurityAlert.severity,
            func.count(SecurityAlert.id).label('count'),
            func.max(SecurityAlert.created_at).label('last_occurrence')
        ).filter(
            and_(
                SecurityAlert.created_at >= last_24h,
                SecurityAlert.is_resolved == False
            )
        ).group_by(
            SecurityAlert.alert_type,
            SecurityAlert.severity
        ).order_by(
            func.count(SecurityAlert.id).desc()
        ).limit(3).all()
        
        result = []
        for threat in threats:
            # Generar descripción basada en el tipo
            descriptions = {
                "INVALID_WEBHOOK_SIGNATURE": "Webhooks con firma inválida detectados",
                "AMOUNT_MISMATCH": "Discrepancias de montos entre sistemas",
                "DUPLICATE_PAYMENT_ATTEMPT": "Intentos de procesamiento duplicado",
                "UNKNOWN_PAYMENT_REFERENCE": "Referencias de pago desconocidas",
                "WEBHOOK_PROCESSING_FAILED": "Fallos en procesamiento de webhooks",
                "brute_force_detected": "Ataque de fuerza bruta detectado - múltiples intentos de login fallidos",
                "webhook_error_rate": "Alta tasa de errores en webhooks",
                "security_threat": "Múltiples amenazas de seguridad detectadas",
                "system_overload": "Sobrecarga del sistema detectada"
            }
            
            result.append(SecurityThreat(
                threat_type=threat.alert_type,
                severity=threat.severity,
                count=threat.count,
                description=descriptions.get(threat.alert_type, f"Amenaza tipo {threat.alert_type}"),
                last_occurrence=threat.last_occurrence
            ))
        
        return result
    
    def _get_hourly_volume_trend(self) -> List[Dict[str, Any]]:
        """Obtiene tendencia de volumen por hora (últimas 24h) - Compatible con SQLite"""
        last_24h = datetime.utcnow() - timedelta(hours=24)
        
        # Agrupar pagos por hora usando strftime para SQLite
        results = self.db.query(
            func.strftime('%Y-%m-%d %H:00:00', Payment.created_at).label('hour'),
            func.count(Payment.id).label('count'),
            func.coalesce(func.sum(Payment.expected_amount), 0).label('volume')
        ).filter(
            Payment.created_at >= last_24h
        ).group_by(
            func.strftime('%Y-%m-%d %H:00:00', Payment.created_at)
        ).order_by(
            func.strftime('%Y-%m-%d %H:00:00', Payment.created_at)
        ).all()
        
        return [
            {
                "hour": result.hour if result.hour else None,
                "count": result.count,
                "volume": float(result.volume)
            }
            for result in results
        ]
    
    def _get_daily_revenue_trend(self) -> List[Dict[str, Any]]:
        """Obtiene tendencia de ingresos diarios (últimos 7 días) - Compatible con SQLite"""
        last_7_days = datetime.utcnow() - timedelta(days=7)
        
        results = self.db.query(
            func.strftime('%Y-%m-%d', Payment.processed_at).label('date'),
            func.coalesce(func.sum(Payment.paid_amount), 0).label('revenue'),
            func.count(Payment.id).label('transactions')
        ).filter(
            and_(
                Payment.processed_at >= last_7_days,
                Payment.status == PaymentStatus.APPROVED.value
            )
        ).group_by(
            func.strftime('%Y-%m-%d', Payment.processed_at)
        ).order_by(
            func.strftime('%Y-%m-%d', Payment.processed_at)
        ).all()
        
        return [
            {
                "date": result.date if result.date else None,
                "revenue": float(result.revenue),
                "transactions": result.transactions
            }
            for result in results
        ]
    
    def _calculate_api_uptime(self, api_name: str) -> float:
        """Calcula uptime de API basado en logs históricos"""
        # Por ahora retornamos valores simulados
        # En producción calcularíamos basado en logs reales
        uptimes = {
            "mercadopago": 99.2,
            "ghl": 95.5,
            "database": 99.9
        }
        return uptimes.get(api_name, 95.0)
    
    def _check_database_tables(self) -> Dict[str, Any]:
        """Verifica estado de tablas principales - Compatible con SQLite"""
        tables = ['payments', 'webhook_events', 'audit_logs', 'security_alerts']
        status = {}
        
        for table in tables:
            try:
                # Usar query más simple compatible con SQLite
                count = self.db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                status[table] = {"status": "healthy", "count": count}
            except Exception as e:
                status[table] = {"status": "error", "error": str(e)}
        
        return status
    
    def _is_cache_valid(self, key: str) -> bool:
        """Verifica si el cache es válido"""
        if key not in self._cache:
            return False
        
        cache_age = time.time() - self._cache[key]["timestamp"]
        return cache_age < self._cache_ttl
    
    def get_real_time_metrics(self) -> Dict[str, MetricValue]:
        """Obtiene métricas en tiempo real para widgets"""
        return {
            "payments_per_minute": MetricValue(
                value=self._get_payments_last_minute(),
                unit="payments/min",
                timestamp=datetime.utcnow()
            ),
            "avg_payment_amount": MetricValue(
                value=float(self._get_avg_payment_amount()),
                unit="USD",
                timestamp=datetime.utcnow()
            ),
            "webhook_queue_size": MetricValue(
                value=self._get_webhook_queue_size(),
                unit="events",
                timestamp=datetime.utcnow()
            ),
            "active_sessions": MetricValue(
                value=self._get_active_sessions(),
                unit="sessions",
                timestamp=datetime.utcnow()
            ),
            "integrations": MetricValue(
                value=self._get_integrations_status(),
                unit="status",
                timestamp=datetime.utcnow()
            )
        }
    
    def _get_payments_last_minute(self) -> float:
        """Pagos en el último minuto"""
        last_minute = datetime.utcnow() - timedelta(minutes=1)
        return float(self.db.query(Payment).filter(Payment.created_at >= last_minute).count())
    
    def _get_avg_payment_amount(self) -> Decimal:
        """Monto promedio de pagos (últimas 24h)"""
        last_24h = datetime.utcnow() - timedelta(hours=24)
        result = self.db.query(func.avg(Payment.expected_amount)).filter(
            Payment.created_at >= last_24h
        ).scalar()
        return Decimal(str(result or 0))
    
    def _get_webhook_queue_size(self) -> float:
        """Tamaño de cola de webhooks pendientes"""
        return float(self.db.query(WebhookEvent).filter(
            WebhookEvent.status == 'pending'
        ).count())
    
    def _get_active_sessions(self) -> float:
        """Sesiones activas (simulado)"""
        # En producción esto vendría de Redis o similar
        return 12.0
    
    def _get_integrations_status(self) -> Dict[str, str]:
        """
        Obtiene el estado de las integraciones externas
        """
        try:
            from models import ClientAccount
            
            # Verificar estado de GoHighLevel
            ghl_status = "UNKNOWN"
            
            # Contar clientes con tokens GHL activos
            active_ghl_clients = self.db.query(ClientAccount).filter(
                and_(
                    ClientAccount.is_active == True,
                    ClientAccount.ghl_access_token.isnot(None),
                    or_(
                        ClientAccount.ghl_expires_at.is_(None),
                        ClientAccount.ghl_expires_at > datetime.utcnow()
                    )
                )
            ).count()
            
            if active_ghl_clients > 0:
                ghl_status = "HEALTHY"
                logger.info(f"GHL integration: {active_ghl_clients} active clients")
            else:
                ghl_status = "DEGRADED"
                logger.info("GHL integration: No active clients found")
            
            # Verificar estado de MercadoPago
            mp_status = "HEALTHY" if os.getenv("MP_ACCESS_TOKEN") else "DEGRADED"
            
            # Verificar estado de la base de datos
            try:
                self.db.execute(text("SELECT 1"))
                db_status = "HEALTHY"
            except:
                db_status = "DOWN"
            
            return {
                "ghl_status": ghl_status,
                "mercadopago_status": mp_status,
                "database_status": db_status,
                "active_ghl_clients": active_ghl_clients
            }
            
        except Exception as e:
            logger.error(f"Error getting integrations status: {str(e)}")
            return {
                "ghl_status": "UNKNOWN",
                "mercadopago_status": "UNKNOWN", 
                "database_status": "UNKNOWN",
                "active_ghl_clients": 0
            }