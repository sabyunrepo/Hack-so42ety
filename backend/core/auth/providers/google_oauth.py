"""
Google OAuth Provider
Google OAuth 2.0 인증
"""

from typing import Optional, Dict, Any
from google.auth.transport import requests
from google.oauth2 import id_token

from ...config import settings


class GoogleOAuthProvider:
    """
    Google OAuth 2.0 인증 제공자

    Google ID Token 검증 및 사용자 정보 추출
    """

    @staticmethod
    async def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Google ID Token 검증

        Args:
            token: Google ID Token (프론트엔드에서 받은 토큰)

        Returns:
            Optional[Dict[str, Any]]: 사용자 정보 또는 None (검증 실패 시)
                {
                    "sub": "구글 사용자 ID",
                    "email": "사용자 이메일",
                    "name": "사용자 이름",
                    "picture": "프로필 이미지 URL"
                }
        """
        if not settings.google_oauth_client_id:
            raise ValueError("GOOGLE_OAUTH_CLIENT_ID is not configured")

        try:
            # Google ID Token 검증
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                settings.google_oauth_client_id,
            )

            # 발급자 검증
            if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
                return None

            # 사용자 정보 반환
            return {
                "sub": idinfo["sub"],  # Google User ID
                "email": idinfo["email"],
                "name": idinfo.get("name", ""),
                "picture": idinfo.get("picture", ""),
            }

        except ValueError:
            # 토큰 검증 실패
            return None
