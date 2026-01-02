"""
Storybook Task Definitions
비동기 파이프라인의 개별 Task 구현
"""

import json
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
from backend.core.events.redis_streams_bus import RedisStreamsEventBus as EventPublisher
from backend.core.events.types import EventType
from backend.infrastructure.storage.base import AbstractStorageService
from backend.infrastructure.ai.factory import AIProviderFactory
from backend.infrastructure.ai.base import StoryResponse
from backend.features.storybook.repository import BookRepository
from backend.features.storybook.models import BookStatus
from backend.features.storybook.schemas import (
    create_stories_response_schema,
    TTSExpressionResponse,
    ShortenedTitle,
)
from backend.features.storybook.prompts.generate_story_prompt import GenerateStoryPrompt
from backend.features.storybook.prompts.generate_tts_expression_prompt import (
    EnhanceAudioPrompt,
)
from backend.features.storybook.prompts.generate_image_prompt import GenerateImagePrompt
from backend.features.storybook.prompts.generate_video_prompt import GenerateVideoPrompt
from backend.features.storybook.validators import ValidatorFactory
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


# ============================================================
# Media Optimization Event Helper
# ============================================================


async def publish_media_optimization_event(
    file_type: str,
    input_path: str,
    output_path: str,
    file_id: str,
):
    """
    미디어 최적화 이벤트 발행
    
    Args:
        file_type: "image_webp" 또는 "video_compress"
        input_path: 원본 파일 경로
        output_path: 최적화된 파일 경로
        file_id: 파일 ID (page_id 등)
    """
    try:
        event_publisher = EventPublisher()
        await event_publisher.publish_event(
            event_type=EventType.MEDIA_OPTIMIZATION,
            payload={
                "type": file_type,
                "input_path": input_path,
                "output_path": output_path,
                "file_id": file_id,
            },
        )
        logger.info(
            f"[Media Optimization] Event published: {file_type} for {input_path}"
        )
    except Exception as e:
        logger.error(
            f"[Media Optimization] Failed to publish event: {e}",
            exc_info=True,
        )


# ============================================================
# Story Task Helper Functions
# ============================================================


def _merge_page_dialogues(dialogues: List[List[str]]) -> List[List[str]]:
    """
    페이지별 대화를 1개로 통합 (2D 구조 유지)

    Emotion 생성 후 호출되어 각 페이지의 여러 대화를 하나로 합침.
    감정 태그가 포함된 경우에도 그대로 유지됨.

    Args:
        dialogues: [["대화1", "대화2"], ["대화1"], ...]

    Returns:
        [["대화1 대화2"], ["대화1"], ...]
    """
    return [[" ".join(page_dialogues)] for page_dialogues in dialogues]


async def _mark_book_failed(book_id: str, stage: str, error: str) -> None:
    """공통: Book 실패 상태 업데이트"""
    try:
        async with AsyncSessionLocal() as session:
            repo = BookRepository(session)
            await repo.update(
                id=uuid.UUID(book_id),
                pipeline_stage="failed",
                error_message=f"{stage}: {error}",
                status=BookStatus.FAILED,
            )
            await session.commit()
    except Exception as e:
        logger.error(f"[Story Task] Failed to update error in DB: {e}")


async def _shorten_title(
    story_provider,
    title: str,
    max_length: int,
) -> str:
    """
    Title 길이 초과 시 AI에게 축약 요청 (1회 한정)

    Args:
        story_provider: AI provider (generate_text 메서드 필요)
        title: 원본 제목
        max_length: 최대 허용 길이

    Returns:
        축약된 제목 (실패 시 단순 자르기)
    """
    prompt = f"""Shorten this title to under {max_length} characters while keeping its core meaning.

Original title: "{title}"

Rules:
- Keep the main subject/theme
- Remove unnecessary words
- Must be under {max_length} characters

Return ONLY the shortened title, nothing else."""

    shortened = title  # AI 호출 실패 시 원본 사용

    try:
        result = await story_provider.generate_text(
            prompt=prompt,
            response_schema=ShortenedTitle,
        )

        # result 타입에 따라 title 추출
        if isinstance(result, str):
            # JSON 문자열인 경우 파싱
            try:
                data = json.loads(result)
                shortened = data.get("title", "").strip()
            except json.JSONDecodeError:
                # 순수 문자열인 경우
                shortened = result.strip()
        elif isinstance(result, dict):
            shortened = result.get("title", "").strip()
        else:
            # ShortenedTitle 객체
            shortened = result.title.strip()

        if 0 < len(shortened) <= max_length + 10:
            logger.info(
                f"[Story Task] Title shortened: '{title}' ({len(title)} chars) "
                f"→ '{shortened}' ({len(shortened)} chars)"
            )
            return shortened
        else:
            logger.warning(
                f"[Story Task] Shortened title invalid: '{shortened}' ({len(shortened)} chars)"
            )

    except Exception as e:
        logger.warning(f"[Story Task] Title shortening failed: {e}")

    # Fallback: 100자 이하면 단순 자르기, 초과면 에러
    max_fallback_length = max_length + 80  # 20 + 80 = 100

    if len(shortened) > max_fallback_length:
        # 100자 초과: 자르면 의미 손실이 큼 → 에러
        raise ValueError(
            f"Title too long for truncation ({len(shortened)} > {max_fallback_length} chars): '{shortened}'"
        )
    return shortened


