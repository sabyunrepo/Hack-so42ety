"""
Auth Service
인증 비즈니스 로직
"""

from typing import Optional, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.auth.jwt_manager import JWTManager
from ...core.auth.providers.credentials import CredentialsAuthProvider
from ...core.auth.providers.google_oauth import GoogleOAuthProvider
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
        cache_service: Any,  # CacheService (Circular import avoidance or use generic)
    ):
        """
        Args:
            user_repo: 사용자 레포지토리
            credentials_provider: 비밀번호 인증 제공자
            google_oauth_provider: Google OAuth 제공자
            jwt_manager: JWT 토큰 관리자
            db: 비동기 데이터베이스 세션
            cache_service: 캐시 서비스 (Redis)
        """
        self.user_repo = user_repo
        self.credentials_provider = credentials_provider
        self.google_oauth_provider = google_oauth_provider
        self.jwt_manager = jwt_manager
        self.db = db
        self.cache_service = cache_service

    async def _store_refresh_token(self, refresh_token: str, user_id: str):
        """Refresh Token 저장 (RTR) - Helper"""
        payload = self.jwt_manager.decode_token(refresh_token)
        if "jti" not in payload:
            return # Should not happen if generated correctly
        
        jti = payload["jti"]
        # TTL: settings.jwt_refresh_token_expire_days (days) -> convert to seconds
        ttl = getattr(self.jwt_manager, "refresh_token_expire_seconds", 7 * 24 * 60 * 60)
        # We can calculate based on exp - now, but using fixed setting is safer/easier
        # Actually better to use exp from token
        exp_timestamp = payload.get("exp")
        if exp_timestamp:
            import time
            current_timestamp = time.time()
            ttl = int(exp_timestamp - current_timestamp)
        else:
             from ..core.config import settings
             ttl = settings.jwt_refresh_token_expire_days * 24 * 60 * 60

        if ttl > 0:
            await self.cache_service.set(f"refresh_token:{jti}", str(user_id), ttl=ttl)

    async def register(self, email: str, password: str) -> Tuple[User, str, str]:
        """
        회원가입
        """
        # ... (Previous validation logic)
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

        # RTR: Redis 저장
        await self._store_refresh_token(refresh_token, str(user.id))

        return user, access_token, refresh_token

    async def login(self, email: str, password: str) -> Tuple[User, str, str]:
        """
        로그인
        """
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

        # RTR: Redis 저장
        await self._store_refresh_token(refresh_token, str(user.id))

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
        
        # RTR: Redis 저장
        await self._store_refresh_token(refresh_token, str(user.id))

        return user, access_token, refresh_token

    async def refresh_access_token(self, refresh_token: str) -> Tuple[str, str]:
        """
        Access Token 갱신 (RTR 적용)
        
        Returns:
            Tuple[str, str]: (New Access Token, New Refresh Token)
        """
        # 1. 서명 검증
        payload = self.jwt_manager.verify_token(refresh_token, token_type="refresh")

        user_id = payload["sub"]
        email = payload.get("email")
        jti = payload.get("jti")

        # 2. Redis 검증 (RTR)
        if jti:
            # JTI가 있는 경우 (RTR 적용 토큰)
            stored_user_id = await self.cache_service.get(f"refresh_token:{jti}")
            
            if not stored_user_id:
                # Key가 없음 -> 만료되었거나 이미 사용됨(탈취 의심)
                # 보안상 로그아웃 처리 등을 할 수 있음
                raise InvalidRefreshTokenException()
            
            # 3. 토큰 사용 처리 (Delete Old)
            await self.cache_service.delete(f"refresh_token:{jti}")
        
        # legacy token without jti is accepted once but rotates to new system
        
        # 4. 새 토큰 발급 (Rotate)
        new_access_token = self.jwt_manager.create_access_token(
            data={"sub": user_id, "email": email}
        )
        # 새 Refresh Token (새 JTI 포함)
        new_refresh_token = self.jwt_manager.create_refresh_token(
            data={"sub": user_id, "email": email}
        )
        
        # 5. 새 토큰 저장
        await self._store_refresh_token(new_refresh_token, user_id)

        return new_access_token, new_refresh_token
    
    async def logout(self, refresh_token: str) -> None:
        """
        로그아웃 (Refresh Token 무효화)
        """
        payload = self.jwt_manager.decode_token(refresh_token)
        if "jti" in payload:
            jti = payload["jti"]
            await self.cache_service.delete(f"refresh_token:{jti}")
