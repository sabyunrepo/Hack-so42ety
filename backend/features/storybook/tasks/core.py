"""
Storybook Task Definitions
비동기 파이프라인의 개별 Task 구현
"""

import logging
import uuid
from typing import List
import httpx
from backend.core.database.session import AsyncSessionLocal
from backend.core.dependencies import (
    get_storage_service,
    get_ai_factory,
    get_cache_service,
    get_event_bus,
)
from backend.infrastructure.storage.base import AbstractStorageService
from backend.infrastructure.ai.factory import AIProviderFactory
from backend.features.storybook.repository import BookRepository
from backend.features.storybook.models import BookStatus
from backend.features.storybook.schemas import (
    create_stories_response_schema,
    TTSExpressionResponse,
)
from backend.features.storybook.prompts.generate_story_prompt import GenerateStoryPrompt
from backend.features.storybook.prompts.generate_tts_expression_prompt import (
    EnhanceAudioPrompt,
)
from backend.features.storybook.prompts.generate_image_prompt import GenerateImagePrompt
from backend.features.storybook.prompts.difficulty_settings import (
    get_difficulty_settings,
)
from backend.features.storybook.utils.difficulty_validator import (
    validate_difficulty,
    get_text_stats,
)
from backend.core.config import settings
from backend.core.limiters import get_limiters
from backend.features.tts.exceptions import BookVoiceNotConfiguredException
from backend.features.tts.producer import TTSProducer

# from backend.features.storybook.dependencies import get_tts_producer


from .schemas import TaskResult, TaskContext, TaskStatus
from .store import TaskStore
from .retry import retry_with_config, BatchRetryTracker, calculate_retry_delay

# test
import asyncio

logger = logging.getLogger(__name__)


