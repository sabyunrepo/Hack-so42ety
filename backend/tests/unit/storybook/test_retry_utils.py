"""
Retry Utilities Unit Tests
재시도 유틸리티 함수 및 BatchRetryTracker 테스트
"""

import asyncio
import pytest
from backend.features.storybook.tasks.retry import (
    calculate_retry_delay,
    retry_with_config,
    BatchRetryTracker,
)
from backend.core.config import settings


class TestCalculateRetryDelay:
    """calculate_retry_delay 함수 테스트"""

    @pytest.mark.asyncio
    async def test_linear_backoff(self):
        """선형 백오프 테스트 (exponential_backoff=False)"""
        # Given
        base_delay = 2.0
        original_value = settings.task_retry_exponential_backoff
        settings.task_retry_exponential_backoff = False

        try:
            # When & Then
            assert await calculate_retry_delay(1, base_delay) == 2.0
            assert await calculate_retry_delay(2, base_delay) == 2.0
            assert await calculate_retry_delay(3, base_delay) == 2.0
        finally:
            settings.task_retry_exponential_backoff = original_value

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """지수 백오프 테스트 (exponential_backoff=True)"""
        # Given
        base_delay = 2.0
        original_value = settings.task_retry_exponential_backoff
        settings.task_retry_exponential_backoff = True

        try:
            # When & Then
            assert await calculate_retry_delay(1, base_delay) == 2.0  # base * 2^0
            assert await calculate_retry_delay(2, base_delay) == 4.0  # base * 2^1
            assert await calculate_retry_delay(3, base_delay) == 8.0  # base * 2^2
            assert await calculate_retry_delay(4, base_delay) == 16.0  # base * 2^3
        finally:
            settings.task_retry_exponential_backoff = original_value


class TestRetryWithConfig:
    """retry_with_config 함수 테스트"""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """첫 시도에서 성공하는 경우"""
        # Given
        call_count = 0

        async def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        # When
        result = await retry_with_config(
            func=successful_func,
            max_retries=3,
            error_message_prefix="Test"
        )

        # Then
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_success_on_second_attempt(self):
        """두 번째 시도에서 성공하는 경우"""
        # Given
        call_count = 0

        async def sometimes_fail_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First attempt failed")
            return "success"

        # When
        result = await retry_with_config(
            func=sometimes_fail_func,
            max_retries=3,
            error_message_prefix="Test"
        )

        # Then
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_fail_after_max_retries(self):
        """모든 시도 실패 시 RuntimeError 발생"""
        # Given
        call_count = 0

        async def always_fail_func():
            nonlocal call_count
            call_count += 1
            raise ValueError(f"Attempt {call_count} failed")

        # When & Then
        with pytest.raises(RuntimeError, match="failed after 3 retries"):
            await retry_with_config(
                func=always_fail_func,
                max_retries=3,
                error_message_prefix="Test"
            )

        assert call_count == 3


