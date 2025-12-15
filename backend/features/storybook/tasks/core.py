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
from backend.core.limiters import get_limiters
from backend.features.tts.exceptions import BookVoiceNotConfiguredException
from backend.features.tts.producer import TTSProducer
# from backend.features.storybook.dependencies import get_tts_producer


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
    ai_factory = get_ai_factory()
    story_provider = ai_factory.get_story_provider()

    MAX_RETRIES = 3

    max_dialogues_per_page = 3  # 임시 고정값, 추후 조정 가능


    response_schema = create_stories_response_schema(
        max_pages=num_pages,
        max_dialogues_per_page=max_dialogues_per_page,
        max_chars_per_dialogue=85,
        max_title_length=20,
    )
    prompt = GenerateStoryPrompt(diary_entries=stories).render()

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            generated_data = await story_provider.generate_story(
                prompt=prompt,
                response_schema=response_schema,
            )

            logger.info(
                f"[Story Task] [Book: {book_id}] Attempt {attempt} generated_data={generated_data}"
            )

            book_title, dialogues = validate_generated_story(generated_data)

            # ✅ 성공
            break

        except Exception as e:
            last_error = e
            logger.info(
                f"[Story Task] [Book: {book_id}] Attempt {attempt} failed: {e}"
            )

    else:
        # ❌ 모든 시도 실패
        logger.error(
            f"[Story Task] All retries failed. Last error: {last_error}"
        )
        raise RuntimeError(
            f"Failed to generate valid story after {MAX_RETRIES} retries"
        )

    # === Phase 2: AI 호출 (Emotion 추가) - 세션 밖에서 실행 ===
    emotion_prefixed_prompt = EnhanceAudioPrompt(stories=dialogues, title=book_title).render()
    response_with_emotion = await story_provider.generate_story(
        prompt=emotion_prefixed_prompt,
        response_schema=TTSExpressionResponse,
    )
    logger.info(f"[Story Task] Generating story with emotions: {response_with_emotion}")
    dialogues_with_emotions = response_with_emotion.stories

    # === Phase 3: Redis 저장 - 세션 밖에서 실행 ===
    task_store = TaskStore()
    story_key = f"story:{book_id}"
    await task_store.set(story_key, {"dialogues": dialogues_with_emotions, "title": book_title}, ttl=3600)

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
                    logger.info(f"[Story Task] [Book: {book_id}] Page {page_idx + 1} not found, skipping dialogues")
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

            # Update DB with title and progress
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

            file_name = f"{book.base_path}/images/cover.png"
            logger.info(f"[Image Task] [Book: {book_id}] Using base_path: {book.base_path}, is_default: {book.is_default}")
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
            logger.info(f"[Image Task] [Book: {book_id}] Updated book with cover image: {file_name}")
            logger.info(f"[Image Task] [Book: {book_id}] ####################################################################")
            logger.info(f"[Image Task] [Book: {book_id}] Image COMPLETED!!!!!!!!!!!!!!!!")
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
            logger.info(f"[TTS Task] [Book: {book_id}] Book loaded: user_id={book.user_id}, voice_id={book.voice_id}")

            # === Phase 2: Build Task List ===
            tasks_to_generate = []
            for page in book.pages:
                for dialogue in page.dialogues:
                    primary_translation = next(
                        (t for t in dialogue.translations if t.is_primary),
                        None
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

                    # file_name = f"users/{book.user_id}/audios/standalone/{uuid.uuid4()}.mp3"
                    audio_uuid = uuid.uuid4()
                    file_name = f"{book.base_path}/{audio_uuid}.mp3"
                    logger.info(f"[TTS Task] [Book: {book_id}] Audio path: {file_name} (is_default: {book.is_default})")
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

                    logger.info(f"[TTS Task] [Book: {book_id}] Enqueuing TTS for dialogue {dialogue.id}, audio_id={audio.id}")
                    logger.info(f"[TTS Task] [Book: {book_id}] Text: {primary_translation.text}")
                    await tts_producer.enqueue_tts_task(
                        dialogue_audio_id=audio.id,
                        text=primary_translation.text,
                    )

            await repo.update(
                book_uuid,
                pipeline_stage="tts",
                progress_percentage=70,
                error_message=None,
            )
            await session.commit()
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
    logger.info(f"[Video Task] [Book: {book_id}] Generated prompts: {prompts}")

    image_key = f"images:{book_id}"
    image_data = await task_store.get(image_key)
    image_uuids = [img_info['imageUUID'] for img_info in image_data.get("images", [])] if image_data else []

    # 글로벌 세마포어로 비디오 생성 동시성 제어
    limiters = get_limiters()
    tasks = []

    for img_uuid, prompt in zip(image_uuids, prompts):
        async def generate_with_limit(uuid=img_uuid, p=prompt):
            """세마포어로 동시 생성 제어"""
            async with limiters.video_generation:
                logger.info(f"[Video Task] [Book: {book_id}] Acquiring semaphore for image {uuid[:8]}...")
                return await video_provider.generate_video(image_uuid=uuid, prompt=p)

        tasks.append(generate_with_limit())

    # asyncio.gather로 병렬 실행 (세마포어 내에서 동시성 제어)
    logger.info(f"[Video Task] [Book: {book_id}] Starting {len(tasks)} video requests (server limit: {settings.video_generation_limit})")
    task_uuids = await asyncio.gather(*tasks)  # generate_video()는 task_uuid 문자열을 직접 반환

    # task_uuid → page_idx 매핑 생성 (순서 보장을 위해)
    task_to_page_idx = {task_uuid: idx for idx, task_uuid in enumerate(task_uuids)}
    logger.info(f"[Video Task] [Book: {book_id}] Created task mapping for {len(task_uuids)} pages")

    max_wait_time = 600  # 10분
    poll_interval = 10   # 10초마다 체크
    elapsed_time = 0
    completed_videos = {}  # task_uuid → video_url 매핑 (딕셔너리로 변경)

    while elapsed_time < max_wait_time and len(completed_videos) < len(task_uuids):
        for task_uuid in task_uuids:
            if task_uuid in completed_videos:  # O(1) 딕셔너리 탐색
                continue  # 이미 완료된 작업

            status_response = await video_provider.check_video_status(task_uuid)
            logger.info(f"[Video Task] [Book: {book_id}] Checked status for task {task_uuid[:8]}...: {status_response['status']}")
            if status_response["status"] == "completed":
                completed_videos[task_uuid] = status_response["video_url"]
                page_idx = task_to_page_idx[task_uuid]
                logger.info(f"[Video Task] [Book: {book_id}] Page {page_idx + 1} (task {task_uuid[:8]}...) completed")
            elif status_response["status"] == "failed":
                page_idx = task_to_page_idx[task_uuid]
                logger.info(f"[Video Task] [Book: {book_id}] Page {page_idx + 1} (task {task_uuid[:8]}...) failed")

        if len(completed_videos) < len(task_uuids):
            await asyncio.sleep(poll_interval)
            elapsed_time += poll_interval

    # 완료되지 않은 작업 확인
    if len(completed_videos) < len(task_uuids):
        failed_tasks = set(task_uuids) - set(completed_videos.keys())
        logger.info(f"[Video Task] [Book: {book_id}] {len(failed_tasks)} videos failed or timed out")

    logger.info(f"[Video Task] [Book: {book_id}] Completed {len(completed_videos)}/{len(task_uuids)} videos")

    # === Phase: Get Book object for base_path (minimal DB access) ===
    async with AsyncSessionLocal() as temp_session:
        temp_repo = BookRepository(temp_session)
        book_uuid = uuid.UUID(book_id)
        book = await temp_repo.get(book_uuid)
        if not book:
            raise ValueError(f"Book {book_id} not found")

    # === Phase: HTTP 다운로드 + S3 업로드 - 세션 밖에서 실행 ===
    # task_uuids 순서대로 정렬하여 video_urls 추출 (페이지 순서 보장)
    storage_service = get_storage_service()
    s3_video_urls = []

    for page_idx, task_uuid in enumerate(task_uuids):
        if task_uuid not in completed_videos:
            # 실패하거나 타임아웃된 경우
            logger.info(f"[Video Task] [Book: {book_id}] Page {page_idx + 1}: Video not completed, skipping")
            s3_video_urls.append(None)  # 순서 유지를 위해 None 추가
            continue

        video_url = completed_videos[task_uuid]
        video_bytes = await video_provider.download_video(video_url)
        video_size = len(video_bytes)

        file_name = f"{book.base_path}/videos/video_{page_idx}.mp4"
        logger.info(f"[Video Task] [Book: {book_id}] Page {page_idx + 1}: Video path: {file_name} (is_default: {book.is_default})")
        storage_url = await storage_service.save(
            video_bytes,
            file_name,
            content_type="video/mp4"
        )
        logger.info(f"[Video Task] [Book: {book_id}] Page {page_idx + 1}: Uploaded to {storage_url} (size: {video_size} bytes)")
        s3_video_urls.append(file_name)

    # === Phase: DB 작업만 세션 안에서 실행 ===
    async with AsyncSessionLocal() as session:
        try:
            repo = BookRepository(session)
            book_uuid = uuid.UUID(book_id)
            book = await repo.get_with_pages(book_uuid)  # ✅ eager loading
            pages = book.pages

            # Update pages with video URLs
            for page_idx, video_url in enumerate(s3_video_urls):
                if video_url is None:
                    # 실패한 비디오는 건너뛰기
                    logger.info(f"[Video Task] [Book: {book_id}] Page {page_idx + 1}: Skipping DB update (video failed)")
                    continue

                page = next((p for p in pages if p.sequence == page_idx + 1), None)
                if not page:
                    logger.info(f"[Video Task] [Book: {book_id}] Page {page_idx + 1} not found in DB, skipping video")
                    continue
                page.image_url = video_url  # 또는 video_url용 컬럼이 있으면 그것
                session.add(page)  # ORM 세션에 반영

            # Update book progress
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
            logger.error(f"[Video Task] [Book: {book_id}] Video generation failed: {e}", exc_info=True)
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

    # === Phase 1: Redis 조회 - 세션 밖에서 실행 ===
    task_store = TaskStore()
    story_key = f"story:{book_id}"
    story_data = await task_store.get(story_key)
    book_title = story_data.get("title", "Untitled Story") if story_data else "Untitled Story"
    num_pages = len(story_data.get("dialogues", [])) if story_data else 0

    # === Phase 2: DB 작업만 세션 안에서 실행 ===
    async with AsyncSessionLocal() as session:
        try:
            repo = BookRepository(session)
            book_uuid = uuid.UUID(book_id)

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
            logger.info(f"[Finalize Task] [Book: {book_id}] Updated book status to COMPLETED")

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

    # === Phase 3: Redis Cleanup - 세션 밖에서 실행 (비동기, 에러 무시) ===
    try:
        cleanup_count = await task_store.cleanup_book_tasks(book_id)
        logger.info(f"[Finalize Task] [Book: {book_id}] Cleaned up {cleanup_count} Redis keys")
    except Exception as cleanup_error:
        logger.info(f"[Finalize Task] [Book: {book_id}] Redis cleanup failed: {cleanup_error}")

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
