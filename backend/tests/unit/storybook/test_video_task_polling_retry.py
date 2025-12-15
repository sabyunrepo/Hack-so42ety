"""
Video Task Polling Retry Logic Tests
Video Task의 폴링 + 재시도 로직 검증
"""

import asyncio
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from backend.features.storybook.tasks.core import generate_video_task
from backend.features.storybook.tasks.schemas import TaskContext, TaskResult, TaskStatus
from backend.features.storybook.models import Book, Page, BookStatus


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
    book.pipeline_stage = "image"
    book.progress_percentage = 60
    book.task_metadata = {}
    book.base_path = f"users/{book.user_id}/books/{book.id}"
    book.is_default = False

    # Pages with video placeholders
    book.pages = [MagicMock(spec=Page, sequence=i+1) for i in range(5)]

    return book


@pytest.fixture
def mock_image_uuids():
    """테스트용 이미지 UUID 리스트 (5개)"""
    return [f"image-uuid-{i}" for i in range(5)]


class TestVideoTaskPollingWithTimeout:
    """Video Task 폴링 + 타임아웃 재시도 테스트"""

    @pytest.mark.asyncio
    async def test_video_polling_with_partial_timeout_and_retry(self, task_context, mock_book, mock_image_uuids):
        """
        시나리오: 폴링 중 일부 타임아웃 → 재시도 → 부분 성공

        Phase 1 (첫 요청):
        - 5개 비디오 요청 → 5개 task_uuid 획득

        Phase 2 (폴링):
        - idx 0, 1, 2: completed
        - idx 3, 4: processing (타임아웃)

        Phase 3 (재시도 요청):
        - idx 3, 4: 새로운 task_uuid 획득

        Phase 4 (재시도 폴링):
        - idx 3: completed
        - idx 4: processing (다시 타임아웃)

        최종: 4/5 완료, COMPLETED (부분 성공)
        """
        # Given
        book_id = task_context.book_id

        # Mock video provider
        mock_video_provider = AsyncMock()

        # Phase 1: Video generation requests
        request_count = 0

        async def generate_video_mock(image_uuid=None, prompt=None):
            nonlocal request_count
            request_count += 1

            # 첫 5번 호출 (initial request)
            if request_count <= 5:
                idx = request_count - 1
                return f"task-uuid-{idx}-attempt-1"
            # 다음 2번 호출 (retry request for idx 3, 4)
            elif request_count <= 7:
                idx = [3, 4][request_count - 6]
                return f"task-uuid-{idx}-attempt-2"

            raise AssertionError(f"Unexpected request count: {request_count}")

        mock_video_provider.generate_video.side_effect = generate_video_mock

        # Phase 2 & 4: Polling status responses
        status_check_count = {}

        async def check_status_mock(task_uuid: str):
            # Track call count per task_uuid
            if task_uuid not in status_check_count:
                status_check_count[task_uuid] = 0
            status_check_count[task_uuid] += 1

            # First attempt videos
            if task_uuid == "task-uuid-0-attempt-1":
                return {"status": "completed", "video_url": "https://example.com/video-0.mp4"}
            elif task_uuid == "task-uuid-1-attempt-1":
                return {"status": "completed", "video_url": "https://example.com/video-1.mp4"}
            elif task_uuid == "task-uuid-2-attempt-1":
                return {"status": "completed", "video_url": "https://example.com/video-2.mp4"}
            elif task_uuid == "task-uuid-3-attempt-1":
                # 계속 processing (타임아웃될 것)
                return {"status": "processing"}
            elif task_uuid == "task-uuid-4-attempt-1":
                # 계속 processing (타임아웃될 것)
                return {"status": "processing"}

            # Retry attempt videos
            elif task_uuid == "task-uuid-3-attempt-2":
                return {"status": "completed", "video_url": "https://example.com/video-3.mp4"}
            elif task_uuid == "task-uuid-4-attempt-2":
                # 다시 processing (또 타임아웃)
                return {"status": "processing"}

            return {"status": "processing"}

        mock_video_provider.check_video_status.side_effect = check_status_mock

        # Mock video download
        async def download_video_mock(video_url: str):
            return b"video_content_data"

        mock_video_provider.download_video.side_effect = download_video_mock

        # Mock AI factory
        mock_ai_factory = MagicMock()
        mock_ai_factory.get_video_provider.return_value = mock_video_provider

        # Mock storage service
        mock_storage = AsyncMock()
        mock_storage.save.side_effect = lambda data, filename, content_type: filename

        # Mock task store (Redis)
        mock_task_store = AsyncMock()
        mock_task_store.get.side_effect = [
            # story data (dialogues should be list of strings for video task)
            {"dialogues": [[f"Page {i} dialogue text"] for i in range(5)]},
            # image data
            {"images": [{"imageUUID": uuid} for uuid in mock_image_uuids]},
            # video cache (첫 시도 전에는 없음)
            None
        ]
        mock_task_store.set.return_value = None

        # Mock database
        mock_db_session = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get.return_value = mock_book
        mock_repo.get_with_pages.return_value = mock_book
        mock_repo.update.return_value = mock_book

        # Mock limiters
        mock_semaphore = AsyncMock()
        mock_semaphore.__aenter__ = AsyncMock()
        mock_semaphore.__aexit__ = AsyncMock()

        mock_limiters = MagicMock()
        mock_limiters.video_generation = mock_semaphore

        with patch("backend.features.storybook.tasks.core.get_ai_factory", return_value=mock_ai_factory):
            with patch("backend.features.storybook.tasks.core.get_storage_service", return_value=mock_storage):
                with patch("backend.features.storybook.tasks.core.TaskStore", return_value=mock_task_store):
                    with patch("backend.features.storybook.tasks.core.AsyncSessionLocal") as mock_session:
                        with patch("backend.features.storybook.tasks.core.BookRepository", return_value=mock_repo):
                            with patch("backend.features.storybook.tasks.core.get_limiters", return_value=mock_limiters):
                                with patch("asyncio.sleep", return_value=asyncio.sleep(0)):  # 폴링/재시도 대기 제거
                                    with patch("backend.core.config.settings.task_video_max_retries", 2):
                                        mock_session.return_value.__aenter__.return_value = mock_db_session
                                        mock_session.return_value.__aexit__.return_value = None

                                        # When
                                        # Note: asyncio.sleep이 mock되어 즉시 진행되므로,
                                        # 폴링 루프는 한 번의 체크 후 타임아웃 처리됨
                                        result = await generate_video_task(book_id, task_context)

        # Then
        # 1. Task 결과 검증
        assert result.status == TaskStatus.COMPLETED  # 부분 성공

        # 2. Request 호출 횟수 검증
        assert request_count == 7  # 5 (initial) + 2 (retry for idx 3, 4)

        # 3. Result 검증
        assert result.result["total_videos"] == 5
        assert result.result["completed_videos"] == 4  # idx 0, 1, 2, 3
        assert result.result["failed_videos"] == 1  # idx 4
        assert result.result.get("partial_failure") == True

        # 4. Storage upload 검증 (성공한 4개만 업로드)
        assert mock_storage.save.call_count == 4  # idx 0, 1, 2, 3

        # 5. DB update 검증
        update_call_args = mock_repo.update.call_args
        task_metadata = update_call_args[1]["task_metadata"]

        video_summary = task_metadata["video"]
        assert video_summary["status"] == "partially_completed"
        assert video_summary["total_items"] == 5
        assert video_summary["completed_items"] == 4
        assert len(video_summary["failed_items"]) == 1

        failed_item = video_summary["failed_items"][0]
        assert failed_item["index"] == 4
        assert "timeout" in failed_item["last_error"].lower()

        print(f"✓ Polling with timeout retry: {video_summary['completed_items']}/{video_summary['total_items']} completed")
        print(f"✓ Failed item: idx {failed_item['index']}, reason: {failed_item['last_error']}")


