"""
Security Headers Integration Tests
보안 헤더 통합 테스트 (실제 HTTP 응답 확인)
"""

import pytest
from httpx import AsyncClient


class TestSecurityHeadersIntegration:
    """보안 헤더 통합 테스트"""

    @pytest.mark.asyncio
    async def test_security_headers_on_health_endpoint(self, client: AsyncClient):
        """헬스 체크 엔드포인트에서 보안 헤더가 올바르게 적용되는지 테스트"""
        response = await client.get("/health")

        assert response.status_code == 200

        # Content-Security-Policy 헤더 확인
        assert "Content-Security-Policy" in response.headers
        assert response.headers["Content-Security-Policy"]

        # X-Content-Type-Options 헤더 확인
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

        # X-Frame-Options 헤더 확인
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] in ["DENY", "SAMEORIGIN"]

        # X-XSS-Protection 헤더 확인
        assert "X-XSS-Protection" in response.headers
        assert response.headers["X-XSS-Protection"] == "1; mode=block"

        # Referrer-Policy 헤더 확인
        assert "Referrer-Policy" in response.headers
        assert response.headers["Referrer-Policy"]

    @pytest.mark.asyncio
    async def test_security_headers_on_root_endpoint(self, client: AsyncClient):
        """루트 엔드포인트에서 보안 헤더가 올바르게 적용되는지 테스트"""
        response = await client.get("/")

        assert response.status_code == 200

        # Content-Security-Policy 헤더 확인
        assert "Content-Security-Policy" in response.headers
        assert response.headers["Content-Security-Policy"]

        # X-Content-Type-Options 헤더 확인
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

        # X-Frame-Options 헤더 확인
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] in ["DENY", "SAMEORIGIN"]

        # X-XSS-Protection 헤더 확인
        assert "X-XSS-Protection" in response.headers
        assert response.headers["X-XSS-Protection"] == "1; mode=block"

        # Referrer-Policy 헤더 확인
        assert "Referrer-Policy" in response.headers
        assert response.headers["Referrer-Policy"]

    @pytest.mark.asyncio
    async def test_all_expected_security_headers_present(self, client: AsyncClient):
        """모든 예상되는 보안 헤더가 응답에 존재하는지 확인"""
        response = await client.get("/health")

        assert response.status_code == 200

        # 모든 필수 보안 헤더 목록
        expected_headers = [
            "Content-Security-Policy",
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Referrer-Policy",
        ]

        # 모든 헤더가 응답에 존재하는지 확인
        for header in expected_headers:
            assert header in response.headers, f"Expected header '{header}' not found in response"

    @pytest.mark.asyncio
    async def test_security_headers_values(self, client: AsyncClient):
        """보안 헤더의 값이 올바르게 설정되어 있는지 확인"""
        response = await client.get("/health")

        assert response.status_code == 200

        # X-Content-Type-Options는 항상 nosniff
        assert response.headers["X-Content-Type-Options"] == "nosniff"

        # X-XSS-Protection은 항상 '1; mode=block'
        assert response.headers["X-XSS-Protection"] == "1; mode=block"

        # X-Frame-Options는 DENY 또는 SAMEORIGIN
        assert response.headers["X-Frame-Options"] in ["DENY", "SAMEORIGIN"]

        # Content-Security-Policy는 비어있지 않아야 함
        assert len(response.headers["Content-Security-Policy"]) > 0

        # Referrer-Policy는 비어있지 않아야 함
        assert len(response.headers["Referrer-Policy"]) > 0

    @pytest.mark.asyncio
    async def test_hsts_header_not_present_for_http(self, client: AsyncClient):
        """HTTP 요청에서는 Strict-Transport-Security 헤더가 없어야 함"""
        response = await client.get("/health")

        assert response.status_code == 200

        # HTTP 요청이므로 HSTS 헤더가 없어야 함
        # (테스트 클라이언트는 기본적으로 HTTP 사용)
        assert "Strict-Transport-Security" not in response.headers
