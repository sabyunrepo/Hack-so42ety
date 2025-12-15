"""
Task Retry Logic Simple Tests
재시도 로직만 간단하게 테스트 (실제 Task 함수의 AI Provider 모킹)
"""

import asyncio
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from backend.features.storybook.tasks.core import (
    generate_story_task,
    finalize_book_task,
)
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


class TestStoryTaskRetryLogic:
    """Story Task 재시도 로직 테스트"""

    @pytest.mark.asyncio
    async def test_story_success_on_first_attempt(self, task_context):
        """첫 시도에서 성공하는 경우"""
        # Given
        book_id = task_context.book_id
        stories = ["A brave knight saves the kingdom"]
        level = 1
        num_pages = 3

        mock_book = MagicMock(spec=Book)
        mock_book.id = uuid.UUID(book_id)
        mock_book.user_id = uuid.UUID(task_context.user_id)
        mock_book.title = "Test Book"
        mock_book.status = BookStatus.CREATING
        mock_book.pipeline_stage = "init"
        mock_book.progress_percentage = 0
        mock_book.task_metadata = {}
        mock_book.pages = []

        # Mock AI responses (두 번 호출됨: Story생성 + Emotion추가)
        ai_response_1 = {
            "title": "The Brave Knight",
            "pages": [
                {
                    "page_number": 1,
                    "image_prompt": "A knight in armor",
                    "dialogues": [
                        {"speaker": "Narrator", "text": "Once upon a time..."}
                    ]
                },
                {
                    "page_number": 2,
                    "image_prompt": "A dragon",
                    "dialogues": [
                        {"speaker": "Knight", "text": "I will save the kingdom!"}
                    ]
                },
                {
                    "page_number": 3,
                    "image_prompt": "Victory celebration",
                    "dialogues": [
                        {"speaker": "Narrator", "text": "And they lived happily ever after."}
                    ]
                }
            ]
        }

        # 두 번째 호출 응답 (Emotion 추가)
        emotion_response = MagicMock()
        emotion_response.stories = [
            {
                "page_number": 1,
                "dialogues": [
                    {"speaker": "Narrator", "text": "Once upon a time...", "emotion": "neutral"}
                ]
            },
            {
                "page_number": 2,
                "dialogues": [
                    {"speaker": "Knight", "text": "I will save the kingdom!", "emotion": "excited"}
                ]
            },
            {
                "page_number": 3,
                "dialogues": [
                    {"speaker": "Narrator", "text": "And they lived happily ever after.", "emotion": "happy"}
                ]
            }
        ]

        mock_story_provider = AsyncMock()
        mock_story_provider.generate_story.side_effect = [ai_response_1, emotion_response]

        mock_ai_factory = MagicMock()
        mock_ai_factory.get_story_provider.return_value = mock_story_provider

        with patch("backend.features.storybook.tasks.core.AsyncSessionLocal") as mock_session:
            with patch("backend.features.storybook.tasks.core.get_ai_factory", return_value=mock_ai_factory):
                with patch("backend.features.storybook.tasks.core.validate_generated_story") as mock_validate:
                    with patch("backend.features.storybook.tasks.core.validate_difficulty") as mock_diff_validate:
                        # Mock validation to always succeed
                        mock_validate.return_value = (
                            "The Brave Knight",  # title
                            [  # stories (pages)
                                {
                                    "page_number": 1,
                                    "image_prompt": "A knight in armor",
                                    "dialogues": [{"speaker": "Narrator", "text": "Once upon a time..."}]
                                },
                                {
                                    "page_number": 2,
                                    "image_prompt": "A dragon",
                                    "dialogues": [{"speaker": "Knight", "text": "I will save the kingdom!"}]
                                },
                                {
                                    "page_number": 3,
                                    "image_prompt": "Victory celebration",
                                    "dialogues": [{"speaker": "Narrator", "text": "And they lived happily ever after."}]
                                }
                            ]
                        )

                        # Mock difficulty validation to always pass
                        mock_diff_validate.return_value = (True, 1.0)  # (is_valid, fk_score)

                        # Mock DB session
                        mock_db_session = AsyncMock()
                        mock_repo = AsyncMock()
                        mock_repo.get.return_value = mock_book
                        mock_repo.update.return_value = mock_book
                        mock_repo.create_pages_bulk.return_value = None

                        mock_session.return_value.__aenter__.return_value = mock_db_session

                        with patch("backend.features.storybook.tasks.core.BookRepository", return_value=mock_repo):
                            # When
                            result = await generate_story_task(book_id, stories, level, num_pages, task_context)

                            # Then
                            assert result.status == TaskStatus.COMPLETED
                            assert mock_story_provider.generate_story.call_count == 2  # Story + Emotion

    @pytest.mark.asyncio
    async def test_story_success_after_retry(self, task_context):
        """두 번째 시도에서 성공하는 경우"""
        # Given
        book_id = task_context.book_id
        stories = ["A brave knight saves the kingdom"]
        level = 1
        num_pages = 3

        mock_book = MagicMock(spec=Book)
        mock_book.id = uuid.UUID(book_id)
        mock_book.user_id = uuid.UUID(task_context.user_id)
        mock_book.title = "Test Book"
        mock_book.status = BookStatus.CREATING
        mock_book.pipeline_stage = "init"
        mock_book.progress_percentage = 0
        mock_book.task_metadata = {}
        mock_book.pages = []

        # Mock AI responses (첫 시도 실패, 재시도 성공, Emotion 추가)
        ai_response = {
            "title": "The Brave Knight",
            "pages": [
                {
                    "page_number": 1,
                    "image_prompt": "A knight in armor",
                    "dialogues": [{"speaker": "Narrator", "text": "Once upon a time..."}]
                }
            ]
        }

        emotion_response = MagicMock()
        emotion_response.stories = [
            {
                "page_number": 1,
                "dialogues": [
                    {"speaker": "Narrator", "text": "Once upon a time...", "emotion": "neutral"}
                ]
            }
        ]

        call_count = 0

        async def generate_story_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("AI service temporarily unavailable")
            elif call_count == 2:
                return ai_response
            else:
                return emotion_response

        mock_story_provider = AsyncMock()
        mock_story_provider.generate_story.side_effect = generate_story_with_retry

        mock_ai_factory = MagicMock()
        mock_ai_factory.get_story_provider.return_value = mock_story_provider

        with patch("backend.features.storybook.tasks.core.AsyncSessionLocal") as mock_session:
            with patch("backend.features.storybook.tasks.core.get_ai_factory", return_value=mock_ai_factory):
                with patch("backend.features.storybook.tasks.core.validate_generated_story") as mock_validate:
                    with patch("backend.features.storybook.tasks.core.validate_difficulty") as mock_diff_validate:
                        with patch("backend.core.config.settings.task_story_max_retries", 3):
                            # Mock validation to always succeed
                            mock_validate.return_value = (
                                "The Brave Knight",  # title
                                [  # stories (pages)
                                    {
                                        "page_number": 1,
                                        "image_prompt": "A knight in armor",
                                        "dialogues": [{"speaker": "Narrator", "text": "Once upon a time..."}]
                                    }
                                ]
                            )

                            # Mock difficulty validation to always pass
                            mock_diff_validate.return_value = (True, 1.0)  # (is_valid, fk_score)

                            mock_db_session = AsyncMock()
                            mock_repo = AsyncMock()
                            mock_repo.get.return_value = mock_book
                            mock_repo.update.return_value = mock_book
                            mock_repo.create_pages_bulk.return_value = None

                            mock_session.return_value.__aenter__.return_value = mock_db_session

                            with patch("backend.features.storybook.tasks.core.BookRepository", return_value=mock_repo):
                                # When
                                result = await generate_story_task(book_id, stories, level, num_pages, task_context)

                                # Then
                                assert result.status == TaskStatus.COMPLETED
                                assert call_count == 3  # 1: fail, 2: success (story), 3: emotion
                                print(f"✓ Retry succeeded after 2 attempts (total {call_count} calls including emotion)")

    @pytest.mark.asyncio
    async def test_story_fail_after_max_retries(self, task_context):
        """최대 재시도 후 실패하는 경우"""
        # Given
        book_id = task_context.book_id
        stories = ["A brave knight saves the kingdom"]
        level = 1
        num_pages = 3

        mock_book = MagicMock(spec=Book)
        mock_book.id = uuid.UUID(book_id)
        mock_book.user_id = uuid.UUID(task_context.user_id)
        mock_book.title = "Test Book"
        mock_book.status = BookStatus.CREATING
        mock_book.pipeline_stage = "init"
        mock_book.progress_percentage = 0
        mock_book.task_metadata = {}

        mock_story_provider = AsyncMock()
        mock_story_provider.generate_story.side_effect = ValueError("AI service persistent error")

        mock_ai_factory = MagicMock()
        mock_ai_factory.get_story_provider.return_value = mock_story_provider

        with patch("backend.features.storybook.tasks.core.AsyncSessionLocal") as mock_session:
            with patch("backend.features.storybook.tasks.core.get_ai_factory", return_value=mock_ai_factory):
                with patch("backend.core.config.settings.task_story_max_retries", 3):
                    mock_db_session = AsyncMock()
                    mock_repo = AsyncMock()
                    mock_repo.get.return_value = mock_book
                    mock_repo.update.return_value = mock_book

                    mock_session.return_value.__aenter__.return_value = mock_db_session

                    with patch("backend.features.storybook.tasks.core.BookRepository", return_value=mock_repo):
                        # When
                        result = await generate_story_task(book_id, stories, level, num_pages, task_context)

                        # Then
                        assert result.status == TaskStatus.FAILED
                        assert mock_story_provider.generate_story.call_count == 3
                        print(f"✓ Failed after {mock_story_provider.generate_story.call_count} retries")


