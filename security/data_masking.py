"""
Data Masking and Sensitive Data Filtering - Banking Grade Privacy
Implements automatic filtering of sensitive data from logs and responses
"""
import re
import json
from typing import Any, Dict, List, Optional, Union
from functools import wraps
import logging

logger = logging.getLogger("data_masking")

class DataMasker:
    """
    Clase para enmascaramiento automático de datos sensibles
    Cumple con estándares bancarios de privacidad y PCI DSS
    """
    
    # Patrones de datos sensibles (case-insensitive)
    SENSITIVE_PATTERNS = {
        # Credenciales y tokens
        'password': r'password',
        'passwd': r'passwd',
        'pwd': r'pwd',
        'secret': r'secret',
        'token': r'token',
        'key': r'key',
        'api_key': r'api[_-]?key',
        'access_token': r'access[_-]?token',
        'refresh_token': r'refresh[_-]?token',
        'bearer': r'bearer',
        'authorization': r'authorization',
        'auth': r'auth',
        
        # Datos financieros
        'cvv': r'cvv',
        'cvc': r'cvc',
        'card_number': r'card[_-]?number',
        'credit_card': r'credit[_-]?card',
        'debit_card': r'debit[_-]?card',
        'account_number': r'account[_-]?number',
        'routing_number': r'routing[_-]?number',
        'iban': r'iban',
        'swift': r'swift',
        
        # Datos personales
        'ssn': r'ssn',
        'social_security': r'social[_-]?security',
        'tax_id': r'tax[_-]?id',
        'passport': r'passport',
        'license': r'license',
        'dni': r'dni',
        'cuit': r'cuit',
        'cuil': r'cuil',
        
        # Datos de MercadoPago específicos
        'client_secret': r'client[_-]?secret',
        'webhook_secret': r'webhook[_-]?secret',
        'mp_access_token': r'mp[_-]?access[_-]?token',
        'mp_public_key': r'mp[_-]?public[_-]?key',
        'mp_private_key': r'mp[_-]?private[_-]?key',
        
        # Headers sensibles
        'x_signature': r'x[_-]?signature',
        'signature': r'signature',
        'hmac': r'hmac',
        
        # Otros
        'pin': r'pin',
        'otp': r'otp',
        'code': r'code',
        'verification_code': r'verification[_-]?code'
    }
    
    # Patrones de valores que parecen sensibles (por formato)
    VALUE_PATTERNS = {
        'credit_card': re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'),
        'token_like': re.compile(r'\b[A-Za-z0-9]{32,}\b'),  # Strings largos alfanuméricos
        'uuid': re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', re.IGNORECASE),
        'base64': re.compile(r'\b[A-Za-z0-9+/]{20,}={0,2}\b'),  # Base64 strings
        'jwt': re.compile(r'\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b'),  # JWT tokens
    }
    
    def __init__(self, mask_char: str = "*", partial_reveal: int = 4):
        self.mask_char = mask_char
        self.partial_reveal = partial_reveal
        
        # Compilar patrones de campos sensibles
        self.compiled_patterns = {}
        for name, pattern in self.SENSITIVE_PATTERNS.items():
            self.compiled_patterns[name] = re.compile(pattern, re.IGNORECASE)
    
    def is_sensitive_field(self, field_name: str) -> bool:
        """Verifica si un campo es sensible basado en su nombre"""
        field_lower = field_name.lower()
        
        for pattern_name, compiled_pattern in self.compiled_patterns.items():
            if compiled_pattern.search(field_lower):
                return True
        
        return False
    
    def is_sensitive_value(self, value: str) -> bool:
        """Verifica si un valor parece sensible basado en su formato"""
        if not isinstance(value, str) or len(value) < 8:
            return False
        
        for pattern_name, pattern in self.VALUE_PATTERNS.items():
            if pattern.search(value):
                return True
        
        return False
    
    def mask_value(self, value: Any, field_name: str = "") -> Any:
        """Enmascara un valor si es sensible"""
        if value is None:
            return None
        
        # Convertir a string para análisis
        str_value = str(value)
        
        # Verificar si el campo o valor es sensible
        is_field_sensitive = self.is_sensitive_field(field_name) if field_name else False
        is_value_sensitive = self.is_sensitive_value(str_value)
        
        if is_field_sensitive or is_value_sensitive:
            return self._apply_masking(str_value, field_name)
        
        return value
    
    def _apply_masking(self, value: str, field_name: str = "") -> str:
        """Aplica enmascaramiento a un valor sensible"""
        if len(value) <= self.partial_reveal * 2:
            # Si el valor es muy corto, enmascarar completamente
            return self.mask_char * min(len(value), 8)
        
        # Enmascaramiento parcial: mostrar primeros y últimos caracteres
        start = value[:self.partial_reveal]
        end = value[-self.partial_reveal:]
        middle_length = len(value) - (self.partial_reveal * 2)
        middle = self.mask_char * min(middle_length, 12)  # Limitar longitud del mask
        
        return f"{start}{middle}{end}"
    
    def mask_sensitive_data(self, data: Any, max_depth: int = 10) -> Any:
        """
        Enmascara datos sensibles en estructuras complejas (dict, list, etc.)
        Implementa protección contra recursión infinita
        """
        if max_depth <= 0:
            return "[MAX_DEPTH_REACHED]"
        
        if isinstance(data, dict):
            masked_dict = {}
            for key, value in data.items():
                if self.is_sensitive_field(key):
                    masked_dict[key] = self.mask_value(value, key)
                else:
                    masked_dict[key] = self.mask_sensitive_data(value, max_depth - 1)
            return masked_dict
        
        elif isinstance(data, list):
            return [self.mask_sensitive_data(item, max_depth - 1) for item in data]
        
        elif isinstance(data, tuple):
            return tuple(self.mask_sensitive_data(item, max_depth - 1) for item in data)
        
        elif isinstance(data, str):
            # Verificar si el string completo parece sensible
            if self.is_sensitive_value(data):
                return self.mask_value(data)
            return data
        
        else:
            # Para otros tipos (int, float, bool, etc.), retornar sin cambios
            return data
    
    def mask_json_string(self, json_string: str) -> str:
        """Enmascara datos sensibles en un string JSON"""
        try:
            data = json.loads(json_string)
            masked_data = self.mask_sensitive_data(data)
            return json.dumps(masked_data, separators=(',', ':'))
        except (json.JSONDecodeError, TypeError):
            # Si no es JSON válido, tratar como string normal
            return self.mask_value(json_string)
    
    def mask_url_params(self, url: str) -> str:
        """Enmascara parámetros sensibles en URLs"""
        if '?' not in url:
            return url
        
        base_url, params = url.split('?', 1)
        param_pairs = params.split('&')
        
        masked_pairs = []
        for pair in param_pairs:
            if '=' in pair:
                key, value = pair.split('=', 1)
                if self.is_sensitive_field(key):
                    masked_pairs.append(f"{key}={self.mask_value(value, key)}")
                else:
                    masked_pairs.append(pair)
            else:
                masked_pairs.append(pair)
        
        return f"{base_url}?{'&'.join(masked_pairs)}"