async def _generate_story_phase(
    story_provider,
    book_id: str,
    stories: List[str],
    level: int,
    target_language: str,
    num_pages: int,
    max_retries: int,
) -> tuple[str, list] | None:
    """
    Phase 1: Story 생성 + 검증 (후보 누적 방식)

    재시도 시 생성된 (title, dialogues) 쌍을 누적 저장하고,
    마지막에 가장 짧은 제목을 가진 후보를 선택하여 에러 발생을 최소화합니다.

    Returns:
        (book_title, dialogues) 또는 실패 시 None
    """
    # 스키마 & 프롬프트 생성
    logger.info(
        f"[Story Task] [Book: {book_id}] stories={stories}, level={level}, num_pages={num_pages}"
    )
    response_schema = create_stories_response_schema(
        max_pages=num_pages,
        max_dialogues_per_page=settings.max_dialogues_per_page,
        max_chars_per_dialogue=settings.max_chars_per_dialogue,
        max_title_length=settings.max_title_length,
    )
    prompt = GenerateStoryPrompt(
        diary_entries=stories,
        level=level,
        target_language=target_language,
    ).render()

    # 후보 저장 리스트: (title, dialogues) 쌍
    candidates: list[tuple[str, list]] = []
    last_error: Exception | None = None
    max_fallback_length = settings.max_title_length + 80  # 100자

    for attempt in range(1, max_retries + 1):
        try:
            # AI 스토리 생성
            generated_data = await story_provider.generate_story(
                prompt=prompt,
                response_schema=response_schema,
            )
            title, dialogues = validate_generated_story(generated_data)

            # 페이지 수 검증 (불일치 시 후보에서 제외)
            if len(dialogues) != num_pages:
                logger.warning(
                    f"[Story Task] [Book: {book_id}] Attempt {attempt}/{max_retries}: "
                    f"Page count mismatch (expected {num_pages}, got {len(dialogues)}), skipping"
                )
                continue

            # Early Return: 30자 이하면 즉시 반환
            if len(title) <= settings.max_title_length + 10:
                logger.info(
                    f"[Story Task] [Book: {book_id}] Title within limit "
                    f"({len(title)} chars), returning immediately"
                )
                return (title, dialogues)

            # 제목 축약 시도 (30자 초과인 경우)
            logger.info(
                f"[Story Task] [Book: {book_id}] Title: '{title}' too long "
                f"({len(title)} chars), requesting AI shortening..."
            )
            try:
                title = await _shorten_title(
                    story_provider,
                    title,
                    settings.max_title_length,
                )
            except ValueError as shorten_error:
                # _shorten_title이 100자 초과로 실패한 경우
                logger.warning(
                    f"[Story Task] [Book: {book_id}] Attempt {attempt}/{max_retries}: "
                    f"Title shortening failed: {shorten_error}, skipping"
                )
                continue

            # 축약 후 검증
            if len(title) <= settings.max_title_length + 10:
                # 30자 이하로 축약 성공 → 즉시 반환
                logger.info(
                    f"[Story Task] [Book: {book_id}] Title shortened to {len(title)} chars, "
                    f"returning immediately"
                )
                return (title, dialogues)
            elif len(title) <= max_fallback_length:
                # 100자 이하: 후보에 추가
                candidates.append((title, dialogues))
                logger.info(
                    f"[Story Task] [Book: {book_id}] Added candidate: title='{title}' "
                    f"({len(title)} chars), total candidates: {len(candidates)}"
                )
            else:
                # 100자 초과: 후보에서 제외
                logger.warning(
                    f"[Story Task] [Book: {book_id}] Attempt {attempt}/{max_retries}: "
                    f"Title still too long after shortening ({len(title)} chars), skipping"
                )

        except Exception as e:
            last_error = e
            logger.warning(
                f"[Story Task] [Book: {book_id}] Attempt {attempt}/{max_retries} failed: {e}"
            )

        # 대기 (마지막 시도가 아닌 경우)
        if attempt < max_retries:
            delay = await calculate_retry_delay(attempt)
            logger.info(f"[Story Task] [Book: {book_id}] Retrying in {delay:.1f}s...")
            await asyncio.sleep(delay)

    # 모든 시도 완료 후: 후보 중 최선 선택
    if candidates:
        best = min(candidates, key=lambda c: len(c[0]))
        logger.info(
            f"[Story Task] [Book: {book_id}] Selected best candidate: title='{best[0]}' "
            f"({len(best[0])} chars) from {len(candidates)} candidates"
        )
        return best

    # 후보 없음: 실패 처리
    error_msg = str(last_error) if last_error else "No valid title candidates"
    logger.error(
        f"[Story Task] [Book: {book_id}] All {max_retries} attempts failed, "
        f"no valid candidates. Last error: {error_msg}"
    )
    await _mark_book_failed(book_id, "Story generation failed", error_msg)
    return None


