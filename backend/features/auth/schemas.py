"""
Auth Schemas
인증 관련 Request/Response 스키마
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ==================== Request Schemas ====================


class UserRegisterRequest(BaseModel):
    """회원가입 요청"""

    email: EmailStr = Field(..., description="사용자 이메일", example="user@example.com")
    password: str = Field(..., min_length=8, description="비밀번호 (최소 8자)", example="SecurePass123!")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "system@moriai.ai",
                "password": "123123123"
            }
        }


class UserLoginRequest(BaseModel):
    """로그인 요청"""

    email: EmailStr = Field(..., description="사용자 이메일", example="user@example.com")
    password: str = Field(..., description="비밀번호", example="SecurePass123!")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "system@moriai.ai",
                "password": "123123123"
            }
        }


class GoogleOAuthRequest(BaseModel):
    """Google OAuth 로그인 요청"""

    token: str = Field(..., description="Google ID Token", example="eyJhbGciOiJSUzI1NiIsImtpZCI6...")

    class Config:
        json_schema_extra = {
            "example": {
                "token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjE4MmU0M2VlZjk3YmY1..."
            }
        }


class RefreshTokenRequest(BaseModel):
    """토큰 갱신 요청"""

    refresh_token: str = Field(..., description="Refresh Token", example="eyJhbGciOiJIUzI1NiIsInR5cCI6...")

    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


# ==================== Response Schemas ====================


class TokenResponse(BaseModel):
    """토큰 응답"""

    access_token: str = Field(..., description="Access Token", example="eyJhbGciOiJIUzI1NiIsInR5cCI6...")
    refresh_token: str = Field(..., description="Refresh Token", example="eyJhbGciOiJIUzI1NiIsInR5cCI6...")
    token_type: str = Field(default="bearer", description="토큰 타입", example="bearer")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMTIzZTQ1NjctZTg5Yi0xMmQzLWE0NTYtNDI2NjE0MTc0MDAwIiwiZXhwIjoxNjQwOTk1MjAwfQ.abc123",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMTIzZTQ1NjctZTg5Yi0xMmQzLWE0NTYtNDI2NjE0MTc0MDAwIiwiZXhwIjoxNjQwOTk1MjAwfQ.def456",
                "token_type": "bearer"
            }
        }


class UserResponse(BaseModel):
    """사용자 정보 응답"""

    id: str = Field(..., description="사용자 UUID", example="123e4567-e89b-12d3-a456-426614174000")
    email: str = Field(..., description="사용자 이메일", example="user@example.com")
    oauth_provider: Optional[str] = Field(None, description="OAuth 제공자", example="google")
    is_active: bool = Field(..., description="활성화 여부", example=True)
    created_at: str = Field(..., description="생성 시간", example="2024-11-30T12:00:00Z")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "oauth_provider": None,
                "is_active": True,
                "created_at": "2024-11-30T12:00:00Z"
            }
        }


class AuthResponse(BaseModel):
    """인증 응답 (토큰 + 사용자 정보)"""

    access_token: str = Field(..., description="Access Token", example="eyJhbGciOiJIUzI1NiIsInR5cCI6...")
    refresh_token: str = Field(..., description="Refresh Token", example="eyJhbGciOiJIUzI1NiIsInR5cCI6...")
    token_type: str = Field(default="bearer", description="토큰 타입", example="bearer")
    user: UserResponse = Field(..., description="사용자 정보")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "user@example.com",
                    "oauth_provider": None,
                    "is_active": True,
                    "created_at": "2024-11-30T12:00:00Z"
                }
            }
        }


# ==================== Error Schemas ====================


class ErrorResponse(BaseModel):
    """에러 응답"""

    detail: str = Field(..., description="에러 메시지")
