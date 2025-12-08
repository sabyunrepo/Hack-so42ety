"""
Voice Clone Schemas
클론 보이스 생성 관련 Pydantic 모델
"""

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """에러 응답 모델"""

    error: str = Field(..., description="에러 메시지")
    detail: str = Field(None, description="상세 에러 정보")