async def _generate_emotion_phase(
    story_provider,
    dialogues: list,
    book_title: str,
    book_id: str,
    max_retries: int,
) -> StoryResponse | None:
    """
    Phase 2: Emotion 생성

    Returns:
        StoryResponse 또는 실패 시 None
    """

    async def _generate_emotion():
        emotion_prompt = EnhanceAudioPrompt(
            stories=dialogues, title=book_title
        ).render()
        return await story_provider.generate_story(
            prompt=emotion_prompt,
            response_schema=TTSExpressionResponse,
        )

    try:
        return await retry_with_config(
            func=_generate_emotion,
            max_retries=max_retries,
            error_message_prefix=f"[Story Task] [Book: {book_id}] Emotion generation",
        )
    except RuntimeError as e:
        logger.error(f"[Story Task] Emotion generation failed: {e}")
        await _mark_book_failed(book_id, "Emotion generation failed", str(e))
        return None


def _restructure_dialogues(dialogues: list, flat_emotions: list) -> list:
    """Emotion을 원본 페이지 구조에 맞게 재구성"""
    page_sizes = [len(page) for page in dialogues]
    result = []
    idx = 0
    for size in page_sizes:
        result.append(flat_emotions[idx : idx + size])
        idx += size
    return result


async def _save_story_to_db(
    book_id: str,
    dialogues: list,
    book_title: str,
    restructured_dialogues: list,
    target_language: str,
    context: TaskContext,
    max_retries: int,
    story_key: str,
) -> TaskResult:
    """
    Phase 3-4: Redis 저장 + DB 저장

    Returns:
        TaskResult (성공 또는 실패)
    """
    # Redis 저장
    task_store = TaskStore()
    logger.info(
        f"[Story Task] [Book: {book_id}] Saving to Redis: key={story_key}, "
        f"dialogues count={len(restructured_dialogues)}, title={book_title}"
    )
    await task_store.set(
        story_key,
        {"dialogues": restructured_dialogues, "title": book_title},
        ttl=3600,
    )
    logger.info(f"[Story Task] [Book: {book_id}] Redis save completed")

    # DB 저장
    async with AsyncSessionLocal() as session:
        try:
            repo = BookRepository(session)
            book_uuid = uuid.UUID(book_id)

            book = await repo.get_with_pages(book_uuid)
            if not book or not book.pages:
                raise ValueError(f"Book {book_id} has no pages for dialogues creation")

            # Dialogue + Translation 생성
            for page_idx, page_dialogues in enumerate(dialogues):
                page = next((p for p in book.pages if p.sequence == page_idx + 1), None)
                if not page:
                    logger.info(
                        f"[Story Task] [Book: {book_id}] Page {page_idx + 1} not found, skipping"
                    )
                    continue

                for dialogue_idx, dialogue_text in enumerate(page_dialogues):
                    await repo.add_dialogue_with_translation(
                        page_id=page.id,
                        speaker="Narrator",
                        sequence=dialogue_idx + 1,
                        translations=[
                            {
                                "language_code": target_language,
                                "text": dialogue_text,
                                "is_primary": True,
                            }
                        ],
                    )

            # Book 메타데이터 업데이트
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
            await _mark_book_failed(book_id, "DB save failed", str(e))
            return TaskResult(status=TaskStatus.FAILED, error=str(e))


