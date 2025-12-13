"""
Storybook Task Definitions
비동기 파이프라인의 개별 Task 구현
"""

import logging
import uuid
from typing import Dict, Any, Optional

from backend.core.database.session import AsyncSessionLocal
from backend.core.dependencies import get_storage_service, get_ai_factory
from backend.infrastructure.storage.base import AbstractStorageService
from backend.infrastructure.ai.factory import AIProviderFactory
from backend.features.storybook.repository import BookRepository
from backend.features.storybook.models import BookStatus
from backend.core.config import settings

from .schemas import TaskResult, TaskContext, TaskStatus
from .store import TaskStore

logger = logging.getLogger(__name__)


async def generate_story_task(
    book_id: str,
    prompt: str,
    num_pages: int,
    target_age: str,
    theme: str,
    context: TaskContext,
) -> TaskResult:
    """
    Task 1: Story 생성 (AI 호출)

    Args:
        book_id: Book UUID (string)
        prompt: 사용자 입력 프롬프트
        num_pages: 페이지 수
        target_age: 대상 연령대
        theme: 테마
        context: Task 실행 컨텍스트

    Returns:
        TaskResult: 성공 시 story_data_key 반환
    """
    print(f"[Story Task] Starting for book_id={book_id}")
    story_key = f"story:{book_id}"
    return TaskResult(
        status=TaskStatus.COMPLETED,
        result={
            "story_key": story_key,
            "title": "hello",
            "num_pages": 2,
        },
    )

    async with AsyncSessionLocal() as session:
        try:
            repo = BookRepository(session)
            task_store = TaskStore()
            ai_factory = get_ai_factory()

            # 1. Update pipeline stage
            book_uuid = uuid.UUID(book_id)
            book = await repo.get(book_uuid)
            if not book:
                raise ValueError(f"Book {book_id} not found")

            book.pipeline_stage = "story"
            book.progress_percentage = 10
            await session.commit()

            logger.debug(f"[Story Task] Updated book pipeline_stage=story")

            # 2. Generate story (AI call)
            story_provider = ai_factory.get_story_provider()

            full_prompt = f"""
Create a children's story for age {target_age} with theme '{theme}'.
Topic: {prompt}
Length: {num_pages} pages.
Format: JSON with 'title', 'pages' (list of {{"content": "...", "image_prompt": "..."}}).
"""

            logger.debug(f"[Story Task] Calling AI story provider")
            generated_data = await story_provider.generate_story_with_images(
                prompt=full_prompt,
                num_images=num_pages,
                context={"target_age": target_age, "theme": theme},
            )

            # 3. Store in Redis
            story_key = f"story:{book_id}"
            await task_store.set(story_key, generated_data, ttl=3600)

            logger.debug(f"[Story Task] Stored story in Redis: {story_key}")

            # 4. Update DB with title
            book.title = generated_data.get("title", "Untitled Story")
            book.progress_percentage = 20
            await session.commit()

            logger.info(f"[Story Task] Completed for book_id={book_id}")

            return TaskResult(
                status=TaskStatus.COMPLETED,
                result={
                    "story_key": story_key,
                    "title": book.title,
                    "num_pages": len(generated_data.get("pages", [])),
                },
            )

        except Exception as e:
            logger.error(f"[Story Task] Failed for book_id={book_id}: {e}", exc_info=True)

            # Update DB error
            try:
                async with AsyncSessionLocal() as error_session:
                    error_repo = BookRepository(error_session)
                    error_book = await error_repo.get(uuid.UUID(book_id))
                    if error_book:
                        error_book.pipeline_stage = "failed"
                        error_book.error_message = f"Story generation failed: {str(e)}"
                        error_book.status = BookStatus.FAILED
                        await error_session.commit()
            except Exception as db_error:
                logger.error(f"[Story Task] Failed to update error in DB: {db_error}")

            return TaskResult(status=TaskStatus.FAILED, error=str(e))


