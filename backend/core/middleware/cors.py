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

    이 함수는 CORS(Cross-Origin Resource Sharing) 정책을 설정합니다.
    환경변수로부터 로드된 설정값을 사용하여 CORSMiddleware를 구성합니다.

    Args:
        app: FastAPI 애플리케이션 인스턴스

    Note:
        allow_headers 처리:
        - 기본값: "Content-Type,Authorization,Accept,X-Request-ID" (최소 권한 원칙)
        - 쉼표로 구분된 문자열은 자동으로 리스트로 변환됩니다
        - 와일드카드 "*"는 하위 호환성을 위해 지원됩니다 (보안상 권장하지 않음)
        - 커스텀 헤더가 필요한 경우 CORS_ALLOW_HEADERS 환경변수로 추가 가능

        expose_headers:
        - Content-Disposition: 파일 다운로드를 위한 응답 헤더 노출
    """
    # Parse comma-separated header list into array
    # Special handling for wildcard "*" to maintain backward compatibility
    parsed_headers = (
        settings.cors_allow_headers.split(",")
        if settings.cors_allow_headers != "*"
        else ["*"]
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods.split(","),
        allow_headers=parsed_headers,
        expose_headers=["Content-Disposition"],
    )
