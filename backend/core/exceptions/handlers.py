"""
Global Exception Handlers
전역 예외 핸들러
"""

import uuid
import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .base import AppException
from .schemas import ErrorResponse, ValidationErrorResponse, ErrorDetail
from .codes import ErrorCode

logger = logging.getLogger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    커스텀 애플리케이션 예외 핸들러

    Args:
        request: FastAPI Request 객체
        exc: AppException 인스턴스

    Returns:
        JSONResponse: 표준 에러 응답
    """
    # 요청 ID 생성 (Request에서 가져오거나 새로 생성)
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    # 로깅
    logger.error(
        f"AppException occurred: [{exc.error_code}] {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            "request_id": request_id,
            "details": exc.details,
        },
    )

    # 에러 응답 생성
    error_response = ErrorResponse(
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        request_id=request_id,
        path=str(request.url.path),
        details=exc.details if exc.details else None,
    )

    return JSONResponse(
        status_code=exc.status_code, content=error_response.model_dump(mode="json")
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Pydantic 검증 에러 핸들러 (422 Unprocessable Entity)

    Args:
        request: FastAPI Request 객체
        exc: RequestValidationError 인스턴스

    Returns:
        JSONResponse: 검증 에러 응답
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    # Pydantic 에러를 우리 포맷으로 변환
    errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        errors.append(
            ErrorDetail(
                field=field_path, message=error["msg"], code=error.get("type", "")
            )
        )

    logger.warning(
        f"Validation error occurred",
        extra={
            "path": request.url.path,
            "method": request.method,
            "request_id": request_id,
            "validation_errors": errors,
        },
    )

    error_response = ValidationErrorResponse(
        error_code=ErrorCode.VAL_INVALID_INPUT,
        message="입력 데이터 검증 실패",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        request_id=request_id,
        path=str(request.url.path),
        errors=[error.model_dump() for error in errors],
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(mode="json"),
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """
    FastAPI/Starlette HTTP 예외 핸들러

    기본 HTTPException을 표준 포맷으로 변환

    Args:
        request: FastAPI Request 객체
        exc: StarletteHTTPException 인스턴스

    Returns:
        JSONResponse: 표준 에러 응답
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    # HTTP 상태 코드에 따라 에러 코드 매핑
    error_code_map = {
        400: ErrorCode.VAL_INVALID_INPUT,
        401: ErrorCode.AUTH_TOKEN_INVALID,
        403: ErrorCode.AUTHZ_FORBIDDEN,
        404: ErrorCode.BIZ_RESOURCE_NOT_FOUND,
        409: ErrorCode.BIZ_DUPLICATE_RESOURCE,
        500: ErrorCode.SYS_INTERNAL_ERROR,
    }

    error_code = error_code_map.get(exc.status_code, ErrorCode.SYS_INTERNAL_ERROR)

    logger.warning(
        f"HTTPException occurred: {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            "request_id": request_id,
        },
    )

    error_response = ErrorResponse(
        error_code=error_code,
        message=str(exc.detail),
        status_code=exc.status_code,
        request_id=request_id,
        path=str(request.url.path),
    )

    return JSONResponse(
        status_code=exc.status_code, content=error_response.model_dump(mode="json")
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    일반 예외 핸들러 (예상치 못한 모든 에러)

    500 Internal Server Error로 처리

    Args:
        request: FastAPI Request 객체
        exc: Exception 인스턴스

    Returns:
        JSONResponse: 500 에러 응답
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    # 심각한 에러이므로 전체 스택 트레이스 로깅
    logger.exception(
        f"Unexpected exception occurred: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "request_id": request_id,
            "exception_type": type(exc).__name__,
        },
    )

    # 프로덕션에서는 상세 에러 정보를 숨김
    from backend.core.config import settings

    details = {"error": str(exc), "type": type(exc).__name__} if settings.debug else None

    error_response = ErrorResponse(
        error_code=ErrorCode.SYS_INTERNAL_ERROR,
        message="서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        request_id=request_id,
        path=str(request.url.path),
        details=details,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(mode="json"),
    )