async def generate_story_task(
    book_id: str,
    stories: List[str],
    level: int,
    num_pages: int,
    context: TaskContext,
) -> TaskResult:
    """
    Task 1: Story 생성 (AI 호출) with 레벨별 난이도 조절

    Args:
        book_id: Book UUID (string)
        stories: 사용자 일기 항목 리스트
        level: 난이도 레벨 (1: 4-5세, 2: 5-6세, 3: 6-8세)
        num_pages: 페이지 수
        context: Task 실행 컨텍스트

    Returns:
        TaskResult: 성공 시 story_data_key 반환
    """
    logger.info(f"[Story Task] Starting for book_id={book_id}")
    logger.info(f"[Story Task] stories={stories}, level={level}, num_pages={num_pages}")
    ai_factory = get_ai_factory()
    story_provider = ai_factory.get_story_provider()

    max_retries = settings.task_story_max_retries

    # 레벨별 난이도 설정 가져오기
    try:
        difficulty_settings = get_difficulty_settings(level)
    except ValueError:
        # 유효하지 않은 레벨이면 기본값 1 사용
        logger.warning(f"[Story Task] Invalid level {level}, using default level 1")
        level = 1
        difficulty_settings = get_difficulty_settings(level)

    # 레벨별 스키마 설정 적용
    # max_dialogues_per_page=difficulty_settings.max_dialogues_per_page,
    # max_chars_per_dialogue=difficulty_settings.max_chars_per_dialogue,
    response_schema = create_stories_response_schema(
        max_pages=num_pages,
        # max_dialogues_per_page는 프론트 최대 허용치보다 작게 제한 필요
        max_dialogues_per_page=settings.max_dialogues_per_page,  # 프론트 허용 최대 개수
        max_chars_per_dialogue=settings.max_chars_per_dialogue,  # 프론트 허용 최대 개수
        max_title_length=settings.max_title_length,
    )

    # 레벨이 적용된 프롬프트 생성
    prompt = GenerateStoryPrompt(diary_entries=stories, level=level).render()

    # === Phase 1: Story 생성 (재시도 유틸리티 사용) ===
    async def _generate_and_validate():
        """Story 생성, 검증 및 Flesch-Kincaid 난이도 검증"""
        generated_data = await story_provider.generate_story(
            prompt=prompt,
            response_schema=response_schema,
        )
        logger.info(f"[Story Task] [Book: {book_id}] generated_data={generated_data}")
        book_title, dialogues = validate_generated_story(generated_data)

        # Flesch-Kincaid 난이도 검증
        full_text = " ".join(" ".join(page) for page in dialogues)
        is_valid, fk_score = validate_difficulty(full_text, level)

        # 텍스트 통계 로깅 (디버깅용)
        text_stats = get_text_stats(full_text)
        logger.info(
            f"[Story Task] [Book: {book_id}] FK Validation - "
            f"Level: {level}, Score: {fk_score:.2f}, Valid: {is_valid}, "
            f"Stats: {text_stats}"
        )

        if not is_valid:
            raise ValueError(
                f"FK score {fk_score:.2f} out of acceptable range for level {level}. "
                f"Target range: {difficulty_settings.fk_grade_range}"
            )

        return book_title, dialogues

    try:
        book_title, dialogues = await retry_with_config(
            func=_generate_and_validate,
            max_retries=max_retries,
            error_message_prefix=f"[Story Task] [Book: {book_id}]",
        )
    except RuntimeError as e:
        # 모든 시도 실패 - DB 업데이트 후 TaskResult(FAILED) 반환
        logger.error(f"[Story Task] All retries failed: {e}")

        async with AsyncSessionLocal() as error_session:
            error_repo = BookRepository(error_session)
            await error_repo.update(
                id=uuid.UUID(book_id),
                pipeline_stage="failed",
                error_message=f"Story generation failed: {str(e)}",
                status=BookStatus.FAILED,
            )
            await error_session.commit()

        return TaskResult(status=TaskStatus.FAILED, error=str(e))

    # === Phase 2: AI 호출 (Emotion 추가) - 세션 밖에서 실행, 재시도 포함 ===
    async def _generate_emotion():
        """감정 표현 생성 (재시도용 래퍼)"""
        emotion_prefixed_prompt = EnhanceAudioPrompt(
            stories=dialogues, title=book_title
        ).render()
        return await story_provider.generate_story(
            prompt=emotion_prefixed_prompt,
            response_schema=TTSExpressionResponse,
        )

    try:
        response_with_emotion = await retry_with_config(
            func=_generate_emotion,
            max_retries=max_retries,
            error_message_prefix=f"[Story Task] [Book: {book_id}] Emotion generation",
        )
    except RuntimeError as e:
        logger.error(f"[Story Task] Emotion generation failed: {e}")

        async with AsyncSessionLocal() as error_session:
            error_repo = BookRepository(error_session)
            await error_repo.update(
                id=uuid.UUID(book_id),
                pipeline_stage="failed",
                error_message=f"Emotion generation failed: {str(e)}",
                status=BookStatus.FAILED,
            )
            await error_session.commit()

        return TaskResult(status=TaskStatus.FAILED, error=str(e))

    logger.info(f"[Story Task] Generating story with emotions: {response_with_emotion}")
    dialogues_with_emotions = response_with_emotion.stories

    # 페이지 구조 복원: dialogues의 페이지별 대사 수에 맞춰 재구성
    page_sizes = [len(page) for page in dialogues]
    flat_emotions = dialogues_with_emotions if dialogues_with_emotions else []

    restructured_dialogues = []
    idx = 0
    for size in page_sizes:
        restructured_dialogues.append(flat_emotions[idx : idx + size])
        idx += size

    logger.info(
        f"[Story Task] Restructured dialogues: {len(restructured_dialogues)} pages"
    )

    # === Phase 3: Redis 저장 - 세션 밖에서 실행 ===
    task_store = TaskStore()
    story_key = f"story:{book_id}"
    await task_store.set(
        story_key, {"dialogues": restructured_dialogues, "title": book_title}, ttl=3600
    )

    # === Phase 4: DB 작업만 세션 안에서 실행 ===
    async with AsyncSessionLocal() as session:
        try:
            repo = BookRepository(session)
            book_uuid = uuid.UUID(book_id)

            # Get book with pages
            book = await repo.get_with_pages(book_uuid)
            if not book or not book.pages:
                raise ValueError(f"Book {book_id} has no pages for dialogues creation")

            pages = book.pages

            # Create Dialogue + DialogueTranslation for each page
            for page_idx, page_dialogues in enumerate(dialogues):
                page = next((p for p in pages if p.sequence == page_idx + 1), None)
                if not page:
                    logger.info(
                        f"[Story Task] [Book: {book_id}] Page {page_idx + 1} not found, skipping dialogues"
                    )
                    continue
                for dialogue_idx, dialogue_text in enumerate(page_dialogues):
                    await repo.add_dialogue_with_translation(
                        page_id=page.id,
                        speaker="Narrator",  # test 이거 무슨 의미?
                        sequence=dialogue_idx + 1,
                        translations=[
                            {
                                "language_code": "en",
                                "text": dialogue_text,
                                "is_primary": True,
                            }
                        ],
                    )

            # Update DB with title and progress
            # task_metadata 업데이트
            task_metadata = book.task_metadata or {}
            task_metadata["story"] = {
                "status": "completed",
                "retry_count": context.retry_count,
                "max_retries": max_retries,
            }

            updated = await repo.update(
                book_uuid,
                pipeline_stage="story",
                progress_percentage=30,
                title=book_title,
                task_metadata=task_metadata,
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
            logger.error(
                f"[Story Task] Failed for book_id={book_id}: {e}", exc_info=True
            )

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
    Task 2: Image 생성 (배치 처리 - 모든 페이지, 재시도 지원)

    실패한 이미지만 재시도하며, 성공한 이미지는 Redis에 보존

    Args:
        book_id: Book UUID (string)
        images: 모든 페이지의 원본 이미지 바이트 리스트
        context: Task 실행 컨텍스트

    Returns:
        TaskResult: 성공 시 모든 페이지의 image_urls 반환
    """
    logger.info(
        f"[Image Task] [Book: {book_id}] Starting batch processing, {len(images)} images"
    )

    storage_service = get_storage_service()
    task_store = TaskStore()
    story_key = f"story:{book_id}"
    story_data = await task_store.get(story_key)
    dialogues = story_data.get("dialogues", []) if story_data else []

    # === Phase 1: 재시도 추적기 초기화 ===
    max_retries = settings.task_image_max_retries
    tracker = BatchRetryTracker(total_items=len(images), max_retries=max_retries)

    # Redis 캐시 복구 (재시도 시)
    image_cache_key = f"images_cache:{book_id}"
    cached_data = await task_store.get(image_cache_key)
    if cached_data:
        for idx_str, img_info in cached_data.get("completed", {}).items():
            tracker.mark_success(int(idx_str), img_info)
        logger.info(
            f"[Image Task] [Book: {book_id}] Recovered {len(tracker.completed)} cached images"
        )

    # === Phase 2: Prompt 생성 ===
    prompts = [
        GenerateImagePrompt(stories=dialogue, style_keyword="cartoon").render()
        for dialogue in dialogues
    ]
    ai_factory = get_ai_factory()
    image_provider = ai_factory.get_image_provider()

    # === Phase 3: 재시도 루프 ===
    while not tracker.is_all_completed():
        pending_indices = tracker.get_pending_indices()

        if not pending_indices:
            break

        logger.info(
            f"[Image Task] [Book: {book_id}] Processing {len(pending_indices)} images "
            f"(completed: {len(tracker.completed)}/{tracker.total_items})"
        )

        # 실패한 이미지만 재시도
        tasks = [
            image_provider.generate_image_from_image(
                image_data=images[idx], prompt=prompts[idx]
            )
            for idx in pending_indices
        ]

        # return_exceptions=True로 개별 실패 허용
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 결과 처리
        for idx, result in zip(pending_indices, results):
            if isinstance(result, Exception):
                tracker.mark_failure(idx, str(result))
                logger.error(
                    f"[Image Task] [Book: {book_id}] Page {idx} failed: {result}"
                )
            else:
                image_info = {
                    "imageUUID": result["data"][0]["imageUUID"],
                    "imageURL": result["data"][0]["imageURL"],
                }
                tracker.mark_success(idx, image_info)
                logger.info(f"[Image Task] [Book: {book_id}] Page {idx} completed")

        # Redis에 중간 결과 저장 (재시도 복구용)
        await task_store.set(
            image_cache_key,
            {
                "completed": {str(k): v for k, v in tracker.completed.items()},
                "retry_counts": tracker.retry_counts,
                "last_errors": tracker.last_errors,
            },
            ttl=3600,
        )

        # 재시도 대기 (마지막이 아니면)
        if not tracker.is_all_completed() and tracker.get_pending_indices():
            delay = await calculate_retry_delay(max(tracker.retry_counts.values()))
            logger.info(f"[Image Task] [Book: {book_id}] Retrying in {delay:.1f}s...")
            await asyncio.sleep(delay)

    # === Phase 4: 결과 평가 ===
    if tracker.is_all_completed():
        status = TaskStatus.COMPLETED
        logger.info(
            f"[Image Task] [Book: {book_id}] All {tracker.total_items} images completed"
        )
    elif tracker.is_partial_failure():
        status = TaskStatus.COMPLETED  # 부분 성공도 COMPLETED로 처리
        logger.warning(
            f"[Image Task] [Book: {book_id}] Partial completion: "
            f"{len(tracker.completed)}/{tracker.total_items} images"
        )
    else:
        status = TaskStatus.FAILED
        logger.error(f"[Image Task] [Book: {book_id}] All images failed")

    # === Phase 5: Cover Image 다운로드 및 저장 ===
    cover_image_info = tracker.completed.get(0)  # 첫 페이지를 커버로 사용

    if cover_image_info:
        timeout = httpx.Timeout(settings.http_timeout, read=settings.http_read_timeout)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(cover_image_info["imageURL"])
            response.raise_for_status()
            image_bytes = response.content

        async with AsyncSessionLocal() as session:
            try:
                repo = BookRepository(session)
                book_uuid = uuid.UUID(book_id)
                book = await repo.get(book_uuid)
                if not book:
                    raise ValueError(f"Book {book_id} not found")

                file_name = f"{book.base_path}/images/cover.png"
                logger.info(
                    f"[Image Task] [Book: {book_id}] Using base_path: {book.base_path}, is_default: {book.is_default}"
                )
                storage_url = await storage_service.save(
                    image_bytes, file_name, content_type="image/png"
                )

                # task_metadata 업데이트
                task_metadata = book.task_metadata or {}
                task_metadata["image"] = tracker.get_summary()

                updated = await repo.update(
                    book_uuid,
                    pipeline_stage="image",
                    progress_percentage=60,
                    cover_image=file_name,
                    task_metadata=task_metadata,
                )
                if not updated:
                    raise ValueError(f"Book {book_id} not found for update")
                await session.commit()

                logger.info(
                    f"[Image Task] [Book: {book_id}] Updated book with cover image and metadata"
                )

            except Exception as e:
                logger.error(
                    f"[Image Task] [Book: {book_id}] DB update failed: {e}",
                    exc_info=True,
                )
                return TaskResult(status=TaskStatus.FAILED, error=str(e))

    # === Phase 6: Redis에 최종 결과 저장 ===
    # 순서 보장을 위해 인덱스 순으로 정렬
    image_infos = [tracker.completed.get(i) for i in range(tracker.total_items)]

    await task_store.set(
        f"images:{book_id}",
        {
            "images": [info for info in image_infos if info is not None],
            "page_count": len(images),
            "failed_pages": tracker.get_failed_indices(),
        },
        ttl=3600,
    )

    logger.info(f"[Image Task] [Book: {book_id}] Image task completed")
    return TaskResult(
        status=status,
        result={
            "image_infos": image_infos,
            "page_count": len(images),
            "completed_count": len(tracker.completed),
            "failed_count": len(tracker.get_failed_indices()),
            "summary": tracker.get_summary(),
        },
    )


async def generate_tts_task(
    book_id: str,
    tts_producer: TTSProducer,
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
            logger.info(
                f"[TTS Task] [Book: {book_id}] Book loaded: user_id={book.user_id}, voice_id={book.voice_id}"
            )

            # === Phase 2: Build Task List ===
            tasks_to_generate = []
            tasks_to_enqueue = []

            # Redis에서 감정 포함 대화 텍스트 가져오기
            dialogues_with_emotion = (
                story_data.get("dialogues", []) if story_data else []
            )
            logger.info(f"[TTS Task] dialogues_with_emotion: {dialogues_with_emotion}")
            logger.info(
                f"[TTS Task] [Book: {book_id}] Loaded {len(dialogues_with_emotion)} pages with emotion from Redis"
            )

            for page in book.pages:
                page_idx = page.sequence - 1  # 0-indexed
                for dialogue in page.dialogues:
                    dialogue_idx = dialogue.sequence - 1  # 0-indexed

                    primary_translation = next(
                        (t for t in dialogue.translations if t.is_primary), None
                    )
                    if not primary_translation:
                        logger.info(
                            f"[TTS Task] [Book: {book_id}] No primary translation for dialogue {dialogue.id}, skipping"
                        )
                        continue

                    # Skip empty text
                    if not primary_translation.text.strip():
                        logger.info(
                            f"[TTS Task] [Book: {book_id}] Empty text for dialogue {dialogue.id}, skipping"
                        )
                        continue

                    # 감정 포함 텍스트 가져오기 (fallback: DB 원본 텍스트)
                    try:
                        emotion_text = dialogues_with_emotion[page_idx][dialogue_idx]
                        if not emotion_text or not emotion_text.strip():
                            raise ValueError("Empty emotion text")
                        logger.info(
                            f"[TTS Task] [Book: {book_id}] Using emotion text for page {page_idx + 1}, dialogue {dialogue_idx + 1}"
                        )
                    except (IndexError, TypeError, ValueError) as e:
                        emotion_text = primary_translation.text
                        logger.warning(
                            f"[TTS Task] [Book: {book_id}] Fallback to DB text for page {page_idx + 1}, dialogue {dialogue_idx + 1}: {e}"
                        )

                    # file_name = f"users/{book.user_id}/audios/standalone/{uuid.uuid4()}.mp3"
                    audio_uuid = uuid.uuid4()
                    file_name = f"{book.base_path}/{audio_uuid}.mp3"
                    logger.info(
                        f"[TTS Task] [Book: {book_id}] Audio path: {file_name} (is_default: {book.is_default})"
                    )
                    audio = await repo.add_dialogue_audio(
                        dialogue_id=dialogue.id,
                        language_code=primary_translation.language_code,
                        voice_id=book.voice_id,
                        audio_url=file_name,
                        status="PENDING",
                    )
                    if not audio:
                        logger.error(
                            f"[TTS Task] Failed to create DialogueAudio record for dialogue {dialogue.id}, skipping"
                        )
                        continue
                    logger.info(
                        f"[TTS Task] [Book: {book_id}] Enqueuing TTS for dialogue {dialogue.id}, audio_id={audio.id}"
                    )
                    logger.info(
                        f"[TTS Task] [Book: {book_id}] Text (with emotion): {emotion_text}"
                    )
                    tasks_to_enqueue.append(
                        {
                            "audio_id": audio.id,
                            "text": emotion_text,
                            "dialogue_id": dialogue.id,
                        }
                    )
                    tasks_to_generate.append(audio.id)

            await repo.update(
                book_uuid,
                pipeline_stage="tts",
                progress_percentage=70,
                error_message=None,
            )
            await session.commit()

            # === Phase 3: Enqueue Tasks (After Commit) ===
            # 트랜잭션 커밋 후 큐에 불어넣어야 Worker가 DB에서 조회 가능 (Race Condition 방지)
            logger.info(
                f"[TTS Task] Enqueuing {len(tasks_to_enqueue)} tasks to Redis..."
            )
            for task in tasks_to_enqueue:
                await tts_producer.enqueue_tts_task(
                    dialogue_audio_id=task["audio_id"],
                    text=task["text"],
                )
                logger.debug(f"[TTS Task] Enqueued audio_id={task['audio_id']}")
            return TaskResult(
                status=TaskStatus.COMPLETED,
                result={
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
            logger.error(f"[TTS Task] Failed for book_id={book_id}: {e}", exc_info=True)
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
    Task 4: Video 생성 (Image Task의 결과 사용, 재시도 지원)

    실패한 비디오만 재시도하며, 성공한 비디오는 유지

    Args:
        book_id: Book UUID (string)
        context: Task 실행 컨텍스트

    Returns:
        TaskResult: 성공 시 video_url 반환
    """
    logger.info(f"[Video Task] [Book: {book_id}] Starting video generation")
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
    image_uuids = (
        [img_info["imageUUID"] for img_info in image_data.get("images", [])]
        if image_data
        else []
    )

    # === Phase 1: 재시도 추적기 초기화 ===
    max_retries = settings.task_video_max_retries
    tracker = BatchRetryTracker(total_items=len(image_uuids), max_retries=max_retries)

    # Redis 캐시 복구
    video_cache_key = f"videos_cache:{book_id}"
    cached_data = await task_store.get(video_cache_key)
    if cached_data:
        for idx_str, video_url in cached_data.get("completed", {}).items():
            tracker.mark_success(int(idx_str), video_url)
        logger.info(
            f"[Video Task] [Book: {book_id}] Recovered {len(tracker.completed)} cached videos"
        )

    # === Phase 2: 재시도 루프 ===
    limiters = get_limiters()

    while not tracker.is_all_completed():
        pending_indices = tracker.get_pending_indices()

        if not pending_indices:
            break

        logger.info(
            f"[Video Task] [Book: {book_id}] Processing {len(pending_indices)} videos "
            f"(completed: {len(tracker.completed)}/{tracker.total_items})"
        )

        # 실패한 비디오만 재시도
        tasks = []
        for idx in pending_indices:
            img_uuid = image_uuids[idx]
            prompt = prompts[idx]

            async def generate_with_limit(uuid=img_uuid, p=prompt, page_idx=idx):
                async with limiters.video_generation:
                    logger.info(
                        f"[Video Task] [Book: {book_id}] Page {page_idx}: Acquiring semaphore for image {uuid[:8]}..."
                    )
                    return await video_provider.generate_video(
                        image_uuid=uuid, prompt=p
                    )

            tasks.append(generate_with_limit())

        # 비디오 생성 요청 (return_exceptions=True)
        task_uuids_results = await asyncio.gather(*tasks, return_exceptions=True)

        # 요청 실패 체크
        pending_to_task_uuid = {}
        for idx, result in zip(pending_indices, task_uuids_results):
            if isinstance(result, Exception):
                tracker.mark_failure(idx, f"Video request failed: {result}")
                logger.error(
                    f"[Video Task] [Book: {book_id}] Page {idx} request failed: {result}"
                )
            else:
                pending_to_task_uuid[idx] = result  # task_uuid 저장

        if not pending_to_task_uuid:
            # 모든 요청 실패
            logger.warning(f"[Video Task] [Book: {book_id}] All video requests failed")
            break

        # === Phase 3: 폴링 루프 (타임아웃 10분) ===
        max_wait_time = 600
        poll_interval = 10
        elapsed_time = 0

        while elapsed_time < max_wait_time and pending_to_task_uuid:
            for idx in list(pending_to_task_uuid.keys()):
                task_uuid = pending_to_task_uuid[idx]

                try:
                    status_response = await video_provider.check_video_status(task_uuid)
                    status = status_response["status"]

                    if status == "completed":
                        video_url = status_response["video_url"]
                        tracker.mark_success(idx, video_url)
                        del pending_to_task_uuid[idx]
                        logger.info(
                            f"[Video Task] [Book: {book_id}] Page {idx} completed"
                        )

                    elif status == "failed":
                        error_msg = status_response.get("error", "Unknown error")
                        tracker.mark_failure(idx, error_msg)
                        del pending_to_task_uuid[idx]
                        logger.error(
                            f"[Video Task] [Book: {book_id}] Page {idx} failed: {error_msg}"
                        )

                except Exception as e:
                    logger.error(
                        f"[Video Task] [Book: {book_id}] Status check failed for page {idx}: {e}"
                    )

            if pending_to_task_uuid:
                await asyncio.sleep(poll_interval)
                elapsed_time += poll_interval

        # 타임아웃된 작업 처리
        for idx in pending_to_task_uuid.keys():
            tracker.mark_failure(idx, "Video generation timeout")
            logger.warning(f"[Video Task] [Book: {book_id}] Page {idx} timed out")

        # Redis에 중간 결과 저장
        await task_store.set(
            video_cache_key,
            {
                "completed": {str(k): v for k, v in tracker.completed.items()},
                "retry_counts": tracker.retry_counts,
                "last_errors": tracker.last_errors,
            },
            ttl=3600,
        )

        # 재시도 대기
        if not tracker.is_all_completed() and tracker.get_pending_indices():
            delay = await calculate_retry_delay(max(tracker.retry_counts.values()))
            logger.info(f"[Video Task] [Book: {book_id}] Retrying in {delay:.1f}s...")
            await asyncio.sleep(delay)

    # === Phase 4: 결과 평가 ===
    if tracker.is_all_completed():
        status = TaskStatus.COMPLETED
        logger.info(
            f"[Video Task] [Book: {book_id}] All {tracker.total_items} videos completed"
        )
    elif tracker.is_partial_failure():
        status = TaskStatus.COMPLETED  # 부분 성공도 허용
        logger.warning(
            f"[Video Task] [Book: {book_id}] Partial completion: "
            f"{len(tracker.completed)}/{tracker.total_items} videos"
        )
    else:
        status = TaskStatus.FAILED
        logger.error(f"[Video Task] [Book: {book_id}] All videos failed")

    # === Phase 5: Get Book object for base_path ===
    async with AsyncSessionLocal() as temp_session:
        temp_repo = BookRepository(temp_session)
        book_uuid = uuid.UUID(book_id)
        book = await temp_repo.get(book_uuid)
        if not book:
            raise ValueError(f"Book {book_id} not found")

    # === Phase 6: HTTP Download + S3 Upload (세션 밖에서 실행) ===
    storage_service = get_storage_service()
    s3_video_urls = []

    for page_idx in range(len(image_uuids)):
        if page_idx in tracker.completed:
            # 성공한 비디오: 다운로드 + S3 업로드
            video_url = tracker.completed[page_idx]
            video_bytes = await video_provider.download_video(video_url)
            video_size = len(video_bytes)

            file_name = f"{book.base_path}/videos/page_{page_idx + 1}.mp4"
            logger.info(
                f"[Video Task] [Book: {book_id}] Page {page_idx + 1}: Uploading to {file_name}"
            )
            storage_url = await storage_service.save(
                video_bytes, file_name, content_type="video/mp4"
            )
            logger.info(
                f"[Video Task] [Book: {book_id}] Page {page_idx + 1}: Uploaded to {storage_url} (size: {video_size} bytes)"
            )
            s3_video_urls.append(file_name)
        else:
            # 실패한 비디오: None 추가 (순서 유지)
            logger.warning(
                f"[Video Task] [Book: {book_id}] Page {page_idx + 1}: Video failed, skipping"
            )
            s3_video_urls.append(None)

    # === Phase 7: DB Update ===
    async with AsyncSessionLocal() as session:
        try:
            repo = BookRepository(session)
            book_uuid = uuid.UUID(book_id)
            book = await repo.get_with_pages(book_uuid)
            pages = book.pages

            # Update pages with video URLs
            for page_idx, video_url in enumerate(s3_video_urls):
                if video_url is None:
                    continue

                page = next((p for p in pages if p.sequence == page_idx + 1), None)
                if not page:
                    logger.warning(
                        f"[Video Task] [Book: {book_id}] Page {page_idx + 1} not found in DB"
                    )
                    continue
                page.image_url = video_url
                session.add(page)

            # task_metadata 업데이트
            task_metadata = book.task_metadata or {}
            task_metadata["video"] = tracker.get_summary()

            # Update book progress
            updated = await repo.update(
                book_uuid,
                pipeline_stage="video",
                progress_percentage=80,
                task_metadata=task_metadata,
                error_message=None,
            )
            if not updated:
                raise ValueError(f"Book {book_id} not found for update")

            await session.commit()

            # 결과 반환
            if tracker.is_all_completed():
                logger.info(
                    f"[Video Task] [Book: {book_id}] All videos completed successfully"
                )
                return TaskResult(
                    status=TaskStatus.COMPLETED,
                    result={
                        "total_videos": len(image_uuids),
                        "completed_videos": len(tracker.completed),
                        "failed_videos": len(tracker.get_failed_indices()),
                    },
                )
            elif tracker.is_partial_failure():
                logger.warning(
                    f"[Video Task] [Book: {book_id}] Partially completed: {len(tracker.completed)}/{len(image_uuids)} videos"
                )
                return TaskResult(
                    status=TaskStatus.COMPLETED,  # DAG 계속 진행
                    result={
                        "total_videos": len(image_uuids),
                        "completed_videos": len(tracker.completed),
                        "failed_videos": len(tracker.get_failed_indices()),
                        "partial_failure": True,
                    },
                )
            else:
                logger.error(f"[Video Task] [Book: {book_id}] All videos failed")
                return TaskResult(
                    status=TaskStatus.FAILED,
                    result={
                        "total_videos": len(image_uuids),
                        "completed_videos": 0,
                        "failed_videos": len(tracker.get_failed_indices()),
                    },
                )

        except Exception as e:
            logger.error(
                f"[Video Task] [Book: {book_id}] Video generation failed: {e}",
                exc_info=True,
            )
            return TaskResult(status=TaskStatus.FAILED, result={"error": str(e)})


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

    # === Phase 1: Redis 조회 - 세션 밖에서 실행 ===
    task_store = TaskStore()
    story_key = f"story:{book_id}"
    story_data = await task_store.get(story_key)
    book_title = (
        story_data.get("title", "Untitled Story") if story_data else "Untitled Story"
    )
    num_pages = len(story_data.get("dialogues", [])) if story_data else 0

    # === Phase 2: DB 작업만 세션 안에서 실행 ===
    async with AsyncSessionLocal() as session:
        try:
            repo = BookRepository(session)
            book_uuid = uuid.UUID(book_id)

            # Get book to analyze task_metadata
            book = await repo.get(book_uuid)
            if not book:
                raise ValueError(f"Book {book_id} not found")

            task_metadata = book.task_metadata or {}

            # task_metadata 분석하여 부분 실패 감지
            has_partial_failure = False
            for task_name in ["image", "video", "tts"]:
                task_info = task_metadata.get(task_name, {})
                failed_items = task_info.get("failed_items", [])
                if failed_items:
                    has_partial_failure = True
                    logger.warning(
                        f"[Finalize Task] {task_name} has {len(failed_items)} failed items"
                    )

            # 상태 결정
            if has_partial_failure:
                final_status = BookStatus.PARTIALLY_COMPLETED
            else:
                final_status = BookStatus.COMPLETED

            # overall_status 추가
            from datetime import datetime

            task_metadata["overall_status"] = final_status
            task_metadata["last_updated"] = datetime.utcnow().isoformat()

            # DB 업데이트
            updated = await repo.update(
                book_uuid,
                status=final_status,
                pipeline_stage="completed",
                progress_percentage=100,
                task_metadata=task_metadata,
                error_message=None,
            )

            if not updated:
                raise ValueError(f"Book {book_id} not found for update")

            await session.commit()
            logger.info(
                f"[Finalize Task] [Book: {book_id}] Updated book status to {final_status}"
            )

        except Exception as e:
            logger.error(
                f"[Finalize Task] Failed for book_id={book_id}: {e}", exc_info=True
            )

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
                logger.error(
                    f"[Finalize Task] Failed to update error in DB: {db_error}"
                )

            return TaskResult(status=TaskStatus.FAILED, error=str(e))

    # === Phase 3: Redis Cleanup - 세션 밖에서 실행 (비동기, 에러 무시) ===
    try:
        cleanup_count = await task_store.cleanup_book_tasks(book_id)
        logger.info(
            f"[Finalize Task] [Book: {book_id}] Cleaned up {cleanup_count} Redis keys"
        )
    except Exception as cleanup_error:
        logger.info(
            f"[Finalize Task] [Book: {book_id}] Redis cleanup failed: {cleanup_error}"
        )

    logger.info(f"[Finalize Task] Completed for book_id={book_id}")

    return TaskResult(
        status=TaskStatus.COMPLETED,
        result={
            "book_id": book_id,
            "title": book_title,
            "num_pages": num_pages,
        },
    )


def validate_generated_story(data) -> tuple[str, list]:
    """
    generated_data 검증
    Returns: (title, dialogues)
    Raises: ValueError
    """
    if data is None:
        raise ValueError("generated_data is None")

    title = getattr(data, "title", None)
    stories = getattr(data, "stories", None)

    if not title or not isinstance(title, str):
        raise ValueError("Missing or invalid title")

    if not stories or not isinstance(stories, list):
        raise ValueError("Missing or invalid stories")

    if len(title) > 20:
        raise ValueError("Title too long")

    return title, stories
