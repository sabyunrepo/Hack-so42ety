"""
Auth Service
인증 비즈니스 로직
"""

from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.auth.jwt_manager import JWTManager
from ...core.auth.providers.credentials import CredentialsAuthProvider
from ...core.auth.providers.google_oauth import GoogleOAuthProvider
from ...domain.models.user import User
from ...domain.repositories.user_repository import UserRepository
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
    """

    def __init__(self, db: AsyncSession):
        """
        Args:
            db: 비동기 데이터베이스 세션
        """
        self.db = db
        self.user_repo = UserRepository(db)
        self.credentials_provider = CredentialsAuthProvider()
        self.google_oauth_provider = GoogleOAuthProvider()
        self.jwt_manager = JWTManager()

    async def register(self, email: str, password: str) -> Tuple[User, str, str]:
        """
        회원가입

        Args:
            email: 사용자 이메일
            password: 평문 비밀번호

        Returns:
            Tuple[User, str, str]: (사용자, Access Token, Refresh Token)

        Raises:
            EmailAlreadyExistsException: 이미 존재하는 이메일
        """
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

        return user, access_token, refresh_token

    async def login(self, email: str, password: str) -> Tuple[User, str, str]:
        """
        로그인

        Args:
            email: 사용자 이메일
            password: 평문 비밀번호

        Returns:
            Tuple[User, str, str]: (사용자, Access Token, Refresh Token)

        Raises:
            InvalidCredentialsException: 인증 실패
            OAuthUserOnlyException: OAuth 전용 사용자
        """
        # 사용자 조회
        user = await self.user_repo.get_by_email(email)

        if user is None:
            raise InvalidCredentialsException()

        # OAuth 전용 사용자 체크 (Google, Kakao 등 소셜 로그인 사용자)
        if user.oauth_provider is not None:
            raise OAuthUserOnlyException(user.oauth_provider)

        # 비밀번호 해시가 없는 경우 (OAuth 사용자)
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

        return user, access_token, refresh_token

    async def google_oauth_login(self, google_token: str) -> Tuple[User, str, str]:
        """
        Google OAuth 로그인

        Args:
            google_token: Google ID Token

        Returns:
            Tuple[User, str, str]: (사용자, Access Token, Refresh Token)

        Raises:
            InvalidGoogleTokenException: 토큰 검증 실패
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

        return user, access_token, refresh_token

    async def refresh_access_token(self, refresh_token: str) -> str:
        """
        Access Token 갱신

        Args:
            refresh_token: Refresh Token

        Returns:
            str: 새로운 Access Token

        Raises:
            InvalidRefreshTokenException: Refresh Token 검증 실패
        """
        # Refresh Token 검증
        payload = self.jwt_manager.verify_token(refresh_token, token_type="refresh")

        if payload is None:
            raise InvalidRefreshTokenException()

        # 새로운 Access Token 생성
        access_token = self.jwt_manager.create_access_token(
            data={"sub": payload["sub"], "email": payload.get("email")}
        )

        return access_token