async def generate_image_task(
    book_id: str,
    page_index: int,
    context: TaskContext,
) -> TaskResult:
    """
    Task 2: Image 생성 (페이지별)

    Args:
        book_id: Book UUID (string)
        page_index: 페이지 인덱스 (0부터 시작)
        context: Task 실행 컨텍스트

    Returns:
        TaskResult: 성공 시 page_id, image_url 반환
    """
    logger.info(f"[Image Task] Starting for book_id={book_id}, page={page_index}")

    async with AsyncSessionLocal() as session:
        try:
            repo = BookRepository(session)
            task_store = TaskStore()
            ai_factory = get_ai_factory()
            storage_service = get_storage_service()

            # 1. Get story data from Redis
            story_key = f"story:{book_id}"
            story_data = await task_store.get(story_key)

            if not story_data:
                raise ValueError(f"Story data not found in Redis: {story_key}")

            pages_data = story_data.get("pages", [])
            if page_index >= len(pages_data):
                raise ValueError(f"Page index {page_index} out of range (total: {len(pages_data)})")

            page_data = pages_data[page_index]
            image_prompt = page_data.get("image_prompt", "")
            content = page_data.get("content", "")

            logger.debug(f"[Image Task] Retrieved story data for page {page_index}")

            # 2. Generate image (AI call)
            image_provider = ai_factory.get_image_provider()

            logger.debug(f"[Image Task] Calling AI image provider")
            image_bytes = await image_provider.generate_image(
                prompt=image_prompt,
                width=1024,
                height=1024
            )

            # 3. Upload to storage
            book_uuid = uuid.UUID(book_id)
            book = await repo.get(book_uuid)
            if not book:
                raise ValueError(f"Book {book_id} not found")

            file_name = f"{book.base_path}/images/page_{page_index + 1}.png"
            image_url = await storage_service.save(
                image_bytes,
                file_name,
                content_type="image/png"
            )

            logger.debug(f"[Image Task] Uploaded image to: {image_url}")

            # 4. Create Page in DB
            page = await repo.add_page(
                book_id=book_uuid,
                page_data={
                    "sequence": page_index + 1,
                    "image_url": image_url,
                    "image_prompt": image_prompt,
                },
            )
            await session.commit()

            # 5. Store page info in Redis for TTS task
            page_info_key = f"page:{book_id}:{page_index}"
            await task_store.set(
                page_info_key,
                {
                    "page_id": str(page.id),
                    "content": content,
                    "image_url": image_url,
                },
                ttl=3600
            )

            logger.info(f"[Image Task] Completed for book_id={book_id}, page={page_index}")

            return TaskResult(
                status=TaskStatus.COMPLETED,
                result={
                    "page_id": str(page.id),
                    "page_index": page_index,
                    "image_url": image_url,
                },
            )

        except Exception as e:
            logger.error(
                f"[Image Task] Failed for book_id={book_id}, page={page_index}: {e}",
                exc_info=True
            )
            return TaskResult(status=TaskStatus.FAILED, error=str(e))


async def generate_tts_task(
    book_id: str,
    page_index: int,
    context: TaskContext,
) -> TaskResult:
    """
    Task 3: TTS 생성 (페이지별)

    Args:
        book_id: Book UUID (string)
        page_index: 페이지 인덱스 (0부터 시작)
        context: Task 실행 컨텍스트

    Returns:
        TaskResult: 성공 시 dialogue_id, audio_url 반환
    """
    logger.info(f"[TTS Task] Starting for book_id={book_id}, page={page_index}")

    async with AsyncSessionLocal() as session:
        try:
            repo = BookRepository(session)
            task_store = TaskStore()
            ai_factory = get_ai_factory()
            storage_service = get_storage_service()

            # 1. Get page info from Redis (created by image task)
            page_info_key = f"page:{book_id}:{page_index}"
            page_info = await task_store.get(page_info_key)

            if not page_info:
                raise ValueError(f"Page info not found in Redis: {page_info_key}")

            page_id_str = page_info.get("page_id")
            content = page_info.get("content", "")

            if not content:
                logger.warning(f"[TTS Task] No content for page {page_index}, skipping")
                return TaskResult(
                    status=TaskStatus.COMPLETED,
                    result={"skipped": True, "reason": "No content"}
                )

            logger.debug(f"[TTS Task] Retrieved page info for page {page_index}")

            # 2. Create dialogue with translation
            page_uuid = uuid.UUID(page_id_str)
            dialogue = await repo.add_dialogue_with_translation(
                page_id=page_uuid,
                speaker="Narrator",
                sequence=1,
                translations=[
                    {"language_code": "en", "text": content, "is_primary": True}
                ],
            )

            # 3. Generate TTS (AI call)
            tts_provider = ai_factory.get_tts_provider()

            logger.debug(f"[TTS Task] Calling AI TTS provider")
            audio_bytes = await tts_provider.text_to_speech(content)

            # 4. Upload to storage
            book_uuid = uuid.UUID(book_id)
            book = await repo.get(book_uuid)
            if not book:
                raise ValueError(f"Book {book_id} not found")

            audio_file_name = f"{book.base_path}/audios/page_{page_index + 1}.mp3"
            audio_url = await storage_service.save(
                audio_bytes,
                audio_file_name,
                content_type="audio/mpeg"
            )

            logger.debug(f"[TTS Task] Uploaded audio to: {audio_url}")

            # 5. Add dialogue audio
            voice_id = (
                settings.DEFAULT_VOICE_ID
                if hasattr(settings, "DEFAULT_VOICE_ID")
                else "default"
            )

            await repo.add_dialogue_audio(
                dialogue_id=dialogue.id,
                language_code="en",
                voice_id=voice_id,
                audio_url=audio_url,
            )
            await session.commit()

            logger.info(f"[TTS Task] Completed for book_id={book_id}, page={page_index}")

            return TaskResult(
                status=TaskStatus.COMPLETED,
                result={
                    "dialogue_id": str(dialogue.id),
                    "page_index": page_index,
                    "audio_url": audio_url,
                },
            )

        except Exception as e:
            logger.error(
                f"[TTS Task] Failed for book_id={book_id}, page={page_index}: {e}",
                exc_info=True
            )
            return TaskResult(status=TaskStatus.FAILED, error=str(e))


async def generate_video_task(
    book_id: str,
    context: TaskContext,
) -> TaskResult:
    """
    Task 4: Video 생성 (전체 책)

    Args:
        book_id: Book UUID (string)
        context: Task 실행 컨텍스트

    Returns:
        TaskResult: 성공 시 video_url 반환 (실패해도 치명적이지 않음)
    """
    logger.info(f"[Video Task] Starting for book_id={book_id}")

    async with AsyncSessionLocal() as session:
        try:
            repo = BookRepository(session)
            ai_factory = get_ai_factory()
            storage_service = get_storage_service()

            # 1. Get book with pages
            book_uuid = uuid.UUID(book_id)
            book = await repo.get_with_pages(book_uuid)

            if not book:
                raise ValueError(f"Book {book_id} not found")

            if not book.pages:
                raise ValueError(f"Book {book_id} has no pages")

            logger.debug(f"[Video Task] Retrieved book with {len(book.pages)} pages")

            # 2. Update pipeline stage
            book.pipeline_stage = "video"
            book.progress_percentage = 80
            await session.commit()

            # 3. Get video provider
            try:
                video_provider = ai_factory.get_video_provider()
            except Exception as e:
                logger.warning(f"[Video Task] Video provider not available: {e}")
                # Video는 선택적 기능이므로 실패해도 OK
                return TaskResult(
                    status=TaskStatus.COMPLETED,
                    result={"skipped": True, "reason": "Video provider not available"}
                )

            # 4. Collect image URLs
            image_urls = [page.image_url for page in book.pages if page.image_url]

            if not image_urls:
                logger.warning(f"[Video Task] No images found for book {book_id}")
                return TaskResult(
                    status=TaskStatus.COMPLETED,
                    result={"skipped": True, "reason": "No images"}
                )

            # 5. Generate video (AI call) - 이 부분은 실제 video provider의 메서드에 따라 조정 필요
            logger.debug(f"[Video Task] Calling AI video provider with {len(image_urls)} images")

            # TODO: Implement actual video generation logic based on video provider API
            # For now, we'll mark as skipped
            logger.warning(f"[Video Task] Video generation not yet implemented")

            return TaskResult(
                status=TaskStatus.COMPLETED,
                result={
                    "skipped": True,
                    "reason": "Video generation not yet implemented"
                }
            )

            # Example implementation (uncomment when video provider is ready):
            # video_bytes = await video_provider.create_video(
            #     image_urls=image_urls,
            #     duration_per_image=3.0
            # )
            #
            # # 6. Upload to storage
            # video_file_name = f"{book.base_path}/videos/book_video.mp4"
            # video_url = await storage_service.save(
            #     video_bytes,
            #     video_file_name,
            #     content_type="video/mp4"
            # )
            #
            # logger.info(f"[Video Task] Completed for book_id={book_id}, video_url={video_url}")
            #
            # return TaskResult(
            #     status=TaskStatus.COMPLETED,
            #     result={"video_url": video_url},
            # )

        except Exception as e:
            logger.error(f"[Video Task] Failed for book_id={book_id}: {e}", exc_info=True)
            # Video 실패는 치명적이지 않으므로 COMPLETED로 반환
            return TaskResult(
                status=TaskStatus.COMPLETED,
                result={"skipped": True, "reason": f"Video generation failed: {str(e)}"}
            )


