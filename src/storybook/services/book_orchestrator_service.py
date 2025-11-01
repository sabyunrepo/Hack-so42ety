"""
Book Orchestrator Service Module
동화책 생성 전체 프로세스 조율
"""

import asyncio
import re
from typing import List, Optional

from ..core.config import settings
from ..core.logging import get_logger
from ..domain.models import Book, Page, Dialogue
from ..storage import AbstractStorageService
from .story_generator_service import StoryGeneratorService
from .image_generator_service import ImageGeneratorService
from .tts_service import TtsService

logger = get_logger(__name__)


class BookOrchestratorService:

    def __init__(
        self,
        storage_service: AbstractStorageService,
        story_generator: StoryGeneratorService,
        tts_service: TtsService,
        image_generator: ImageGeneratorService,
    ):
        self.storage = storage_service
        self.story_generator = story_generator
        self.tts_service = tts_service
        self.image_generator = image_generator

        logger.info("BookOrchestratorService initialized (DI mode)")

    async def create_book_with_tts(
        self,
        stories: List[str],
        images: List[dict],
        book_id: Optional[str] = None,
        voice_id: Optional[str] = None,
    ) -> Book:
        # 입력 검증
        if not stories or not images:
            raise ValueError("At least one page is required")

        if len(stories) != len(images):
            raise ValueError(
                f"Stories and images count mismatch: {len(stories)} vs {len(images)}"
            )

        # 객체 초기화 (status='process')
        if book_id:
            # 기존 Book ID 사용 (BackgroundTasks에서 호출 시)
            book = Book(
                id=book_id,
                title="",  # 기본 제목 (나중에 업데이트 가능)
                cover_image="",
                status="success",
                pages=[],
            )
        else:
            # 새 Book 생성 (일반 호출 시)
            book = Book(title="", cover_image="", status="success", pages=[])

        result = await self.story_generator.generate_story_with_ai(stories)
        stories = result["stories"]

        # 2. TTS 생성 태스크 (병렬 처리)
        tts_task = asyncio.create_task(
            self.tts_service.generate_tts_audio(stories, voice_id)
        )

        page_tasks = [
            asyncio.create_task(self._generate_page(i, story, img, book.id))
            for i, (story, img) in enumerate(zip(stories, images))
        ]

        tts_results, page_results = await asyncio.gather(
            tts_task, asyncio.gather(*page_tasks)
        )
        logger.info(f"tts_results: {tts_results}")
        logger.info(f"page_results: {page_results}")

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

        # Book
        return book

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

        # 2. 비디오 생성 (템플릿 또는 Kling API)

        # 3. Page 객체 조립
        page = await self._assemble_page(index, image_url, video_url=None)

        return page

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
