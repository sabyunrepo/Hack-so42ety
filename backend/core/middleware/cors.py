"""
CORS Middleware
Cross-Origin Resource Sharing 설정
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import settings


def setup_cors(app: FastAPI) -> None:
    """
    CORS 미들웨어 설정

    Args:
        app: FastAPI 애플리케이션 인스턴스
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods.split(","),
        allow_headers=settings.cors_allow_headers.split(",")
        if settings.cors_allow_headers != "*"
        else ["*"],
        expose_headers=["Content-Disposition"],  # 파일 다운로드를 위한 헤더
    )
