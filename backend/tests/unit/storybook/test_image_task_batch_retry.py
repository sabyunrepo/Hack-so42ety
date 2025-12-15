"""
Image Task Batch Retry Logic Tests
Image Task의 배치 재시도 로직 검증
"""

import asyncio
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List

from backend.features.storybook.tasks.core import generate_image_task
from backend.features.storybook.tasks.schemas import TaskContext, TaskResult, TaskStatus
from backend.features.storybook.models import Book, BookStatus


@pytest.fixture
def task_context():
    """테스트용 TaskContext"""
    return TaskContext(
        book_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        execution_id=str(uuid.uuid4()),
        retry_count=0,
        params={}
    )


@pytest.fixture
def mock_book():
    """테스트용 Book 객체 Mock"""
    book = MagicMock(spec=Book)
    book.id = uuid.uuid4()
    book.user_id = uuid.uuid4()
    book.title = "Test Book"
    book.status = BookStatus.CREATING
    book.pipeline_stage = "story"
    book.progress_percentage = 20
    book.task_metadata = {}
    book.base_path = f"users/{book.user_id}/books/{book.id}"
    book.is_default = False
    return book


@pytest.fixture
def mock_images():
    """테스트용 이미지 데이터 (5개)"""
    return [b"image_data_0", b"image_data_1", b"image_data_2", b"image_data_3", b"image_data_4"]


