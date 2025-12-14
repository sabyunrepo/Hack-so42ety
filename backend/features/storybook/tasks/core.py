"""
Storybook Task Definitions
비동기 파이프라인의 개별 Task 구현
"""

import logging
import uuid
from typing import  List
import httpx
from backend.core.database.session import AsyncSessionLocal
from backend.core.dependencies import get_storage_service, get_ai_factory, get_cache_service, get_event_bus
from backend.infrastructure.storage.base import AbstractStorageService
from backend.infrastructure.ai.factory import AIProviderFactory
from backend.features.storybook.repository import BookRepository
from backend.features.storybook.models import BookStatus
from backend.features.storybook.schemas import create_stories_response_schema, TTSExpressionResponse
from backend.features.storybook.prompts.generate_story_prompt import GenerateStoryPrompt
from backend.features.storybook.prompts.generate_tts_expression_prompt import EnhanceAudioPrompt
from backend.features.storybook.prompts.generate_image_prompt import GenerateImagePrompt
from backend.core.config import settings
from backend.features.tts.service import TTSService
from backend.features.tts.repository import AudioRepository, VoiceRepository
from backend.features.tts.exceptions import BookVoiceNotConfiguredException


from .schemas import TaskResult, TaskContext, TaskStatus
from .store import TaskStore

#test
import asyncio

logger = logging.getLogger(__name__)