class TestVideoTaskPollingWithFailedStatus:
    """Video Task 폴링 중 failed 상태 감지 테스트"""

    @pytest.mark.asyncio
    async def test_video_polling_detects_failed_status(self, task_context, mock_book, mock_image_uuids):
        """
        시나리오: 폴링 중 일부 비디오가 failed 상태 반환

        Phase 1 (요청):
        - 5개 비디오 요청 → 5개 task_uuid 획득

        Phase 2 (폴링):
        - idx 0, 1, 2: completed
        - idx 3: failed (API 에러)
        - idx 4: processing (타임아웃)

        Phase 3 (재시도):
        - idx 3, 4: 새로운 요청
        - idx 3: completed
        - idx 4: failed

        최종: 4/5 완료, COMPLETED (부분 성공)
        """
        # Given
        book_id = task_context.book_id

        # Mock video provider
        mock_video_provider = AsyncMock()

        request_count = 0

        async def generate_video_mock(image_uuid=None, prompt=None):
            nonlocal request_count
            request_count += 1

            if request_count <= 5:
                idx = request_count - 1
                return f"task-uuid-{idx}-v1"
            elif request_count <= 7:
                idx = [3, 4][request_count - 6]
                return f"task-uuid-{idx}-v2"

            raise AssertionError(f"Unexpected request count: {request_count}")

        mock_video_provider.generate_video.side_effect = generate_video_mock

        # Polling status
        async def check_status_mock(task_uuid: str):
            # First attempt
            if task_uuid == "task-uuid-0-v1":
                return {"status": "completed", "video_url": "https://example.com/video-0.mp4"}
            elif task_uuid == "task-uuid-1-v1":
                return {"status": "completed", "video_url": "https://example.com/video-1.mp4"}
            elif task_uuid == "task-uuid-2-v1":
                return {"status": "completed", "video_url": "https://example.com/video-2.mp4"}
            elif task_uuid == "task-uuid-3-v1":
                # Failed status
                return {"status": "failed", "error": "Video generation API error"}
            elif task_uuid == "task-uuid-4-v1":
                # Processing (타임아웃)
                return {"status": "processing"}

            # Retry attempt
            elif task_uuid == "task-uuid-3-v2":
                return {"status": "completed", "video_url": "https://example.com/video-3.mp4"}
            elif task_uuid == "task-uuid-4-v2":
                # Failed again
                return {"status": "failed", "error": "Video processing failed"}

            return {"status": "processing"}

        mock_video_provider.check_video_status.side_effect = check_status_mock
        mock_video_provider.download_video.side_effect = lambda url: b"video_data"

        # Mock dependencies
        mock_ai_factory = MagicMock()
        mock_ai_factory.get_video_provider.return_value = mock_video_provider

        mock_storage = AsyncMock()
        mock_storage.save.side_effect = lambda data, filename, content_type: filename

        mock_task_store = AsyncMock()
        mock_task_store.get.side_effect = [
            {"dialogues": [[f"Page {i} dialogue text"] for i in range(5)]},
            {"images": [{"imageUUID": uuid} for uuid in mock_image_uuids]},
            None  # No cache
        ]
        mock_task_store.set.return_value = None

        mock_db_session = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get.return_value = mock_book
        mock_repo.get_with_pages.return_value = mock_book
        mock_repo.update.return_value = mock_book

        mock_semaphore = AsyncMock()
        mock_semaphore.__aenter__ = AsyncMock()
        mock_semaphore.__aexit__ = AsyncMock()
        mock_limiters = MagicMock()
        mock_limiters.video_generation = mock_semaphore

        with patch("backend.features.storybook.tasks.core.get_ai_factory", return_value=mock_ai_factory):
            with patch("backend.features.storybook.tasks.core.get_storage_service", return_value=mock_storage):
                with patch("backend.features.storybook.tasks.core.TaskStore", return_value=mock_task_store):
                    with patch("backend.features.storybook.tasks.core.AsyncSessionLocal") as mock_session:
                        with patch("backend.features.storybook.tasks.core.BookRepository", return_value=mock_repo):
                            with patch("backend.features.storybook.tasks.core.get_limiters", return_value=mock_limiters):
                                with patch("asyncio.sleep", return_value=asyncio.sleep(0)):
                                    with patch("backend.core.config.settings.task_video_max_retries", 2):
                                        mock_session.return_value.__aenter__.return_value = mock_db_session
                                        mock_session.return_value.__aexit__.return_value = None

                                        # When
                                        result = await generate_video_task(book_id, task_context)

        # Then
        # 1. Task 결과 검증
        assert result.status == TaskStatus.COMPLETED

        # 2. Result 검증
        assert result.result["total_videos"] == 5
        assert result.result["completed_videos"] == 4  # idx 0, 1, 2, 3
        assert result.result["failed_videos"] == 1  # idx 4

        # 3. DB update 검증
        update_call_args = mock_repo.update.call_args
        task_metadata = update_call_args[1]["task_metadata"]
        video_summary = task_metadata["video"]

        assert video_summary["status"] == "partially_completed"
        assert video_summary["completed_items"] == 4
        assert len(video_summary["failed_items"]) == 1

        # 4. Failed status가 올바르게 감지되었는지 확인
        failed_item = video_summary["failed_items"][0]
        assert failed_item["index"] == 4
        assert "failed" in failed_item["last_error"].lower()

        print(f"✓ Failed status detection: {video_summary['completed_items']}/{video_summary['total_items']} completed")
        print(f"✓ Detected failed status for idx {failed_item['index']}")