# Instancia global del masker
_global_masker = DataMasker()

def sensitive_data_filter(func):
    """
    Decorador que filtra automáticamente datos sensibles de los argumentos
    y valores de retorno de una función antes de que lleguen a los logs
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Ejecutar función original
            result = func(*args, **kwargs)
            
            # Si la función retorna un diccionario, enmascarar datos sensibles
            if isinstance(result, dict):
                # Crear copia para no modificar el resultado original
                masked_result = _global_masker.mask_sensitive_data(result.copy())
                
                # Log con datos enmascarados
                logger.debug(
                    f"Function {func.__name__} executed with masked result",
                    extra={
                        'function': func.__name__,
                        'masked_result': masked_result,
                        'args_count': len(args),
                        'kwargs_keys': list(kwargs.keys())
                    }
                )
            
            return result
            
        except Exception as e:
            # Log error sin datos sensibles
            logger.error(
                f"Function {func.__name__} failed",
                extra={
                    'function': func.__name__,
                    'error': str(e),
                    'args_count': len(args),
                    'kwargs_keys': list(kwargs.keys())
                }
            )
            raise
    
    return wrapper

def mask_log_record(record: logging.LogRecord) -> logging.LogRecord:
    """
    Filtra datos sensibles de un LogRecord antes de escribirlo
    Se usa en el formatter personalizado
    """
    # Enmascarar mensaje principal
    if hasattr(record, 'msg') and isinstance(record.msg, str):
        record.msg = _global_masker.mask_value(record.msg)
    
    # Enmascarar argumentos del mensaje
    if hasattr(record, 'args') and record.args:
        masked_args = []
        for arg in record.args:
            if isinstance(arg, (dict, list)):
                masked_args.append(_global_masker.mask_sensitive_data(arg))
            else:
                masked_args.append(_global_masker.mask_value(arg))
        record.args = tuple(masked_args)
    
    # Enmascarar datos extra
    if hasattr(record, '__dict__'):
        for key, value in record.__dict__.items():
            if key.startswith('_') or key in ['name', 'levelno', 'levelname', 'pathname', 'filename', 'module', 'lineno', 'funcName', 'created', 'msecs', 'relativeCreated', 'thread', 'threadName', 'processName', 'process', 'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                continue  # Skip standard logging fields
            
            if _global_masker.is_sensitive_field(key) or isinstance(value, (dict, list)):
                setattr(record, key, _global_masker.mask_sensitive_data(value))
    
    return record

# Funciones de utilidad
def mask_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Función de utilidad para enmascarar un diccionario"""
    return _global_masker.mask_sensitive_data(data)

def mask_string(text: str, field_name: str = "") -> str:
    """Función de utilidad para enmascarar un string"""
    return _global_masker.mask_value(text, field_name)

def is_sensitive(field_name: str) -> bool:
    """Función de utilidad para verificar si un campo es sensible"""
    return _global_masker.is_sensitive_field(field_name)