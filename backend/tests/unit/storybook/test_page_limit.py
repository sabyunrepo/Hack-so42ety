"""
Page Count Limit Validation Tests (Unit Test with Mocks)
페이지 수 제한 검증 테스트 (Mock 기반 단위 테스트)

📋 테스트 목적:
    책 생성 시 페이지 수 제한(MAX_PAGES_PER_BOOK)을 검증하는 비즈니스 로직을 테스트합니다.

🎯 주요 테스트 항목:
    1. 페이지 수 범위 검증 (1~5 페이지)
       - 최소값(1): 통과
       - 최대값(5): 통과
       - 0, 음수: InvalidPageCountException 발생
       - 6 이상: InvalidPageCountException 발생

    2. create_storybook() 메서드
       - num_pages 파라미터 검증
       - 유효 범위: 1 ≤ num_pages ≤ settings.max_pages_per_book

    3. create_storybook_with_images() 메서드
       - stories 배열 길이 검증
       - 유효 범위: 1 ≤ len(stories) ≤ settings.max_pages_per_book

    4. 환경변수 설정 검증
       - 기본값(5페이지) 사용
       - 커스텀 값(환경변수) 사용

    5. 예외 세부 정보 검증
       - requested: 요청된 페이지 수
       - min: 최소 페이지 수 (1)
       - max: 최대 페이지 수 (설정값)

⚙️ 테스트 방식:
    - Mock 객체 사용 (실제 DB 없이 메모리에서 테스트)
    - BookRepository, StorageService, AIFactory 모두 모킹
    - 페이지 수 검증 로직만 독립적으로 테스트
    - 매우 빠른 실행 속도 (0.1초 이내)

🔗 관련 파일:
    - backend/features/storybook/service.py (BookOrchestratorService)
    - backend/features/storybook/exceptions.py (InvalidPageCountException)
    - backend/features/storybook/schemas.py (CreateBookRequest validator)
    - backend/core/config.py (Settings.max_pages_per_book)

⚠️ 주의사항:
    - @patch로 settings를 모킹할 때는 max_books_per_user도 함께 설정 필요
      (create_storybook 내부에서 quota check가 먼저 실행되기 때문)

💡 테스트 시나리오 예시:
    ✅ num_pages=3 → 통과
    ✅ num_pages=5 → 통과
    ❌ num_pages=0 → InvalidPageCountException
    ❌ num_pages=6 → InvalidPageCountException
    ✅ MAX_PAGES_PER_BOOK=10, num_pages=10 → 통과 (환경변수 반영)
"""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.storybook.service import BookOrchestratorService
from backend.features.storybook.repository import BookRepository
from backend.features.storybook.exceptions import InvalidPageCountException
from backend.infrastructure.storage.base import AbstractStorageService
from backend.infrastructure.ai.factory import AIProviderFactory


@pytest.fixture
def mock_book_repo():
    """Mock Book Repository"""
    repo = MagicMock(spec=BookRepository)
    repo.count_active_books = AsyncMock(return_value=0)  # quota 통과
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
def book_service(mock_book_repo, mock_storage_service, mock_ai_factory, mock_db_session):
    """Book Orchestrator Service Fixture"""
    return BookOrchestratorService(
        book_repo=mock_book_repo,
        storage_service=mock_storage_service,
        ai_factory=mock_ai_factory,
        db_session=mock_db_session,
    )


