"""
Cookie Utility Module
인증 쿠키 설정 및 관리 헬퍼 함수
"""

import logging
from typing import Dict, Any, Optional
from fastapi import Response

from ..config import settings

logger = logging.getLogger(__name__)


def get_cookie_settings() -> Dict[str, Any]:
    """
    쿠키 보안 설정 반환

    Returns:
        Dict[str, Any]: 쿠키 설정 딕셔너리 (httponly, secure, samesite, path, domain)
    """
    cookie_settings = {
        "httponly": settings.cookie_httponly,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
        "path": settings.cookie_path,
    }

    # domain은 None이 아닐 때만 추가 (same-origin의 경우 None)
    if settings.cookie_domain is not None:
        cookie_settings["domain"] = settings.cookie_domain

    logger.debug(
        "🍪 [COOKIE SETTINGS] Retrieved",
        extra={
            "httponly": cookie_settings["httponly"],
            "secure": cookie_settings["secure"],
            "samesite": cookie_settings["samesite"],
            "path": cookie_settings["path"],
            "domain": cookie_settings.get("domain", "same-origin"),
        }
    )

    return cookie_settings


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
) -> None:
    """
    인증 쿠키 설정 (access_token, refresh_token)

    Args:
        response: FastAPI Response 객체
        access_token: JWT Access Token
        refresh_token: JWT Refresh Token
    """
    cookie_settings = get_cookie_settings()

    # Access Token 쿠키 설정 (만료 시간: 분 단위)
    access_token_max_age = settings.jwt_access_token_expire_minutes * 60
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=access_token_max_age,
        **cookie_settings,
    )

    # Refresh Token 쿠키 설정 (만료 시간: 일 단위)
    refresh_token_max_age = settings.jwt_refresh_token_expire_days * 24 * 60 * 60
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=refresh_token_max_age,
        **cookie_settings,
    )

    logger.info(
        "🍪 [SET COOKIES] Auth cookies set successfully",
        extra={
            "access_token_max_age_seconds": access_token_max_age,
            "refresh_token_max_age_seconds": refresh_token_max_age,
            "httponly": cookie_settings["httponly"],
            "secure": cookie_settings["secure"],
        }
    )


def clear_auth_cookies(response: Response) -> None:
    """
    인증 쿠키 삭제 (로그아웃 시 사용)

    Args:
        response: FastAPI Response 객체
    """
    cookie_settings = get_cookie_settings()

    # Access Token 쿠키 삭제 (max_age=0으로 즉시 만료)
    response.set_cookie(
        key="access_token",
        value="",
        max_age=0,
        **cookie_settings,
    )

    # Refresh Token 쿠키 삭제
    response.set_cookie(
        key="refresh_token",
        value="",
        max_age=0,
        **cookie_settings,
    )

    logger.info(
        "🍪 [CLEAR COOKIES] Auth cookies cleared successfully",
        extra={
            "path": cookie_settings["path"],
            "domain": cookie_settings.get("domain", "same-origin"),
        }
    )
