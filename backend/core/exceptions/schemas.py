"""
Error Response Schemas
에러 응답 스키마
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime


class ErrorDetail(BaseModel):
    """개별 에러 상세 정보"""

    field: Optional[str] = Field(None, description="에러 발생 필드명")
    message: str = Field(..., description="에러 메시지")
    code: Optional[str] = Field(None, description="세부 에러 코드")

    class Config:
        json_schema_extra = {
            "example": {
                "field": "email",
                "message": "이메일 형식이 올바르지 않습니다",
                "code": "VAL_003",
            }
        }


class ErrorResponse(BaseModel):
    """
    표준 에러 응답

    모든 API 에러는 이 형식으로 반환됩니다.
    """

    error_code: str = Field(..., description="에러 코드 (예: AUTH_001)", example="AUTH_001")
    message: str = Field(
        ..., description="사용자 친화적 에러 메시지", example="이메일 또는 비밀번호가 일치하지 않습니다"
    )
    status_code: int = Field(..., description="HTTP 상태 코드", example=401)
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="에러 발생 시각"
    )
    request_id: Optional[str] = Field(None, description="요청 추적 ID", example="req-abc123")
    path: Optional[str] = Field(None, description="요청 경로", example="/api/v1/auth/login")
    details: Optional[Dict[str, Any]] = Field(
        None, description="추가 에러 정보 (선택사항)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "error_code": "AUTH_002",
                "message": "소셜 로그인 사용자입니다. google 로그인을 이용해주세요",
                "status_code": 401,
                "timestamp": "2025-12-02T07:00:00.000Z",
                "request_id": "req-abc123",
                "path": "/api/v1/auth/login",
                "details": {"oauth_provider": "google", "email": "user@example.com"},
            }
        }


class ValidationErrorResponse(BaseModel):
    """검증 에러 응답 (422)"""

    error_code: str = Field(
        default="VAL_001", description="에러 코드", example="VAL_001"
    )
    message: str = Field(
        default="입력 데이터 검증 실패", description="에러 메시지"
    )
    status_code: int = Field(default=422, description="HTTP 상태 코드")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = Field(None, description="요청 추적 ID")
    path: Optional[str] = Field(None, description="요청 경로")
    errors: List[ErrorDetail] = Field(..., description="검증 에러 목록")

    class Config:
        json_schema_extra = {
            "example": {
                "error_code": "VAL_001",
                "message": "입력 데이터 검증 실패",
                "status_code": 422,
                "timestamp": "2025-12-02T07:00:00.000Z",
                "request_id": "req-xyz789",
                "path": "/api/v1/auth/register",
                "errors": [
                    {
                        "field": "email",
                        "message": "이메일 형식이 올바르지 않습니다",
                        "code": "VAL_003",
                    }
                ],
            }
        }