class TestImageTaskPartialFailureRetry:
    """Image Task 부분 실패 재시도 테스트"""

    @pytest.mark.asyncio
    async def test_image_partial_failure_with_retry(self, task_context, mock_book, mock_images):
        """
        시나리오: 5개 이미지 중 2개 실패 → 재시도 → 1개 성공, 1개 최종 실패

        Phase 1 (첫 시도):
        - idx 0, 1, 2: 성공
        - idx 3, 4: 실패

        Phase 2 (재시도):
        - idx 3: 성공
        - idx 4: 여전히 실패

        최종: 4/5 완료, COMPLETED (부분 성공도 COMPLETED)
        """
        # Given
        book_id = task_context.book_id

        # Mock 호출 횟수 추적
        call_count = 0

        async def generate_image_with_partial_failure(image_data=None, prompt=None):
            nonlocal call_count
            call_count += 1

            # 첫 5번 호출 (pending_indices = [0, 1, 2, 3, 4])
            if call_count <= 5:
                idx = call_count - 1
                if idx in [3, 4]:
                    raise Exception(f"Image {idx} generation failed on attempt 1")
                return {
                    "data": [{
                        "imageUUID": f"uuid-{idx}",
                        "imageURL": f"https://example.com/image-{idx}.png"
                    }]
                }

            # 다음 2번 호출 (pending_indices = [3, 4])
            elif call_count <= 7:
                idx = [3, 4][call_count - 6]
                if idx == 4:
                    raise Exception(f"Image {idx} generation still failed on attempt 2")
                return {
                    "data": [{
                        "imageUUID": f"uuid-{idx}",
                        "imageURL": f"https://example.com/image-{idx}.png"
                    }]
                }

        # Mock providers
        mock_image_provider = AsyncMock()
        mock_image_provider.generate_image_from_image.side_effect = generate_image_with_partial_failure

        mock_ai_factory = MagicMock()
        mock_ai_factory.get_image_provider.return_value = mock_image_provider

        # Mock storage service
        mock_storage = AsyncMock()
        mock_storage.save.return_value = f"{mock_book.base_path}/images/cover.png"

        # Mock httpx client for cover image download
        mock_httpx_response = MagicMock()
        mock_httpx_response.content = b"cover_image_data"
        mock_httpx_response.raise_for_status = MagicMock()

        mock_httpx_client = AsyncMock()
        mock_httpx_client.get.return_value = mock_httpx_response
        mock_httpx_client.__aenter__.return_value = mock_httpx_client
        mock_httpx_client.__aexit__.return_value = None

        # Mock task store (Redis)
        mock_task_store = AsyncMock()
        mock_task_store.get.side_effect = [
            # story data
            {"dialogues": [
                [{"speaker": "Narrator", "text": f"Page {i}"}] for i in range(5)
            ]},
            # image cache (첫 시도 전에는 없음)
            None
        ]
        mock_task_store.set.return_value = None

        # Mock database
        mock_db_session = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get.return_value = mock_book
        mock_repo.update.return_value = mock_book

        with patch("backend.features.storybook.tasks.core.get_ai_factory", return_value=mock_ai_factory):
            with patch("backend.features.storybook.tasks.core.get_storage_service", return_value=mock_storage):
                with patch("backend.features.storybook.tasks.core.TaskStore", return_value=mock_task_store):
                    with patch("backend.features.storybook.tasks.core.AsyncSessionLocal") as mock_session:
                        with patch("backend.features.storybook.tasks.core.BookRepository", return_value=mock_repo):
                            with patch("httpx.AsyncClient", return_value=mock_httpx_client):
                                with patch("asyncio.sleep", return_value=asyncio.sleep(0)):  # 대기 시간 제거
                                    with patch("backend.core.config.settings.task_image_max_retries", 2):
                                        mock_session.return_value.__aenter__.return_value = mock_db_session
                                        mock_session.return_value.__aexit__.return_value = None

                                        # When
                                        result = await generate_image_task(book_id, mock_images, task_context)

        # Then
        # 1. Task 결과 검증
        assert result.status == TaskStatus.COMPLETED  # 부분 성공도 COMPLETED

        # 2. 호출 횟수 검증 (핵심!)
        assert call_count == 7  # 5 (첫 시도) + 2 (재시도)
        assert mock_image_provider.generate_image_from_image.call_count == 7

        # 3. Task metadata 검증
        update_call_args = mock_repo.update.call_args
        assert update_call_args is not None

        task_metadata = update_call_args[1]["task_metadata"]
        assert "image" in task_metadata

        image_summary = task_metadata["image"]
        assert image_summary["status"] == "partially_completed"  # 부분 완료
        assert image_summary["total_items"] == 5
        assert image_summary["completed_items"] == 4  # 0, 1, 2, 3 성공
        assert len(image_summary["failed_items"]) == 1  # idx 4만 실패

        # 4. 실패 항목 상세 검증
        failed_item = image_summary["failed_items"][0]
        assert failed_item["index"] == 4
        assert failed_item["retry_count"] == 2  # max_retries 도달
        assert "failed" in failed_item["last_error"]

        # 5. Redis 저장 검증 (중간 결과 + 최종 결과)
        assert mock_task_store.set.call_count >= 2  # 최소 2번 (첫 루프, 두 번째 루프)

        print(f"✓ Partial failure retry succeeded: {image_summary['completed_items']}/{image_summary['total_items']} completed")
        print(f"✓ Failed item index: {failed_item['index']}, retry count: {failed_item['retry_count']}")


