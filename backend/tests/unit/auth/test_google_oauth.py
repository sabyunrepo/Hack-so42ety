"""
Google OAuth Provider Unit Tests
Google OAuth 토큰 검증 테스트
"""

import pytest
from unittest.mock import AsyncMock, patch

from backend.core.auth.providers.google_oauth import GoogleOAuthProvider


class TestGoogleOAuthProvider:
    """Google OAuth Provider 단위 테스트"""

    @pytest.mark.asyncio
    async def test_verify_token_valid(self):
        """유효한 Google 토큰 검증 테스트"""
        mock_user_info = {
            "sub": "google_user_123",
            "email": "test@gmail.com",
            "name": "Test User",
            "picture": "https://example.com/photo.jpg",
        }

        with patch(
            "backend.core.auth.providers.google_oauth.id_token.verify_oauth2_token",
            return_value=mock_user_info,
        ):
            result = await GoogleOAuthProvider.verify_token("valid_token")

            assert result is not None
            assert result["sub"] == "google_user_123"
            assert result["email"] == "test@gmail.com"
            assert result["name"] == "Test User"
            assert result["picture"] == "https://example.com/photo.jpg"

    @pytest.mark.asyncio
    async def test_verify_token_invalid(self):
        """잘못된 Google 토큰 검증 테스트"""
        with patch(
            "backend.core.auth.providers.google_oauth.id_token.verify_oauth2_token",
            side_effect=ValueError("Invalid token"),
        ):
            result = await GoogleOAuthProvider.verify_token("invalid_token")

            assert result is None

    @pytest.mark.asyncio
    async def test_verify_token_missing_fields(self):
        """필수 필드 누락된 토큰 테스트"""
        mock_user_info = {
            "sub": "google_user_123",
            "email": "test@gmail.com",
            # name과 picture 누락
        }

        with patch(
            "backend.core.auth.providers.google_oauth.id_token.verify_oauth2_token",
            return_value=mock_user_info,
        ):
            result = await GoogleOAuthProvider.verify_token("token_without_name")

            assert result is not None
            assert result["sub"] == "google_user_123"
            assert result["email"] == "test@gmail.com"
            assert result["name"] == ""  # 기본값
            assert result["picture"] == ""  # 기본값

    @pytest.mark.asyncio
    async def test_verify_token_network_error(self):
        """네트워크 에러 처리 테스트"""
        with patch(
            "backend.core.auth.providers.google_oauth.id_token.verify_oauth2_token",
            side_effect=Exception("Network error"),
        ):
            result = await GoogleOAuthProvider.verify_token("any_token")

            assert result is None

    @pytest.mark.asyncio
    async def test_verify_token_expired(self):
        """만료된 토큰 검증 테스트"""
        with patch(
            "backend.core.auth.providers.google_oauth.id_token.verify_oauth2_token",
            side_effect=ValueError("Token expired"),
        ):
            result = await GoogleOAuthProvider.verify_token("expired_token")

            assert result is None
