"""
Auth API Endpoints
인증 관련 API 라우터
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.auth import get_current_user
from .schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    GoogleOAuthRequest,
    RefreshTokenRequest,
    AuthResponse,
    TokenResponse,
    UserResponse,
    ErrorResponse,
)
from .service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "회원가입 성공"},
        400: {"model": ErrorResponse, "description": "이메일 중복"},
    },
)
async def register(
    request: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    회원가입

    Args:
        request: 회원가입 요청 (email, password)
        db: 데이터베이스 세션

    Returns:
        AuthResponse: 토큰 + 사용자 정보
    """
    auth_service = AuthService(db)

    try:
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

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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
    db: AsyncSession = Depends(get_db),
):
    """
    로그인

    Args:
        request: 로그인 요청 (email, password)
        db: 데이터베이스 세션

    Returns:
        AuthResponse: 토큰 + 사용자 정보
    """
    auth_service = AuthService(db)

    try:
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

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


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
    db: AsyncSession = Depends(get_db),
):
    """
    Google OAuth 로그인

    Args:
        request: Google OAuth 요청 (Google ID Token)
        db: 데이터베이스 세션

    Returns:
        AuthResponse: 토큰 + 사용자 정보
    """
    auth_service = AuthService(db)

    try:
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

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


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
    db: AsyncSession = Depends(get_db),
):
    """
    Access Token 갱신

    Args:
        request: 토큰 갱신 요청 (Refresh Token)
        db: 데이터베이스 세션

    Returns:
        TokenResponse: 새로운 Access Token
    """
    auth_service = AuthService(db)

    try:
        access_token = await auth_service.refresh_access_token(
            refresh_token=request.refresh_token
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=request.refresh_token,  # Refresh Token은 그대로 유지
            token_type="bearer",
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        200: {"description": "현재 사용자 정보 조회 성공"},
        401: {"model": ErrorResponse, "description": "인증 실패"},
    },
)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    현재 인증된 사용자 정보 조회

    Args:
        current_user: 현재 사용자 (JWT에서 추출)
        db: 데이터베이스 세션

    Returns:
        UserResponse: 사용자 정보
    """
    from backend.features.auth.repository import UserRepository
    import uuid

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(uuid.UUID(current_user["user_id"]))

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserResponse(
        id=str(user.id),
        email=user.email,
        oauth_provider=user.oauth_provider,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )
