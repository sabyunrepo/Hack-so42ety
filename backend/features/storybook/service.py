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

#test
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
        tts_producer: Optional[TTSProducer] = None, # Make it optional but we expect it injected
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
        mybooks = await self.book_repo.get_user_books(user_id, skip=0, limit=100)
        current_count = len(mybooks)
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
        level: int=1,

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
        print(f"[BookService] user_id={user_id} 동화책 갯수 검사 시작")
        # write only로 변화 인해 할당량 검사 불화
        # await self._check_book_quota(user_id)

        logger.info("#########################################################################")
        logger.info(f"[BookService] Checking book quota {stories}, {len(stories)}")

        # 2. 페이지 수 검증
        print(f"[BookService] user_id={user_id} 동화책 페이지 수 검사 시작")
        story_page_count = len(stories)
        if story_page_count < 1 or story_page_count > settings.max_pages_per_book:
            raise InvalidPageCountException(
                page_count=story_page_count, max_pages=settings.max_pages_per_book
            )
        
        # 3. 페이지 수, 이미지 수 검증
        print(f"[BookService] user_id={user_id} 동화책 페이지 수 및 이미지 수 검사 시작")
        if story_page_count != len(images):
            raise StoriesImagesMismatchException(
                stories_count=story_page_count, images_count=len(images)
            )


        # 3. Book 레코드 즉시 생성 (모니터링용)
        print(f"[BookService] user_id={user_id} 동화책 임시 생성")
        book = await self.book_repo.create(
            user_id=user_id,
            title="생성중...",  # Story 생성 후 업데이트됨
            status=BookStatus.CREATING,
            voice_id=voice_id,
            level=level,
            pipeline_stage="init",
        )

        # 3-1. Page Skeleton 생성 (len(images)만큼)
        print(f"[BookService] Creating {len(images)} page skeletons")
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

        print(
            f"[BookService] Created book {book.id} for async processing, "
            f"user_id={user_id}, num_pages={story_page_count}"
        )
        # 4. DAG 생성 및 백그라운드 실행
        task_ids = await create_storybook_dag(
            user_id=user_id,
            book_id=book.id,
            stories=stories,
            images=images,
            voice_id=voice_id,
            level=level,
        )

        # 5. Task IDs를 Book 메타데이터에 저장
        book.task_metadata = task_ids
        await self.db_session.commit()

        return await self.book_repo.get_with_pages(book.id)

    async def get_books(self, user_id: uuid.UUID) -> List[Book]:
        """사용자의 책 목록 조회"""
        return await self.book_repo.get_user_books(user_id)

    async def get_book(self, book_id: uuid.UUID, user_id: uuid.UUID = None) -> Book:
        """책 상세 조회"""
        book = await self.book_repo.get_with_pages(book_id)
        if not book:
            raise StorybookNotFoundException(storybook_id=str(book_id))

        # 권한 체크 (user_id가 제공된 경우)
        if user_id and book.user_id != user_id:
            raise StorybookUnauthorizedException(
                storybook_id=str(book_id), user_id=str(user_id)
            )

        return book

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


    def resize_image_for_video(
        image_data: bytes,
        max_width: int = 1920,
        max_height: int = 1080,
        min_width: int = 512,
        min_height: int = 512,
    ) -> bytes:
        """
        비디오 생성을 위해 이미지를 리사이징합니다.
        - aspect ratio 유지
        - 최소/최대 width/height 제한
        - 8의 배수로 조정 (video encoding 요구사항)
        - Runware API 요구사항: width 300-2048 사이

        Args:
            image_data: 원본 이미지 바이너리 데이터
            max_width: 최대 너비 (기본값: 1920)
            max_height: 최대 높이 (기본값: 1080)
            min_width: 최소 너비 (기본값: 512, Runware는 최소 300)
            min_height: 최소 높이 (기본값: 512)

        Returns:
            bytes: 리사이징된 이미지 바이너리 데이터

        사용할 때 'image_base64 = base64.b64encode(resized_image_data).decode('utf-8')'

        이미지 사이즈 확인용 
        img = Image.open(BytesIO(image_data))
        width, height = img.size
        """
        # PIL Image로 로드
        img = Image.open(BytesIO(image_data))
        original_width, original_height = img.size

        print(f"Original image size: {original_width}x{original_height}")

        # Aspect ratio 계산
        aspect_ratio = original_width / original_height

        # 1단계: 이미지가 너무 작은 경우 키우기
        if original_width < min_width or original_height < min_height:
            if aspect_ratio > 1:
                # 가로가 더 긴 경우
                new_width = max(min_width, original_width)
                new_height = int(new_width / aspect_ratio)
                if new_height < min_height:
                    new_height = min_height
                    new_width = int(new_height * aspect_ratio)
            else:
                # 세로가 더 긴 경우
                new_height = max(min_height, original_height)
                new_width = int(new_height * aspect_ratio)
                if new_width < min_width:
                    new_width = min_width
                    new_height = int(new_width / aspect_ratio)
            print(f"Image too small, upscaling to: {new_width}x{new_height}")
        # 2단계: 이미지가 너무 큰 경우 줄이기
        elif original_width > max_width or original_height > max_height:
            if aspect_ratio > max_width / max_height:
                # 너비가 제한 요소
                new_width = max_width
                new_height = int(max_width / aspect_ratio)
            else:
                # 높이가 제한 요소
                new_height = max_height
                new_width = int(max_height * aspect_ratio)
            print(f"Image too large, downscaling to: {new_width}x{new_height}")
        else:
            # 적절한 크기
            new_width = original_width
            new_height = original_height
            print(f"Image size OK, keeping original size")

        # 8의 배수로 조정 (video encoding 요구사항)
        new_width = (new_width // 8) * 8
        new_height = (new_height // 8) * 8

        # 최소 크기 재확인 (8의 배수 조정 후에도 최소 크기 보장)
        if new_width < 304:  # Runware 최소 300, 8의 배수면 304
            new_width = 304
        if new_height < 304:
            new_height = 304

        print(f"Resized image size: {new_width}x{new_height}")

        # 리사이징
        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # BytesIO로 저장
        output = BytesIO()

        # 원본 포맷 유지 (RGBA면 RGB로 변환)
        if img_resized.mode == 'RGBA':
            # PNG로 저장
            img_resized.save(output, format='PNG', optimize=True)
        else:
            # JPEG로 저장 (더 작은 크기)
            if img_resized.mode != 'RGB':
                img_resized = img_resized.convert('RGB')
            img_resized.save(output, format='JPEG', quality=95, optimize=True)

        resized_data = output.getvalue()
        print(f"Image size reduced: {len(image_data)} -> {len(resized_data)} bytes "
                f"({len(resized_data) / len(image_data) * 100:.1f}%)")

        return resized_data
