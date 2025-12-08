"""
Book Orchestrator Service Module
동화책 생성 전체 프로세스 조율
"""

import asyncio
import re
from typing import List, Optional

from ..core.config import settings
from ..core.logging import get_logger
from ..domain.models import Book, Dialogue, Page
from ..storage import AbstractStorageService

# 서비스 imports
from .tts_service import TtsService
from .story_generator_service import StoryGeneratorService
from .image_generator_service import ImageGeneratorService
from .video_generator_service import VideoGeneratorService

logger = get_logger(__name__)


class BookOrchestratorService:
    """
    동화책 생성 전체 프로세스 조율 서비스

    책임:
    - 전체 동화책 생성 프로세스 조율
    - 하위 서비스 간 협업 관리
    - 에러 처리 및 롤백

    의존성:
    - 모든 하위 서비스는 생성자를 통해 주입 (DI)
    - 클라이언트 생명주기는 의존성 컨테이너에서 관리
    """

    def __init__(
        self,
        storage_service: AbstractStorageService,
        tts_service: TtsService,
        story_generator: StoryGeneratorService,
        image_generator: ImageGeneratorService,
        video_generator: VideoGeneratorService,
    ):
        """
        BookOrchestratorService 초기화

        Args:
            storage_service: 파일 스토리지 서비스
            tts_service: TTS 오디오 생성 서비스
            story_generator: AI 스토리 생성 서비스
            image_generator: 이미지 생성 서비스
            video_generator: 비디오 생성 서비스
        """
        self.storage = storage_service
        self.tts_service = tts_service
        self.story_generator = story_generator
        self.image_generator = image_generator
        self.video_generator = video_generator

        logger.info("BookOrchestratorService initialized (DI mode)")

    async def create_book_with_tts(
        self,
        stories: List[str],
        images: List[dict],
        voice_id: Optional[str] = None,
        book_id: Optional[str] = None,
    ) -> Book:
        """
        동화책 생성 및 TTS 오디오 생성

        Args:
            stories: 각 페이지의 텍스트 배열
            images: 각 페이지의 이미지 파일 배열 (stories와 순서 매칭)
            voice_id: TTS 음성 ID
            book_id: 기존 Book ID (선택, BackgroundTasks에서 사용)

        Returns:
            Book: 생성된 Book 객체 (status='success' or 'error')

        Raises:
            ValueError: stories와 images 길이가 다를 경우
            Exception: 처리 중 오류 발생 시
        """
        # 입력 검증
        if not stories or not images:
            raise ValueError("At least one page is required")

        if len(stories) != len(images):
            raise ValueError(
                f"Stories and images count mismatch: {len(stories)} vs {len(images)}"
            )

        # Book 객체 초기화 (status='process')
        if book_id:
            # 기존 Book ID 사용 (BackgroundTasks에서 호출 시)
            book = Book(
                id=book_id,
                title="",  # 기본 제목 (나중에 업데이트 가능)
                voice_id=voice_id,
                cover_image="",
                status="process",
                pages=[],
            )
        else:
            # 새 Book 생성 (일반 호출 시)
            book = Book(
                title="", cover_image="", voice_id=voice_id, status="process", pages=[]
            )

        try:
            # 1. AI 스토리 생성
            result = await self.story_generator.generate_story_with_ai(stories)
            logger.info(f"Generated stories: {result}")

            if result is None or not result.get("stories"):
                logger.warning("[BookOrchestratorService] No stories generated")
                book.status = "error"
                return book

            stories = result["stories"]
            book.title = result.get("title", "Untitled Story")

            # 2. TTS 생성 태스크 (병렬 처리)
            tts_task = asyncio.create_task(
                self.tts_service.generate_tts_audio(stories, voice_id)
            )

            # 3. 이미지 + 비디오 병렬 생성
            page_tasks = [
                asyncio.create_task(self._generate_page(i, story, img, book.id))
                for i, (story, img) in enumerate(zip(stories, images))
            ]

            # 4. 병렬 처리 결과 수집
            tts_results, page_results = await asyncio.gather(
                tts_task, asyncio.gather(*page_tasks)
            )
            logger.info(f"[BookOrchestratorService] TTS results: {tts_results}")
            logger.info(f"[BookOrchestratorService] Page results: {page_results}")

            # 5. TTS 결과를 각 Page의 Dialogue로 추가
            for page_idx, (page, story_dialogues, tts_urls) in enumerate(
                zip(page_results, stories, tts_results)
            ):
                # 각 대사마다 Dialogue 객체 생성
                for dialogue_idx, (text, audio_url) in enumerate(
                    zip(story_dialogues, tts_urls if tts_urls else [])
                ):
                    # 감정 태그 제거 (예: "[excited] Hello!" -> "Hello!")
                    clean_text = re.sub(r"\[[\w\s]+\]\s*", "", text).strip()

                    dialogue = Dialogue(
                        index=dialogue_idx + 1,
                        text=clean_text,
                        part_audio_url=audio_url if audio_url else "",
                    )
                    page.dialogues.append(dialogue)

                logger.info(
                    f"[BookOrchestratorService] Page {page_idx + 1}: {len(page.dialogues)} dialogues added"
                )

            # 6. Book 객체 조합
            book.pages = page_results

            # 첫 번째 페이지의 이미지를 커버로 설정
            if page_results and page_results[0].content:
                # video 타입이면 fallback_image를 커버로 사용
                if page_results[0].type == "video" and page_results[0].fallback_image:
                    book.cover_image = page_results[0].fallback_image
                else:
                    book.cover_image = page_results[0].content

            book.status = "success"
            logger.info(
                f"[BookOrchestratorService] Book creation completed successfully: {book.id}"
            )
            return book

        except Exception as e:
            logger.error(
                f"[BookOrchestratorService] Book creation failed: {e}", exc_info=True
            )
            book.status = "error"

            # 롤백: 업로드된 파일 삭제 시도 (오디오 포함)
            logger.warning(
                f"[BookOrchestratorService] Attempting rollback: deleting book assets {book.id}..."
            )
            try:
                await self.storage.delete_book_assets(book)
                logger.info(
                    f"[BookOrchestratorService] Rollback completed: book assets deleted"
                )
            except Exception as rollback_error:
                logger.error(
                    f"[BookOrchestratorService] Rollback failed: {rollback_error}"
                )

            raise

    async def _generate_page(
        self, index: int, story: List[str], image: dict, book_id: str
    ):
        """
        페이지 시나리오에 대한 이미지 및 비디오 생성 및 Page 객체 조립

        Args:
            index: 페이지 인덱스
            story: 페이지 시나리오 텍스트 배열
            image: 업로드할 이미지 파일
            book_id: Book ID

        Returns:
            Page: 생성된 페이지 객체

        Raises:
            Exception: 이미지 생성 실패 시 (필수 리소스)
        """
        page_id = f"page_{index + 1}"

        # 1. 이미지 생성 (템플릿 또는 GenAI)
        # 현재는 템플릿 모드 (settings.use_template_mode)
        if settings.use_template_mode:
            image_url = await self.image_generator.generate_image_from_template(
                index, story, image, book_id, page_id
            )
        else:
            image_url = await self.image_generator.generate_image_with_genai(
                index, story, image, book_id, page_id
            )

        # 이미지 생성 실패 체크 (필수 리소스)
        if not image_url:
            error_msg = f"Image generation failed for page {index + 1}"
            logger.error(f"[BookOrchestratorService] {error_msg}")
            raise Exception(error_msg)

        # 2. 비디오 생성 (템플릿 또는 Kling API)
        # 비디오는 선택적 리소스 - 실패해도 이미지로 대체 가능
        if settings.use_template_mode:
            video_url = await self.video_generator.generate_video_from_template(
                index, story, image_url, book_id, page_id
            )
        else:
            # Kling API 사용 (GenAI 대신)
            video_url = await self.video_generator.generate_video_with_kling(
                index, story, image_url, book_id, page_id
            )

        # 3. Page 객체 조립
        page = await self._assemble_page(index, image_url, video_url)

        return page

    async def delete_book_assets(self, book: Book) -> bool:
        """
        Book에 속한 모든 파일 리소스 삭제

        StorageService를 사용하여 이미지, 비디오, 오디오 파일 삭제
        Repository는 메타데이터만 삭제하므로, Service가 파일 삭제 조율

        Args:
            book: 파일을 삭제할 Book 객체

        Returns:
            bool: 삭제 성공 여부
        """
        try:
            # StorageService를 통해 Book의 모든 리소스 삭제 (오디오 포함)
            result = await self.storage.delete_book_assets(book)

            if result:
                logger.info(f"[BookOrchestratorService] Book assets deleted: {book.id}")
            else:
                logger.warning(
                    f"[BookOrchestratorService] Some assets failed to delete: {book.id}"
                )

            return result
        except Exception as e:
            logger.error(
                f"[BookOrchestratorService] Failed to delete book assets: {e}",
                exc_info=True,
            )
            return False

    async def _assemble_page(
        self,
        index: int,
        image_url: str,
        video_url: Optional[str],
    ) -> Page:
        """
        이미지, 비디오를 조합하여 Page 객체 생성

        Args:
            index: 페이지 인덱스
            image_url: 생성된 이미지 URL
            video_url: 생성된 비디오 URL (선택적)

        Returns:
            Page: 생성된 페이지 객체
        """
        try:
            # 비디오 생성 성공 시 - video 타입 페이지
            if video_url:
                page = Page(
                    index=index + 1,
                    type="video",
                    content=video_url,
                    fallback_image=image_url,
                    dialogues=[],
                )
                logger.info(
                    f"[BookOrchestratorService] Page {index + 1} generated - "
                    f"Type: video, Content: {video_url}, Fallback: {image_url}"
                )
            else:
                # 비디오 생성 실패 시 - image 타입 페이지
                page = Page(
                    index=index + 1,
                    type="image",
                    content=image_url,
                    fallback_image="",
                    dialogues=[],
                )
                logger.info(
                    f"[BookOrchestratorService] Page {index + 1} generated - "
                    f"Type: image, Content: {image_url}"
                )

            return page

        except Exception as e:
            logger.error(
                f"[BookOrchestratorService] Page generation failed for page {index + 1}: {e}",
                exc_info=True,
            )
            # 에러 발생 시 빈 이미지 페이지 반환
            return Page(
                index=index + 1,
                type="image",
                content="",
                fallback_image="",
                dialogues=[],
            )