# ============================================================
# Story Task Main Function
# ============================================================


async def generate_story_task(
    book_id: str,
    stories: List[str],
    level: int,
    num_pages: int,
    context: TaskContext,
    target_language: str = "en",
) -> TaskResult:
    """
    Task 1: Story 생성 (AI 호출) with 레벨별 난이도 조절

    Args:
        book_id: Book UUID (string)
        stories: 사용자 일기 항목 리스트
        level: 난이도 레벨 (1: 4-5세, 2: 5-6세, 3: 6-8세)
        num_pages: 페이지 수
        context: Task 실행 컨텍스트
        target_language: 목표 언어 코드 (en, ko, zh, vi, ru, th)

    Returns:
        TaskResult: 성공 시 story_data_key 반환
    """
    logger.info(
        f"[Story Task] Starting for book_id={book_id}, target_language={target_language}. level={level}, num_pages={num_pages}"
    )

    # === 준비 ===
    ai_factory = get_ai_factory()
    story_provider = ai_factory.get_story_provider()
    max_retries = settings.task_story_max_retries

    # 레벨 검증
    if not (settings.min_level <= level <= settings.max_level):
        logger.warning(
            f"[Story Task] Invalid level {level}, using default level {settings.min_level}"
        )
        level = settings.min_level

    # === Phase 1: Story 생성 ===
    result = await _generate_story_phase(
        story_provider=story_provider,
        book_id=book_id,
        stories=stories,
        level=level,
        target_language=target_language,
        num_pages=num_pages,
        max_retries=max_retries,
    )
    if result is None:
        return TaskResult(status=TaskStatus.FAILED, error="Story generation failed")

    book_title, dialogues = result
    # === Phase 2: Emotion 생성 ===
    emotion_result = await _generate_emotion_phase(
        story_provider, dialogues, book_title, book_id, max_retries
    )
    if emotion_result is None:
        return TaskResult(status=TaskStatus.FAILED, error="Emotion generation failed")

    logger.info(f"[Story Task] Emotion generated: {emotion_result}")
    flat_emotions = emotion_result.stories if emotion_result.stories else []
    restructured_dialogues = _restructure_dialogues(dialogues, flat_emotions)
    logger.info(
        f"[Story Task] Restructured dialogues: {len(restructured_dialogues)} pages"
    )

    # === Phase 3.5: 페이지별 대화 통합 (2D 구조 유지) ===
    merged_dialogues = _merge_page_dialogues(dialogues)
    merged_restructured = _merge_page_dialogues(restructured_dialogues)
    logger.info(
        f"[Story Task] [Book: {book_id}] Merged dialogues: {len(merged_dialogues)} pages, "
        f"each with 1 dialogue"
    )

    # === Phase 4: 저장 (Redis + DB) ===
    story_key = f"story:{book_id}"
    return await _save_story_to_db(
        book_id=book_id,
        dialogues=merged_dialogues,
        book_title=book_title,
        restructured_dialogues=merged_restructured,
        target_language=target_language,
        context=context,
        max_retries=max_retries,
        story_key=story_key,
    )


