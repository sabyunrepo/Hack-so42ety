"""
JWT Manager Unit Tests
JWT 토큰 생성 및 검증 테스트
"""

import pytest
from datetime import timedelta

from backend.core.auth.jwt_manager import JWTManager


class TestJWTManager:
    """JWT Manager 단위 테스트"""

    def test_create_access_token(self):
        """Access Token 생성 테스트"""
        data = {"sub": "user123", "email": "test@example.com"}
        token = JWTManager.create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self):
        """Refresh Token 생성 테스트"""
        data = {"sub": "user123", "email": "test@example.com"}
        token = JWTManager.create_refresh_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_valid_token(self):
        """유효한 토큰 디코딩 테스트"""
        data = {"sub": "user123", "email": "test@example.com"}
        token = JWTManager.create_access_token(data)

        payload = JWTManager.decode_token(token)

        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"

    def test_decode_invalid_token(self):
        """잘못된 토큰 디코딩 테스트"""
        invalid_token = "invalid.token.here"
        payload = JWTManager.decode_token(invalid_token)

        assert payload is None

    def test_verify_access_token(self):
        """Access Token 검증 테스트"""
        data = {"sub": "user123", "email": "test@example.com"}
        token = JWTManager.create_access_token(data)

        payload = JWTManager.verify_token(token, token_type="access")

        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["type"] == "access"

    def test_verify_refresh_token(self):
        """Refresh Token 검증 테스트"""
        data = {"sub": "user123", "email": "test@example.com"}
        token = JWTManager.create_refresh_token(data)

        payload = JWTManager.verify_token(token, token_type="refresh")

        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["type"] == "refresh"

    def test_verify_token_type_mismatch(self):
        """토큰 타입 불일치 테스트"""
        data = {"sub": "user123", "email": "test@example.com"}
        access_token = JWTManager.create_access_token(data)

        # Access Token을 Refresh로 검증 시도
        payload = JWTManager.verify_token(access_token, token_type="refresh")

        assert payload is None

    def test_custom_expiration(self):
        """커스텀 만료 시간 테스트"""
        data = {"sub": "user123", "email": "test@example.com"}
        custom_expire = timedelta(minutes=30)

        token = JWTManager.create_access_token(data, expires_delta=custom_expire)
        payload = JWTManager.decode_token(token)

        assert payload is not None
        assert "exp" in payload
