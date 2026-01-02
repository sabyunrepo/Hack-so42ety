"""
Authentication Dependencies
FastAPI Depends용 인증 의존성
"""

import hashlib
import logging
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.session import get_db_readonly
from ..dependencies import get_cache_service
from ..cache.service import CacheService
from .jwt_manager import JWTManager
from ..exceptions import AuthenticationException, ErrorCode

logger = logging.getLogger(__name__)

# HTTP Bearer 토큰 스킴 (auto_error=False for optional auth)
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: AsyncSession = Depends(get_db_readonly),
    cache_service: CacheService = Depends(get_cache_service),
) -> dict:
    """
    현재 인증된 사용자 정보 추출 (블랙리스트 확인 포함)

    쿠키 우선, Authorization 헤더 폴백 방식:
    1) 쿠키에서 access_token 추출 시도
    2) 없으면 Authorization 헤더에서 추출 (마이그레이션 호환성)

    Args:
        request: FastAPI Request 객체 (쿠키에서 토큰 추출)
        credentials: HTTP Authorization Bearer 토큰 (폴백용)
        db: 데이터베이스 세션
        cache_service: Redis 캐시 서비스

    Returns:
        dict: 사용자 정보 (user_id, email 등)

    Raises:
        HTTPException: 토큰이 유효하지 않거나 만료된 경우
    """
    # 1. Extract token from cookie (preferred) or fallback to Authorization header
    token = request.cookies.get("access_token")
    token_source = "cookie"

    if not token and credentials:
        token = credentials.credentials
        token_source = "header"

    if not token:
        logger.warning("❌ [AUTH] No access token found in cookie or header")
        raise AuthenticationException(
            error_code=ErrorCode.AUTH_TOKEN_INVALID,
            message="Authentication credentials not provided"
        )

    logger.debug(
        f"🔑 [AUTH] Access token extracted from {token_source}",
        extra={"token_source": token_source, "token_length": len(token)}
    )

    # 2. JWT 토큰 검증
    payload = JWTManager.verify_token(token, token_type="access")

    if payload is None:
        logger.warning("❌ [AUTH] Invalid access token")
        raise AuthenticationException(
            error_code=ErrorCode.AUTH_TOKEN_INVALID,
            message="Invalid authentication credentials"
        )

    # 3. 블랙리스트 확인 (로그아웃된 토큰)
    token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
    blacklist_key = f"blacklist:access:{token_hash}"
    is_blacklisted = await cache_service.get(blacklist_key)

    if is_blacklisted:
        logger.warning(
            "⚠️ [AUTH] Access token is blacklisted",
            extra={"user_id": payload.get("sub"), "blacklist_key": blacklist_key}
        )
        raise AuthenticationException(
            error_code=ErrorCode.AUTH_TOKEN_INVALID,
            message="Token has been revoked"
        )

    # user_id 추출
    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise AuthenticationException(
            error_code=ErrorCode.AUTH_TOKEN_INVALID,
            message="Invalid token payload"
        )

    logger.info(
        "✅ [AUTH] Access token validated",
        extra={"user_id": user_id, "token_source": token_source}
    )

    # 사용자 정보 반환 (DB 조회는 Repository에서 수행)
    return {
        "user_id": user_id,
        "email": payload.get("email"),
        "sub": user_id,  # for consistency
    }


async def get_current_active_user(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    활성화된 사용자 정보 추출

    추후 사용자 비활성화 기능 추가 시 사용

    Args:
        current_user: 현재 사용자 정보

    Returns:
        dict: 활성화된 사용자 정보

    Raises:
        HTTPException: 사용자가 비활성화된 경우
    """
    # 추후 User 모델에 is_active 필드 추가 시 검증 로직 구현
    # if not current_user.get("is_active"):
    #     raise HTTPException(status_code=400, detail="Inactive user")

    return current_user

async def get_current_user_object(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_readonly),
):
    """
    현재 인증된 사용자 객체(DB 모델) 반환
    """
    from backend.features.auth.repository import UserRepository
    import uuid
    
    user_repo = UserRepository(db)
    try:
        user_id = uuid.UUID(current_user["user_id"])
        user = await user_repo.get(user_id)
        if user is None:
             raise AuthenticationException(
                 error_code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                 message="User not found"
             )
        return user
    except ValueError:
        raise AuthenticationException(
            error_code=ErrorCode.AUTH_TOKEN_INVALID,
            message="Invalid user ID format"
        )


async def get_optional_user_object(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: AsyncSession = Depends(get_db_readonly),
):
    """
    선택적 사용자 객체 반환 (인증되지 않은 경우 None)

    쿠키 우선, Authorization 헤더 폴백 방식:
    1) 쿠키에서 access_token 추출 시도
    2) 없으면 Authorization 헤더에서 추출 (마이그레이션 호환성)

    공개 파일 접근 시 사용
    """
    # 1. Extract token from cookie (preferred) or fallback to Authorization header
    token = request.cookies.get("access_token")
    token_source = "cookie"

    if not token and credentials:
        token = credentials.credentials
        token_source = "header"

    if not token:
        logger.debug("🔓 [AUTH] No access token found, allowing unauthenticated access")
        return None

    logger.debug(
        f"🔑 [AUTH] Optional access token extracted from {token_source}",
        extra={"token_source": token_source, "token_length": len(token)}
    )

    try:
        # 2. JWT 토큰 검증
        payload = JWTManager.verify_token(token, token_type="access")

        if payload is None:
            logger.debug("⚠️ [AUTH] Invalid optional access token, allowing unauthenticated access")
            return None

        # 3. user_id 추출
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            logger.debug("⚠️ [AUTH] No user_id in token payload, allowing unauthenticated access")
            return None

        # 4. 사용자 객체 조회
        from backend.features.auth.repository import UserRepository
        import uuid

        user_repo = UserRepository(db)
        try:
            user_uuid = uuid.UUID(user_id)
            user = await user_repo.get(user_uuid)
            if user:
                logger.debug(
                    "✅ [AUTH] Optional access token validated",
                    extra={"user_id": user_id, "token_source": token_source}
                )
            else:
                logger.debug(
                    "⚠️ [AUTH] User not found for optional token",
                    extra={"user_id": user_id}
                )
            return user
        except ValueError:
            logger.debug("⚠️ [AUTH] Invalid user ID format in optional token")
            return None
    except Exception as e:
        # 인증 실패(만료, 위조 등) 시 None 반환 (공개 파일 접근 허용)
        # TokenExpiredException, InvalidTokenException 등 모든 예외 무시
        logger.debug(
            f"⚠️ [AUTH] Optional token validation failed: {type(e).__name__}, allowing unauthenticated access"
        )
        return None
