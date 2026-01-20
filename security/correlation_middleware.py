"""
Correlation ID Middleware - Global Request Tracking
Implements X-Correlation-ID propagation for distributed tracing
"""
import uuid
import time
from contextvars import ContextVar
from typing import Optional, Callable
from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger("correlation_middleware")

# Context variable para almacenar correlation ID en el contexto de la request
_correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
_request_start_time: ContextVar[Optional[float]] = ContextVar('requ