"""
JWT Authentication Module for Kling API

Kling API requires JWT token authentication using Access Key (ak) and Secret Key (sk).
This module provides automatic JWT token generation and refresh mechanism.
"""

import time
from typing import Generator, Optional, TYPE_CHECKING
import httpx
import jwt  # PyJWT

from .logging import get_logger

if TYPE_CHECKING:
    from .key_pool_manager import AbstractKeyPoolManager

logger = get_logger(__name__)


class KlingJWTAuth(httpx.Auth):
    """
    Kling API JWT 인증 핸들러

    httpx.Auth를 상속하여 요청마다 자동으로 JWT 토큰을 생성/갱신하여 Authorization 헤더에 주입합니다.

    토큰 특성:
    - 알고리즘: HS256
    - 유효 시간: 30분 (1800초)
    - 발급 시점: 현재 시간 - 5초 (nbf)
    - 만료 시점: 현재 시간 + 30분 (exp)

    토큰 갱신 전략:
    - Lazy Refresh: 만료된 토큰으로 요청 시도 시점에 자동 갱신
    - 메모리 캐싱: 모듈 레벨 변수로 토큰 저장 (프로세스 내 공유)
    """

    def __init__(self, key_pool_manager: "AbstractKeyPoolManager"):
        """
        KlingJWTAuth 초기화 (키 풀 매니저 기반)

        Args:
            key_pool_manager: 키 풀 관리자
        """
        self.key_pool_manager = key_pool_manager

        # 초기 키 설정
        self.access_key, self.secret_key = key_pool_manager.get_current_key_pair()

        # 토큰 캐시 (인스턴스 변수)
        self._cached_token: Optional[str] = None
        self._token_expires_at: float = 0.0

        logger.info("KlingJWTAuth initialized with key pool manager")

    def encode_jwt_token(self) -> str:
        """
        JWT 토큰 생성

        Kling API 규격에 맞춰 HS256 알고리즘으로 JWT 토큰을 생성합니다.

        Returns:
            str: 생성된 JWT 토큰

        Raises:
            jwt.PyJWTError: JWT 인코딩 실패 시
        """
        current_time = int(time.time())

        headers = {
            "alg": "HS256",
            "typ": "JWT",
        }

        payload = {
            "iss": self.access_key,  # Issuer: Access Key
            "exp": current_time + 1800,  # Expiration: 현재 시간 + 30분
            "nbf": current_time - 5,  # Not Before: 현재 시간 - 5초
        }

        try:
            token = jwt.encode(payload, self.secret_key, algorithm="HS256", headers=headers)
            logger.info(f"JWT token generated (expires in 30 minutes)")
            return token
        except Exception as e:
            logger.error(f"Failed to encode JWT token: {e}", exc_info=True)
            raise

    def is_token_expired(self) -> bool:
        """
        토큰 만료 여부 확인

        현재 시간과 토큰 만료 시간을 비교하여 만료 여부를 판단합니다.
        안전을 위해 실제 만료 시간보다 10초 일찍 만료로 간주합니다.

        Returns:
            bool: 만료되었으면 True, 유효하면 False
        """
        if self._cached_token is None:
            return True

        # 현재 시간 + 10초 (안전 마진)
        current_time_with_margin = time.time() + 10

        is_expired = current_time_with_margin >= self._token_expires_at

        if is_expired:
            logger.info("JWT token expired, will generate new token")

        return is_expired

    def invalidate_token(self) -> None:
        """
        현재 캐시된 JWT 토큰 무효화

        키 전환 시 호출하여 다음 요청 때 새로운 키로 토큰을 재생성합니다.
        """
        self._cached_token = None
        self._token_expires_at = 0.0
        logger.info("🔄 JWT token invalidated (will regenerate with new key)")

    def get_valid_token(self) -> str:
        """
        유효한 JWT 토큰 반환 (Lazy Refresh)

        캐시된 토큰이 없거나 만료되었으면 새로 생성하고,
        유효한 토큰이 있으면 캐시된 토큰을 반환합니다.
        토큰 갱신 시 키 풀 매니저로부터 최신 활성 키를 가져옵니다.

        Returns:
            str: 유효한 JWT 토큰
        """
        if self.is_token_expired():
            # 최신 활성 키로 갱신
            self.access_key, self.secret_key = self.key_pool_manager.get_current_key_pair()

            # 새 토큰 생성
            self._cached_token = self.encode_jwt_token()
            self._token_expires_at = time.time() + 1800  # 30분 후

            logger.info(
                f"New JWT token cached (valid until {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self._token_expires_at))})"
            )

        return self._cached_token

    def auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        """
        httpx.Auth 인터페이스 구현

        요청마다 자동으로 호출되어 Authorization 헤더에 유효한 JWT 토큰을 주입합니다.

        Args:
            request: httpx Request 객체

        Yields:
            httpx.Request: Authorization 헤더가 추가된 요청 객체
        """
        # 유효한 토큰 가져오기 (필요시 자동 갱신)
        token = self.get_valid_token()

        # Authorization 헤더 추가
        request.headers["Authorization"] = f"Bearer {token}"

        # 요청 전송
        yield request


