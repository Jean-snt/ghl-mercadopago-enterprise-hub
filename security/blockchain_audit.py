"""
Blockchain Immutable Audit System - Banking Grade Security
Implements SHA-256 hash chain for tamper-proof audit logs
"""
import hashlib
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
import logging

from models import AuditLog, AuditAction

logger = logging.getLogger("blockchain_audit")

class AuditBlockchain:
    """
    Sistema de blockchain simplificado para auditoría inmutable
    Cada registro contiene el hash del registro anterior, creando una cadena verificable
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._genesis_hash = "0000000000000000000000000000000000000000000000000000000000000000"
    
    def calculate_block_hash(
        self,
        block_number: int,
        previous_hash: str,
        timestamp: datetime,
        action: str,
        performed_by: str,
        description: str,
        data_payload: str
    ) -> str:
        """
        Calcula el hash SHA-256 de un bloque de auditoría
        Incluye todos los campos críticos para garantizar integridad
        """
        # Crear string determinístico para hash
        block_data = {
            "block_number": block_number,
            "previous_hash": previous_hash,
            "timestamp": timestamp.isoformat(),
            "action": action,
            "performed_by": performed_by,
            "description": description,
            "data_payload": data_payload,
            "nonce": int(time.time() * 1000000)  # Microsegundos para unicidad
        }
        
        # Convertir a JSON ordenado para consistencia
        block_string = json.dumps(block_data, sort_keys=True, separators=(',', ':'))
        
        # Calcular SHA-256
        return hashlib.sha256(block_string.encode('utf-8')).hexdigest()
    
    def get_last_block(self) -> Optional[AuditLog]:
        """Obtiene el último bloque de la cadena"""
        return self.db.query(AuditLog).order_by(desc(AuditLog.block_number)).first()
    
    def get_next_block_number(self) -> int:
        """Obtiene el siguiente número de bloque"""
        last_block = self.get_last_block()
        return (last_block.block_number + 1) if last_block else 1
    
    def get_previous_hash(self) -> str:
        """Obtiene el hash del bloque anterior"""
        last_block = self.get_last_block()
        return last_block.current_hash if last_block else self._genesis_hash
    
    def verify_chain_integrity(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Verifica la integridad de la cadena de bloques
        Retorna reporte detallado de verificación
        """
        start_time = time.time()
        
        query = self.db.query(AuditLog).order_by(AuditLog.block_number)
        if limit:
            query = query.limit(limit)
        
        blocks = query.all()
        
        verification_result = {
            "is_valid": True,
            "total_blocks": len(blocks),
            "verified_blocks": 0,
            "invalid_blocks": [],
            "missing_blocks": [],
            "hash_mismatches": [],
            "verification_time": 0,
            "last_verified_block": None
        }
        
        expected_previous_hash = self._genesis_hash
        expected_block_number = 1
        
        for block in blocks:
            # Verificar número de bloque secuencial
            if block.block_number != expected_block_number:
                verification_result["missing_blocks"].append({
                    "expected": expected_block_number,
                    "found": block.block_number,
                    "block_id": block.id
                })
                verification_result["is_valid"] = False
            
            # Verificar hash del bloque anterior
            if block.previous_hash != expected_previous_hash:
                verification_result["hash_mismatches"].append({
                    "block_id": block.id,
                    "block_number": block.block_number,
                    "expected_previous_hash": expected_previous_hash,
                    "actual_previous_hash": block.previous_hash
                })
                verification_result["is_valid"] = False
            
            # Recalcular hash del bloque actual
            data_payload = self._create_data_payload(block)
            calculated_hash = self.calculate_block_hash(
                block.block_number,
                block.previous_hash,
                block.timestamp,
                block.action,
                block.performed_by,
                block.description,
                data_payload
            )
            
            # Verificar hash actual
            if block.current_hash != calculated_hash:
                verification_result["invalid_blocks"].append({
                    "block_id": block.id,
                    "block_number": block.block_number,
                    "stored_hash": block.current_hash,
                    "calculated_hash": calculated_hash,
                    "timestamp": block.timestamp.isoformat()
                })
                verification_result["is_valid"] = False
            else:
                verification_result["verified_blocks"] += 1
            
            # Preparar para siguiente iteración
            expected_previous_hash = block.current_hash
            expected_block_number = block.block_number + 1
            verification_result["last_verified_block"] = block.block_number
        
        verification_result["verification_time"] = time.time() - start_time
        
        # Log resultado de verificación
        if verification_result["is_valid"]:
            logger.info(f"Blockchain verification PASSED: {verification_result['verified_blocks']} blocks verified")
        else:
            logger.error(f"Blockchain verification FAILED: {len(verification_result['invalid_blocks'])} invalid blocks found")
        
        return verification_result
    
    def _create_data_payload(self, audit_log: AuditLog) -> str:
        """Crea payload de datos para hash (sin datos sensibles)"""
        payload = {
            "payment_id": audit_log.payment_id,
            "session_id": audit_log.session_id,
            "correlation_id": audit_log.correlation_id,
            "ip_address": audit_log.ip_address,
            "user_agent": audit_log.user_agent[:100] if audit_log.user_agent else None,  # Truncar para consistencia
            "error_message": audit_log.error_message[:200] if audit_log.error_message else None,
            "data_checksum": audit_log.data_checksum
        }
        
        return json.dumps(payload, sort_keys=True, separators=(',', ':'))

