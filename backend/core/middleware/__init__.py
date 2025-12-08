"""
Middleware Module
CORS, 인증, 로깅 등 미들웨어 관리
"""

from .cors import setup_cors

__all__ = ["setup_cors"]
