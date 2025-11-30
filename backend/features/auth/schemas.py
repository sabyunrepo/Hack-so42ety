"""
Auth Schemas
인증 관련 Request/Response 스키마
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ==================== Request Schemas ====================


class UserRegisterRequest(BaseModel):
    """회원가입 요청"""

    email: EmailStr = Field(..., description="사용자 이메일")
    password: str = Field(..., min_length=8, description="비밀번호 (최소 8자)")


class UserLoginRequest(BaseModel):
    """로그인 요청"""

    email: EmailStr = Field(..., description="사용자 이메일")
    password: str = Field(..., description="비밀번호")


class GoogleOAuthRequest(BaseModel):
    """Google OAuth 로그인 요청"""

    token: str = Field(..., description="Google ID Token")


class RefreshTokenRequest(BaseModel):
    """토큰 갱신 요청"""

    refresh_token: str = Field(..., description="Refresh Token")


# ==================== Response Schemas ====================


class TokenResponse(BaseModel):
    """토큰 응답"""

    access_token: str = Field(..., description="Access Token")
    refresh_token: str = Field(..., description="Refresh Token")
    token_type: str = Field(default="bearer", description="토큰 타입")


class UserResponse(BaseModel):
    """사용자 정보 응답"""

    id: str = Field(..., description="사용자 UUID")
    email: str = Field(..., description="사용자 이메일")
    oauth_provider: Optional[str] = Field(None, description="OAuth 제공자")
    is_active: bool = Field(..., description="활성화 여부")
    created_at: str = Field(..., description="생성 시간")

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    """인증 응답 (토큰 + 사용자 정보)"""

    access_token: str = Field(..., description="Access Token")
    refresh_token: str = Field(..., description="Refresh Token")
    token_type: str = Field(default="bearer", description="토큰 타입")
    user: UserResponse = Field(..., description="사용자 정보")


# ==================== Error Schemas ====================


class ErrorResponse(BaseModel):
    """에러 응답"""

    detail: str = Field(..., description="에러 메시지")
