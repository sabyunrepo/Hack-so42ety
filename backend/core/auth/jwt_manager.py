"""
JWT Manager
JWT 토큰 생성 및 검증
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import uuid
from jose import JWTError, jwt, ExpiredSignatureError

from ..config import settings
from .exceptions import TokenExpiredException, InvalidTokenException


class JWTManager:
    """
    JWT 토큰 관리자

    Access Token과 Refresh Token 생성/검증 담당
    """

    @staticmethod
    def create_access_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Access Token 생성

        Args:
            data: JWT payload에 포함할 데이터 (user_id, email 등)
            expires_delta: 만료 시간 (기본값: 설정에서 가져옴)

        Returns:
            str: 생성된 JWT 토큰
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now() + expires_delta
        else:
            expire = datetime.now() + timedelta(
                minutes=settings.jwt_access_token_expire_minutes
            )

        to_encode.update({"exp": expire, "type": "access"})

        encoded_jwt = jwt.encode(
            to_encode,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

        return encoded_jwt

    @staticmethod
    def create_refresh_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Refresh Token 생성

        Args:
            data: JWT payload에 포함할 데이터
            expires_delta: 만료 시간 (기본값: 설정에서 가져옴)

        Returns:
            str: 생성된 Refresh 토큰
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now() + expires_delta
        else:
            expire = datetime.now() + timedelta(
                days=settings.jwt_refresh_token_expire_days
            )

        if "jti" not in to_encode:
            to_encode["jti"] = str(uuid.uuid4())

        to_encode.update({"exp": expire, "type": "refresh"})

        encoded_jwt = jwt.encode(
            to_encode,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
        """
        JWT 토큰 디코딩 및 검증

        Args:
            token: JWT 토큰 문자열

        Returns:
            Optional[Dict[str, Any]]: 디코딩된 payload 또는 None (검증 실패 시)
        """
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            return payload
        except ExpiredSignatureError:
            raise TokenExpiredException()
        except JWTError:
            raise InvalidTokenException()

    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """
        토큰 타입 검증 포함 디코딩

        Args:
            token: JWT 토큰 문자열
            token_type: 토큰 타입 ("access" 또는 "refresh")

        Returns:
            Optional[Dict[str, Any]]: 검증된 payload 또는 None
        """
        payload = JWTManager.decode_token(token)

        # 토큰 타입 검증
        if payload.get("type") != token_type:
            raise InvalidTokenException()

        return payload