@pytest.mark.asyncio
class TestPageCountValidation:
    """페이지 수 검증 테스트"""

    async def test_valid_page_count_min(self, book_service, mock_book_repo):
        """최소 페이지 수 (1) 검증 통과"""
        user_id = uuid.uuid4()

        # num_pages=1 은 유효해야 함
        # 실제 생성은 모킹되지 않았으므로 에러가 나지만,
        # InvalidPageCountException이 아닌 다른 에러가 발생해야 함
        try:
            await book_service.create_storybook(
                user_id=user_id,
                prompt="Test story",
                num_pages=1,
            )
        except InvalidPageCountException:
            pytest.fail("num_pages=1 should be valid")
        except Exception:
            # 다른 예외는 괜찮음 (AI provider 등)
            pass

    async def test_valid_page_count_max(self, book_service):
        """최대 페이지 수 (5) 검증 통과"""
        user_id = uuid.uuid4()

        try:
            await book_service.create_storybook(
                user_id=user_id,
                prompt="Test story",
                num_pages=5,
            )
        except InvalidPageCountException:
            pytest.fail("num_pages=5 should be valid")
        except Exception:
            # 다른 예외는 괜찮음
            pass

    async def test_valid_page_count_middle(self, book_service):
        """중간 페이지 수 (3) 검증 통과"""
        user_id = uuid.uuid4()

        try:
            await book_service.create_storybook(
                user_id=user_id,
                prompt="Test story",
                num_pages=3,
            )
        except InvalidPageCountException:
            pytest.fail("num_pages=3 should be valid")
        except Exception:
            pass

    async def test_invalid_page_count_zero(self, book_service):
        """페이지 수 0 은 거부되어야 함"""
        user_id = uuid.uuid4()

        with pytest.raises(InvalidPageCountException) as exc_info:
            await book_service.create_storybook(
                user_id=user_id,
                prompt="Test story",
                num_pages=0,
            )

        assert exc_info.value.details["requested"] == 0
        assert exc_info.value.details["min"] == 1
        assert exc_info.value.details["max"] == 5

    async def test_invalid_page_count_negative(self, book_service):
        """음수 페이지 수는 거부되어야 함"""
        user_id = uuid.uuid4()

        with pytest.raises(InvalidPageCountException):
            await book_service.create_storybook(
                user_id=user_id,
                prompt="Test story",
                num_pages=-1,
            )

    async def test_invalid_page_count_over_limit(self, book_service):
        """최대 제한(5) 초과 시 거부"""
        user_id = uuid.uuid4()

        with pytest.raises(InvalidPageCountException) as exc_info:
            await book_service.create_storybook(
                user_id=user_id,
                prompt="Test story",
                num_pages=6,
            )

        assert exc_info.value.details["requested"] == 6
        assert exc_info.value.details["max"] == 5

    async def test_invalid_page_count_far_over_limit(self, book_service):
        """훨씬 큰 페이지 수도 거부"""
        user_id = uuid.uuid4()

        with pytest.raises(InvalidPageCountException) as exc_info:
            await book_service.create_storybook(
                user_id=user_id,
                prompt="Test story",
                num_pages=20,
            )

        assert exc_info.value.details["requested"] == 20
        assert exc_info.value.details["max"] == 5

    @patch("backend.features.storybook.service.settings")
    async def test_page_count_respects_custom_max(
        self, mock_settings, book_service
    ):
        """환경변수로 설정된 max_pages_per_book을 존중"""
        user_id = uuid.uuid4()
        mock_settings.max_pages_per_book = 10  # 커스텀 제한: 10페이지
        mock_settings.max_books_per_user = 3  # quota check를 위해 필요

        # 10페이지는 이제 유효해야 함
        try:
            await book_service.create_storybook(
                user_id=user_id,
                prompt="Test story",
                num_pages=10,
            )
        except InvalidPageCountException:
            pytest.fail("num_pages=10 should be valid with custom max=10")
        except Exception:
            pass

    @patch("backend.features.storybook.service.settings")
    async def test_page_count_fails_over_custom_max(
        self, mock_settings, book_service
    ):
        """커스텀 제한 초과 시 거부"""
        user_id = uuid.uuid4()
        mock_settings.max_pages_per_book = 10
        mock_settings.max_books_per_user = 3  # quota check를 위해 필요

        with pytest.raises(InvalidPageCountException) as exc_info:
            await book_service.create_storybook(
                user_id=user_id,
                prompt="Test story",
                num_pages=11,
            )

        assert exc_info.value.details["requested"] == 11
        assert exc_info.value.details["max"] == 10