# ================================================================
# 편의 함수
# ================================================================


def create_kling_jwt_auth(key_pool_manager: "AbstractKeyPoolManager") -> KlingJWTAuth:
    """
    KlingJWTAuth 인스턴스 생성 편의 함수

    Args:
        key_pool_manager: 키 풀 관리자

    Returns:
        KlingJWTAuth: JWT 인증 핸들러
    """
    return KlingJWTAuth(key_pool_manager=key_pool_manager)


async def check_kling_credits(
    access_key: str, secret_key: str, api_url: str = "https://api-singapore.klingai.com"
) -> dict:
    """
    Kling API 크레딧 잔량 확인

    서버 시작 시 또는 필요 시 Kling API 계정의 크레딧 잔량을 확인합니다.

    Args:
        access_key: Kling API Access Key
        secret_key: Kling API Secret Key
        api_url: Kling API 엔드포인트 (기본값: Singapore)

    Returns:
        dict: 크레딧 정보 (total_quantity, remaining_quantity, resource_pack_name 등)

    Raises:
        Exception: API 호출 실패 시
    """
    try:
        # 임시 키 풀 매니저 생성 (단일 키)
        from .key_pool_manager import KlingKeyPoolManager

        temp_key_pool = KlingKeyPoolManager(
            access_keys=[access_key], secret_keys=[secret_key], cooldown_seconds=0
        )

        # JWT 인증 핸들러 생성
        auth = KlingJWTAuth(key_pool_manager=temp_key_pool)

        # httpx 클라이언트 생성
        async with httpx.AsyncClient(auth=auth, timeout=30.0) as client:
            # 크레딧 정보 조회
            # /account/costs는 start_time, end_time 파라미터 필요 (밀리초 단위)
            current_time_ms = int(time.time() * 1000)  # 밀리초 단위
            start_time_ms = current_time_ms - (30 * 24 * 60 * 60 * 1000)  # 30일 전

            params = {
                "start_time": start_time_ms,
                "end_time": current_time_ms,
            }

            response = await client.get(f"{api_url}/account/costs", params=params)

            response.raise_for_status()
            data = response.json()

            if data.get("code") != 0:
                logger.error(f"Failed to fetch Kling resource packs: {data.get('message')}")
                return {}

            # 리소스 팩 정보 추출
            # API 응답 구조에 따라 다를 수 있으므로 여러 경로 시도
            resource_packs = (
                data.get("data", {}).get("resource_pack_subscribe_infos", [])
                or data.get("data", {}).get("subscribes", [])
                or data.get("data", [])
            )

            if not resource_packs:
                logger.warning("No resource packs found in Kling account")
                return {}

            # 첫 번째 활성 리소스 팩 정보 로깅
            for pack in resource_packs:
                if pack.get("status") == "online":
                    logger.info(
                        f"📊 Kling API Credits - "
                        f"Pack: {pack.get('resource_pack_name', 'Unknown')}, "
                        f"Total: {pack.get('total_quantity', 0):.0f}, "
                        f"Remaining: {pack.get('remaining_quantity', 0):.0f} "
                        f"({pack.get('remaining_quantity', 0) / pack.get('total_quantity', 1) * 100:.1f}%)"
                    )

                    return {
                        "resource_pack_name": pack.get("resource_pack_name"),
                        "total_quantity": pack.get("total_quantity"),
                        "remaining_quantity": pack.get("remaining_quantity"),
                        "status": pack.get("status"),
                        "effective_time": pack.get("effective_time"),
                        "invalid_time": pack.get("invalid_time"),
                    }

            logger.warning("No online resource packs found")
            return {}

    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP error while checking Kling credits: {e.response.status_code} - {e.response.text}"
        )
        return {}
    except Exception as e:
        logger.error(f"Failed to check Kling credits: {e}", exc_info=True)
        return {}
