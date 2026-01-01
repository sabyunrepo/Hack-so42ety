"""
Auth API Endpoints (v1)
인증 관련 API 라우터
"""

import logging
from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.session import get_db_readonly, get_db_write
from backend.core.dependencies import get_cache_service, create_rate_limit_dependency
from backend.core.cache.service import CacheService
from backend.core.config import settings

logger = logging.getLogger(__name__)
from backend.core.auth import get_current_user
from backend.core.dependencies import get_cache_service
from backend.core.auth.jwt_manager import JWTManager
from backend.core.auth.providers.credentials import CredentialsAuthProvider
from backend.core.auth.providers.google_oauth import GoogleOAuthProvider
from backend.core.exceptions import NotFoundException, ErrorCode
from backend.features.auth.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    GoogleOAuthRequest,
    RefreshTokenRequest,
    LogoutRequest,
    AuthResponse,
    TokenResponse,
    UserResponse,
    LogoutResponse,
    ErrorResponse,
)
from backend.features.auth.service import AuthService
from backend.features.auth.repository import UserRepository
from backend.core.events.redis_streams_bus import RedisStreamsEventBus
from backend.core.cache.service import CacheService

router = APIRouter()
security = HTTPBearer()

# Rate limiting dependencies
rate_limit_login = create_rate_limit_dependency(
    endpoint="auth:login",
    limit=settings.auth_login_rate_limit,
    window_seconds=settings.auth_rate_limit_window_seconds,
)

rate_limit_register = create_rate_limit_dependency(
    endpoint="auth:register",
    limit=settings.auth_register_rate_limit,
    window_seconds=settings.auth_rate_limit_window_seconds,
)

rate_limit_google = create_rate_limit_dependency(
    endpoint="auth:google",
    limit=settings.auth_google_rate_limit,
    window_seconds=settings.auth_rate_limit_window_seconds,
)


def get_auth_service_write(
    db: AsyncSession = Depends(get_db_write),
    cache_service: CacheService = Depends(get_cache_service),
) -> AuthService:
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
        cache_service=cache_service,
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_register)],
    responses={
        201: {"description": "회원가입 성공"},
        409: {"model": ErrorResponse, "description": "이메일 중복"},
        429: {"model": ErrorResponse, "description": "요청 속도 제한 초과"},
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
    dependencies=[Depends(rate_limit_login)],
    responses={
        200: {"description": "로그인 성공"},
        401: {"model": ErrorResponse, "description": "인증 실패"},
        429: {"model": ErrorResponse, "description": "요청 속도 제한 초과"},
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
    dependencies=[Depends(rate_limit_google)],
    responses={
        200: {"description": "Google OAuth 로그인 성공"},
        401: {"model": ErrorResponse, "description": "토큰 검증 실패"},
        429: {"model": ErrorResponse, "description": "요청 속도 제한 초과"},
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
    logger.info(
        "🔄 [ENDPOINT] /auth/refresh called",
        extra={"refresh_token_length": len(request.refresh_token)}
    )

    try:
        access_token, new_refresh_token = await auth_service.refresh_access_token(
            refresh_token=request.refresh_token
        )

        logger.info("✅ [ENDPOINT] Token refresh successful")

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
        )
    except Exception as e:
        logger.error(f"❌ [ENDPOINT] Token refresh failed: {str(e)}", exc_info=True)
        raise


@router.post(
    "/logout",
    response_model=LogoutResponse,
    responses={
        200: {"description": "로그아웃 성공"},
        401: {"model": ErrorResponse, "description": "인증 실패"},
    },
)
async def logout(
    request: LogoutRequest,
    current_user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service_write),
):
    """
    로그아웃 - 토큰 무효화

    Args:
        request: 로그아웃 요청 (Refresh Token)
        current_user: 현재 사용자 (JWT에서 추출)
        credentials: Authorization Bearer 토큰
        auth_service: 인증 서비스

    Returns:
        LogoutResponse: 로그아웃 성공 메시지
    """
    logger.info(
        "🚪 [ENDPOINT] /auth/logout called",
        extra={"user_id": current_user["user_id"]}
    )

    try:
        access_token = credentials.credentials

        await auth_service.logout(
            user_id=current_user["user_id"],
            access_token=access_token,
            refresh_token=request.refresh_token,
        )

        logger.info("✅ [ENDPOINT] Logout successful")

        return LogoutResponse(message="Logout successful")
    except Exception as e:
        logger.error(f"❌ [ENDPOINT] Logout failed: {str(e)}", exc_info=True)
        raise





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