@pytest.mark.asyncio
class TestPageCountValidationWithImages:
    """이미지 기반 생성에서의 페이지 수 검증 테스트"""

    @pytest.fixture
    def book_service(self, mock_book_repo, mock_storage_service, mock_ai_factory, mock_db_session):
        """Book Orchestrator Service Fixture"""
        return BookOrchestratorService(
            book_repo=mock_book_repo,
            storage_service=mock_storage_service,
            ai_factory=mock_ai_factory,
            db_session=mock_db_session,
        )

    async def test_valid_stories_count(self, book_service):
        """유효한 스토리 개수 (5개 이하)"""
        user_id = uuid.uuid4()
        stories = ["Story 1", "Story 2", "Story 3"]
        images = [b"img1", b"img2", b"img3"]
        content_types = ["image/png"] * 3

        try:
            await book_service.create_storybook_with_images(
                user_id=user_id,
                stories=stories,
                images=images,
                image_content_types=content_types,
            )
        except InvalidPageCountException:
            pytest.fail("3 stories should be valid")
        except Exception:
            pass

    async def test_invalid_stories_count_over_limit(self, book_service):
        """스토리 개수가 5개 초과 시 거부"""
        user_id = uuid.uuid4()
        stories = [f"Story {i}" for i in range(6)]
        images = [b"img"] * 6
        content_types = ["image/png"] * 6

        with pytest.raises(InvalidPageCountException) as exc_info:
            await book_service.create_storybook_with_images(
                user_id=user_id,
                stories=stories,
                images=images,
                image_content_types=content_types,
            )

        assert exc_info.value.details["requested"] == 6
        assert exc_info.value.details["max"] == 5

    async def test_invalid_stories_count_zero(self, book_service):
        """스토리 개수가 0개일 때 거부"""
        user_id = uuid.uuid4()

        with pytest.raises(InvalidPageCountException):
            await book_service.create_storybook_with_images(
                user_id=user_id,
                stories=[],
                images=[],
                image_content_types=[],
            )

    @patch("backend.features.storybook.service.settings")
    async def test_stories_count_respects_custom_max(
        self, mock_settings, book_service
    ):
        """이미지 기반 생성도 커스텀 제한 존중"""
        user_id = uuid.uuid4()
        mock_settings.max_pages_per_book = 10
        mock_settings.max_books_per_user = 3  # quota check를 위해 필요

        stories = [f"Story {i}" for i in range(10)]
        images = [b"img"] * 10
        content_types = ["image/png"] * 10

        try:
            await book_service.create_storybook_with_images(
                user_id=user_id,
                stories=stories,
                images=images,
                image_content_types=content_types,
            )
        except InvalidPageCountException:
            pytest.fail("10 stories should be valid with custom max=10")
        except Exception:
            pass


@pytest.mark.asyncio
class TestExceptionDetails:
    """예외 세부 정보 테스트"""

    @pytest.fixture
    def book_service(self, mock_book_repo, mock_storage_service, mock_ai_factory, mock_db_session):
        """Book Orchestrator Service Fixture"""
        return BookOrchestratorService(
            book_repo=mock_book_repo,
            storage_service=mock_storage_service,
            ai_factory=mock_ai_factory,
            db_session=mock_db_session,
        )

    async def test_exception_contains_correct_details(self, book_service):
        """예외에 올바른 세부 정보가 포함되는지 확인"""
        user_id = uuid.uuid4()

        with pytest.raises(InvalidPageCountException) as exc_info:
            await book_service.create_storybook(
                user_id=user_id,
                prompt="Test",
                num_pages=10,
            )

        exception = exc_info.value
        assert exception.details["requested"] == 10
        assert exception.details["min"] == 1
        assert exception.details["max"] == 5
        assert "페이지 수는 1~5 사이여야 합니다" in str(exception)