class TestImageTaskRedisCache:
    """Image Task Redis 캐시 복구 테스트"""

    @pytest.mark.asyncio
    async def test_image_redis_cache_recovery(self, task_context, mock_book, mock_images):
        """
        시나리오: 이전 실행에서 일부 성공 → 재시도 시 복구

        Phase 1 (캐시):
        - idx 0, 2, 4: 성공 (캐시에 저장됨)

        Phase 2 (재시도):
        - idx 1, 3만 시도

        최종: 5/5 완료, COMPLETED
        """
        # Given
        book_id = task_context.book_id

        # Redis 캐시 데이터 (이전 실행에서 idx 0, 2, 4 성공)
        cached_completed = {
            "0": {"imageUUID": "cached-uuid-0", "imageURL": "https://example.com/cached-0.png"},
            "2": {"imageUUID": "cached-uuid-2", "imageURL": "https://example.com/cached-2.png"},
            "4": {"imageUUID": "cached-uuid-4", "imageURL": "https://example.com/cached-4.png"},
        }

        call_count = 0

        async def generate_only_pending_images(image_data=None, prompt=None):
            nonlocal call_count
            call_count += 1

            # idx 1, 3만 호출되어야 함 (pending_indices = [1, 3])
            if call_count == 1:
                idx = 1
            elif call_count == 2:
                idx = 3
            else:
                raise AssertionError(f"Unexpected call count: {call_count}")

            return {
                "data": [{
                    "imageUUID": f"new-uuid-{idx}",
                    "imageURL": f"https://example.com/new-{idx}.png"
                }]
            }

        # Mock providers
        mock_image_provider = AsyncMock()
        mock_image_provider.generate_image_from_image.side_effect = generate_only_pending_images

        mock_ai_factory = MagicMock()
        mock_ai_factory.get_image_provider.return_value = mock_image_provider

        # Mock storage service
        mock_storage = AsyncMock()
        mock_storage.save.return_value = f"{mock_book.base_path}/images/cover.png"

        # Mock httpx client
        mock_httpx_response = MagicMock()
        mock_httpx_response.content = b"cover_image_data"
        mock_httpx_response.raise_for_status = MagicMock()

        mock_httpx_client = AsyncMock()
        mock_httpx_client.get.return_value = mock_httpx_response
        mock_httpx_client.__aenter__.return_value = mock_httpx_client
        mock_httpx_client.__aexit__.return_value = None

        # Mock task store (Redis)
        mock_task_store = AsyncMock()
        mock_task_store.get.side_effect = [
            # story data
            {"dialogues": [
                [{"speaker": "Narrator", "text": f"Page {i}"}] for i in range(5)
            ]},
            # image cache (복구할 데이터)
            {
                "completed": cached_completed,
                "retry_counts": {0: 0, 1: 1, 2: 0, 3: 1, 4: 0},
                "last_errors": {1: "Error 1", 3: "Error 3"}
            }
        ]
        mock_task_store.set.return_value = None

        # Mock database
        mock_db_session = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get.return_value = mock_book
        mock_repo.update.return_value = mock_book

        with patch("backend.features.storybook.tasks.core.get_ai_factory", return_value=mock_ai_factory):
            with patch("backend.features.storybook.tasks.core.get_storage_service", return_value=mock_storage):
                with patch("backend.features.storybook.tasks.core.TaskStore", return_value=mock_task_store):
                    with patch("backend.features.storybook.tasks.core.AsyncSessionLocal") as mock_session:
                        with patch("backend.features.storybook.tasks.core.BookRepository", return_value=mock_repo):
                            with patch("httpx.AsyncClient", return_value=mock_httpx_client):
                                with patch("asyncio.sleep", return_value=asyncio.sleep(0)):
                                    with patch("backend.core.config.settings.task_image_max_retries", 2):
                                        mock_session.return_value.__aenter__.return_value = mock_db_session
                                        mock_session.return_value.__aexit__.return_value = None

                                        # When
                                        result = await generate_image_task(book_id, mock_images, task_context)

        # Then
        # 1. Task 결과 검증
        assert result.status == TaskStatus.COMPLETED

        # 2. 호출 횟수 검증 (핵심! idx 1, 3만 호출되어야 함)
        assert call_count == 2  # idx 1, 3만
        assert mock_image_provider.generate_image_from_image.call_count == 2

        # 3. Task metadata 검증
        update_call_args = mock_repo.update.call_args
        task_metadata = update_call_args[1]["task_metadata"]
        image_summary = task_metadata["image"]

        assert image_summary["status"] == "completed"
        assert image_summary["total_items"] == 5
        assert image_summary["completed_items"] == 5  # 모두 성공
        assert len(image_summary["failed_items"]) == 0

        print(f"✓ Redis cache recovery succeeded: recovered 3 items, generated 2 new items")
        print(f"✓ Total {image_summary['completed_items']}/{image_summary['total_items']} completed")