async def generate_image_task(
    book_id: str,
    images: List[bytes],
    context: TaskContext,
) -> TaskResult:
    """
    Task 2: Image 생성 (Async Mode + Polling)

    비동기 모드로 이미지 생성 요청을 제출하고 폴링으로 결과를 수집합니다.
    Cloudflare 타임아웃 문제를 해결하기 위해 동기 방식에서 변경되었습니다.

    Flow:
        Phase 1: Initialize trackers + Redis cache recovery
        Phase 2: Generate prompts from dialogues
        Phase 3: MAIN RETRY LOOP
            Phase 3a: Submit async requests (get task_uuids)
            Phase 3b: Polling loop (check_image_status)
            Phase 3c: Handle timeouts + Save to Redis
        Phase 4: Evaluate results (all/partial/failed)
        Phase 5: Download images from CDN → Save to S3
        Phase 6: Update database (Page.storybook_image_url)
        Phase 7: Save final results to Redis

    Args:
        book_id: Book UUID (string)
        images: 모든 페이지의 원본 이미지 바이트 리스트
        context: Task 실행 컨텍스트

    Returns:
        TaskResult: 성공 시 모든 페이지의 image_urls 반환
    """
    logger.info(
        f"[Image Task] [Book: {book_id}] Starting async batch processing, {len(images)} images"
    )
    # return ""

    # === Dependencies ===
    storage_service = get_storage_service()
    task_store = TaskStore()
    story_key = f"story:{book_id}"
    story_data = await task_store.get(story_key)
    dialogues = story_data.get("dialogues", []) if story_data else []

    # 디버깅: Redis에서 가져온 데이터 확인
    logger.info(
        f"[Image Task] [Book: {book_id}] Redis story_data exists: {story_data is not None}, "
        f"dialogues count: {len(dialogues)}, images count: {len(images)}"
    )

    # === Phase 1: Initialize Trackers ===
    logger.info(f"[Image Task] [Book: {book_id}] Phase 1: Initializing trackers")
    max_retries = settings.task_image_max_retries
    tracker = BatchRetryTracker(total_items=len(images), max_retries=max_retries)

    # Redis cache recovery (for restart scenarios)
    image_cache_key = f"images_cache:{book_id}"
    cached_data = await task_store.get(image_cache_key)
    if cached_data:
        for idx_str, img_info in cached_data.get("completed", {}).items():
            tracker.mark_success(int(idx_str), img_info)
        logger.info(
            f"[Image Task] [Book: {book_id}] Recovered {len(tracker.completed)} cached images from Redis"
        )

    # === Phase 2: Prompt 생성 ===
    logger.info(f"[Image Task] [Book: {book_id}] Phase 2: Generating prompts")
    prompts = [
        GenerateImagePrompt(stories=dialogue, style_keyword="cartoon").render()
        for dialogue in dialogues
    ]
    ai_factory = get_ai_factory()
    image_provider = ai_factory.get_image_provider()

    # === Phase 3: Async Request + Polling Loop ===
    while not tracker.is_all_completed():
        pending_indices = tracker.get_pending_indices()

        if not pending_indices:
            break

        logger.info(
            f"[Image Task] [Book: {book_id}] Phase 3: Processing {len(pending_indices)} images "
            f"(completed: {len(tracker.completed)}/{tracker.total_items})"
        )

        # === Phase 3a: Submit Async Requests ===
        logger.info(
            f"[Image Task] [Book: {book_id}] Phase 3a: Submitting async requests"
        )

        tasks = [
            image_provider.generate_image_from_image(
                image_data=images[idx], prompt=prompts[idx]
            )
            for idx in pending_indices
        ]

        # return_exceptions=True로 개별 실패 허용
        task_uuid_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Map successful submissions to pending_to_task_uuid
        pending_to_task_uuid: dict[int, str] = {}
        for idx, result in zip(pending_indices, task_uuid_results):
            if isinstance(result, Exception):
                tracker.mark_failure(idx, f"Request failed: {result}")
                logger.error(
                    f"[Image Task] [Book: {book_id}] Page {idx} request failed: {result}"
                )
            else:
                task_uuid = result.get("task_uuid")
                if task_uuid:
                    pending_to_task_uuid[idx] = task_uuid
                    logger.info(
                        f"[Image Task] [Book: {book_id}] Page {idx} submitted: task_uuid={task_uuid}"
                    )
                else:
                    tracker.mark_failure(idx, "No task_uuid in response")
                    logger.error(
                        f"[Image Task] [Book: {book_id}] Page {idx}: no task_uuid in response"
                    )

        if not pending_to_task_uuid:
            logger.warning(
                f"[Image Task] [Book: {book_id}] All requests failed, breaking loop"
            )
            break

        # === Phase 3b: Polling Loop ===
        logger.info(
            f"[Image Task] [Book: {book_id}] Phase 3b: Starting polling for {len(pending_to_task_uuid)} tasks"
        )

        max_wait_time = settings.task_image_max_wait_time  # 300 seconds
        poll_interval = settings.task_image_poll_interval  # 5 seconds
        elapsed_time = 0

        while elapsed_time < max_wait_time and pending_to_task_uuid:
            logger.info(
                f"[Image Task] [Book: {book_id}] Polling: {len(pending_to_task_uuid)} pending, "
                f"elapsed={elapsed_time}s/{max_wait_time}s"
            )

            for idx in list(pending_to_task_uuid.keys()):
                task_uuid = pending_to_task_uuid[idx]

                try:
                    status_response = await image_provider.check_image_status(task_uuid)
                    status = status_response["status"]
                    progress = status_response.get("progress", 0)

                    if status == "completed":
                        image_info = {
                            "imageUUID": status_response.get("image_uuid"),
                            "imageURL": status_response.get("image_url"),
                        }
                        tracker.mark_success(idx, image_info)
                        del pending_to_task_uuid[idx]
                        logger.info(
                            f"[Image Task] [Book: {book_id}] Page {idx} ✅ completed: "
                            f"imageURL={image_info['imageURL'][:50] if image_info['imageURL'] else 'None'}..."
                        )

                    elif status == "failed":
                        error_msg = status_response.get("error", "Unknown error")
                        tracker.mark_failure(idx, error_msg)
                        del pending_to_task_uuid[idx]
                        logger.error(
                            f"[Image Task] [Book: {book_id}] Page {idx} ❌ failed: {error_msg}"
                        )

                    else:
                        # processing/pending 상태
                        logger.info(
                            f"[Image Task] [Book: {book_id}] Page {idx} ⏳ {status} (progress={progress}%)"
                        )

                except Exception as e:
                    logger.error(
                        f"[Image Task] [Book: {book_id}] Page {idx} ⚠️ status check error: {e}"
                    )

            if pending_to_task_uuid:
                await asyncio.sleep(poll_interval)
                elapsed_time += poll_interval

        # Handle timed-out tasks
        for idx in list(pending_to_task_uuid.keys()):
            tracker.mark_failure(idx, "Image generation timeout")
            logger.warning(f"[Image Task] [Book: {book_id}] Page {idx} timed out")

        # === Phase 3c: Save Intermediate Results to Redis ===
        logger.info(
            f"[Image Task] [Book: {book_id}] Phase 3c: Saving intermediate results"
        )
        await task_store.set(
            image_cache_key,
            {
                "completed": {str(k): v for k, v in tracker.completed.items()},
                "retry_counts": tracker.retry_counts,
                "last_errors": tracker.last_errors,
            },
            ttl=3600,
        )

        # Wait before retry (if needed)
        if not tracker.is_all_completed() and tracker.get_pending_indices():
            delay = await calculate_retry_delay(max(tracker.retry_counts.values()))
            logger.info(f"[Image Task] [Book: {book_id}] Retrying in {delay:.1f}s...")
            await asyncio.sleep(delay)

    # === Phase 4: Evaluate Results ===
    logger.info(f"[Image Task] [Book: {book_id}] Phase 4: Evaluating results")
    if tracker.is_all_completed():
        status = TaskStatus.COMPLETED
        logger.info(
            f"[Image Task] [Book: {book_id}] All {tracker.total_items} images completed successfully"
        )
    elif tracker.is_partial_failure():
        status = TaskStatus.FAILED  # 부분 실패는 실패로 처리
        logger.error(
            f"[Image Task] [Book: {book_id}] Partial failure: "
            f"{len(tracker.completed)}/{tracker.total_items} images"
        )
    else:
        status = TaskStatus.FAILED
        logger.error(f"[Image Task] [Book: {book_id}] All images failed")

    # === Phase 5: Download and Store ALL Images ===
    logger.info(f"[Image Task] [Book: {book_id}] Phase 5: Starting image storage phase")

    # Get book for base_path
    async with AsyncSessionLocal() as session:
        repo = BookRepository(session)
        book = await repo.get(uuid.UUID(book_id))
        if not book:
            raise ValueError(f"Book {book_id} not found")
        base_path = book.base_path

    # Storage tracker (separate from generation tracker)
    storage_tracker = BatchRetryTracker(total_items=tracker.total_items, max_retries=2)

    # Pre-mark failed generation items as storage failed
    for idx in tracker.get_failed_indices():
        storage_tracker.mark_failure(idx, "Generation failed - skipping storage")

    # Download and store image
    async def download_and_store_image(idx: int, image_info: dict) -> str:
        """Download from Runware CDN and save to permanent storage"""
        image_url = image_info.get("imageURL")

        # Download with timeout
        timeout = httpx.Timeout(settings.http_timeout, read=settings.http_read_timeout)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(image_url)
            response.raise_for_status()
            image_bytes = response.content

        # Save to storage
        file_name = f"{base_path}/images/page_{idx + 1}.png"
        await storage_service.save(image_bytes, file_name, content_type="image/png")

        logger.info(
            f"[Image Task] [Book: {book_id}] Page {idx + 1}: "
            f"Saved to {file_name} ({len(image_bytes)} bytes)"
        )
        
        # Publish media optimization event for WebP conversion
        webp_file_name = file_name.replace('.png', '.webp')
        await publish_media_optimization_event(
            file_type="image_webp",
            input_path=file_name,
            output_path=webp_file_name,
            file_id=f"{book_id}_page_{idx + 1}",
        )

        return file_name

    # Process images sequentially for memory management
    for idx, image_info in tracker.completed.items():
        try:
            storage_path = await download_and_store_image(idx, image_info)
            storage_tracker.mark_success(idx, storage_path)
        except Exception as e:
            storage_tracker.mark_failure(idx, str(e))
            logger.error(
                f"[Image Task] [Book: {book_id}] Page {idx + 1} storage failed: {e}"
            )

    logger.info(
        f"[Image Task] [Book: {book_id}] Phase 5 completed: "
        f"{len(storage_tracker.completed)}/{storage_tracker.total_items} images stored"
    )

    # === Phase 6: DB Update (Page.image_url + Book metadata) ===
    logger.info(f"[Image Task] [Book: {book_id}] Phase 6: Updating database")
    async with AsyncSessionLocal() as session:
        try:
            repo = BookRepository(session)
            book_uuid = uuid.UUID(book_id)
            book = await repo.get_with_pages(book_uuid)

            if not book:
                raise ValueError(f"Book {book_id} not found")

            # Update each page with storybook image path and prompt
            for page_idx, storage_path in storage_tracker.completed.items():
                page = next((p for p in book.pages if p.sequence == page_idx + 1), None)
                if page:
                    page.storybook_image_url = storage_path
                    # 이미지 생성에 사용된 프롬프트 저장
                    page.image_prompt = prompts[page_idx]
                    session.add(page)
                    logger.debug(
                        f"[Image Task] [Book: {book_id}] Updated Page {page_idx + 1} "
                        f"storybook_image_url={storage_path}"
                    )

            # Update book with cover and metadata
            task_metadata = book.task_metadata or {}
            task_metadata["image"] = {
                **tracker.get_summary(),
                "storage": storage_tracker.get_summary(),
            }

            # Cover is first page image
            cover_path = storage_tracker.completed.get(0)

            updated = await repo.update(
                book_uuid,
                pipeline_stage="image",
                progress_percentage=60,
                cover_image=cover_path,
                task_metadata=task_metadata,
            )

            if not updated:
                raise ValueError(f"Book {book_id} not found for update")

            await session.commit()

            logger.info(
                f"[Image Task] [Book: {book_id}] Updated {len(storage_tracker.completed)} "
                f"page images, cover={cover_path is not None}"
            )

        except Exception as e:
            logger.error(
                f"[Image Task] [Book: {book_id}] DB update failed: {e}",
                exc_info=True,
            )
            return TaskResult(status=TaskStatus.FAILED, error=str(e))

    # === Phase 7: Save Final Results to Redis ===
    logger.info(
        f"[Image Task] [Book: {book_id}] Phase 7: Saving final results to Redis"
    )
    # Order preservation: build arrays using range(total_items)
    # 중요: None을 유지하여 Video Task에서 인덱스가 일치하도록 함
    image_infos = [tracker.completed.get(i) for i in range(tracker.total_items)]
    storage_paths = [
        storage_tracker.completed.get(i) for i in range(tracker.total_items)
    ]

    await task_store.set(
        f"images:{book_id}",
        {
            # None 유지하여 순서 보존 (Video Task에서 인덱스 매칭 필요)
            "images": image_infos,
            "storage_paths": storage_paths,
            "page_count": len(images),
            "failed_pages": tracker.get_failed_indices(),
            "storage_failed_pages": storage_tracker.get_failed_indices(),
        },
        ttl=3600,
    )

    logger.info(
        f"[Image Task] [Book: {book_id}] All phases completed. "
        f"Generated: {len(tracker.completed)}/{tracker.total_items}, "
        f"Stored: {len(storage_tracker.completed)}/{storage_tracker.total_items}"
    )
    return TaskResult(
        status=status,
        result={
            "image_infos": image_infos,
            "storage_paths": storage_paths,
            "page_count": len(images),
            "completed_count": len(tracker.completed),
            "failed_count": len(tracker.get_failed_indices()),
            "storage_completed_count": len(storage_tracker.completed),
            "storage_failed_count": len(storage_tracker.get_failed_indices()),
            "summary": tracker.get_summary(),
            "storage_summary": storage_tracker.get_summary(),
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
    # return ""
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
    # return ""
    ai_factory = get_ai_factory()
    video_provider = ai_factory.get_video_provider()

    task_store = TaskStore()
    story_key = f"story:{book_id}"
    story_data = await task_store.get(story_key)
    dialogues = story_data.get("dialogues", []) if story_data else []
    prompts = [
        GenerateVideoPrompt(dialogues=page_dialogues).render()
        for page_dialogues in dialogues
    ]

    image_key = f"images:{book_id}"
    image_data = await task_store.get(image_key)

    # 이미지 정보 추출 (None 포함하여 순서 유지)
    image_infos = image_data.get("images", []) if image_data else []

    # imageUUID 추출 (None인 경우 None 유지)
    image_uuids = [
        img_info["imageUUID"] if img_info is not None else None
        for img_info in image_infos
    ]

    # 이미지 생성 실패한 페이지 인덱스
    failed_image_indices = [idx for idx, uuid in enumerate(image_uuids) if uuid is None]

    if failed_image_indices:
        logger.warning(
            f"[Video Task] [Book: {book_id}] Skipping pages with failed images: {failed_image_indices}"
        )

    # === Phase 1: 재시도 추적기 초기화 ===
    max_retries = settings.task_video_max_retries
    total_pages = len(image_uuids)
    tracker = BatchRetryTracker(total_items=total_pages, max_retries=max_retries)

    # 이미지 생성 실패한 페이지는 영구 실패 처리 (재시도 불가)
    # retry_counts를 max_retries로 설정하여 get_pending_indices()에서 제외
    for idx in failed_image_indices:
        tracker.retry_counts[idx] = max_retries  # 최대 재시도 초과로 설정
        tracker.last_errors[idx] = "Image generation failed - skipping video"
        logger.debug(
            f"[Video Task] [Book: {book_id}] Page {idx} permanently failed: no image available"
        )

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
        status = TaskStatus.FAILED  # 부분 실패는 실패로 처리
        logger.error(
            f"[Video Task] [Book: {book_id}] Partial failure: "
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
            
            # Publish media optimization event for H.265 compression
            await publish_media_optimization_event(
                file_type="video_compress",
                input_path=file_name,
                output_path=file_name,  # Same path (replace original)
                file_id=f"{book_id}_page_{page_idx + 1}",
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
                page.video_prompt = prompts[page_idx]
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
                final_status = BookStatus.FAILED  # 부분 실패도 실패로 처리
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


def validate_generated_story(data: StoryResponse) -> tuple[str, list]:
    """
    StoryResponse 검증

    Args:
        data: AI Provider에서 반환된 StoryResponse

    Returns:
        (title, stories) 튜플

    Raises:
        ValueError: 검증 실패 시

    Note:
        길이 검증은 _generate_story_phase()에서 처리됨.
        초과 시 _shorten_title()로 AI 축약 요청.
    """
    if data is None:
        raise ValueError(
            "StoryResponse is None - AI returned empty response (check logs for details)"
        )

    # StoryResponse는 이미 파싱된 상태이므로 타입 체크만
    if not data.title or not isinstance(data.title, str):
        raise ValueError(f"Invalid title in StoryResponse. Got title={data.title}")

    if not data.stories or not isinstance(data.stories, list):
        raise ValueError(
            f"Invalid stories in StoryResponse. Got stories={data.stories}"
        )

    return data.title, data.stories
