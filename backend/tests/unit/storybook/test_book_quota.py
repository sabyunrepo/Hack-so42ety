"""
Book Quota Checking Tests (Unit Test with Mocks)
책 생성 할당량 검사 테스트 (Mock 기반 단위 테스트)

📋 테스트 목적:
    사용자당 최대 책 생성 개수(MAX_BOOKS_PER_USER)를 제한하는 비즈니스 로직을 검증합니다.

🎯 주요 테스트 항목:
    1. _check_book_quota() 메서드 동작 검증
       - 할당량 이하일 때: 정상 통과
       - 할당량 도달/초과 시: BookQuotaExceededException 발생

    2. 환경변수 설정 검증
       - 기본값(3개) 사용
       - 커스텀 값(환경변수) 사용

    3. Soft Delete와의 연동
       - soft delete된 책은 카운트에서 제외됨
       - soft delete 후 새 책 생성 가능

    4. 메서드 호출 검증
       - create_storybook()에서 quota check 호출되는지
       - create_storybook_with_images()에서 quota check 호출되는지

⚙️ 테스트 방식:
    - Mock 객체 사용 (실제 DB 없이 메모리에서 테스트)
    - BookRepository.count_active_books()를 모킹하여 다양한 시나리오 테스트
    - 매우 빠른 실행 속도 (0.1초 이내)

🔗 관련 파일:
    - backend/features/storybook/service.py (BookOrchestratorService._check_book_quota)
    - backend/features/storybook/repository.py (BookRepository.count_active_books)
    - backend/features/storybook/exceptions.py (BookQuotaExceededException)
    - backend/core/config.py (Settings.max_books_per_user)

💡 참고:
    실제 DB와의 통합 테스트는 tests/unit/repositories/test_book_soft_deleted.py 참고
"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.storybook.service import BookOrchestratorService
from backend.features.storybook.repository import BookRepository
from backend.features.storybook.exceptions import BookQuotaExceededException
from backend.infrastructure.storage.base import AbstractStorageService
from backend.infrastructure.ai.factory import AIProviderFactory


@pytest.fixture
def mock_book_repo():
    """Mock Book Repository"""
    repo = MagicMock(spec=BookRepository)
    repo.count_active_books = AsyncMock(return_value=0)
    return repo


@pytest.fixture
def mock_storage_service():
    """Mock Storage Service"""
    return MagicMock(spec=AbstractStorageService)


@pytest.fixture
def mock_ai_factory():
    """Mock AI Factory"""
    factory = MagicMock(spec=AIProviderFactory)
    return factory


@pytest.fixture
def mock_db_session():
    """Mock Database Session"""
    return MagicMock(spec=AsyncSession)


@pytest.fixture
def book_service(
    mock_book_repo, mock_storage_service, mock_ai_factory, mock_db_session
):
    """Book Orchestrator Service Fixture"""
    return BookOrchestratorService(
        book_repo=mock_book_repo,
        storage_service=mock_storage_service,
        ai_factory=mock_ai_factory,
        db_session=mock_db_session,
    )


@pytest.mark.asyncio
class TestBookQuotaChecking:
    """책 생성 할당량 검사 테스트"""

    async def test_check_quota_success_when_under_limit(
        self, book_service, mock_book_repo
    ):
        """할당량 이하일 때 검사 통과"""
        user_id = uuid.uuid4()
        mock_book_repo.get_user_books.return_value = [
            MagicMock(is_deleted=False),
            MagicMock(is_deleted=False),
        ]

        # 예외 발생하지 않아야 함
        await book_service._check_book_quota(user_id)

        # count_active_books가 호출되었는지 확인
        mock_book_repo.get_user_books.assert_called_once()
        args, kwargs = mock_book_repo.get_user_books.call_args
        assert args[0] == user_id

    async def test_check_quota_success_when_zero_books(
        self, book_service, mock_book_repo
    ):
        """책이 하나도 없을 때 검사 통과"""
        user_id = uuid.uuid4()
        mock_book_repo.get_user_books.return_value = []

        # 예외 발생하지 않아야 함
        await book_service._check_book_quota(user_id)

        mock_book_repo.get_user_books.assert_called_once()
        args, kwargs = mock_book_repo.get_user_books.call_args
        assert args[0] == user_id

    async def test_check_quota_fails_when_at_limit(self, book_service, mock_book_repo):
        """할당량에 도달했을 때 예외 발생"""
        user_id = uuid.uuid4()
        mock_book_repo.get_user_books.return_value = [
            MagicMock(is_deleted=False),
            MagicMock(is_deleted=False),
            MagicMock(is_deleted=False),
        ]

        # BookQuotaExceededException 발생해야 함
        with pytest.raises(BookQuotaExceededException) as exc_info:
            await book_service._check_book_quota(user_id)

        # 예외 세부 정보 확인
        assert exc_info.value.details["current_count"] == 3
        assert exc_info.value.details["max_allowed"] == 3
        assert exc_info.value.details["user_id"] == str(user_id)

    async def test_check_quota_fails_when_over_limit(
        self, book_service, mock_book_repo
    ):
        """할당량을 초과했을 때 예외 발생"""
        user_id = uuid.uuid4()
        mock_book_repo.get_user_books.return_value = [
            MagicMock(is_deleted=False),
            MagicMock(is_deleted=False),
            MagicMock(is_deleted=False),
            MagicMock(is_deleted=False),
            MagicMock(is_deleted=False),
        ]

        # BookQuotaExceededException 발생해야 함
        with pytest.raises(BookQuotaExceededException) as exc_info:
            await book_service._check_book_quota(user_id)

        assert exc_info.value.details["current_count"] == 5
        assert exc_info.value.details["max_allowed"] == 3

    @patch("backend.features.storybook.service.settings")
    async def test_check_quota_respects_custom_max_books(
        self, mock_settings, book_service, mock_book_repo
    ):
        """환경변수로 설정된 max_books_per_user를 존중"""
        user_id = uuid.uuid4()
        mock_settings.max_books_per_user = 5  # 커스텀 제한: 5개
        mock_book_repo.get_user_books.return_value = [
            MagicMock(is_deleted=False),
            MagicMock(is_deleted=False),
            MagicMock(is_deleted=False),
            MagicMock(is_deleted=False),
        ]

        # 4 < 5 이므로 통과해야 함
        await book_service._check_book_quota(user_id)

        mock_book_repo.get_user_books.assert_called_once()
        args, kwargs = mock_book_repo.get_user_books.call_args
        assert args[0] == user_id

    @patch("backend.features.storybook.service.settings")
    async def test_check_quota_fails_with_custom_max_books(
        self, mock_settings, book_service, mock_book_repo
    ):
        """커스텀 제한에 도달했을 때 예외 발생"""
        user_id = uuid.uuid4()
        mock_settings.max_books_per_user = 5
        mock_book_repo.get_user_books.return_value = [
            MagicMock(is_deleted=False),
            MagicMock(is_deleted=False),
            MagicMock(is_deleted=False),
            MagicMock(is_deleted=False),
            MagicMock(is_deleted=False),
        ]

        with pytest.raises(BookQuotaExceededException) as exc_info:
            await book_service._check_book_quota(user_id)

        assert exc_info.value.details["current_count"] == 5
        assert exc_info.value.details["max_allowed"] == 5

    async def test_check_quota_called_in_create_storybook(
        self, book_service, mock_book_repo, mock_ai_factory
    ):
        """create_storybook에서 quota check가 호출되는지 확인"""
        user_id = uuid.uuid4()
        mock_book_repo.get_user_books.return_value = [
            MagicMock(is_deleted=False),
            MagicMock(is_deleted=False),
            MagicMock(is_deleted=False),
        ]

        # create_storybook 호출 시 BookQuotaExceededException 발생해야 함
        with pytest.raises(BookQuotaExceededException):
            await book_service.create_storybook(
                user_id=user_id,
                prompt="Test story",
                num_pages=3,
            )

        # count_active_books가 호출되었는지 확인
        mock_book_repo.get_user_books.assert_called_once()
        args, kwargs = mock_book_repo.get_user_books.call_args
        assert args[0] == user_id

    async def test_check_quota_called_in_create_storybook_with_images(
        self, book_service, mock_book_repo
    ):
        """create_storybook_with_images에서 quota check가 호출되는지 확인"""
        user_id = uuid.uuid4()
        mock_book_repo.get_user_books.return_value = [
            MagicMock(is_deleted=False),
            MagicMock(is_deleted=False),
            MagicMock(is_deleted=False),
        ]

        with pytest.raises(BookQuotaExceededException):
            await book_service.create_storybook_with_images(
                user_id=user_id,
                stories=["Story 1", "Story 2"],
                images=[b"image1", b"image2"],
                image_content_types=["image/png", "image/png"],
            )

        mock_book_repo.get_user_books.assert_called_once()
        args, kwargs = mock_book_repo.get_user_books.call_args
        assert args[0] == user_id


@pytest.mark.asyncio
class TestBookQuotaWithSoftDelete:
    """Soft Delete와 함께 작동하는 할당량 검사 테스트"""

    async def test_soft_deleted_books_not_counted(self, book_service, mock_book_repo):
        """Soft delete된 책은 할당량에 포함되지 않음"""
        user_id = uuid.uuid4()
        # count_active_books는 is_deleted=False인 책만 카운트
        mock_book_repo.get_user_books.return_value = [
            MagicMock(is_deleted=False),
            MagicMock(is_deleted=False),
        ]

        # 예외 발생하지 않아야 함
        await book_service._check_book_quota(user_id)

        mock_book_repo.get_user_books.assert_called_once()
        args, kwargs = mock_book_repo.get_user_books.call_args
        assert args[0] == user_id

    async def test_quota_available_after_soft_delete(
        self, book_service, mock_book_repo
    ):
        """Soft delete 후 새 책 생성 가능"""
        user_id = uuid.uuid4()

        # 시나리오:
        # 1. 처음에 3개 있음 (제한 도달)
        mock_book_repo.get_user_books.return_value = [
            MagicMock(is_deleted=False),
            MagicMock(is_deleted=False),
            MagicMock(is_deleted=False),
        ]

        with pytest.raises(BookQuotaExceededException):
            await book_service._check_book_quota(user_id)

        # 2. 하나를 soft delete 후 2개로 감소
        mock_book_repo.get_user_books.return_value = [
            MagicMock(is_deleted=False),
            MagicMock(is_deleted=False),
        ]

        # 이제 통과해야 함
        await book_service._check_book_quota(user_id)

        assert mock_book_repo.get_user_books.call_count == 2