class TestImageTaskReturnExceptions:
    """Image Task의 return_exceptions=True 동작 검증"""

    @pytest.mark.asyncio
    async def test_image_return_exceptions_allows_partial_completion(self, task_context, mock_book, mock_images):
        """
        시나리오: asyncio.gather가 일부 실패에도 불구하고 계속 진행

        Phase 1 (첫 시도):
        - gather 결과: [성공, 실패, 성공, 실패, 성공]
        - 전체 gather가 중단되지 않고 각각 처리됨

        최종: 3/5 완료, COMPLETED (부분 성공)
        """
        # Given
        book_id = task_context.book_id

        # side_effect 리스트로 간단하게 구현
        first_batch = [
            {"data": [{"imageUUID": "uuid-0", "imageURL": "https://example.com/0.png"}]},  # idx 0 성공
            Exception("Image 1 failed"),  # idx 1 실패
            {"data": [{"imageUUID": "uuid-2", "imageURL": "https://example.com/2.png"}]},  # idx 2 성공
            Exception("Image 3 failed"),  # idx 3 실패
            {"data": [{"imageUUID": "uuid-4", "imageURL": "https://example.com/4.png"}]},  # idx 4 성공
        ]

        # 재시도 (idx 1, 3) - 모두 실패
        second_batch = [
            Exception("Image 1 still failed"),  # idx 1 실패
            Exception("Image 3 still failed"),  # idx 3 실패
        ]

        # Mock providers
        mock_image_provider = AsyncMock()
        mock_image_provider.generate_image_from_image.side_effect = first_batch + second_batch

        mock_ai_factory = MagicMock()
        mock_ai_factory.get_image_provider.return_value = mock_image_provider

        # Mock storage service
        mock_storage = AsyncMock()
        mock_storage.save.return_value = f"{mock_book.base_path}/images/cover.png"

        # Mock httpx client
        mock_httpx_response = MagicMock()
        mock_httpx_response.content = b"cover_image_data"
        mock_httpx_response.raise_for_status = MagicMock()

        mock_httpx_client = AsyncMock()
        mock_httpx_client.get.return_value = mock_httpx_response
        mock_httpx_client.__aenter__.return_value = mock_httpx_client
        mock_httpx_client.__aexit__.return_value = None

        # Mock task store (Redis)
        mock_task_store = AsyncMock()
        mock_task_store.get.side_effect = [
            # story data
            {"dialogues": [
                [{"speaker": "Narrator", "text": f"Page {i}"}] for i in range(5)
            ]},
            # image cache (없음)
            None
        ]
        mock_task_store.set.return_value = None

        # Mock database
        mock_db_session = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get.return_value = mock_book
        mock_repo.update.return_value = mock_book

        with patch("backend.features.storybook.tasks.core.get_ai_factory", return_value=mock_ai_factory):
            with patch("backend.features.storybook.tasks.core.get_storage_service", return_value=mock_storage):
                with patch("backend.features.storybook.tasks.core.TaskStore", return_value=mock_task_store):
                    with patch("backend.features.storybook.tasks.core.AsyncSessionLocal") as mock_session:
                        with patch("backend.features.storybook.tasks.core.BookRepository", return_value=mock_repo):
                            with patch("httpx.AsyncClient", return_value=mock_httpx_client):
                                with patch("asyncio.sleep", return_value=asyncio.sleep(0)):
                                    with patch("backend.core.config.settings.task_image_max_retries", 2):
                                        mock_session.return_value.__aenter__.return_value = mock_db_session
                                        mock_session.return_value.__aexit__.return_value = None

                                        # When
                                        result = await generate_image_task(book_id, mock_images, task_context)

        # Then
        # 1. Task 결과 검증 (예외가 발생해도 전체가 실패하지 않음)
        assert result.status == TaskStatus.COMPLETED  # 부분 성공

        # 2. Task metadata 검증
        update_call_args = mock_repo.update.call_args
        task_metadata = update_call_args[1]["task_metadata"]
        image_summary = task_metadata["image"]

        assert image_summary["status"] == "partially_completed"
        assert image_summary["total_items"] == 5
        assert image_summary["completed_items"] == 3  # idx 0, 2, 4 성공
        assert len(image_summary["failed_items"]) == 2  # idx 1, 3 실패

        # 3. 실패 항목 검증
        failed_indices = [item["index"] for item in image_summary["failed_items"]]
        assert 1 in failed_indices
        assert 3 in failed_indices

        print(f"✓ return_exceptions=True worked: {image_summary['completed_items']} succeeded, {len(image_summary['failed_items'])} failed")
        print(f"✓ Task status: {image_summary['status']}")
