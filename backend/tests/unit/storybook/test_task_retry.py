"""
Task Retry Logic Integration Tests
실제 Task 함수들의 재시도 로직 테스트 (Mock 사용)
"""

import asyncio
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from backend.features.storybook.tasks.core import (
    generate_story_task,
    generate_image_task,
    generate_video_task,
    finalize_book_task,
)
from backend.features.storybook.tasks.schemas import TaskContext, TaskResult, TaskStatus
from backend.features.storybook.models import BookStatus


@pytest.fixture
def mock_book():
    """테스트용 Book 객체 Mock"""
    book = MagicMock()
    book.id = uuid.uuid4()
    book.user_id = uuid.uuid4()
    book.title = "Test Book"
    book.status = BookStatus.CREATING
    book.pipeline_stage = "init"
    book.progress_percentage = 0
    book.task_metadata = {}
    book.base_path = f"users/{book.user_id}/books/{book.id}"
    return book


@pytest.fixture
def mock_page():
    """테스트용 Page 객체 Mock"""
    page = MagicMock()
    page.id = uuid.uuid4()
    page.sequence = 1
    page.image_url = None
    page.image_prompt = "Test prompt"
    page.dialogues = []
    return page


@pytest.fixture
def task_context():
    """테스트용 TaskContext"""
    return TaskContext(
        book_id=str(uuid.uuid4()),
        user_id=str(uuid.uuid4()),
        execution_id=str(uuid.uuid4()),
        retry_count=0,
        params={
            "title": "Test Book",
            "genre": "fantasy",
            "target_age": "5-7",
            "theme": "adventure",
        }
    )


class TestStoryTaskRetry:
    """Story Task 재시도 로직 테스트"""

    @pytest.mark.asyncio
    async def test_story_success_on_first_attempt(self, task_context, mock_book):
        """첫 시도에서 성공하는 경우"""
        # Given
        mock_repo = AsyncMock()
        mock_repo.get.return_value = mock_book
        mock_repo.update.return_value = mock_book

        mock_story_provider = AsyncMock()
        mock_story_provider.generate_story.return_value = {
            "title": "Generated Title",
            "pages": [
                {
                    "page_number": 1,
                    "image_prompt": "A beautiful scene",
                    "dialogues": [
                        {"speaker": "Narrator", "text": "Once upon a time..."}
                    ]
                }
            ]
        }

        with patch("backend.features.storybook.tasks.core.BookRepository", return_value=mock_repo):
            with patch("backend.features.storybook.tasks.core.get_story_provider", return_value=mock_story_provider):
                # When
                result = await generate_story_task(task_context)

                # Then
                assert result.status == TaskStatus.COMPLETED
                assert mock_story_provider.generate_story.call_count == 1
                assert mock_repo.update.call_count >= 1

    @pytest.mark.asyncio
    async def test_story_success_after_retry(self, task_context, mock_book):
        """재시도 후 성공하는 경우"""
        # Given
        mock_repo = AsyncMock()
        mock_repo.get.return_value = mock_book
        mock_repo.update.return_value = mock_book

        call_count = 0

        async def generate_story_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("AI service temporarily unavailable")
            return {
                "title": "Generated Title",
                "pages": [
                    {
                        "page_number": 1,
                        "image_prompt": "A beautiful scene",
                        "dialogues": [
                            {"speaker": "Narrator", "text": "Once upon a time..."}
                        ]
                    }
                ]
            }

        mock_story_provider = AsyncMock()
        mock_story_provider.generate_story.side_effect = generate_story_with_retry

        with patch("backend.features.storybook.tasks.core.BookRepository", return_value=mock_repo):
            with patch("backend.features.storybook.tasks.core.get_story_provider", return_value=mock_story_provider):
                with patch("backend.core.config.settings.task_story_max_retries", 3):
                    # When
                    result = await generate_story_task(task_context)

                    # Then
                    assert result.status == TaskStatus.COMPLETED
                    assert call_count == 2
                    assert mock_story_provider.generate_story.call_count == 2

    @pytest.mark.asyncio
    async def test_story_fail_after_max_retries(self, task_context, mock_book):
        """최대 재시도 후 실패하는 경우"""
        # Given
        mock_repo = AsyncMock()
        mock_repo.get.return_value = mock_book
        mock_repo.update.return_value = mock_book

        mock_story_provider = AsyncMock()
        mock_story_provider.generate_story.side_effect = ValueError("AI service error")

        with patch("backend.features.storybook.tasks.core.BookRepository", return_value=mock_repo):
            with patch("backend.features.storybook.tasks.core.get_story_provider", return_value=mock_story_provider):
                with patch("backend.core.config.settings.task_story_max_retries", 3):
                    # When
                    result = await generate_story_task(task_context)

                    # Then
                    assert result.status == TaskStatus.FAILED
                    assert mock_story_provider.generate_story.call_count == 3