class TestBatchRetryTracker:
    """BatchRetryTracker 클래스 테스트"""

    def test_initialization(self):
        """초기화 테스트"""
        # Given
        tracker = BatchRetryTracker(total_items=5, max_retries=2)

        # Then
        assert tracker.total_items == 5
        assert tracker.max_retries == 2
        assert len(tracker.completed) == 0
        assert len(tracker.retry_counts) == 5
        assert all(count == 0 for count in tracker.retry_counts.values())

    def test_mark_success(self):
        """성공 기록 테스트"""
        # Given
        tracker = BatchRetryTracker(total_items=3, max_retries=2)

        # When
        tracker.mark_success(0, "result_0")
        tracker.mark_success(2, "result_2")

        # Then
        assert len(tracker.completed) == 2
        assert tracker.completed[0] == "result_0"
        assert tracker.completed[2] == "result_2"

    def test_mark_failure(self):
        """실패 기록 테스트"""
        # Given
        tracker = BatchRetryTracker(total_items=3, max_retries=2)

        # When
        tracker.mark_failure(0, "error_1")
        tracker.mark_failure(0, "error_2")

        # Then
        assert tracker.retry_counts[0] == 2
        assert tracker.last_errors[0] == "error_2"

    def test_get_pending_indices(self):
        """재시도 대상 인덱스 조회 테스트"""
        # Given
        tracker = BatchRetryTracker(total_items=5, max_retries=2)

        # When
        tracker.mark_success(0, "result_0")
        tracker.mark_failure(1, "error_1")
        tracker.mark_failure(1, "error_2")  # retry_count=2 (max 도달)
        tracker.mark_failure(2, "error_1")  # retry_count=1 (재시도 가능)

        # Then
        pending = tracker.get_pending_indices()
        assert 0 not in pending  # 성공
        assert 1 not in pending  # max_retries 도달
        assert 2 in pending  # 재시도 가능
        assert 3 in pending  # 아직 시도 안 함
        assert 4 in pending  # 아직 시도 안 함

    def test_get_failed_indices(self):
        """최종 실패 인덱스 조회 테스트"""
        # Given
        tracker = BatchRetryTracker(total_items=5, max_retries=2)

        # When
        tracker.mark_success(0, "result_0")
        tracker.mark_failure(1, "error_1")
        tracker.mark_failure(1, "error_2")  # retry_count=2 (max 도달)
        tracker.mark_failure(2, "error_1")  # retry_count=1 (재시도 가능)

        # Then
        failed = tracker.get_failed_indices()
        assert 0 not in failed  # 성공
        assert 1 in failed  # max_retries 도달
        assert 2 not in failed  # 재시도 가능

    def test_is_all_completed(self):
        """전체 완료 여부 테스트"""
        # Given
        tracker = BatchRetryTracker(total_items=3, max_retries=2)

        # When & Then
        assert not tracker.is_all_completed()

        tracker.mark_success(0, "result_0")
        assert not tracker.is_all_completed()

        tracker.mark_success(1, "result_1")
        tracker.mark_success(2, "result_2")
        assert tracker.is_all_completed()

    def test_is_partial_failure(self):
        """부분 실패 여부 테스트"""
        # Given
        tracker = BatchRetryTracker(total_items=3, max_retries=2)

        # When & Then
        assert not tracker.is_partial_failure()  # 아무것도 완료 안 됨

        tracker.mark_success(0, "result_0")
        assert tracker.is_partial_failure()  # 일부만 완료

        tracker.mark_success(1, "result_1")
        tracker.mark_success(2, "result_2")
        assert not tracker.is_partial_failure()  # 전부 완료

    def test_get_summary_completed(self):
        """요약 정보 (전체 완료) 테스트"""
        # Given
        tracker = BatchRetryTracker(total_items=3, max_retries=2)

        # When
        tracker.mark_success(0, "result_0")
        tracker.mark_success(1, "result_1")
        tracker.mark_success(2, "result_2")

        summary = tracker.get_summary()

        # Then
        assert summary["status"] == "completed"
        assert summary["total_items"] == 3
        assert summary["completed_items"] == 3
        assert summary["max_retries"] == 2
        assert len(summary["failed_items"]) == 0

    def test_get_summary_partially_completed(self):
        """요약 정보 (부분 완료) 테스트"""
        # Given
        tracker = BatchRetryTracker(total_items=3, max_retries=2)

        # When
        tracker.mark_success(0, "result_0")
        tracker.mark_failure(1, "error_1")
        tracker.mark_failure(1, "error_2")  # max 도달
        tracker.mark_failure(2, "error_1")
        tracker.mark_failure(2, "error_2")  # max 도달

        summary = tracker.get_summary()

        # Then
        assert summary["status"] == "partially_completed"
        assert summary["total_items"] == 3
        assert summary["completed_items"] == 1
        assert summary["max_retries"] == 2
        assert len(summary["failed_items"]) == 2
        assert summary["failed_items"][0]["index"] == 1
        assert summary["failed_items"][0]["retry_count"] == 2
        assert summary["failed_items"][1]["index"] == 2

    def test_get_summary_failed(self):
        """요약 정보 (전체 실패) 테스트"""
        # Given
        tracker = BatchRetryTracker(total_items=2, max_retries=2)

        # When
        tracker.mark_failure(0, "error_1")
        tracker.mark_failure(0, "error_2")  # max 도달
        tracker.mark_failure(1, "error_1")
        tracker.mark_failure(1, "error_2")  # max 도달

        summary = tracker.get_summary()

        # Then
        assert summary["status"] == "failed"
        assert summary["total_items"] == 2
        assert summary["completed_items"] == 0
        assert len(summary["failed_items"]) == 2