class BlockchainAuditLogger:
    """
    Logger de auditoría con blockchain inmutable
    Garantiza que los logs no puedan ser alterados sin detección
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.blockchain = AuditBlockchain(db)
    
    def log_action(
        self,
        action: AuditAction,
        description: str,
        performed_by: str,
        payment_id: Optional[int] = None,
        request_data: Optional[Dict] = None,
        response_data: Optional[Dict] = None,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        correlation_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> AuditLog:
        """
        Registra una acción en el blockchain de auditoría
        Aplica automáticamente filtrado de datos sensibles
        """
        try:
            from .data_masking import DataMasker
            
            # Filtrar datos sensibles
            masker = DataMasker()
            filtered_request = masker.mask_sensitive_data(request_data) if request_data else None
            filtered_response = masker.mask_sensitive_data(response_data) if response_data else None
            
            # Calcular checksum de datos
            data_for_checksum = {
                "request": filtered_request,
                "response": filtered_response,
                "error": error_message
            }
            data_checksum = hashlib.sha256(
                json.dumps(data_for_checksum, sort_keys=True, default=str).encode('utf-8')
            ).hexdigest()
            
            # Obtener información del blockchain
            block_number = self.blockchain.get_next_block_number()
            previous_hash = self.blockchain.get_previous_hash()
            timestamp = datetime.utcnow()
            
            # Crear payload para hash
            data_payload = json.dumps({
                "payment_id": payment_id,
                "session_id": session_id,
                "correlation_id": correlation_id,
                "ip_address": ip_address,
                "user_agent": user_agent[:100] if user_agent else None,
                "error_message": error_message[:200] if error_message else None,
                "data_checksum": data_checksum
            }, sort_keys=True, separators=(',', ':'))
            
            # Calcular hash del bloque actual
            current_hash = self.blockchain.calculate_block_hash(
                block_number=block_number,
                previous_hash=previous_hash,
                timestamp=timestamp,
                action=action.value,
                performed_by=performed_by,
                description=description,
                data_payload=data_payload
            )
            
            # Crear registro de auditoría
            audit_log = AuditLog(
                payment_id=payment_id,
                action=action.value,
                description=description,
                performed_by=performed_by,
                user_agent=user_agent,
                ip_address=ip_address,
                request_data=json.dumps(filtered_request) if filtered_request else None,
                response_data=json.dumps(filtered_response) if filtered_response else None,
                error_message=error_message,
                timestamp=timestamp,
                session_id=session_id,
                correlation_id=correlation_id,
                previous_hash=previous_hash,
                current_hash=current_hash,
                block_number=block_number,
                data_checksum=data_checksum,
                is_verified=True,
                verification_timestamp=timestamp
            )
            
            self.db.add(audit_log)
            self.db.commit()
            
            logger.info(
                f"Blockchain audit logged",
                extra={
                    'block_number': block_number,
                    'action': action.value,
                    'correlation_id': correlation_id,
                    'current_hash': current_hash[:8],
                    'previous_hash': previous_hash[:8]
                }
            )
            
            return audit_log
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to log blockchain audit: {str(e)}")
            raise
    
    def verify_log_integrity(self, audit_log_id: int) -> Dict[str, Any]:
        """Verifica la integridad de un log específico"""
        audit_log = self.db.query(AuditLog).filter(AuditLog.id == audit_log_id).first()
        
        if not audit_log:
            return {"is_valid": False, "error": "Audit log not found"}
        
        # Recalcular hash
        data_payload = self.blockchain._create_data_payload(audit_log)
        calculated_hash = self.blockchain.calculate_block_hash(
            audit_log.block_number,
            audit_log.previous_hash,
            audit_log.timestamp,
            audit_log.action,
            audit_log.performed_by,
            audit_log.description,
            data_payload
        )
        
        is_valid = audit_log.current_hash == calculated_hash
        
        return {
            "is_valid": is_valid,
            "audit_log_id": audit_log_id,
            "block_number": audit_log.block_number,
            "stored_hash": audit_log.current_hash,
            "calculated_hash": calculated_hash,
            "timestamp": audit_log.timestamp.isoformat()
        }
    
    def get_blockchain_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del blockchain de auditoría"""
        total_blocks = self.db.query(func.count(AuditLog.id)).scalar()
        
        if total_blocks == 0:
            return {
                "total_blocks": 0,
                "genesis_hash": self._genesis_hash,
                "last_block": None,
                "chain_length": 0
            }
        
        last_block = self.blockchain.get_last_block()
        first_block = self.db.query(AuditLog).order_by(AuditLog.block_number).first()
        
        return {
            "total_blocks": total_blocks,
            "genesis_hash": self.blockchain._genesis_hash,
            "first_block": {
                "number": first_block.block_number,
                "hash": first_block.current_hash,
                "timestamp": first_block.timestamp.isoformat()
            } if first_block else None,
            "last_block": {
                "number": last_block.block_number,
                "hash": last_block.current_hash,
                "timestamp": last_block.timestamp.isoformat()
            } if last_block else None,
            "chain_length": last_block.block_number if last_block else 0
        }