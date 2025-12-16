"""
Task Retry Utilities
재시도 로직을 위한 유틸리티 함수 및 클래스
"""

import asyncio
import logging
from typing import TypeVar, Callable, Awaitable, Any, List, Dict

from backend.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar('T')


async def calculate_retry_delay(attempt: int, base_delay: float = None) -> float:
    """
    재시도 대기 시간 계산 (Exponential Backoff 지원)

    Args:
        attempt: 현재 시도 횟수 (1부터 시작)
        base_delay: 기본 대기 시간 (None이면 설정값 사용)

    Returns:
        float: 대기 시간 (초)
    """
    base = base_delay or settings.task_retry_delay

    if settings.task_retry_exponential_backoff:
        # Exponential backoff: base * (2 ^ (attempt - 1))
        # attempt=1 → base, attempt=2 → base*2, attempt=3 → base*4
        return base * (2 ** (attempt - 1))
    else:
        return base


async def retry_with_config(
    func: Callable[..., Awaitable[T]],
    max_retries: int,
    error_message_prefix: str = "Operation",
    **kwargs: Any
) -> T:
    """
    재시도 로직이 포함된 함수 실행 (for-else 패턴 일반화)

    Args:
        func: 실행할 비동기 함수
        max_retries: 최대 재시도 횟수
        error_message_prefix: 에러 로그 접두사
        **kwargs: func에 전달할 키워드 인자

    Returns:
        T: func의 반환값

    Raises:
        RuntimeError: 모든 시도 실패 시
    """
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            result = await func(**kwargs)

            if attempt > 1:
                logger.info(
                    f"{error_message_prefix} succeeded on attempt {attempt}/{max_retries}"
                )

            return result

        except Exception as e:
            last_error = e
            logger.warning(
                f"{error_message_prefix} failed on attempt {attempt}/{max_retries}: {e}"
            )

            # 마지막 시도가 아니면 대기
            if attempt < max_retries:
                delay = await calculate_retry_delay(attempt)
                logger.info(f"Retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)

    # for-else: 모든 시도 실패
    logger.error(
        f"{error_message_prefix} failed after {max_retries} attempts. Last error: {last_error}"
    )
    raise RuntimeError(
        f"{error_message_prefix} failed after {max_retries} retries: {last_error}"
    )


class BatchRetryTracker:
    """
    배치 처리 재시도 추적기

    배치 처리에서 개별 항목의 성공/실패를 추적하고,
    실패한 항목만 재시도할 수 있도록 지원
    """

    def __init__(self, total_items: int, max_retries: int):
        """
        Args:
            total_items: 전체 항목 수
            max_retries: 항목별 최대 재시도 횟수
        """
        self.total_items = total_items
        self.max_retries = max_retries

        # 인덱스 → 성공 결과 매핑
        self.completed: Dict[int, Any] = {}

        # 인덱스 → 재시도 횟수 매핑
        self.retry_counts: Dict[int, int] = {i: 0 for i in range(total_items)}

        # 인덱스 → 마지막 에러 매핑
        self.last_errors: Dict[int, str] = {}

    def mark_success(self, idx: int, result: Any):
        """항목 성공 기록"""
        self.completed[idx] = result
        logger.debug(f"[BatchRetryTracker] Item {idx} marked as success")

    def mark_failure(self, idx: int, error: str):
        """항목 실패 기록"""
        self.retry_counts[idx] = self.retry_counts.get(idx, 0) + 1
        self.last_errors[idx] = error
        logger.debug(
            f"[BatchRetryTracker] Item {idx} marked as failure "
            f"(retry {self.retry_counts[idx]}/{self.max_retries}): {error}"
        )

    def get_pending_indices(self) -> List[int]:
        """재시도가 필요한 인덱스 목록 반환"""
        return [
            i for i in range(self.total_items)
            if i not in self.completed and self.retry_counts[i] < self.max_retries
        ]

    def get_failed_indices(self) -> List[int]:
        """최종 실패한 인덱스 목록 반환 (max_retries 초과)"""
        return [
            i for i in range(self.total_items)
            if i not in self.completed and self.retry_counts[i] >= self.max_retries
        ]

    def is_all_completed(self) -> bool:
        """모든 항목 완료 여부"""
        return len(self.completed) == self.total_items

    def is_partial_failure(self) -> bool:
        """부분 실패 여부 (일부 성공, 일부 실패)"""
        return len(self.completed) > 0 and len(self.completed) < self.total_items

    def get_summary(self) -> dict:
        """재시도 정보 요약 (task_metadata 저장용)"""
        failed_items_list = [
            {
                "index": idx,
                "retry_count": self.retry_counts[idx],
                "last_error": self.last_errors.get(idx, "Unknown error")
            }
            for idx in self.get_failed_indices()
        ]

        # 상태 결정
        if self.is_all_completed():
            status = "completed"
        elif self.is_partial_failure():
            status = "partially_completed"
        else:
            status = "failed"

        return {
            "status": status,
            "total_items": self.total_items,
            "completed_items": len(self.completed),
            "max_retries": self.max_retries,
            "failed_items": failed_items_list
        }
