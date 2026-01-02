"""
Security Headers Middleware Unit Tests
보안 헤더 미들웨어 단위 테스트
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi import FastAPI, Request, Response
from starlette.datastructures import URL

from backend.core.middleware.security_headers import SecurityHeadersMiddleware


class TestSecurityHeadersMiddleware:
    """보안 헤더 미들웨어 단위 테스트"""

    @pytest.fixture
    def app(self):
        """테스트용 FastAPI 앱"""
        return FastAPI()

    @pytest.fixture
    def mock_request(self):
        """테스트용 Request 모킹"""
        request = Mock(spec=Request)
        request.url = URL("http://test.example.com/api/test")
        return request

    @pytest.fixture
    def mock_response(self):
        """테스트용 Response 모킹"""
        response = Response(content="test", status_code=200)
        return response

    @pytest.mark.asyncio
    async def test_content_security_policy_header(self, app, mock_request, mock_response):
        """Content-Security-Policy 헤더가 올바르게 추가되는지 테스트"""
        middleware = SecurityHeadersMiddleware(app)

        # Mock call_next to return our mock response
        async def call_next(request):
            return mock_response

        # settings에서 CSP 설정 사용
        with patch("backend.core.middleware.security_headers.settings") as mock_settings:
            mock_settings.enable_security_headers = True
            mock_settings.csp_directives = "default-src 'self'; script-src 'self'"
            mock_settings.x_frame_options = "DENY"
            mock_settings.hsts_max_age = 31536000
            mock_settings.hsts_include_subdomains = True
            mock_settings.hsts_preload = False
            mock_settings.referrer_policy = "strict-origin-when-cross-origin"

            result = await middleware.dispatch(mock_request, call_next)

        assert "Content-Security-Policy" in result.headers
        assert result.headers["Content-Security-Policy"] == "default-src 'self'; script-src 'self'"

    @pytest.mark.asyncio
    async def test_x_content_type_options_header(self, app, mock_request, mock_response):
        """X-Content-Type-Options 헤더가 올바르게 추가되는지 테스트"""
        middleware = SecurityHeadersMiddleware(app)

        async def call_next(request):
            return mock_response

        with patch("backend.core.middleware.security_headers.settings") as mock_settings:
            mock_settings.enable_security_headers = True
            mock_settings.csp_directives = "default-src 'self'"
            mock_settings.x_frame_options = "DENY"
            mock_settings.hsts_max_age = 31536000
            mock_settings.hsts_include_subdomains = True
            mock_settings.hsts_preload = False
            mock_settings.referrer_policy = "strict-origin-when-cross-origin"

            result = await middleware.dispatch(mock_request, call_next)

        assert "X-Content-Type-Options" in result.headers
        assert result.headers["X-Content-Type-Options"] == "nosniff"

    @pytest.mark.asyncio
    async def test_x_frame_options_header_deny(self, app, mock_request, mock_response):
        """X-Frame-Options 헤더가 DENY로 올바르게 추가되는지 테스트"""
        middleware = SecurityHeadersMiddleware(app)

        async def call_next(request):
            return mock_response

        with patch("backend.core.middleware.security_headers.settings") as mock_settings:
            mock_settings.enable_security_headers = True
            mock_settings.csp_directives = "default-src 'self'"
            mock_settings.x_frame_options = "DENY"
            mock_settings.hsts_max_age = 31536000
            mock_settings.hsts_include_subdomains = True
            mock_settings.hsts_preload = False
            mock_settings.referrer_policy = "strict-origin-when-cross-origin"

            result = await middleware.dispatch(mock_request, call_next)

        assert "X-Frame-Options" in result.headers
        assert result.headers["X-Frame-Options"] == "DENY"

    @pytest.mark.asyncio
    async def test_x_frame_options_header_sameorigin(self, app, mock_request, mock_response):
        """X-Frame-Options 헤더가 SAMEORIGIN으로 올바르게 추가되는지 테스트"""
        middleware = SecurityHeadersMiddleware(app)

        async def call_next(request):
            return mock_response

        with patch("backend.core.middleware.security_headers.settings") as mock_settings:
            mock_settings.enable_security_headers = True
            mock_settings.csp_directives = "default-src 'self'"
            mock_settings.x_frame_options = "SAMEORIGIN"
            mock_settings.hsts_max_age = 31536000
            mock_settings.hsts_include_subdomains = True
            mock_settings.hsts_preload = False
            mock_settings.referrer_policy = "strict-origin-when-cross-origin"

            result = await middleware.dispatch(mock_request, call_next)

        assert "X-Frame-Options" in result.headers
        assert result.headers["X-Frame-Options"] == "SAMEORIGIN"

    @pytest.mark.asyncio
    async def test_strict_transport_security_header_https(self, app, mock_response):
        """HTTPS 요청 시 Strict-Transport-Security 헤더가 올바르게 추가되는지 테스트"""
        middleware = SecurityHeadersMiddleware(app)

        # HTTPS 요청 모킹
        https_request = Mock(spec=Request)
        https_request.url = URL("https://test.example.com/api/test")

        async def call_next(request):
            return mock_response

        with patch("backend.core.middleware.security_headers.settings") as mock_settings:
            mock_settings.enable_security_headers = True
            mock_settings.csp_directives = "default-src 'self'"
            mock_settings.x_frame_options = "DENY"
            mock_settings.hsts_max_age = 31536000
            mock_settings.hsts_include_subdomains = True
            mock_settings.hsts_preload = False
            mock_settings.referrer_policy = "strict-origin-when-cross-origin"

            result = await middleware.dispatch(https_request, call_next)

        assert "Strict-Transport-Security" in result.headers
        assert result.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"

    @pytest.mark.asyncio
    async def test_strict_transport_security_header_https_with_preload(self, app, mock_response):
        """HTTPS 요청 시 preload 옵션이 포함된 HSTS 헤더가 올바르게 추가되는지 테스트"""
        middleware = SecurityHeadersMiddleware(app)

        # HTTPS 요청 모킹
        https_request = Mock(spec=Request)
        https_request.url = URL("https://test.example.com/api/test")

        async def call_next(request):
            return mock_response

        with patch("backend.core.middleware.security_headers.settings") as mock_settings:
            mock_settings.enable_security_headers = True
            mock_settings.csp_directives = "default-src 'self'"
            mock_settings.x_frame_options = "DENY"
            mock_settings.hsts_max_age = 31536000
            mock_settings.hsts_include_subdomains = True
            mock_settings.hsts_preload = True
            mock_settings.referrer_policy = "strict-origin-when-cross-origin"

            result = await middleware.dispatch(https_request, call_next)

        assert "Strict-Transport-Security" in result.headers
        assert result.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains; preload"

    @pytest.mark.asyncio
    async def test_strict_transport_security_header_http_not_added(self, app, mock_request, mock_response):
        """HTTP 요청 시 Strict-Transport-Security 헤더가 추가되지 않는지 테스트"""
        middleware = SecurityHeadersMiddleware(app)

        async def call_next(request):
            return mock_response

        with patch("backend.core.middleware.security_headers.settings") as mock_settings:
            mock_settings.enable_security_headers = True
            mock_settings.csp_directives = "default-src 'self'"
            mock_settings.x_frame_options = "DENY"
            mock_settings.hsts_max_age = 31536000
            mock_settings.hsts_include_subdomains = True
            mock_settings.hsts_preload = False
            mock_settings.referrer_policy = "strict-origin-when-cross-origin"

            result = await middleware.dispatch(mock_request, call_next)

        # HTTP 요청이므로 HSTS 헤더가 없어야 함
        assert "Strict-Transport-Security" not in result.headers

    @pytest.mark.asyncio
    async def test_x_xss_protection_header(self, app, mock_request, mock_response):
        """X-XSS-Protection 헤더가 올바르게 추가되는지 테스트"""
        middleware = SecurityHeadersMiddleware(app)

        async def call_next(request):
            return mock_response

        with patch("backend.core.middleware.security_headers.settings") as mock_settings:
            mock_settings.enable_security_headers = True
            mock_settings.csp_directives = "default-src 'self'"
            mock_settings.x_frame_options = "DENY"
            mock_settings.hsts_max_age = 31536000
            mock_settings.hsts_include_subdomains = True
            mock_settings.hsts_preload = False
            mock_settings.referrer_policy = "strict-origin-when-cross-origin"

            result = await middleware.dispatch(mock_request, call_next)

        assert "X-XSS-Protection" in result.headers
        assert result.headers["X-XSS-Protection"] == "1; mode=block"

    @pytest.mark.asyncio
    async def test_referrer_policy_header(self, app, mock_request, mock_response):
        """Referrer-Policy 헤더가 올바르게 추가되는지 테스트"""
        middleware = SecurityHeadersMiddleware(app)

        async def call_next(request):
            return mock_response

        with patch("backend.core.middleware.security_headers.settings") as mock_settings:
            mock_settings.enable_security_headers = True
            mock_settings.csp_directives = "default-src 'self'"
            mock_settings.x_frame_options = "DENY"
            mock_settings.hsts_max_age = 31536000
            mock_settings.hsts_include_subdomains = True
            mock_settings.hsts_preload = False
            mock_settings.referrer_policy = "strict-origin-when-cross-origin"

            result = await middleware.dispatch(mock_request, call_next)

        assert "Referrer-Policy" in result.headers
        assert result.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    @pytest.mark.asyncio
    async def test_referrer_policy_header_custom(self, app, mock_request, mock_response):
        """커스텀 Referrer-Policy 헤더가 올바르게 추가되는지 테스트"""
        middleware = SecurityHeadersMiddleware(app)

        async def call_next(request):
            return mock_response

        with patch("backend.core.middleware.security_headers.settings") as mock_settings:
            mock_settings.enable_security_headers = True
            mock_settings.csp_directives = "default-src 'self'"
            mock_settings.x_frame_options = "DENY"
            mock_settings.hsts_max_age = 31536000
            mock_settings.hsts_include_subdomains = True
            mock_settings.hsts_preload = False
            mock_settings.referrer_policy = "no-referrer"

            result = await middleware.dispatch(mock_request, call_next)

        assert "Referrer-Policy" in result.headers
        assert result.headers["Referrer-Policy"] == "no-referrer"

    @pytest.mark.asyncio
    async def test_security_headers_disabled(self, app, mock_request, mock_response):
        """보안 헤더가 비활성화된 경우 헤더가 추가되지 않는지 테스트"""
        middleware = SecurityHeadersMiddleware(app)

        async def call_next(request):
            return mock_response

        with patch("backend.core.middleware.security_headers.settings") as mock_settings:
            mock_settings.enable_security_headers = False

            result = await middleware.dispatch(mock_request, call_next)

        # 보안 헤더가 비활성화되어 있으므로 헤더가 추가되지 않아야 함
        assert "Content-Security-Policy" not in result.headers
        assert "X-Content-Type-Options" not in result.headers
        assert "X-Frame-Options" not in result.headers
        assert "X-XSS-Protection" not in result.headers
        assert "Referrer-Policy" not in result.headers

    @pytest.mark.asyncio
    async def test_custom_csp_directives(self, app, mock_request, mock_response):
        """커스텀 CSP 지시문이 올바르게 적용되는지 테스트"""
        middleware = SecurityHeadersMiddleware(app)

        async def call_next(request):
            return mock_response

        custom_csp = "default-src 'none'; script-src 'self' https://cdn.example.com; style-src 'self' 'unsafe-inline'"

        with patch("backend.core.middleware.security_headers.settings") as mock_settings:
            mock_settings.enable_security_headers = True
            mock_settings.csp_directives = custom_csp
            mock_settings.x_frame_options = "DENY"
            mock_settings.hsts_max_age = 31536000
            mock_settings.hsts_include_subdomains = True
            mock_settings.hsts_preload = False
            mock_settings.referrer_policy = "strict-origin-when-cross-origin"

            result = await middleware.dispatch(mock_request, call_next)

        assert "Content-Security-Policy" in result.headers
        assert result.headers["Content-Security-Policy"] == custom_csp

    @pytest.mark.asyncio
    async def test_all_headers_together(self, app, mock_response):
        """모든 보안 헤더가 함께 올바르게 추가되는지 테스트 (HTTPS)"""
        middleware = SecurityHeadersMiddleware(app)

        # HTTPS 요청 모킹
        https_request = Mock(spec=Request)
        https_request.url = URL("https://test.example.com/api/test")

        async def call_next(request):
            return mock_response

        with patch("backend.core.middleware.security_headers.settings") as mock_settings:
            mock_settings.enable_security_headers = True
            mock_settings.csp_directives = "default-src 'self'"
            mock_settings.x_frame_options = "DENY"
            mock_settings.hsts_max_age = 31536000
            mock_settings.hsts_include_subdomains = True
            mock_settings.hsts_preload = True
            mock_settings.referrer_policy = "strict-origin-when-cross-origin"

            result = await middleware.dispatch(https_request, call_next)

        # 모든 헤더가 존재하는지 확인
        assert "Content-Security-Policy" in result.headers
        assert "X-Content-Type-Options" in result.headers
        assert "X-Frame-Options" in result.headers
        assert "Strict-Transport-Security" in result.headers
        assert "X-XSS-Protection" in result.headers
        assert "Referrer-Policy" in result.headers

        # 헤더 값 검증
        assert result.headers["Content-Security-Policy"] == "default-src 'self'"
        assert result.headers["X-Content-Type-Options"] == "nosniff"
        assert result.headers["X-Frame-Options"] == "DENY"
        assert result.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains; preload"
        assert result.headers["X-XSS-Protection"] == "1; mode=block"
        assert result.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    @pytest.mark.asyncio
    async def test_hsts_without_subdomains(self, app, mock_response):
        """includeSubDomains 옵션 없이 HSTS 헤더가 올바르게 추가되는지 테스트"""
        middleware = SecurityHeadersMiddleware(app)

        # HTTPS 요청 모킹
        https_request = Mock(spec=Request)
        https_request.url = URL("https://test.example.com/api/test")

        async def call_next(request):
            return mock_response

        with patch("backend.core.middleware.security_headers.settings") as mock_settings:
            mock_settings.enable_security_headers = True
            mock_settings.csp_directives = "default-src 'self'"
            mock_settings.x_frame_options = "DENY"
            mock_settings.hsts_max_age = 31536000
            mock_settings.hsts_include_subdomains = False
            mock_settings.hsts_preload = False
            mock_settings.referrer_policy = "strict-origin-when-cross-origin"

            result = await middleware.dispatch(https_request, call_next)

        assert "Strict-Transport-Security" in result.headers
        assert result.headers["Strict-Transport-Security"] == "max-age=31536000"
        # includeSubDomains가 포함되지 않아야 함
        assert "includeSubDomains" not in result.headers["Strict-Transport-Security"]

    @pytest.mark.asyncio
    async def test_custom_hsts_max_age(self, app, mock_response):
        """커스텀 HSTS max-age가 올바르게 적용되는지 테스트"""
        middleware = SecurityHeadersMiddleware(app)

        # HTTPS 요청 모킹
        https_request = Mock(spec=Request)
        https_request.url = URL("https://test.example.com/api/test")

        async def call_next(request):
            return mock_response

        with patch("backend.core.middleware.security_headers.settings") as mock_settings:
            mock_settings.enable_security_headers = True
            mock_settings.csp_directives = "default-src 'self'"
            mock_settings.x_frame_options = "DENY"
            mock_settings.hsts_max_age = 63072000  # 2 years
            mock_settings.hsts_include_subdomains = False
            mock_settings.hsts_preload = False
            mock_settings.referrer_policy = "strict-origin-when-cross-origin"

            result = await middleware.dispatch(https_request, call_next)

        assert "Strict-Transport-Security" in result.headers
        assert "max-age=63072000" in result.headers["Strict-Transport-Security"]