async def finalize_book_task(
    book_id: str,
    context: TaskContext,
) -> TaskResult:
    """
    Task 5: Book 완료 처리

    - DB 상태를 COMPLETED로 변경
    - Redis Task 결과 정리
    - 진행률 100%로 설정

    Args:
        book_id: Book UUID (string)
        context: Task 실행 컨텍스트

    Returns:
        TaskResult: 성공 시 book_id 반환
    """
    logger.info(f"[Finalize Task] Starting for book_id={book_id}")

    async with AsyncSessionLocal() as session:
        try:
            repo = BookRepository(session)
            task_store = TaskStore()

            # 1. Get book
            book_uuid = uuid.UUID(book_id)
            book = await repo.get_with_pages(book_uuid)

            if not book:
                raise ValueError(f"Book {book_id} not found")

            logger.debug(f"[Finalize Task] Retrieved book: {book.title}")

            # 2. Update status to COMPLETED
            book.status = BookStatus.COMPLETED
            book.pipeline_stage = "completed"
            book.progress_percentage = 100
            book.error_message = None  # Clear any previous errors
            await session.commit()

            logger.debug(f"[Finalize Task] Updated book status to COMPLETED")

            # 3. Cleanup Redis (비동기 실행, 에러 무시)
            try:
                cleanup_count = await task_store.cleanup_book_tasks(book_id)
                logger.debug(f"[Finalize Task] Cleaned up {cleanup_count} Redis keys")
            except Exception as cleanup_error:
                logger.warning(f"[Finalize Task] Redis cleanup failed: {cleanup_error}")

            logger.info(f"[Finalize Task] Completed for book_id={book_id}")

            return TaskResult(
                status=TaskStatus.COMPLETED,
                result={
                    "book_id": book_id,
                    "title": book.title,
                    "num_pages": len(book.pages) if book.pages else 0,
                },
            )

        except Exception as e:
            logger.error(f"[Finalize Task] Failed for book_id={book_id}: {e}", exc_info=True)

            # Update DB error
            try:
                async with AsyncSessionLocal() as error_session:
                    error_repo = BookRepository(error_session)
                    error_book = await error_repo.get(uuid.UUID(book_id))
                    if error_book:
                        error_book.pipeline_stage = "failed"
                        error_book.error_message = f"Finalization failed: {str(e)}"
                        error_book.status = BookStatus.FAILED
                        await error_session.commit()
            except Exception as db_error:
                logger.error(f"[Finalize Task] Failed to update error in DB: {db_error}")

            return TaskResult(status=TaskStatus.FAILED, error=str(e))
