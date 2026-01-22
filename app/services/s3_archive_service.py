"""
S3ArchiveService - Servicio de Archivado de Logs en Amazon S3
Implementa backup automático de logs de alertas y auditoría para retención a largo plazo
"""
import os
import json
import gzip
import boto3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from botocore.exceptions import ClientError, NoCredentialsError
from dataclasses import dataclass
import tempfile
from pathlib import Path

from models import AuditLog, SecurityAlert, WebhookEvent

logger = logging.getLogger("s3_archive_service")

@dataclass
class ArchiveResult:
    """Resultado de operación de archivado"""
    success: bool
    files_uploaded: int
    total_records: int
    s3_keys: List[str]
    error_message: Optional[str] = None
    bytes_uploaded: int = 0

@dataclass
class S3Config:
    """Configuración de S3"""
    bucket_name: str
    region: str
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    prefix: str = "mercadopago-enterprise-logs"
    storage_class: str = "STANDARD_IA"  # Intelligent-Tiering para optimización de costos

class S3ArchiveService:
    """
    Servicio enterprise para archivado de logs en Amazon S3
    Implementa compresión, organización por fechas y lifecycle management
    """
    
    def __init__(self, db: Session, config: Optional[S3Config] = None):
        self.db = db
        self.config = config or self._load_config_from_env()
        self.s3_client = None
        self._initialize_s3_client()
        
        logger.info(f"S3ArchiveService initialized for bucket: {self.config.bucket_name}")
    
    def _load_config_from_env(self) -> S3Config:
        """Carga configuración desde variables de entorno"""
        return S3Config(
            bucket_name=os.getenv("S3_BUCKET_NAME", "mercadopago-enterprise-logs"),
            region=os.getenv("AWS_REGION", "us-east-1"),
            access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            prefix=os.getenv("S3_LOG_PREFIX", "mercadopago-enterprise-logs"),
            storage_class=os.getenv("S3_STORAGE_CLASS", "STANDARD_IA")
        )
    
    def _initialize_s3_client(self):
        """Inicializa cliente de S3 con credenciales"""
        try:
            session_kwargs = {
                "region_name": self.config.region
            }
            
            # Usar credenciales específicas si están configuradas
            if self.config.access_key_id and self.config.secret_access_key:
                session_kwargs.update({
                    "aws_access_key_id": self.config.access_key_id,
                    "aws_secret_access_key": self.config.secret_access_key
                })
            
            session = boto3.Session(**session_kwargs)
            self.s3_client = session.client('s3')
            
            # Verificar conectividad
            self._verify_s3_access()
            
        except NoCredentialsError:
            logger.error("AWS credentials not found. Configure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
            self.s3_client = None
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {str(e)}")
            self.s3_client = None
    
    def _verify_s3_access(self):
        """Verifica acceso al bucket de S3"""
        if not self.s3_client:
            return False
        
        try:
            # Intentar listar objetos del bucket
            self.s3_client.head_bucket(Bucket=self.config.bucket_name)
            logger.info(f"S3 bucket access verified: {self.config.bucket_name}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.warning(f"S3 bucket does not exist: {self.config.bucket_name}")
                # Intentar crear el bucket
                return self._create_bucket_if_not_exists()
            else:
                logger.error(f"S3 access error: {error_code} - {e}")
                return False
        except Exception as e:
            logger.error(f"S3 verification failed: {str(e)}")
            return False
    
    def _create_bucket_if_not_exists(self) -> bool:
        """Crea el bucket si no existe"""
        try:
            if self.config.region == 'us-east-1':
                # us-east-1 no requiere LocationConstraint
                self.s3_client.create_bucket(Bucket=self.config.bucket_name)
            else:
                self.s3_client.create_bucket(
                    Bucket=self.config.bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': self.config.region}
                )
            
            # Configurar lifecycle policy para optimización de costos
            self._setup_lifecycle_policy()
            
            logger.info(f"S3 bucket created successfully: {self.config.bucket_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create S3 bucket: {str(e)}")
            return False
    
    def _setup_lifecycle_policy(self):
        """Configura lifecycle policy para optimización de costos"""
        try:
            lifecycle_config = {
                'Rules': [
                    {
                        'ID': 'MercadoPagoLogsLifecycle',
                        'Status': 'Enabled',
                        'Filter': {'Prefix': f"{self.config.prefix}/"},
                        'Transitions': [
                            {
                                'Days': 30,
                                'StorageClass': 'STANDARD_IA'
                            },
                            {
                                'Days': 90,
                                'StorageClass': 'GLACIER'
                            },
                            {
                                'Days': 365,
                                'StorageClass': 'DEEP_ARCHIVE'
                            }
                        ]
                    }
                ]
            }
            
            self.s3_client.put_bucket_lifecycle_configuration(
                Bucket=self.config.bucket_name,
                LifecycleConfiguration=lifecycle_config
            )
            
            logger.info("S3 lifecycle policy configured for cost optimization")
            
        except Exception as e:
            logger.warning(f"Failed to setup lifecycle policy: {str(e)}")
    
    def archive_audit_logs(
        self, 
        start_date: datetime, 
        end_date: datetime,
        compress: bool = True
    ) -> ArchiveResult:
        """
        Archiva logs de auditoría en S3 para un rango de fechas
        """
        if not self.s3_client:
            return ArchiveResult(
                success=False,
                files_uploaded=0,
                total_records=0,
                s3_keys=[],
                error_message="S3 client not initialized"
            )
        
        try:
            # Obtener logs de auditoría
            audit_logs = self.db.query(AuditLog).filter(
                and_(
                    AuditLog.timestamp >= start_date,
                    AuditLog.timestamp <= end_date
                )
            ).order_by(AuditLog.timestamp).all()
            
            if not audit_logs:
                logger.info(f"No audit logs found for period {start_date} to {end_date}")
                return ArchiveResult(
                    success=True,
                    files_uploaded=0,
                    total_records=0,
                    s3_keys=[]
                )
            
            # Convertir a formato JSON
            logs_data = []
            for log in audit_logs:
                log_dict = {
                    "id": log.id,
                    "payment_id": log.payment_id,
                    "action": log.action,
                    "description": log.description,
                    "performed_by": log.performed_by,
                    "timestamp": log.timestamp.isoformat(),
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                    "request_data": log.request_data,
                    "response_data": log.response_data,
                    "error_message": log.error_message,
                    "correlation_id": log.correlation_id,
                    "block_number": log.block_number,
                    "current_hash": log.current_hash,
                    "previous_hash": log.previous_hash,
                    "is_verified": log.is_verified
                }
                logs_data.append(log_dict)
            
            # Generar nombre de archivo
            date_str = start_date.strftime("%Y-%m-%d")
            filename = f"audit_logs_{date_str}_{end_date.strftime('%Y-%m-%d')}.json"
            
            # Subir a S3
            s3_key = f"{self.config.prefix}/audit_logs/{start_date.year}/{start_date.month:02d}/{filename}"
            
            bytes_uploaded = self._upload_json_to_s3(logs_data, s3_key, compress)
            
            logger.info(f"Archived {len(logs_data)} audit logs to S3: {s3_key}")
            
            return ArchiveResult(
                success=True,
                files_uploaded=1,
                total_records=len(logs_data),
                s3_keys=[s3_key],
                bytes_uploaded=bytes_uploaded
            )
            
        except Exception as e:
            logger.error(f"Failed to archive audit logs: {str(e)}")
            return ArchiveResult(
                success=False,
                files_uploaded=0,
                total_records=0,
                s3_keys=[],
                error_message=str(e)
            )
    
    def archive_security_alerts(
        self, 
        start_date: datetime, 
        end_date: datetime,
        compress: bool = True
    ) -> ArchiveResult:
        """
        Archiva alertas de seguridad en S3 para un rango de fechas
        """
        if not self.s3_client:
            return ArchiveResult(
                success=False,
                files_uploaded=0,
                total_records=0,
                s3_keys=[],
                error_message="S3 client not initialized"
            )
        
        try:
            # Obtener alertas de seguridad
            security_alerts = self.db.query(SecurityAlert).filter(
                and_(
                    SecurityAlert.created_at >= start_date,
                    SecurityAlert.created_at <= end_date
                )
            ).order_by(SecurityAlert.created_at).all()
            
            if not security_alerts:
                logger.info(f"No security alerts found for period {start_date} to {end_date}")
                return ArchiveResult(
                    success=True,
                    files_uploaded=0,
                    total_records=0,
                    s3_keys=[]
                )
            
            # Convertir a formato JSON
            alerts_data = []
            for alert in security_alerts:
                alert_dict = {
                    "id": alert.id,
                    "payment_id": alert.payment_id,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "title": alert.title,
                    "description": alert.description,
                    "expected_value": alert.expected_value,
                    "actual_value": alert.actual_value,
                    "source_ip": alert.source_ip,
                    "is_resolved": alert.is_resolved,
                    "resolved_by": alert.resolved_by,
                    "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                    "resolution_notes": alert.resolution_notes,
                    "created_at": alert.created_at.isoformat(),
                    "updated_at": alert.updated_at.isoformat()
                }
                alerts_data.append(alert_dict)
            
            # Generar nombre de archivo
            date_str = start_date.strftime("%Y-%m-%d")
            filename = f"security_alerts_{date_str}_{end_date.strftime('%Y-%m-%d')}.json"
            
            # Subir a S3
            s3_key = f"{self.config.prefix}/security_alerts/{start_date.year}/{start_date.month:02d}/{filename}"
            
            bytes_uploaded = self._upload_json_to_s3(alerts_data, s3_key, compress)
            
            logger.info(f"Archived {len(alerts_data)} security alerts to S3: {s3_key}")
            
            return ArchiveResult(
                success=True,
                files_uploaded=1,
                total_records=len(alerts_data),
                s3_keys=[s3_key],
                bytes_uploaded=bytes_uploaded
            )
            
        except Exception as e:
            logger.error(f"Failed to archive security alerts: {str(e)}")
            return ArchiveResult(
                success=False,
                files_uploaded=0,
                total_records=0,
                s3_keys=[],
                error_message=str(e)
            )
    
    def archive_webhook_events(
        self, 
        start_date: datetime, 
        end_date: datetime,
        compress: bool = True
    ) -> ArchiveResult:
        """
        Archiva eventos de webhook en S3 para un rango de fechas
        """
        if not self.s3_client:
            return ArchiveResult(
                success=False,
                files_uploaded=0,
                total_records=0,
                s3_keys=[],
                error_message="S3 client not initialized"
            )
        
        try:
            # Obtener eventos de webhook
            webhook_events = self.db.query(WebhookEvent).filter(
                and_(
                    WebhookEvent.created_at >= start_date,
                    WebhookEvent.created_at <= end_date
                )
            ).order_by(WebhookEvent.created_at).all()
            
            if not webhook_events:
                logger.info(f"No webhook events found for period {start_date} to {end_date}")
                return ArchiveResult(
                    success=True,
                    files_uploaded=0,
                    total_records=0,
                    s3_keys=[]
                )
            
            # Convertir a formato JSON
            events_data = []
            for event in webhook_events:
                event_dict = {
                    "id": event.id,
                    "mp_event_id": event.mp_event_id,
                    "topic": event.topic,
                    "resource": event.resource,
                    "raw_data": event.raw_data,
                    "headers": event.headers,
                    "source_ip": event.source_ip,
                    "status": event.status,
                    "attempts": event.attempts,
                    "last_error": event.last_error,
                    "payment_id": event.payment_id,
                    "mp_payment_id": event.mp_payment_id,
                    "signature_valid": event.signature_valid,
                    "created_at": event.created_at.isoformat(),
                    "processed_at": event.processed_at.isoformat() if event.processed_at else None
                }
                events_data.append(event_dict)
            
            # Generar nombre de archivo
            date_str = start_date.strftime("%Y-%m-%d")
            filename = f"webhook_events_{date_str}_{end_date.strftime('%Y-%m-%d')}.json"
            
            # Subir a S3
            s3_key = f"{self.config.prefix}/webhook_events/{start_date.year}/{start_date.month:02d}/{filename}"
            
            bytes_uploaded = self._upload_json_to_s3(events_data, s3_key, compress)
            
            logger.info(f"Archived {len(events_data)} webhook events to S3: {s3_key}")
            
            return ArchiveResult(
                success=True,
                files_uploaded=1,
                total_records=len(events_data),
                s3_keys=[s3_key],
                bytes_uploaded=bytes_uploaded
            )
            
        except Exception as e:
            logger.error(f"Failed to archive webhook events: {str(e)}")
            return ArchiveResult(
                success=False,
                files_uploaded=0,
                total_records=0,
                s3_keys=[],
                error_message=str(e)
            )
    
    def _upload_json_to_s3(self, data: List[Dict], s3_key: str, compress: bool = True) -> int:
        """Sube datos JSON a S3 con compresión opcional"""
        json_content = json.dumps(data, indent=2, ensure_ascii=False)
        
        if compress:
            # Comprimir con gzip
            with tempfile.NamedTemporaryFile() as temp_file:
                with gzip.open(temp_file.name, 'wt', encoding='utf-8') as gz_file:
                    gz_file.write(json_content)
                
                temp_file.seek(0)
                content = temp_file.read()
                
                # Agregar extensión .gz al key
                s3_key += '.gz'
                content_type = 'application/gzip'
        else:
            content = json_content.encode('utf-8')
            content_type = 'application/json'
        
        # Subir a S3
        self.s3_client.put_object(
            Bucket=self.config.bucket_name,
            Key=s3_key,
            Body=content,
            ContentType=content_type,
            StorageClass=self.config.storage_class,
            Metadata={
                'source': 'mercadopago-enterprise',
                'record_count': str(len(data)),
                'compressed': str(compress).lower(),
                'upload_timestamp': datetime.utcnow().isoformat()
            }
        )
        
        return len(content)
    
    def archive_all_logs_for_date_range(
        self, 
        start_date: datetime, 
        end_date: datetime,
        compress: bool = True
    ) -> Dict[str, ArchiveResult]:
        """
        Archiva todos los tipos de logs para un rango de fechas
        """
        results = {}
        
        # Archivar logs de auditoría
        results['audit_logs'] = self.archive_audit_logs(start_date, end_date, compress)
        
        # Archivar alertas de seguridad
        results['security_alerts'] = self.archive_security_alerts(start_date, end_date, compress)
        
        # Archivar eventos de webhook
        results['webhook_events'] = self.archive_webhook_events(start_date, end_date, compress)
        
        return results
    
    def get_archive_summary(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Obtiene resumen de archivos disponibles para archivar
        """
        summary = {}
        
        try:
            # Contar logs de auditoría
            audit_count = self.db.query(AuditLog).filter(
                and_(
                    AuditLog.timestamp >= start_date,
                    AuditLog.timestamp <= end_date
                )
            ).count()
            
            # Contar alertas de seguridad
            alerts_count = self.db.query(SecurityAlert).filter(
                and_(
                    SecurityAlert.created_at >= start_date,
                    SecurityAlert.created_at <= end_date
                )
            ).count()
            
            # Contar eventos de webhook
            webhooks_count = self.db.query(WebhookEvent).filter(
                and_(
                    WebhookEvent.created_at >= start_date,
                    WebhookEvent.created_at <= end_date
                )
            ).count()
            
            summary = {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": (end_date - start_date).days
                },
                "records_to_archive": {
                    "audit_logs": audit_count,
                    "security_alerts": alerts_count,
                    "webhook_events": webhooks_count,
                    "total": audit_count + alerts_count + webhooks_count
                },
                "s3_config": {
                    "bucket": self.config.bucket_name,
                    "prefix": self.config.prefix,
                    "region": self.config.region,
                    "storage_class": self.config.storage_class
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get archive summary: {str(e)}")
            summary["error"] = str(e)
        
        return summary
    
    def list_archived_files(self, prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lista archivos archivados en S3
        """
        if not self.s3_client:
            return []
        
        try:
            search_prefix = f"{self.config.prefix}/"
            if prefix:
                search_prefix += prefix
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.config.bucket_name,
                Prefix=search_prefix
            )
            
            files = []
            for obj in response.get('Contents', []):
                files.append({
                    "key": obj['Key'],
                    "size": obj['Size'],
                    "last_modified": obj['LastModified'].isoformat(),
                    "storage_class": obj.get('StorageClass', 'STANDARD')
                })
            
            return files
            
        except Exception as e:
            logger.error(f"Failed to list archived files: {str(e)}")
            return []