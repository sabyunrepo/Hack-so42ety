import uuid
import asyncio
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Book, Page, Dialogue, DialogueTranslation, DialogueAudio, BookStatus
from .repository import BookRepository
from backend.core.utils.trace import log_process
from backend.infrastructure.ai.factory import AIProviderFactory
from backend.infrastructure.storage.base import AbstractStorageService
from backend.core.config import settings
from .tasks.runner import create_storybook_dag
from backend.features.tts.producer import TTSProducer
from .exceptions import (
    StorybookNotFoundException,
    StorybookUnauthorizedException,
    StorybookCreationFailedException,
    ImageUploadFailedException,
    StoriesImagesMismatchException,
    AIGenerationFailedException,
    InvalidPageCountException,
    BookQuotaExceededException,
)

# test
from PIL import Image
from io import BytesIO

logger = logging.getLogger(__name__)


class BookOrchestratorService:
    """
    동화책 생성 및 관리를 위한 오케스트레이터 서비스
    AI Provider와 Repository를 조율하여 동화책을 생성하고 저장합니다.

    DI Pattern: 모든 의존성을 생성자를 통해 주입받습니다.
    """

    def __init__(
        self,
        book_repo: BookRepository,
        storage_service: AbstractStorageService,
        ai_factory: AIProviderFactory,
        db_session: AsyncSession,
        tts_producer: Optional[
            TTSProducer
        ] = None,  # Make it optional but we expect it injected
    ):
        self.book_repo = book_repo
        self.storage_service = storage_service
        self.ai_factory = ai_factory
        self.db_session = db_session
        self.tts_producer = tts_producer

    async def _check_book_quota(self, user_id: uuid.UUID) -> None:
        """
        사용자의 책 생성 할당량을 검사합니다.

        Args:
            user_id: 사용자 UUID

        Raises:
            BookQuotaExceededException: 할당량 초과 시
        """
        current_count = await self.book_repo.count_user_created_books(user_id)
        max_books = settings.max_books_per_user

        if current_count >= max_books:
            raise BookQuotaExceededException(
                current_count=current_count, max_allowed=max_books, user_id=str(user_id)
            )

    @log_process(step="Create Storybook", desc="비동기 동화책 생성 (DAG-Task 패턴)")
    async def create_storybook_async(
        self,
        user_id: uuid.UUID,
        stories: List[str],
        images: List[bytes],
        voice_id: str,
        level: int,
        is_default: bool,
        is_shared: bool = False,
        target_language: str = "en",
    ) -> Book:
        """
        비동기 동화책 생성 (즉시 응답)

        DAG-Task 패턴을 사용하여 백그라운드에서 동화책 생성 파이프라인 실행
        - API 응답: <1초 (Book 레코드만 생성 후 즉시 반환)
        - 전체 처리: ~55초 (백그라운드에서 병렬 실행)

        진행 상황은 book.pipeline_stage, book.progress_percentage로 추적 가능

        Args:
            user_id: 사용자 UUID
            prompt: 동화책 주제/프롬프트
            num_pages: 페이지 수 (기본 5)
            target_age: 대상 연령대 (기본 "5-7")
            theme: 테마 (기본 "adventure")
            is_public: 공개 여부 (기본 False)
            visibility: 가시성 설정 (기본 "private")

        Returns:
            Book: status=CREATING, pipeline_stage="initializing", progress=0

        Raises:
            BookQuotaExceededException: 할당량 초과
            InvalidPageCountException: 페이지 수 범위 초과
        """

        # 1. 할당량 검사
        await self._check_book_quota(user_id)

        logger.info(
            "#########################################################################"
        )
        logger.info(f"[BookService] Checking book quota {stories}, {len(stories)}")

        # 2. 페이지 수 검증
        story_page_count = len(stories)
        if story_page_count < 1 or story_page_count > settings.max_pages_per_book:
            raise InvalidPageCountException(
                page_count=story_page_count, max_pages=settings.max_pages_per_book
            )

        # 3. 페이지 수, 이미지 수 검증
        if story_page_count != len(images):
            raise StoriesImagesMismatchException(
                stories_count=story_page_count, images_count=len(images)
            )

        # 3. Book 레코드 즉시 생성 (모니터링용)
        book = await self.book_repo.create(
            user_id=user_id,
            title="생성중...",  # Story 생성 후 업데이트됨
            status=BookStatus.CREATING,
            voice_id=voice_id,
            level=level,
            is_default=is_default,
            is_shared=is_shared,
            pipeline_stage="init",
        )

        # 3-1. Page Skeleton 생성 (len(images)만큼)
        for page_idx in range(len(images)):
            await self.book_repo.add_page(
                book_id=book.id,
                page_data={
                    "sequence": page_idx + 1,
                    "image_url": None,  # Image Task에서 업데이트
                    "image_prompt": "",
                },
            )

        await self.db_session.commit()

        # Refresh to reload attributes after commit
        await self.db_session.refresh(book)

        # 4. DAG 생성 및 백그라운드 실행
        task_ids = await create_storybook_dag(
            user_id=user_id,
            book_id=book.id,
            stories=stories,
            tts_producer=self.tts_producer,
            images=images,
            voice_id=voice_id,
            level=level,
            target_language=target_language,
        )

        # 5. Task IDs를 Book 메타데이터에 저장
        book.task_metadata = task_ids
        await self.db_session.commit()

        return await self.book_repo.get_with_pages(book.id)

    async def get_books(self, user_id: uuid.UUID) -> List[Book]:
        """사용자의 책 목록 조회"""
        return await self.book_repo.get_user_books(user_id)

    async def get_books_summary(self, user_id: uuid.UUID) -> List[Book]:
        """사용자의 책 목록 조회 (목록용, 페이지 제외)"""
        return await self.book_repo.get_user_books_summary(user_id)

    @log_process(step='Get Storybook', desc='동화책 상세 조회')
    async def get_book(self, book_id: uuid.UUID, user_id: uuid.UUID = None) -> Book:
        """책 상세 조회"""
        book = await self.book_repo.get_with_pages(book_id)
        if not book:
            raise StorybookNotFoundException(storybook_id=str(book_id))

        # 권한 체크
        # 1. 공유된 책은 무조건 접근 허용
        if book.is_shared:
            return book

        # 2. 비공개 책: 로그인 필요 & 소유자 확인
        if not user_id or book.user_id != user_id:
            raise StorybookUnauthorizedException(
                storybook_id=str(book_id),
                user_id=str(user_id) if user_id else "anonymous",
            )

        return book

    @log_process(step='Update Book Sharing', desc='동화책 공유 상태 변경')
    async def update_book_sharing(
        self, book_id: uuid.UUID, is_shared: bool, user_id: uuid.UUID
    ) -> Book:
        """책 공유 상태 업데이트"""
        # 1. 책 조회 (권한 체크 포함)
        # get_book calls repo.get_with_pages which detaches.
        # But we need to verify ownership.
        # However, update() in repo will fetch again attached.

        # Verify ownership simply via get (attached) or query.
        # Efficient way: Use repo.get() which returns attached object?
        # AbstractRepository.get() usually returns scalar.
        # But let's check repo implementation. Repository inherits AbstractRepository.
        # AbstractRepository implementation typically: session.get(Model, id).

        # Safe way:
        book = await self.book_repo.get(book_id)
        if not book:
            raise StorybookNotFoundException(storybook_id=str(book_id))

        if book.user_id != user_id:
            raise StorybookUnauthorizedException(
                storybook_id=str(book_id), user_id=str(user_id)
            )

        # Update
        book.is_shared = is_shared
        self.db_session.add(book)
        await self.db_session.commit()

        # Reload with pages for response schema
        return await self.book_repo.get_with_pages(book_id)

    @log_process(step='Delete Storybook', desc='동화책 삭제 처리')
    async def delete_book(self, book_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """책 삭제"""
        # 본인 책인지 확인 로직은 Repository나 Service 레벨에서 수행
        # 여기서는 Repository의 get을 통해 확인 후 삭제
        book = await self.book_repo.get(book_id)
        if not book:
            raise StorybookNotFoundException(storybook_id=str(book_id))

        if book.user_id != user_id:
            raise StorybookUnauthorizedException(
                storybook_id=str(book_id), user_id=str(user_id)
            )

        # 스토리지 파일 삭제 로직 추가 필요 (S3 비용 절감)
        # ...

        result = await self.book_repo.soft_delete(book_id)
        if result:
            await self.db_session.commit()
        return result