class TestFinalizeTaskMetadata:
    """Finalize Task의 task_metadata 분석 테스트"""

    @pytest.mark.asyncio
    async def test_finalize_with_all_success(self, task_context):
        """모든 Task 성공 시 COMPLETED"""
        # Given
        book_id = task_context.book_id

        mock_book = MagicMock(spec=Book)
        mock_book.id = uuid.UUID(book_id)
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

        with patch("backend.features.storybook.tasks.core.AsyncSessionLocal") as mock_session:
            mock_db_session = AsyncMock()
            mock_repo = AsyncMock()
            mock_repo.get.return_value = mock_book
            mock_repo.update.return_value = mock_book

            mock_session.return_value.__aenter__.return_value = mock_db_session

            with patch("backend.features.storybook.tasks.core.BookRepository", return_value=mock_repo):
                # When
                result = await finalize_book_task(book_id, task_context)

                # Then
                assert result.status == TaskStatus.COMPLETED
                # update 호출 확인
                mock_repo.update.assert_called()
                update_call = mock_repo.update.call_args
                assert update_call[1]["status"] == BookStatus.COMPLETED
                print("✓ Book status set to COMPLETED")

    @pytest.mark.asyncio
    async def test_finalize_with_partial_failure(self, task_context):
        """일부 Task 실패 시 PARTIALLY_COMPLETED"""
        # Given
        book_id = task_context.book_id

        mock_book = MagicMock(spec=Book)
        mock_book.id = uuid.UUID(book_id)
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

        with patch("backend.features.storybook.tasks.core.AsyncSessionLocal") as mock_session:
            mock_db_session = AsyncMock()
            mock_repo = AsyncMock()
            mock_repo.get.return_value = mock_book
            mock_repo.update.return_value = mock_book

            mock_session.return_value.__aenter__.return_value = mock_db_session

            with patch("backend.features.storybook.tasks.core.BookRepository", return_value=mock_repo):
                # When
                result = await finalize_book_task(book_id, task_context)

                # Then
                assert result.status == TaskStatus.COMPLETED
                update_call = mock_repo.update.call_args
                assert update_call[1]["status"] == BookStatus.PARTIALLY_COMPLETED
                # task_metadata에 overall_status 추가 확인
                assert "overall_status" in update_call[1]["task_metadata"]
                assert update_call[1]["task_metadata"]["overall_status"] == BookStatus.PARTIALLY_COMPLETED
                print("✓ Book status set to PARTIALLY_COMPLETED")
                print(f"✓ Image failures detected: {len(mock_book.task_metadata['image']['failed_items'])} items")

    @pytest.mark.asyncio
    async def test_finalize_with_multiple_partial_failures(self, task_context):
        """여러 Task에서 부분 실패 시 PARTIALLY_COMPLETED"""
        # Given
        book_id = task_context.book_id

        mock_book = MagicMock(spec=Book)
        mock_book.id = uuid.UUID(book_id)
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

        with patch("backend.features.storybook.tasks.core.AsyncSessionLocal") as mock_session:
            mock_db_session = AsyncMock()
            mock_repo = AsyncMock()
            mock_repo.get.return_value = mock_book
            mock_repo.update.return_value = mock_book

            mock_session.return_value.__aenter__.return_value = mock_db_session

            with patch("backend.features.storybook.tasks.core.BookRepository", return_value=mock_repo):
                # When
                result = await finalize_book_task(book_id, task_context)

                # Then
                assert result.status == TaskStatus.COMPLETED
                update_call = mock_repo.update.call_args
                assert update_call[1]["status"] == BookStatus.PARTIALLY_COMPLETED
                print("✓ Book status set to PARTIALLY_COMPLETED")
                print(f"✓ Image failures: {len(mock_book.task_metadata['image']['failed_items'])} items")
                print(f"✓ Video failures: {len(mock_book.task_metadata['video']['failed_items'])} items")