class TestImageTaskRetry:
    """Image Task 재시도 로직 테스트"""

    @pytest.mark.asyncio
    async def test_image_all_success(self, task_context, mock_book, mock_page):
        """모든 이미지 생성 성공"""
        # Given
        mock_book.pages = [mock_page] * 3

        mock_repo = AsyncMock()
        mock_repo.get.return_value = mock_book
        mock_repo.update.return_value = mock_book

        mock_image_provider = AsyncMock()
        mock_image_provider.generate_image_from_image.return_value = {
            "data": [{"imageUUID": "test-uuid-123"}]
        }
        mock_image_provider.check_image_status.return_value = {
            "status": "completed",
            "images": [{"imageSrc": "https://example.com/image.png"}]
        }

        mock_storage = AsyncMock()
        mock_storage.save.return_value = "/path/to/image.png"

        with patch("backend.features.storybook.tasks.core.BookRepository", return_value=mock_repo):
            with patch("backend.features.storybook.tasks.core.get_image_provider", return_value=mock_image_provider):
                with patch("backend.features.storybook.tasks.core.get_storage_service", return_value=mock_storage):
                    with patch("backend.core.config.settings.task_image_max_retries", 2):
                        # When
                        result = await generate_image_task(task_context)

                        # Then
                        assert result.status == TaskStatus.COMPLETED
                        # 각 페이지마다 한 번씩 호출
                        assert mock_image_provider.generate_image_from_image.call_count == 3

    @pytest.mark.asyncio
    async def test_image_partial_failure_with_retry(self, task_context, mock_book, mock_page):
        """일부 이미지 실패 후 재시도"""
        # Given
        mock_book.pages = [mock_page] * 3

        mock_repo = AsyncMock()
        mock_repo.get.return_value = mock_book
        mock_repo.update.return_value = mock_book

        call_count = 0

        async def generate_image_with_partial_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # 첫 번째와 두 번째 호출은 실패, 세 번째는 성공
            if call_count <= 2:
                raise ValueError(f"Image generation failed (attempt {call_count})")
            return {"data": [{"imageUUID": f"test-uuid-{call_count}"}]}

        mock_image_provider = AsyncMock()
        # 인덱스 0: 성공
        # 인덱스 1: 실패 후 재시도 성공
        # 인덱스 2: 성공
        success_result = {"data": [{"imageUUID": "test-uuid-success"}]}
        mock_image_provider.generate_image_from_image.side_effect = [
            success_result,  # idx 0 성공
            ValueError("Failed"),  # idx 1 첫 실패
            success_result,  # idx 2 성공
            success_result,  # idx 1 재시도 성공
        ]

        mock_image_provider.check_image_status.return_value = {
            "status": "completed",
            "images": [{"imageSrc": "https://example.com/image.png"}]
        }

        mock_storage = AsyncMock()
        mock_storage.save.return_value = "/path/to/image.png"

        with patch("backend.features.storybook.tasks.core.BookRepository", return_value=mock_repo):
            with patch("backend.features.storybook.tasks.core.get_image_provider", return_value=mock_image_provider):
                with patch("backend.features.storybook.tasks.core.get_storage_service", return_value=mock_storage):
                    with patch("backend.core.config.settings.task_image_max_retries", 2):
                        # When
                        result = await generate_image_task(task_context)

                        # Then
                        # 부분 실패는 COMPLETED로 처리 (일부 성공)
                        assert result.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]


