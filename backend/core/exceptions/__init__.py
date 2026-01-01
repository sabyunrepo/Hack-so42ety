"""
Core Exceptions Module
"""

from .base import (
    AppException,
    AuthenticationException,
    AuthorizationException,
    ValidationException,
    NotFoundException,
    ConflictException,
    BusinessLogicException,
    InternalServerException,
    RateLimitExceededException,
)
from .codes import ErrorCode
from .schemas import ErrorResponse, ErrorDetail, ValidationErrorResponse

__all__ = [
    # Base Exceptions
    "AppException",
    "AuthenticationException",
    "AuthorizationException",
    "ValidationException",
    "NotFoundException",
    "ConflictException",
    "BusinessLogicException",
    "InternalServerException",
    "RateLimitExceededException",
    # Error Codes
    "ErrorCode",
    # Schemas
    "ErrorResponse",
    "ErrorDetail",
    "ValidationErrorResponse",
]
