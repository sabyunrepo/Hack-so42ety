"""
Kling API Key Pool Manager
다중 API 키 관리 및 자동 Failover
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Dict
import asyncio
import time

from .logging import get_logger

logger = get_logger(__name__)


class AbstractKeyPoolManager(ABC):
    """키 풀 관리자 추상 인터페이스"""

    @abstractmethod
    def get_current_key_pair(self) -> Tuple[str, str]:
        """
        현재 활성 키 쌍 반환

        Returns:
            Tuple[str, str]: (access_key, secret_key)
        """
        pass

    @abstractmethod
    def mark_key_failed(self, reason: str) -> None:
        """
        현재 키를 실패로 표시하고 쿨다운

        Args:
            reason: 실패 사유
        """
        pass

    @abstractmethod
    def is_rate_limit_error(self, status_code: int, response_data: dict) -> bool:
        """
        429 Rate Limit 에러 여부 판단

        Args:
            status_code: HTTP 상태 코드
            response_data: API 응답 데이터

        Returns:
            bool: Rate Limit 에러 여부
        """
        pass

    @abstractmethod
    def get_all_key_pairs(self) -> List[Tuple[str, str]]:
        """
        모든 키 쌍 반환 (크레딧 확인용)

        Returns:
            List[Tuple[str, str]]: [(ak1, sk1), (ak2, sk2), ...]
        """
        pass


class KlingKeyPoolManager(AbstractKeyPoolManager):
    """
    Kling API 키 풀 관리자

    특징:
    - Round-Robin 방식으로 키 순환
    - 실패한 키는 쿨다운 기간 동안 비활성화 (기본 5분)
    - 429 에러 감지 (Kling API 에러 코드 1302, 1303, 1304)
    - Thread-safe (asyncio.Lock)
    """

    def __init__(
        self, access_keys: List[str], secret_keys: List[str], cooldown_seconds: int = 300
    ):
        """
        KlingKeyPoolManager 초기화

        Args:
            access_keys: Kling Access Key 리스트
            secret_keys: Kling Secret Key 리스트
            cooldown_seconds: 실패한 키 쿨다운 시간 (초)

        Raises:
            ValueError: 키 개수가 일치하지 않거나 비어있을 때
        """
        if len(access_keys) != len(secret_keys):
            raise ValueError(
                f"access_keys와 secret_keys 개수가 일치하지 않습니다 "
                f"(access: {len(access_keys)}, secret: {len(secret_keys)})"
            )
        if not access_keys:
            raise ValueError("최소 1개 이상의 키가 필요합니다")

        # 키 풀: 각 키의 상태 추적
        self._key_pool: List[Dict] = [
            {"ak": ak, "sk": sk, "failed_until": 0.0}
            for ak, sk in zip(access_keys, secret_keys)
        ]
        self._current_index = 0
        self._cooldown_seconds = cooldown_seconds
        self._lock = asyncio.Lock()

        logger.info(
            f"KlingKeyPoolManager initialized with {len(self._key_pool)} keys "
            f"(cooldown: {cooldown_seconds}s)"
        )

    def get_current_key_pair(self) -> Tuple[str, str]:
        """
        사용 가능한 키 반환 (쿨다운 체크)

        쿨다운 중이 아닌 키를 Round-Robin 방식으로 반환합니다.
        모든 키가 쿨다운 중이면 첫 번째 키를 강제로 반환합니다.

        Returns:
            Tuple[str, str]: (access_key, secret_key)
        """
        current_time = time.time()

        # 쿨다운 중이 아닌 키 찾기
        for _ in range(len(self._key_pool)):
            key_info = self._key_pool[self._current_index]

            if current_time >= key_info["failed_until"]:
                # 사용 가능한 키 발견
                return (key_info["ak"], key_info["sk"])

            # 다음 키로 이동
            self._current_index = (self._current_index + 1) % len(self._key_pool)

        # 모든 키가 쿨다운 중이면 첫 번째 키 강제 사용
        logger.warning(
            "⚠️ 모든 키가 쿨다운 중입니다. 첫 번째 키를 강제 사용합니다."
        )
        self._current_index = 0
        key_info = self._key_pool[0]
        return (key_info["ak"], key_info["sk"])

    def mark_key_failed(self, reason: str) -> None:
        """
        현재 키 실패 표시 및 다음 키로 전환

        Args:
            reason: 실패 사유
        """
        current_key = self._key_pool[self._current_index]
        current_key["failed_until"] = time.time() + self._cooldown_seconds

        cooldown_until_str = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(current_key["failed_until"])
        )

        logger.warning(
            f"❌ Key #{self._current_index + 1} marked as failed: {reason}. "
            f"Cooldown until {cooldown_until_str}"
        )

        # 다음 키로 전환
        old_index = self._current_index
        self._current_index = (self._current_index + 1) % len(self._key_pool)

        logger.info(
            f"🔄 Switched from key #{old_index + 1} to key #{self._current_index + 1}"
        )

    def is_rate_limit_error(self, status_code: int, response_data: dict) -> bool:
        """
        429 에러 + Kling API 에러 코드 1302/1303/1304 체크

        Kling API 에러 코드:
        - 1302: API 요청 속도 초과 (Rate Limit)
        - 1303: 동시성/QPS 초과 (Concurrency Limit)
        - 1304: IP 화이트리스트 정책 위반

        Args:
            status_code: HTTP 상태 코드
            response_data: API 응답 데이터

        Returns:
            bool: Rate Limit 에러 여부
        """
        if status_code != 429:
            return False

        error_code = response_data.get("code")
        # Kling API Rate Limit 에러 코드
        return error_code in [1302, 1303, 1304]

    def get_all_key_pairs(self) -> List[Tuple[str, str]]:
        """
        모든 키 쌍 반환 (크레딧 확인용)

        Returns:
            List[Tuple[str, str]]: [(ak1, sk1), (ak2, sk2), ...]
        """
        return [(key["ak"], key["sk"]) for key in self._key_pool]

    def get_pool_status(self) -> List[Dict]:
        """
        키 풀 상태 정보 반환 (디버깅용)

        Returns:
            List[Dict]: 각 키의 상태 정보
        """
        current_time = time.time()
        status = []

        for idx, key_info in enumerate(self._key_pool):
            is_active = current_time >= key_info["failed_until"]
            status.append(
                {
                    "index": idx + 1,
                    "is_active": is_active,
                    "failed_until": key_info["failed_until"],
                    "is_current": idx == self._current_index,
                }
            )

        return status