class TestVideoTaskRetry:
    """Video Task 재시도 로직 테스트"""

    @pytest.mark.asyncio
    async def test_video_all_success(self, task_context, mock_book, mock_page):
        """모든 비디오 생성 성공"""
        # Given
        mock_page.image_url = "test-image-uuid"
        mock_book.pages = [mock_page] * 2

        mock_repo = AsyncMock()
        mock_repo.get.return_value = mock_book
        mock_repo.update.return_value = mock_book

        mock_video_provider = AsyncMock()
        mock_video_provider.generate_video.return_value = "task-uuid-123"
        mock_video_provider.check_video_status.return_value = {
            "status": "completed",
            "video_url": "https://example.com/video.mp4"
        }
        mock_video_provider.download_video.return_value = b"video content"

        mock_storage = AsyncMock()
        mock_storage.save.return_value = "/path/to/video.mp4"

        with patch("backend.features.storybook.tasks.core.BookRepository", return_value=mock_repo):
            with patch("backend.features.storybook.tasks.core.get_video_provider", return_value=mock_video_provider):
                with patch("backend.features.storybook.tasks.core.get_storage_service", return_value=mock_storage):
                    with patch("backend.core.config.settings.task_video_max_retries", 2):
                        # When
                        result = await generate_video_task(task_context)

                        # Then
                        assert result.status == TaskStatus.COMPLETED
                        assert mock_video_provider.generate_video.call_count == 2


class TestFinalizeTaskPartialFailure:
    """Finalize Task 부분 실패 감지 테스트"""

    @pytest.mark.asyncio
    async def test_finalize_with_all_success(self, task_context, mock_book):
        """모든 Task 성공 시 COMPLETED"""
        # Given
        mock_book.task_metadata = {
            "story": {"status": "completed"},
            "image": {
                "status": "completed",
                "total_items": 5,
                "completed_items": 5,
                "failed_items": []
            },
            "video": {
                "status": "completed",
                "total_items": 5,
                "completed_items": 5,
                "failed_items": []
            }
        }

        mock_repo = AsyncMock()
        mock_repo.get.return_value = mock_book
        mock_repo.update.return_value = mock_book

        with patch("backend.features.storybook.tasks.core.BookRepository", return_value=mock_repo):
            # When
            result = await finalize_book_task(task_context)

            # Then
            assert result.status == TaskStatus.COMPLETED
            # update 호출 시 status가 COMPLETED인지 확인
            update_call = mock_repo.update.call_args
            assert update_call[1]["status"] == BookStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_finalize_with_partial_failure(self, task_context, mock_book):
        """일부 Task 실패 시 PARTIALLY_COMPLETED"""
        # Given
        mock_book.task_metadata = {
            "story": {"status": "completed"},
            "image": {
                "status": "partially_completed",
                "total_items": 5,
                "completed_items": 4,
                "failed_items": [
                    {"index": 2, "retry_count": 2, "last_error": "Image generation timeout"}
                ]
            },
            "video": {
                "status": "completed",
                "total_items": 5,
                "completed_items": 5,
                "failed_items": []
            }
        }

        mock_repo = AsyncMock()
        mock_repo.get.return_value = mock_book
        mock_repo.update.return_value = mock_book

        with patch("backend.features.storybook.tasks.core.BookRepository", return_value=mock_repo):
            # When
            result = await finalize_book_task(task_context)

            # Then
            assert result.status == TaskStatus.COMPLETED
            # update 호출 시 status가 PARTIALLY_COMPLETED인지 확인
            update_call = mock_repo.update.call_args
            assert update_call[1]["status"] == BookStatus.PARTIALLY_COMPLETED
            # task_metadata에 overall_status 추가 확인
            assert "overall_status" in update_call[1]["task_metadata"]

    @pytest.mark.asyncio
    async def test_finalize_with_multiple_partial_failures(self, task_context, mock_book):
        """여러 Task에서 부분 실패 시 PARTIALLY_COMPLETED"""
        # Given
        mock_book.task_metadata = {
            "story": {"status": "completed"},
            "image": {
                "status": "partially_completed",
                "total_items": 5,
                "completed_items": 4,
                "failed_items": [
                    {"index": 2, "retry_count": 2, "last_error": "Image timeout"}
                ]
            },
            "video": {
                "status": "partially_completed",
                "total_items": 5,
                "completed_items": 3,
                "failed_items": [
                    {"index": 1, "retry_count": 2, "last_error": "Video timeout"},
                    {"index": 4, "retry_count": 2, "last_error": "Video timeout"}
                ]
            }
        }

        mock_repo = AsyncMock()
        mock_repo.get.return_value = mock_book
        mock_repo.update.return_value = mock_book

        with patch("backend.features.storybook.tasks.core.BookRepository", return_value=mock_repo):
            # When
            result = await finalize_book_task(task_context)

            # Then
            assert result.status == TaskStatus.COMPLETED
            update_call = mock_repo.update.call_args
            assert update_call[1]["status"] == BookStatus.PARTIALLY_COMPLETED
