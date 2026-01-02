"""
Security Headers Middleware
보안 헤더 설정 미들웨어
"""

from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    보안 헤더를 모든 HTTP 응답에 추가하는 미들웨어

    XSS, 클릭재킹, MIME 타입 혼동 공격 등으로부터 보호
    """

    async def dispatch(self, request: Request, call_next):
        # 응답 처리
        response = await call_next(request)

        # 보안 헤더가 활성화된 경우에만 추가
        if not settings.enable_security_headers:
            return response

        # Content-Security-Policy
        # XSS 공격 방지를 위한 콘텐츠 소스 정책
        response.headers["Content-Security-Policy"] = settings.csp_directives

        # X-Content-Type-Options
        # MIME 타입 스니핑 방지
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options
        # 클릭재킹 공격 방지 (iframe 삽입 차단)
        response.headers["X-Frame-Options"] = settings.x_frame_options

        # Strict-Transport-Security (HSTS)
        # HTTPS 강제 사용 (HTTPS 요청인 경우에만 설정)
        if request.url.scheme == "https":
            hsts_value = f"max-age={settings.hsts_max_age}"
            if settings.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            if settings.hsts_preload:
                hsts_value += "; preload"
            response.headers["Strict-Transport-Security"] = hsts_value

        # X-XSS-Protection
        # 브라우저의 XSS 필터 활성화 (레거시 브라우저 지원)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer-Policy
        # 리퍼러 정보 전송 정책 설정
        response.headers["Referrer-Policy"] = settings.referrer_policy

        return response
