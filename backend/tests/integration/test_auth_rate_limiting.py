"""
Authentication Rate Limiting Integration Tests
인증 엔드포인트 속도 제한 통합 테스트
"""

import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.rate_limiter import get_rate_limiter
from backend.core.config import settings


class TestLoginRateLimiting:
    """로그인 엔드포인트 속도 제한 테스트"""

    @pytest.mark.asyncio
    async def test_login_rate_limit_exceeded(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """로그인 엔드포인트 - 속도 제한 초과 시 429 응답 테스트"""
        # 먼저 회원가입
        register_payload = {"email": "ratelimit@example.com", "password": "password123"}
        await client.post("/api/v1/auth/register", json=register_payload)

        # 속도 제한 초기화
        rate_limiter = get_rate_limiter()
        await rate_limiter.connect()
        await rate_limiter.reset_limit("auth:login:test")

        # 로그인 시도 (정확히 제한 수까지 시도)
        login_payload = {"email": "ratelimit@example.com", "password": "password123"}

        # 제한 내 요청들은 성공해야 함
        for i in range(settings.auth_login_rate_limit):
            response = await client.post("/api/v1/auth/login", json=login_payload)
            assert response.status_code == 200, f"Request {i+1} should succeed"

            # Rate limit 헤더 확인
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers

            assert response.headers["X-RateLimit-Limit"] == str(settings.auth_login_rate_limit)

        # 제한 초과 요청 - 429 응답
        response = await client.post("/api/v1/auth/login", json=login_payload)

        assert response.status_code == 429
        assert "Retry-After" in response.headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert response.headers["X-RateLimit-Remaining"] == "0"

        data = response.json()
        assert "detail" in data
        assert "retry_after" in data["details"]

    @pytest.mark.asyncio
    async def test_login_rate_limit_headers_present(self, client: AsyncClient, db_session: AsyncSession):
        """로그인 엔드포인트 - Rate limit 헤더 존재 확인"""
        # 회원가입
        await client.post(
            "/api/v1/auth/register",
            json={"email": "headers@example.com", "password": "password123"}
        )

        # 속도 제한 초기화
        rate_limiter = get_rate_limiter()
        await rate_limiter.connect()
        await rate_limiter.reset_limit("auth:login:test")

        # 로그인 요청
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "headers@example.com", "password": "password123"}
        )

        assert response.status_code == 200

        # Rate limit 헤더 확인
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

        # 값 검증
        assert int(response.headers["X-RateLimit-Limit"]) == settings.auth_login_rate_limit
        assert int(response.headers["X-RateLimit-Remaining"]) >= 0
        assert int(response.headers["X-RateLimit-Reset"]) > 0

    @pytest.mark.asyncio
    async def test_login_rate_limit_reset_after_window(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """로그인 엔드포인트 - 윈도우 만료 후 리셋 테스트"""
        # 회원가입
        await client.post(
            "/api/v1/auth/register",
            json={"email": "reset@example.com", "password": "password123"}
        )

        # 속도 제한 초기화
        rate_limiter = get_rate_limiter()
        await rate_limiter.connect()
        await rate_limiter.reset_limit("auth:login:test")

        # 제한까지 요청
        login_payload = {"email": "reset@example.com", "password": "password123"}
        for _ in range(settings.auth_login_rate_limit):
            response = await client.post("/api/v1/auth/login", json=login_payload)
            assert response.status_code == 200

        # 제한 초과 확인
        response = await client.post("/api/v1/auth/login", json=login_payload)
        assert response.status_code == 429

        # 수동으로 속도 제한 리셋 (실제 시간 대기 대신)
        await rate_limiter.reset_limit("auth:login:test")

        # 리셋 후 다시 요청 가능
        response = await client.post("/api/v1/auth/login", json=login_payload)
        assert response.status_code == 200
        assert int(response.headers["X-RateLimit-Remaining"]) == settings.auth_login_rate_limit - 1


class TestRegisterRateLimiting:
    """회원가입 엔드포인트 속도 제한 테스트"""

    @pytest.mark.asyncio
    async def test_register_rate_limit_exceeded(self, client: AsyncClient):
        """회원가입 엔드포인트 - 속도 제한 초과 시 429 응답 테스트"""
        # 속도 제한 초기화
        rate_limiter = get_rate_limiter()
        await rate_limiter.connect()
        await rate_limiter.reset_limit("auth:register:test")

        # 제한 내 요청
        for i in range(settings.auth_register_rate_limit):
            response = await client.post(
                "/api/v1/auth/register",
                json={"email": f"user{i}@example.com", "password": "password123"}
            )
            assert response.status_code == 201, f"Request {i+1} should succeed"

            # Rate limit 헤더 확인
            assert "X-RateLimit-Limit" in response.headers
            assert response.headers["X-RateLimit-Limit"] == str(settings.auth_register_rate_limit)

        # 제한 초과 요청
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "exceeded@example.com", "password": "password123"}
        )

        assert response.status_code == 429
        assert "Retry-After" in response.headers
        assert response.headers["X-RateLimit-Remaining"] == "0"

    @pytest.mark.asyncio
    async def test_register_rate_limit_headers(self, client: AsyncClient):
        """회원가입 엔드포인트 - Rate limit 헤더 존재 확인"""
        # 속도 제한 초기화
        rate_limiter = get_rate_limiter()
        await rate_limiter.connect()
        await rate_limiter.reset_limit("auth:register:test")

        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "newuser@example.com", "password": "password123"}
        )

        assert response.status_code == 201

        # Rate limit 헤더 확인
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

        assert int(response.headers["X-RateLimit-Limit"]) == settings.auth_register_rate_limit
        assert int(response.headers["X-RateLimit-Remaining"]) >= 0


class TestGoogleOAuthRateLimiting:
    """Google OAuth 엔드포인트 속도 제한 테스트"""

    @pytest.mark.asyncio
    async def test_google_oauth_rate_limit_exceeded(self, client: AsyncClient):
        """Google OAuth 엔드포인트 - 속도 제한 초과 시 429 응답 테스트"""
        from unittest.mock import patch

        # 속도 제한 초기화
        rate_limiter = get_rate_limiter()
        await rate_limiter.connect()
        await rate_limiter.reset_limit("auth:google:test")

        # Mock Google token verification
        mock_user_info = {
            "sub": "google_123",
            "email": "google@gmail.com",
            "name": "Google User",
        }

        with patch(
            "backend.core.auth.providers.google_oauth.id_token.verify_oauth2_token",
            return_value=mock_user_info,
        ):
            # 제한 내 요청
            for i in range(settings.auth_google_rate_limit):
                response = await client.post(
                    "/api/v1/auth/google",
                    json={"token": f"valid_token_{i}"}
                )
                assert response.status_code == 200, f"Request {i+1} should succeed"

                # Rate limit 헤더 확인
                assert "X-RateLimit-Limit" in response.headers
                assert response.headers["X-RateLimit-Limit"] == str(settings.auth_google_rate_limit)

            # 제한 초과 요청
            response = await client.post(
                "/api/v1/auth/google",
                json={"token": "exceeded_token"}
            )

            assert response.status_code == 429
            assert "Retry-After" in response.headers
            assert response.headers["X-RateLimit-Remaining"] == "0"

    @pytest.mark.asyncio
    async def test_google_oauth_rate_limit_headers(self, client: AsyncClient):
        """Google OAuth 엔드포인트 - Rate limit 헤더 존재 확인"""
        from unittest.mock import patch

        # 속도 제한 초기화
        rate_limiter = get_rate_limiter()
        await rate_limiter.connect()
        await rate_limiter.reset_limit("auth:google:test")

        mock_user_info = {
            "sub": "google_456",
            "email": "test@gmail.com",
            "name": "Test User",
        }

        with patch(
            "backend.core.auth.providers.google_oauth.id_token.verify_oauth2_token",
            return_value=mock_user_info,
        ):
            response = await client.post(
                "/api/v1/auth/google",
                json={"token": "valid_token"}
            )

            assert response.status_code == 200

            # Rate limit 헤더 확인
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers

            assert int(response.headers["X-RateLimit-Limit"]) == settings.auth_google_rate_limit


class TestRefreshTokenRateLimiting:
    """토큰 갱신 엔드포인트 속도 제한 테스트"""

    @pytest.mark.asyncio
    async def test_refresh_rate_limit_exceeded(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """토큰 갱신 엔드포인트 - 속도 제한 초과 시 429 응답 테스트"""
        # 회원가입으로 refresh token 획득
        register_response = await client.post(
            "/api/v1/auth/register",
            json={"email": "refresh@example.com", "password": "password123"}
        )
        refresh_token = register_response.json()["refresh_token"]

        # 속도 제한 초기화
        rate_limiter = get_rate_limiter()
        await rate_limiter.connect()
        await rate_limiter.reset_limit("auth:refresh:test")

        # 제한 내 요청
        for i in range(settings.auth_refresh_rate_limit):
            response = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh_token}
            )
            assert response.status_code == 200, f"Request {i+1} should succeed"

            # Rate limit 헤더 확인
            assert "X-RateLimit-Limit" in response.headers
            assert response.headers["X-RateLimit-Limit"] == str(settings.auth_refresh_rate_limit)

        # 제한 초과 요청
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert response.status_code == 429
        assert "Retry-After" in response.headers
        assert response.headers["X-RateLimit-Remaining"] == "0"

    @pytest.mark.asyncio
    async def test_refresh_rate_limit_headers(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """토큰 갱신 엔드포인트 - Rate limit 헤더 존재 확인"""
        # 회원가입
        register_response = await client.post(
            "/api/v1/auth/register",
            json={"email": "refreshheaders@example.com", "password": "password123"}
        )
        refresh_token = register_response.json()["refresh_token"]

        # 속도 제한 초기화
        rate_limiter = get_rate_limiter()
        await rate_limiter.connect()
        await rate_limiter.reset_limit("auth:refresh:test")

        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert response.status_code == 200

        # Rate limit 헤더 확인
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

        assert int(response.headers["X-RateLimit-Limit"]) == settings.auth_refresh_rate_limit


class TestRateLimitIpIsolation:
    """IP 격리 테스트 - 서로 다른 IP는 독립적인 제한을 가져야 함"""

    @pytest.mark.asyncio
    async def test_different_ips_have_separate_limits(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """서로 다른 IP는 독립적인 속도 제한을 가져야 함"""
        # 회원가입
        await client.post(
            "/api/v1/auth/register",
            json={"email": "iplimit@example.com", "password": "password123"}
        )

        # 속도 제한 초기화
        rate_limiter = get_rate_limiter()
        await rate_limiter.connect()
        await rate_limiter.reset_limit("auth:login:192.168.1.1")
        await rate_limiter.reset_limit("auth:login:192.168.1.2")

        login_payload = {"email": "iplimit@example.com", "password": "password123"}

        # IP 1에서 제한까지 요청
        for _ in range(settings.auth_login_rate_limit):
            response = await client.post(
                "/api/v1/auth/login",
                json=login_payload,
                headers={"X-Forwarded-For": "192.168.1.1"}
            )
            assert response.status_code == 200

        # IP 1에서 제한 초과
        response = await client.post(
            "/api/v1/auth/login",
            json=login_payload,
            headers={"X-Forwarded-For": "192.168.1.1"}
        )
        assert response.status_code == 429

        # IP 2에서는 여전히 요청 가능 (별도의 제한)
        response = await client.post(
            "/api/v1/auth/login",
            json=login_payload,
            headers={"X-Forwarded-For": "192.168.1.2"}
        )
        assert response.status_code == 200

        # IP 2는 full limit을 가지고 있어야 함
        remaining = int(response.headers["X-RateLimit-Remaining"])
        assert remaining == settings.auth_login_rate_limit - 1

    @pytest.mark.asyncio
    async def test_x_real_ip_header_support(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """X-Real-IP 헤더 지원 테스트 (Nginx 등)"""
        # 회원가입
        await client.post(
            "/api/v1/auth/register",
            json={"email": "realip@example.com", "password": "password123"}
        )

        # 속도 제한 초기화
        rate_limiter = get_rate_limiter()
        await rate_limiter.connect()
        await rate_limiter.reset_limit("auth:login:10.0.0.1")

        login_payload = {"email": "realip@example.com", "password": "password123"}

        # X-Real-IP로 요청
        response = await client.post(
            "/api/v1/auth/login",
            json=login_payload,
            headers={"X-Real-IP": "10.0.0.1"}
        )

        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers


class TestRateLimitWithRateLimitDisabled:
    """속도 제한 비활성화 테스트"""

    @pytest.mark.asyncio
    async def test_rate_limit_disabled(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """RATE_LIMIT_ENABLED=False일 때 속도 제한 우회"""
        # 원래 설정 저장
        original_enabled = settings.rate_limit_enabled

        try:
            # 속도 제한 비활성화
            settings.rate_limit_enabled = False

            # 회원가입
            await client.post(
                "/api/v1/auth/register",
                json={"email": "disabled@example.com", "password": "password123"}
            )

            # 제한을 훨씬 초과하는 요청도 모두 성공해야 함
            login_payload = {"email": "disabled@example.com", "password": "password123"}
            for i in range(settings.auth_login_rate_limit + 10):
                response = await client.post("/api/v1/auth/login", json=login_payload)
                assert response.status_code == 200, f"Request {i+1} should succeed when rate limiting is disabled"

        finally:
            # 설정 복원
            settings.rate_limit_enabled = original_enabled
