"""
Auth Service
인증 비즈니스 로직
"""

import hashlib
import logging
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.auth.jwt_manager import JWTManager

logger = logging.getLogger(__name__)
from ...core.auth.providers.credentials import CredentialsAuthProvider
from ...core.auth.providers.google_oauth import GoogleOAuthProvider
from ...core.cache.service import CacheService
from ...core.config import settings
from ...core.utils.trace import log_process
from .models import User
from .repository import UserRepository
from .exceptions import (
    InvalidCredentialsException,
    OAuthUserOnlyException,
    EmailAlreadyExistsException,
    InvalidGoogleTokenException,
    InvalidRefreshTokenException,
)


class AuthService:
    """
    인증 서비스

    회원가입, 로그인, OAuth 인증 처리

    DI Pattern: 모든 의존성을 생성자를 통해 주입받습니다.
    """

    def __init__(
        self,
        user_repo: UserRepository,
        credentials_provider: CredentialsAuthProvider,
        google_oauth_provider: GoogleOAuthProvider,
        jwt_manager: JWTManager,
        db: AsyncSession,
        cache_service: CacheService,
    ):
        """
        Args:
            user_repo: 사용자 레포지토리
            credentials_provider: 비밀번호 인증 제공자
            google_oauth_provider: Google OAuth 제공자
            jwt_manager: JWT 토큰 관리자
            db: 비동기 데이터베이스 세션
            cache_service: Redis 캐시 서비스
        """
        self.user_repo = user_repo
        self.credentials_provider = credentials_provider
        self.google_oauth_provider = google_oauth_provider
        self.jwt_manager = jwt_manager
        self.db = db
        self.cache_service = cache_service

    def _hash_token(self, token: str) -> str:
        """토큰 해시 생성 (Redis 키용)"""
        return hashlib.sha256(token.encode()).hexdigest()[:16]

    async def register(self, email: str, password: str) -> Tuple[User, str, str]:
        """
        회원가입
        """
        logger.info(f"📝 [REGISTER] Starting registration", extra={"email": email})

        # 이메일 중복 확인
        if await self.user_repo.exists_by_email(email):
            raise EmailAlreadyExistsException(email)

        # 비밀번호 해싱
        password_hash = self.credentials_provider.hash_password(password)

        # 사용자 생성
        user = User(
            email=email,
            password_hash=password_hash,
            oauth_provider=None,
            oauth_id=None,
        )

        user = await self.user_repo.save(user)
        await self.db.commit()

        # JWT 토큰 생성
        access_token = self.jwt_manager.create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        refresh_token = self.jwt_manager.create_refresh_token(
            data={"sub": str(user.id), "email": user.email}
        )

        # Refresh Token Redis 저장 (화이트리스트)
        cache_key = f"refresh_token:{user.id}"
        ttl = settings.jwt_refresh_token_expire_days * 24 * 3600
        await self.cache_service.set(cache_key, refresh_token, ttl=ttl)

        logger.info(
            "💾 [REDIS] Refresh token stored",
            extra={"user_id": str(user.id), "cache_key": cache_key, "ttl": ttl}
        )
        logger.info(f"✅ [REGISTER] Registration successful", extra={"user_id": str(user.id)})

        return user, access_token, refresh_token

    async def login(self, email: str, password: str) -> Tuple[User, str, str]:
        """
        로그인
        """
        logger.info(f"🔐 [LOGIN] Attempting login", extra={"email": email})

        # 사용자 조회
        user = await self.user_repo.get_by_email(email)

        if user is None:
            raise InvalidCredentialsException()

        # OAuth 전용 사용자 체크
        if user.oauth_provider is not None:
            raise OAuthUserOnlyException(user.oauth_provider)

        # 비밀번호 해시가 없는 경우
        if user.password_hash is None:
            raise OAuthUserOnlyException("social")

        # 비밀번호 검증
        verify_result = self.credentials_provider.verify_password(password, user.password_hash)

        if not verify_result:
            raise InvalidCredentialsException()

        # JWT 토큰 생성
        access_token = self.jwt_manager.create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        refresh_token = self.jwt_manager.create_refresh_token(
            data={"sub": str(user.id), "email": user.email}
        )

        # Refresh Token Redis 저장 (화이트리스트)
        cache_key = f"refresh_token:{user.id}"
        ttl = settings.jwt_refresh_token_expire_days * 24 * 3600
        await self.cache_service.set(cache_key, refresh_token, ttl=ttl)

        logger.info(
            "💾 [REDIS] Refresh token stored",
            extra={"user_id": str(user.id), "cache_key": cache_key}
        )
        logger.info(f"✅ [LOGIN] Login successful", extra={"user_id": str(user.id)})

        return user, access_token, refresh_token

    async def google_oauth_login(self, google_token: str) -> Tuple[User, str, str]:
        """
        Google OAuth 로그인
        """
        # Google ID Token 검증
        user_info = await self.google_oauth_provider.verify_token(google_token)

        if user_info is None:
            raise InvalidGoogleTokenException()

        # 기존 사용자 조회
        user = await self.user_repo.get_by_oauth(
            oauth_provider="google", oauth_id=user_info["sub"]
        )

        # 신규 사용자 생성
        if user is None:
            user = User(
                email=user_info["email"],
                password_hash=None,  # OAuth 전용
                oauth_provider="google",
                oauth_id=user_info["sub"],
            )
            user = await self.user_repo.save(user)
            await self.db.commit()

        # JWT 토큰 생성
        access_token = self.jwt_manager.create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        refresh_token = self.jwt_manager.create_refresh_token(
            data={"sub": str(user.id), "email": user.email}
        )

        # Refresh Token Redis 저장 (화이트리스트)
        cache_key = f"refresh_token:{user.id}"
        ttl = settings.jwt_refresh_token_expire_days * 24 * 3600
        await self.cache_service.set(cache_key, refresh_token, ttl=ttl)

        logger.info(
            "💾 [REDIS] Refresh token stored",
            extra={"user_id": str(user.id), "cache_key": cache_key}
        )

        return user, access_token, refresh_token

    async def refresh_access_token(self, refresh_token: str) -> Tuple[str, str]:
        """
        Access Token 갱신 (RTR 적용)
        
        Returns:
            Tuple[str, str]: (New Access Token, New Refresh Token)
        """
        logger.info("🔄 [REFRESH] Starting token refresh")

        # 1. JWT 검증
        payload = self.jwt_manager.verify_token(refresh_token, token_type="refresh")

        if payload is None:
            logger.error("❌ [REFRESH] Invalid refresh token (JWT decode failed)")
            raise InvalidRefreshTokenException()

        user_id = payload.get("sub")

        # 2. 블랙리스트 확인 (로그아웃된 토큰)
        blacklist_key = f"blacklist:refresh:{self._hash_token(refresh_token)}"
        is_blacklisted = await self.cache_service.get(blacklist_key)

        if is_blacklisted:
            logger.warning(
                "⚠️ [REDIS] Refresh token is blacklisted",
                extra={"user_id": user_id, "blacklist_key": blacklist_key}
            )
            raise InvalidRefreshTokenException()

        # 3. 화이트리스트 확인 (유효한 토큰)
        cache_key = f"refresh_token:{user_id}"
        cached_token = await self.cache_service.get(cache_key)
        
        # DEBUG LOGGING start
        logger.debug(
            f"🔍 [DEBUG] Checking whitelist for user {user_id}",
            extra={
                "cache_key": cache_key,
                "cached_token_exists": cached_token is not None,
                "cached_token_prefix": cached_token[:10] if cached_token else "None",
                "request_token_prefix": refresh_token[:10]
            }
        )
        # DEBUG LOGGING end

        if cached_token != refresh_token:
            logger.warning(
                "⚠️ [REDIS] Refresh token not in whitelist or mismatch",
                extra={"user_id": user_id, "cache_key": cache_key}
            )
            raise InvalidRefreshTokenException()

        logger.info(
            "✅ [REDIS] Refresh token validated from whitelist",
            extra={"user_id": user_id}
        )

        # 4. 새로운 Access Token 생성
        access_token = self.jwt_manager.create_access_token(
            data={"sub": payload["sub"], "email": payload.get("email")}
        )
        # 새 Refresh Token (새 JTI 포함)
        new_refresh_token = self.jwt_manager.create_refresh_token(
            data={"sub": user_id, "email": payload.get("email")}
        )

        # 5. 새 Refresh Token Redis 저장 (화이트리스트 갱신)
        cache_key = f"refresh_token:{user_id}"
        ttl = settings.jwt_refresh_token_expire_days * 24 * 3600
        await self.cache_service.set(cache_key, new_refresh_token, ttl=ttl)

        logger.info(
            "💾 [REDIS] New refresh token stored",
            extra={"user_id": user_id, "ttl": ttl}
        )
        logger.info(f"🔑 [REFRESH] New access token created", extra={"user_id": user_id})

        return access_token, new_refresh_token

    async def logout(self, user_id: str, access_token: str, refresh_token: str) -> None:
        """
        로그아웃 - 토큰 무효화

        Args:
            user_id: 사용자 UUID
            access_token: Access Token (블랙리스트 추가)
            refresh_token: Refresh Token (블랙리스트 추가 + 화이트리스트 삭제)
        """
        logger.info(f"🚪 [LOGOUT] Starting logout", extra={"user_id": user_id})

        # 1. Refresh Token 화이트리스트에서 삭제
        whitelist_key = f"refresh_token:{user_id}"
        await self.cache_service.delete(whitelist_key)
        logger.info(f"🗑️ [REDIS] Refresh token removed from whitelist", extra={"user_id": user_id})

        # 2. Access Token 블랙리스트 추가 (남은 만료 시간만큼 TTL)
        access_blacklist_key = f"blacklist:access:{self._hash_token(access_token)}"
        access_ttl = settings.jwt_access_token_expire_minutes * 60
        await self.cache_service.set(access_blacklist_key, "1", ttl=access_ttl)
        logger.info(f"🚫 [REDIS] Access token blacklisted", extra={"ttl": access_ttl})

        # 3. Refresh Token 블랙리스트 추가
        refresh_blacklist_key = f"blacklist:refresh:{self._hash_token(refresh_token)}"
        refresh_ttl = settings.jwt_refresh_token_expire_days * 24 * 3600
        await self.cache_service.set(refresh_blacklist_key, "1", ttl=refresh_ttl)
        logger.info(f"🚫 [REDIS] Refresh token blacklisted", extra={"ttl": refresh_ttl})

        logger.info(f"✅ [LOGOUT] Logout successful", extra={"user_id": user_id})
