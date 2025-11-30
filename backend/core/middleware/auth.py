"""
Authentication Middleware
사용자 컨텍스트 설정 미들웨어
"""

from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class UserContextMiddleware(BaseHTTPMiddleware):
    """
    사용자 컨텍스트를 Request State에 저장하는 미들웨어

    PostgreSQL Row Level Security (RLS) 정책에서 사용할
    current_user_id를 설정
    """

    async def dispatch(self, request: Request, call_next):
        # Request State에 user_id 초기화
        request.state.user_id: Optional[str] = None

        # 응답 처리
        response = await call_next(request)

        return response
