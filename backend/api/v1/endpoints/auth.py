"""
Auth API Endpoints (v1)
인증 관련 API 라우터
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.session import get_db_readonly, get_db_write
from backend.core.auth import get_current_user
from backend.core.auth.jwt_manager import JWTManager
from backend.core.auth.providers.credentials import CredentialsAuthProvider
from backend.core.auth.providers.google_oauth import GoogleOAuthProvider
from backend.core.exceptions import NotFoundException, ErrorCode
from backend.features.auth.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    GoogleOAuthRequest,
    RefreshTokenRequest,
    AuthResponse,
    TokenResponse,
    UserResponse,
    ErrorResponse,
)
from backend.features.auth.service import AuthService
from backend.features.auth.repository import UserRepository

router = APIRouter()


def get_auth_service_write(db: AsyncSession = Depends(get_db_write)) -> AuthService:
    """AuthService 의존성 주입 (Write용 - 회원가입, 로그인 등)"""
    user_repo = UserRepository(db)
    credentials_provider = CredentialsAuthProvider()
    google_oauth_provider = GoogleOAuthProvider()
    jwt_manager = JWTManager()
    return AuthService(
        user_repo=user_repo,
        credentials_provider=credentials_provider,
        google_oauth_provider=google_oauth_provider,
        jwt_manager=jwt_manager,
        db=db,
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "회원가입 성공"},
        409: {"model": ErrorResponse, "description": "이메일 중복"},
    },
)
async def register(
    request: UserRegisterRequest,
    auth_service: AuthService = Depends(get_auth_service_write),
):
    """
    회원가입

    Args:
        request: 회원가입 요청 (email, password)
        auth_service: 인증 서비스

    Returns:
        AuthResponse: 토큰 + 사용자 정보
    """
    user, access_token, refresh_token = await auth_service.register(
        email=request.email,
        password=request.password,
    )

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            oauth_provider=user.oauth_provider,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
        ),
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    responses={
        200: {"description": "로그인 성공"},
        401: {"model": ErrorResponse, "description": "인증 실패"},
    },
)
async def login(
    request: UserLoginRequest,
    auth_service: AuthService = Depends(get_auth_service_write),
):
    """
    로그인

    Args:
        request: 로그인 요청 (email, password)
        auth_service: 인증 서비스

    Returns:
        AuthResponse: 토큰 + 사용자 정보
    """
    user, access_token, refresh_token = await auth_service.login(
        email=request.email,
        password=request.password,
    )

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            oauth_provider=user.oauth_provider,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
        ),
    )


@router.post(
    "/google",
    response_model=AuthResponse,
    responses={
        200: {"description": "Google OAuth 로그인 성공"},
        401: {"model": ErrorResponse, "description": "토큰 검증 실패"},
    },
)
async def google_oauth(
    request: GoogleOAuthRequest,
    auth_service: AuthService = Depends(get_auth_service_write),
):
    """
    Google OAuth 로그인

    Args:
        request: Google OAuth 요청 (Google ID Token)
        auth_service: 인증 서비스

    Returns:
        AuthResponse: 토큰 + 사용자 정보
    """
    user, access_token, refresh_token = await auth_service.google_oauth_login(
        google_token=request.token
    )

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            oauth_provider=user.oauth_provider,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
        ),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={
        200: {"description": "토큰 갱신 성공"},
        401: {"model": ErrorResponse, "description": "Refresh Token 검증 실패"},
    },
)
async def refresh(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service_write),
):
    """
    Access Token 갱신

    Args:
        request: 토큰 갱신 요청 (Refresh Token)
        auth_service: 인증 서비스

    Returns:
        TokenResponse: 새로운 Access Token
    """
    access_token = await auth_service.refresh_access_token(
        refresh_token=request.refresh_token
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=request.refresh_token,  # Refresh Token은 그대로 유지
        token_type="bearer",
    )


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        200: {"description": "현재 사용자 정보 조회 성공"},
        401: {"model": ErrorResponse, "description": "인증 실패"},
        404: {"model": ErrorResponse, "description": "사용자를 찾을 수 없음"},
    },
)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_readonly),
):
    """
    현재 인증된 사용자 정보 조회

    Args:
        current_user: 현재 사용자 (JWT에서 추출)
        db: 데이터베이스 세션

    Returns:
        UserResponse: 사용자 정보
    """
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(current_user["email"])

    if user is None:
        raise NotFoundException(
            error_code=ErrorCode.BIZ_001,
            message="사용자를 찾을 수 없습니다"
        )

    return UserResponse(
        id=str(user.id),
        email=user.email,
        oauth_provider=user.oauth_provider,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )
