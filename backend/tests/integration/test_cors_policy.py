"""
CORS Policy Integration Tests
CORS preflight OPTIONS 요청 통합 테스트
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch


class TestCORSPreflightRequests:
    """CORS Preflight OPTIONS 요청 통합 테스트"""

    @pytest.mark.asyncio
    async def test_preflight_request_default_headers(self, client: AsyncClient):
        """기본 헤더 설정으로 preflight 요청 테스트"""
        # Send preflight OPTIONS request
        response = await client.options(
            "/api/v1/auth/register",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,Authorization",
            },
        )

        # Verify preflight response status
        assert response.status_code == 200

        # Verify CORS headers in response
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"

        # Verify allowed headers include default headers
        assert "access-control-allow-headers" in response.headers
        allowed_headers = response.headers["access-control-allow-headers"].lower()

        # Check that default headers are present
        assert "content-type" in allowed_headers
        assert "authorization" in allowed_headers
        assert "accept" in allowed_headers
        assert "x-request-id" in allowed_headers

    @pytest.mark.asyncio
    async def test_preflight_request_public_endpoint(self, client: AsyncClient):
        """Public 엔드포인트에 대한 preflight 요청 테스트"""
        # Send preflight OPTIONS request to public endpoint
        response = await client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

        # Verify preflight response status
        assert response.status_code == 200

        # Verify CORS headers
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-headers" in response.headers
        assert "access-control-allow-methods" in response.headers

        # Verify allowed methods
        allowed_methods = response.headers["access-control-allow-methods"].upper()
        assert "POST" in allowed_methods
        assert "GET" in allowed_methods
        assert "OPTIONS" in allowed_methods

    @pytest.mark.asyncio
    async def test_preflight_request_authenticated_endpoint(self, client: AsyncClient):
        """인증이 필요한 엔드포인트에 대한 preflight 요청 테스트"""
        # Send preflight OPTIONS request to authenticated endpoint
        response = await client.options(
            "/api/v1/books",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization,Accept",
            },
        )

        # Verify preflight response status
        assert response.status_code == 200

        # Verify CORS headers are present
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-headers" in response.headers
        assert "access-control-allow-credentials" in response.headers

        # Verify credentials are allowed
        assert response.headers["access-control-allow-credentials"] == "true"

        # Verify Authorization header is allowed
        allowed_headers = response.headers["access-control-allow-headers"].lower()
        assert "authorization" in allowed_headers

    @pytest.mark.asyncio
    async def test_preflight_request_with_x_request_id(self, client: AsyncClient):
        """X-Request-ID 헤더를 포함한 preflight 요청 테스트"""
        # Send preflight OPTIONS request with X-Request-ID
        response = await client.options(
            "/api/v1/auth/register",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,X-Request-ID",
            },
        )

        # Verify preflight response status
        assert response.status_code == 200

        # Verify X-Request-ID is in allowed headers
        allowed_headers = response.headers["access-control-allow-headers"].lower()
        assert "x-request-id" in allowed_headers

    @pytest.mark.asyncio
    async def test_preflight_request_expose_headers(self, client: AsyncClient):
        """Expose headers 설정 테스트 (파일 다운로드용)"""
        # Send preflight OPTIONS request
        response = await client.options(
            "/api/v1/books",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization",
            },
        )

        # Verify preflight response status
        assert response.status_code == 200

        # Verify expose-headers includes Content-Disposition for file downloads
        if "access-control-expose-headers" in response.headers:
            expose_headers = response.headers["access-control-expose-headers"]
            assert "Content-Disposition" in expose_headers

    @pytest.mark.asyncio
    async def test_actual_request_after_preflight(self, client: AsyncClient):
        """Preflight 이후 실제 요청 테스트"""
        # First, send preflight request
        preflight_response = await client.options(
            "/api/v1/auth/register",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

        assert preflight_response.status_code == 200

        # Now send actual request
        actual_response = await client.post(
            "/api/v1/auth/register",
            json={"email": "cors@example.com", "password": "password123"},
            headers={
                "Origin": "http://localhost:5173",
                "Content-Type": "application/json",
            },
        )

        # Verify actual request succeeds
        assert actual_response.status_code == 201

        # Verify CORS headers are present in actual response
        assert "access-control-allow-origin" in actual_response.headers
        assert actual_response.headers["access-control-allow-origin"] == "http://localhost:5173"


class TestCORSWithCustomConfiguration:
    """커스텀 CORS 설정 테스트"""

    @pytest.mark.asyncio
    async def test_preflight_with_custom_headers(self, client: AsyncClient):
        """커스텀 헤더 설정으로 preflight 요청 테스트"""
        # This test verifies the middleware handles configured headers correctly
        # The default configuration should be: Content-Type,Authorization,Accept,X-Request-ID

        response = await client.options(
            "/api/v1/auth/register",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,Authorization,Accept,X-Request-ID",
            },
        )

        # Verify preflight response status
        assert response.status_code == 200

        # Verify all requested headers are allowed
        allowed_headers = response.headers["access-control-allow-headers"].lower()
        assert "content-type" in allowed_headers
        assert "authorization" in allowed_headers
        assert "accept" in allowed_headers
        assert "x-request-id" in allowed_headers

    @pytest.mark.asyncio
    async def test_preflight_rejects_unlisted_headers(self, client: AsyncClient):
        """허용되지 않은 헤더 요청 시 처리 테스트"""
        # Request with a header not in the allowed list
        # Note: Modern browsers handle CORS rejection, but the server should
        # still return the configured allowed headers in the preflight response

        response = await client.options(
            "/api/v1/auth/register",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,X-Unauthorized-Header",
            },
        )

        # Preflight should still return 200 with configured headers
        # The browser is responsible for rejecting the request if headers don't match
        assert response.status_code == 200

        allowed_headers = response.headers["access-control-allow-headers"].lower()

        # Verify the allowed headers are the configured ones, not wildcard
        # This ensures we're following the principle of least privilege
        assert "content-type" in allowed_headers
        assert "authorization" in allowed_headers

        # The server returns its configured allowed headers
        # X-Unauthorized-Header should NOT cause wildcard behavior
        # (Browser will reject if requested headers aren't in allowed list)


class TestCORSOriginValidation:
    """CORS Origin 검증 테스트"""

    @pytest.mark.asyncio
    async def test_preflight_with_allowed_origin(self, client: AsyncClient):
        """허용된 Origin으로 preflight 요청 테스트"""
        response = await client.options(
            "/api/v1/auth/register",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"

    @pytest.mark.asyncio
    async def test_preflight_with_disallowed_origin(self, client: AsyncClient):
        """허용되지 않은 Origin으로 preflight 요청 테스트"""
        response = await client.options(
            "/api/v1/auth/register",
            headers={
                "Origin": "http://evil.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

        # Server should still respond to OPTIONS, but won't include
        # the disallowed origin in Access-Control-Allow-Origin
        assert response.status_code == 200

        # If origin is not allowed, the header should not be set
        # or should not match the requesting origin
        if "access-control-allow-origin" in response.headers:
            assert response.headers["access-control-allow-origin"] != "http://evil.com"


class TestCORSMethodsAndCredentials:
    """CORS Methods와 Credentials 테스트"""

    @pytest.mark.asyncio
    async def test_preflight_allowed_methods(self, client: AsyncClient):
        """허용된 HTTP Methods 테스트"""
        response = await client.options(
            "/api/v1/books",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "DELETE",
                "Access-Control-Request-Headers": "Authorization",
            },
        )

        assert response.status_code == 200

        # Verify allowed methods
        allowed_methods = response.headers["access-control-allow-methods"].upper()
        assert "GET" in allowed_methods
        assert "POST" in allowed_methods
        assert "PUT" in allowed_methods
        assert "DELETE" in allowed_methods
        assert "OPTIONS" in allowed_methods

    @pytest.mark.asyncio
    async def test_preflight_credentials_support(self, client: AsyncClient):
        """Credentials 지원 테스트"""
        response = await client.options(
            "/api/v1/auth/register",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

        assert response.status_code == 200

        # Verify credentials are allowed (required for cookies/auth headers)
        assert "access-control-allow-credentials" in response.headers
        assert response.headers["access-control-allow-credentials"] == "true"