async def generate_story_task(
    book_id: str,
    stories: List[str],
    level: str,
    num_pages: int,
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
    logger.info(f"[Story Task] Starting for book_id={book_id}")
    logger.info(f"[Story Task] stories={stories}, level={level}, num_pages={num_pages}")

    async with AsyncSessionLocal() as session:
        try:
            repo = BookRepository(session)
            task_store = TaskStore()
            ai_factory = get_ai_factory()

            # 1. Update pipeline stage
            book_uuid = uuid.UUID(book_id)

            # 2. Generate story (AI call)
            max_dialogues_per_page = 3  # 임시 고정값, 추후 조정 가능
            story_provider = ai_factory.get_story_provider()
            response_schema = create_stories_response_schema(
                max_pages=num_pages,
                max_dialogues_per_page=max_dialogues_per_page,
                max_chars_per_dialogue=85,
                max_title_length=20,
            )
            prompt = GenerateStoryPrompt(diary_entries=stories).render()
            generated_data = await story_provider.generate_story(
                prompt=prompt,
                response_schema=response_schema,
            )
            book_title = generated_data.title
            dialogues = generated_data.stories

            emotion_prefixed_prompt = EnhanceAudioPrompt(stories=dialogues, title=book_title).render()
            response_with_emotion = await story_provider.generate_story(
                prompt=emotion_prefixed_prompt,
                response_schema=TTSExpressionResponse,
            )
            dialogues_with_emotions = response_with_emotion.stories

            # 3. Store in Redis
            story_key = f"story:{book_id}"
            await task_store.set(story_key, {"dialogues": dialogues_with_emotions, "title": book_title}, ttl=3600)

            # 4. Create Dialogue + DialogueTranslation for each page
            book = await repo.get_with_pages(book_uuid)
            if not book or not book.pages:
                raise ValueError(f"Book {book_id} has no pages for dialogues creation")

            pages = book.pages
            
            for page_idx, page_dialogues in enumerate(dialogues):
                page = next((p for p in pages if p.sequence == page_idx + 1), None)
                if not page:
                    logger.warning(f"[Story Task] Page {page_idx + 1} not found, skipping dialogues")
                    continue
                for dialogue_idx, dialogue_text in enumerate(page_dialogues):
                    await repo.add_dialogue_with_translation(
                        page_id=page.id,
                        speaker="Narrator", # test 이거 무슨 의미?
                        sequence=dialogue_idx + 1,
                        translations=[
                            {"language_code": "en", "text": dialogue_text, "is_primary": True}
                        ],
                    )

            # 5. Update DB with title
            updated = await repo.update(
                    book_uuid,
                    pipeline_stage="story",
                    progress_percentage=30,
                    title=book_title,
                    error_message=None,
                )
            if not updated:
                raise ValueError(f"Book {book_id} not found for update")
            await session.commit()


            logger.info(f"[Story Task] Completed for book_id={book_id}")
            return TaskResult(
                status=TaskStatus.COMPLETED,
                result={
                    "story_key": story_key,
                    "title": book_title,
                    "dialogues": dialogues,
                },
            )

        except Exception as e:
            logger.error(f"[Story Task] Failed for book_id={book_id}: {e}", exc_info=True)

            # Update DB error
            try:
                async with AsyncSessionLocal() as error_session:
                    error_repo = BookRepository(error_session)
                    updated_book = await error_repo.update(
                        id=uuid.UUID(book_id),
                        pipeline_stage="failed",
                        error_message=f"Story generation failed: {str(e)}",
                        status=BookStatus.FAILED,
                    )
                    if updated_book:
                        await error_session.commit()
            except Exception as db_error:
                logger.error(f"[Story Task] Failed to update error in DB: {db_error}")
            return TaskResult(status=TaskStatus.FAILED, error=str(e))


async def generate_image_task(
    book_id: str,
    images: List[bytes],
    context: TaskContext,
) -> TaskResult:
    """
    Task 2: Image 생성 (배치 처리 - 모든 페이지)

    Args:
        book_id: Book UUID (string)
        images: 모든 페이지의 원본 이미지 바이트 리스트
        context: Task 실행 컨텍스트

    Returns:
        TaskResult: 성공 시 모든 페이지의 image_urls 반환
    """
    logger.info(f"[Image Task] Starting batch processing for book_id={book_id}, {len(images)} images")
    logger.info(f"[Image Task] Batch processing {len(images)} images for book_id={book_id}")

    storage_service = get_storage_service()
    task_store = TaskStore()
    story_key = f"story:{book_id}"
    story_data = await task_store.get(story_key)
    dialogues = story_data.get("dialogues", []) if story_data else []

    prompts = [GenerateImagePrompt(
        stories=dialogue, style_keyword="cartoon"
    ).render() for dialogue in dialogues]       
    ai_factory = get_ai_factory()    
    image_provider = ai_factory.get_image_provider()

    # Image-to-Image 모드
    tasks = [
        image_provider.generate_image_from_image(image_data=img, prompt=prompt)
        for img, prompt in zip(images, prompts)
    ]

    # asyncio.gather로 병렬 실행
    results = await asyncio.gather(*tasks)
    image_infos = [
        {
            "imageUUID": r["data"][0]["imageUUID"],
            "imageURL": r["data"][0]["imageURL"]
        }
        for r in results
    ]

    await task_store.set(
        f"images:{book_id}",
        {"images": image_infos, "page_count": len(images)},
        ttl=3600
    )

    # cover image 다운로드받아서 저장하기
    timeout = httpx.Timeout(settings.http_timeout, read=settings.http_read_timeout)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(image_infos[0]['imageURL'])
        response.raise_for_status()
        image_bytes =  response.content

    
    async with AsyncSessionLocal() as session:
        try:
            repo = BookRepository(session)
            book_uuid = uuid.UUID(book_id)
            book = await repo.get(book_uuid)
            if not book:
                raise ValueError(f"Book {book_id} not found")
            user_id = book.user_id

            file_name = f"users/{user_id}/books/{book_id}/images/page_1_cover.png"
            storage_url = await storage_service.save(
                image_bytes,
                file_name,
                content_type="image/png"
            )

            # 5. Update DB with cover image
            updated = await repo.update(
                    book_uuid,
                    pipeline_stage="image",
                    progress_percentage=60,
                    cover_image=file_name,
                )
            if not updated:
                raise ValueError(f"Book {book_id} not found for update")
            await session.commit()
            logger.debug(f"[Image Task] Updated book with cover image: {file_name}")
            return TaskResult(
                status=TaskStatus.COMPLETED,
                result={
                    "image_infos": image_infos,
                    "page_count": len(images),
                },
            )

        except Exception as e:
            logger.error(
                f"[Image Task] Batch failed for book_id={book_id}: {e}",
                exc_info=True
            )
            return TaskResult(status=TaskStatus.FAILED, error=str(e))


async def generate_tts_task(
    book_id: str,
    context: TaskContext,
) -> TaskResult:
    """
    Task 3: TTS 생성 (배치 처리 - 모든 페이지)

    Args:
        book_id: Book UUID (string)
        context: Task 실행 컨텍스트

    Returns:
        TaskResult: 성공 시 모든 audio_urls 반환
    """
    logger.info(f"[TTS Task] Starting batch processing for book_id={book_id}")
    async with AsyncSessionLocal() as session:
        try:
            # === Phase 1: Data Retrieval & Validation ===
            repo = BookRepository(session)
            task_store = TaskStore()
            book_uuid = uuid.UUID(book_id)

            # Get story data from Redis
            story_key = f"story:{book_id}"
            story_data = await task_store.get(story_key)
            if not story_data:
                raise ValueError(f"Story data not found in Redis: {story_key}")

            # Get Book with eager loading (IMPORTANT: use get_with_pages!)
            book = await repo.get_with_pages(book_uuid)
            if not book:
                raise ValueError(f"Book {book_id} not found")

            # Validate voice_id
            if not book.voice_id:
                raise BookVoiceNotConfiguredException(book_id=book_id)
            logger.info(f"[TTS Task] Book loaded: user_id={book.user_id}, voice_id={book.voice_id}")

            # === Phase 2: Build Task List ===
            tasks_to_generate = []
            for page in book.pages:
                for dialogue in page.dialogues:
                    primary_translation = next(
                        (t for t in dialogue.translations if t.is_primary),
                        None
                    )
                    if not primary_translation:
                        logger.warning(
                            f"[TTS Task] No primary translation for dialogue {dialogue.id}, skipping"
                        )
                        continue

                    # Skip empty text
                    if not primary_translation.text.strip():
                        logger.warning(
                            f"[TTS Task] Empty text for dialogue {dialogue.id}, skipping"
                        )
                        continue


                    tasks_to_generate.append({
                        "dialogue_id": dialogue.id,
                        "text": primary_translation.text,
                        "language_code": primary_translation.language_code,
                        "page_seq": page.sequence,
                        "dialogue_seq": dialogue.sequence,
                    })

            if not tasks_to_generate:
                raise ValueError("No dialogues found for TTS generation")

            logger.info(f"[TTS Task] Generating TTS for {len(tasks_to_generate)} dialogues")

            # === Phase 3: TTS Service Setup & Parallel Generation ===
            # Initialize TTSService manually for background tasks
            audio_repo = AudioRepository(session)
            voice_repo = VoiceRepository(session)
            storage_service = get_storage_service()
            ai_factory = get_ai_factory()
            event_bus = get_event_bus()
            cache_service = get_cache_service(event_bus=event_bus)

            tts_service = TTSService(
                audio_repo=audio_repo,
                voice_repo=voice_repo,
                storage_service=storage_service,
                ai_factory=ai_factory,
                db_session=session,
                cache_service=cache_service,
                event_bus=event_bus,
            )

            async def generate_single_tts(task_info):
                """Generate TTS for a single dialogue (TTS only, no DB)"""
                try:
                    logger.info(f"[TTS Task] Generating TTS for dialogue {task_info['dialogue_id']}")
                    # 1. Generate TTS using TTSService (saves to standalone path)
                    audio = await tts_service.generate_speech(
                        user_id=book.user_id,
                        text=task_info["text"],
                        voice_id=book.voice_id,
                    )

                    logger.info(f"[TTS Task] Successfully generated TTS for dialogue {task_info['dialogue_id']}")
                    return {
                        "success": True,
                        "dialogue_id": task_info["dialogue_id"],
                        "language_code": task_info["language_code"],
                        "audio_url": audio.file_path,
                        "duration": None,
                    }

                except Exception as e:
                    logger.error(
                        f"[TTS Task] Failed to generate TTS for dialogue {task_info['dialogue_id']}: {e}",
                        exc_info=True
                    )
                    return {
                        "success": False,
                        "dialogue_id": task_info["dialogue_id"],
                        "language_code": task_info.get("language_code", "en"),
                        "error": str(e),
                    }

            # === Phase 4: Batch Processing (5 at a time to avoid ElevenLabs concurrency limit) ===
            BATCH_SIZE = 5
            all_results = []
            success_count = 0
            failed_count = 0

            logger.info(f"[TTS Task] Processing {len(tasks_to_generate)} tasks in batches of {BATCH_SIZE}")
            for i in range(0, len(tasks_to_generate), BATCH_SIZE):
                batch = tasks_to_generate[i:i+BATCH_SIZE]
                batch_num = (i // BATCH_SIZE) + 1
                total_batches = (len(tasks_to_generate) + BATCH_SIZE - 1) // BATCH_SIZE
                logger.info(f"[TTS Task] Processing batch {batch_num}/{total_batches} ({len(batch)} items)")

                # Execute batch in parallel
                batch_tasks = [generate_single_tts(task_info) for task_info in batch]
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

                # Process batch results and save to DB sequentially
                for result in batch_results:
                    if isinstance(result, Exception):
                        failed_count += 1
                        logger.error(f"[TTS Task] Task raised exception: {result}")
                        continue

                    if not result["success"]:
                        failed_count += 1
                        # Create failed DialogueAudio record
                        await repo.add_dialogue_audio(
                            dialogue_id=result["dialogue_id"],
                            language_code=result.get("language_code", "en"),
                            voice_id=book.voice_id,
                            audio_url="",
                            duration=None,
                            status="FAILED",
                        )
                        continue

                    # Create successful DialogueAudio record
                    await repo.add_dialogue_audio(
                        dialogue_id=result["dialogue_id"],
                        language_code=result["language_code"],
                        voice_id=book.voice_id,
                        audio_url=result["audio_url"],
                        duration=result.get("duration"),
                        status="COMPLETED",
                    )
                    success_count += 1

                # Commit batch to DB
                await session.commit()
                logger.info(f"[TTS Task] Batch {batch_num}/{total_batches} completed and committed to DB")

                all_results.extend(batch_results)

            # === Phase 5: Update Progress ===
            await repo.update(
                book_uuid,
                pipeline_stage="tts",
                progress_percentage=70,
                error_message=None,
            )
            await session.commit()

            logger.info(
                f"[TTS Task] Completed for book_id={book_id}: "
                f"{success_count} succeeded, {failed_count} failed"
            )

            return TaskResult(
                status=TaskStatus.COMPLETED,
                result={
                    "success_count": success_count,
                    "failed_count": failed_count,
                    "total_count": len(tasks_to_generate),
                },
            )

        except BookVoiceNotConfiguredException as e:
            logger.error(f"[TTS Task] Voice not configured for book_id={book_id}: {e}")
            # Update book status to FAILED
            try:
                async with AsyncSessionLocal() as error_session:
                    error_repo = BookRepository(error_session)
                    await error_repo.update(
                        id=book_uuid,
                        pipeline_stage="failed",
                        error_message=f"TTS generation failed: {str(e)}",
                        status=BookStatus.FAILED,
                    )
                    await error_session.commit()
            except Exception as db_error:
                logger.error(f"[TTS Task] Failed to update error in DB: {db_error}")

            return TaskResult(status=TaskStatus.FAILED, error=str(e))

        except Exception as e:
            logger.error(
                f"[TTS Task] Failed for book_id={book_id}: {e}",
                exc_info=True
            )
            # Update book status to FAILED
            try:
                async with AsyncSessionLocal() as error_session:
                    error_repo = BookRepository(error_session)
                    await error_repo.update(
                        id=uuid.UUID(book_id),
                        pipeline_stage="failed",
                        error_message=f"TTS generation failed: {str(e)}",
                        status=BookStatus.FAILED,
                    )
                    await error_session.commit()
            except Exception as db_error:
                logger.error(f"[TTS Task] Failed to update error in DB: {db_error}")

            return TaskResult(status=TaskStatus.FAILED, error=str(e))



async def generate_video_task(
    book_id: str,
    context: TaskContext,
) -> TaskResult:
    """
    Task 4: Video 생성 (Image Task의 결과 사용)

    Args:
        book_id: Book UUID (string)
        context: Task 실행 컨텍스트

    Note:
        Image Task가 생성한 이미지 URL을 Redis에서 조회하여 사용
        Redis key: images:{book_id} -> {"image_urls": [...]}

    Returns:
        TaskResult: 성공 시 video_url 반환 (실패해도 치명적이지 않음)
    """
    logger.info(f"[Video Task] Starting for book_id={book_id}")
    ai_factory = get_ai_factory()
    video_provider = ai_factory.get_video_provider()

    task_store = TaskStore()
    story_key = f"story:{book_id}"
    story_data = await task_store.get(story_key)
    prompts = []
    dialogues = story_data.get("dialogues", []) if story_data else []
    for dialogue in dialogues:
        prompt = " ".join(dialogue)
        prompts.append(prompt)

    image_key = f"images:{book_id}"
    image_data = await task_store.get(image_key)
    image_uuids = [img_info['imageUUID'] for img_info in image_data.get("images", [])] if image_data else []

    tasks = [
        video_provider.generate_video(image_uuid=img_uuid, prompt=prompt)
        for img_uuid, prompt in zip(image_uuids, prompts)
    ]

    # asyncio.gather로 병렬 실행
    results = await asyncio.gather(*tasks)

    max_wait_time = 600  # 10분
    poll_interval = 10   # 10초마다 체크
    elapsed_time = 0
    completed_videos = []
    task_uuids = results  # generate_video()는 task_uuid 문자열을 직접 반환

    while elapsed_time < max_wait_time and len(completed_videos) < len(task_uuids):
        for task_uuid in task_uuids:
            if task_uuid in [v["task_uuid"] for v in completed_videos]:
                continue  # 이미 완료된 작업

            status_response = await video_provider.check_video_status(task_uuid)
            if status_response["status"] == "completed":
                completed_videos.append({
                    "task_uuid": task_uuid,
                    "video_url": status_response["video_url"]
                })
                logger.debug(f"[Video Task] Video task {task_uuid} completed")
            elif status_response["status"] == "failed":
                logger.warning(f"[Video Task] Video task {task_uuid} failed")

        if len(completed_videos) < len(task_uuids):
            await asyncio.sleep(poll_interval)
            elapsed_time += poll_interval
    # 결과 확인
    logger.info(f"[Video Task] All task results: {completed_videos}")

    async with AsyncSessionLocal() as session:
        try:
            repo = BookRepository(session)
            storage_service = get_storage_service()
            book_uuid = uuid.UUID(book_id)
            s3_video_urls = []
            book = await repo.get_with_pages(book_uuid)  # ✅ eager loading            
            pages = book.pages
            user_id = book.user_id

            completed_videos_urls = [v["video_url"] for v in completed_videos]
            for idx, url in enumerate(completed_videos_urls):
                video_bytes = await video_provider.download_video(url)
                video_size = len(video_bytes)
                
                file_name = f"users/{user_id}/books/{book_id}/videos/book_video_{idx}.mp4"
                storage_url = await storage_service.save(
                    video_bytes,
                    file_name,
                    content_type="video/mp4"
                )
                logger.debug(f"[Video Task] Uploaded video to storage: {storage_url} (size: {video_size} bytes)")
                s3_video_urls.append(file_name)

            for page_idx, video_url in enumerate(s3_video_urls):
                page = next((p for p in pages if p.sequence == page_idx + 1), None)
                if not page:
                    logger.warning(f"[Story Task] Page {page_idx + 1} not found, skipping dialogues")
                    continue
                page.image_url = video_url  # 또는 video_url용 컬럼이 있으면 그것
                session.add(page)  # ORM 세션에 반영
            await session.commit()

            updated = await repo.update(
                    book_uuid,
                    pipeline_stage="video",
                    progress_percentage=80,
                    error_message=None,
                )
            if not updated:
                raise ValueError(f"Book {book_id} not found for update")
            await session.commit()

            # 4. Get video provider
            return TaskResult(
                status=TaskStatus.COMPLETED,
                result={
                    "skipped": True,
                    "reason": "Video generation not yet implemented"
                }
            )

        except Exception as e:
            logger.error(f"[Video Task] Failed for book_id={book_id}: {e}", exc_info=True)
            return TaskResult(
                status=TaskStatus.FAILED,
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
            book_uuid = uuid.UUID(book_id)
            task_store = TaskStore()
            story_key = f"story:{book_id}"
            story_data = await task_store.get(story_key)
            book_title = story_data.get("title", "Untitled Story") if story_data else "Untitled Story"
            num_pages = len(story_data.get("dialogues", [])) if story_data else 0

            updated = await repo.update(
                book_uuid,
                status=BookStatus.COMPLETED,
                pipeline_stage="completed",
                progress_percentage=100,
                error_message=None,
            )

            if not updated:
                raise ValueError(f"Book {book_id} not found for update")

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
                    "title": book_title,
                    "num_pages": num_pages,
                },
            )

        except Exception as e:
            logger.error(f"[Finalize Task] Failed for book_id={book_id}: {e}", exc_info=True)

            # Update DB error
            try:
                async with AsyncSessionLocal() as error_session:
                    error_repo = BookRepository(error_session)
                    updated_book = await error_repo.update(
                        id=uuid.UUID(book_id),
                        pipeline_stage="failed",
                        error_message=f"Finalization failed: {str(e)}",
                        status=BookStatus.FAILED,
                    )
                    if updated_book:
                        await error_session.commit()
            except Exception as db_error:
                logger.error(f"[Finalize Task] Failed to update error in DB: {db_error}")

            return TaskResult(status=TaskStatus.FAILED, error=str(e))
