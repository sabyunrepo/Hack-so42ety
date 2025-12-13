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

    async def test_fun(
        self,
        mode: str = "image",
        image_bytes: Optional[bytes] = None,
        prompt: str = "a cute cat playing with a ball",
        strength: float = 0.7,
        cfg_scale: float = 7.0,
        steps: int = 30,
        video_duration: int = 5,
        video_width: int = 1920,
        video_height: int = 1080,
    ) -> dict:
        """
        Runware 테스트 함수 (이미지 또는 비디오 생성)

        Args:
            mode: 생성 모드 ("image", "video")
            image_bytes: 입력 이미지 바이너리 (None인 경우 Text-to-Image 모드)
            prompt: 생성 프롬프트
            strength: 이미지-to-이미지 변환 강도 (0.0-1.0)
            cfg_scale: 프롬프트 가이드 강도
            steps: 디노이징 스텝
            video_duration: 비디오 길이 (초, video 모드일 때)
            video_width: 비디오 너비 (video 모드일 때)
            video_height: 비디오 높이 (video 모드일 때)

        Returns:
            dict: 생성 결과 정보
        """
        if mode == "video":
            return await self._test_video_generation(
                image_bytes=image_bytes,
                prompt=prompt,
                duration=video_duration,
                width=video_width,
                height=video_height,
            )
        else:
            return await self._test_image_generation(
                image_bytes=image_bytes,
                prompt=prompt,
                strength=strength,
                cfg_scale=cfg_scale,
                steps=steps,
            )

    async def _test_image_generation(
        self,
        image_bytes: Optional[bytes] = None,
        prompt: str = "a cute cat playing with a ball",
        strength: float = 0.7,
        cfg_scale: float = 7.0,
        steps: int = 30,
    ) -> dict:
        """이미지 생성 테스트 (내부 메서드)"""
        import time
        import os

        print(f"[test_fun] Starting image generation test")
        if image_bytes:
            print(f"  Mode: image-to-image")
            print(f"  Prompt: {prompt}")
            print(f"  Strength: {strength}, CFGScale: {cfg_scale}, Steps: {steps}")
        else:
            print(f"  Mode: text-to-image")
            print(f"  Prompt: {prompt}")

        # Runware image provider 가져오기
        image_provider = self.ai_factory.get_image_provider()

        try:
            # 이미지 생성 (text-to-image 또는 image-to-image)
            if image_bytes:
                # Image-to-Image 모드
                generated_image_bytes = await image_provider.generate_image_from_image(
                    image_data=image_bytes,
                    prompt=prompt,
                    width=1024,
                    height=1024,
                    strength=strength,
                    cfg_scale=cfg_scale,
                    steps=steps
                )
                gen_mode = "image-to-image"
            else:
                # Text-to-Image 모드
                generated_image_bytes = await image_provider.generate_image(
                    prompt=prompt,
                    width=1024,
                    height=1024
                )
                gen_mode = "text-to-image"

            image_size = len(generated_image_bytes)
            print(f"[test_fun] Image generated successfully. Size: {image_size} bytes")

            # backend 폴더 안에 임시 저장
            timestamp = int(time.time() * 1000)
            temp_dir = os.path.join(os.path.dirname(__file__), "..", "..", "temp_images")
            os.makedirs(temp_dir, exist_ok=True)

            temp_file_path = os.path.join(temp_dir, f"runware_test_{gen_mode}_{timestamp}.png")
            with open(temp_file_path, "wb") as f:
                f.write(generated_image_bytes)

            print(f"[test_fun] Image saved to: {temp_file_path}")

            return {
                "status": "success",
                "image_size": image_size,
                "image_path": temp_file_path,
                "mode": gen_mode,
                "parameters": {
                    "prompt": prompt,
                    "strength": strength if gen_mode == "image-to-image" else None,
                    "cfg_scale": cfg_scale,
                    "steps": steps
                },
                "message": f"Image generated ({gen_mode}) and saved! Size: {image_size} bytes ({image_size / 1024:.2f} KB)"
            }

        except Exception as e:
            logger.error(f"[test_fun] Error during image generation: {str(e)}")
            return {
                "status": "error",
                "image_size": 0,
                "image_path": None,
                "mode": "image-to-image" if image_bytes else "text-to-image",
                "parameters": {
                    "prompt": prompt,
                    "strength": strength if image_bytes else None,
                    "cfg_scale": cfg_scale,
                    "steps": steps
                },
                "message": f"Image generation failed: {str(e)}"
            }

    async def _test_video_generation(
        self,
        image_bytes: Optional[bytes] = None,
        prompt: str = "animate this scene with natural movement",
        duration: int = 5,
        width: int = 1920,
        height: int = 1080,
    ) -> dict:
        """
        비디오 생성 테스트 (내부 메서드)

        이미지 기반 비디오 생성:
        1. 이미지가 제공되지 않으면 먼저 이미지 생성
        2. 생성된/제공된 이미지로 비디오 생성
        3. Polling으로 완료 대기
        4. 완료된 비디오 다운로드 및 로컬 저장
        """
        import time
        import os
        import asyncio
        import traceback

        print(f"[test_fun] Starting video generation test")
        print(f"  Prompt: {prompt}")
        print(f"  Duration: {duration}s, Size: {width}x{height}")

        # Runware provider 가져오기 (video provider는 image provider와 동일)
        video_provider = self.ai_factory.get_image_provider()

        try:
            # Step 1: 이미지 준비 (없으면 생성 - 선택사항)
            if image_bytes is None:
                print("[test_fun] No image provided - using text-to-video mode")
                # Text-to-video 모드: 이미지 없이 텍스트만으로 비디오 생성
            else:
                print(f"[test_fun] Image provided. Size: {len(image_bytes)} bytes")
                # Image-to-video 모드: 제공된 이미지로 비디오 생성

            # Step 2: 비디오 생성 시작
            print("[test_fun] Starting video generation...")
            task_uuid = await video_provider.generate_video(
                image_data=image_bytes,  # None이면 text-to-video, 있으면 image-to-video
                prompt=prompt,
                duration=duration,
                width=width,
                height=height,
            )
            print(f"[test_fun] Video generation started. task_uuid: {task_uuid}")

            # Step 3: Polling으로 완료 대기 (최대 10분)
            max_wait_time = 600  # 10분
            poll_interval = 10   # 10초마다 체크
            elapsed_time = 0

            print(f"[test_fun] Polling for video completion (max {max_wait_time}s)...")

            video_url = None
            while elapsed_time < max_wait_time:
                await asyncio.sleep(poll_interval)
                elapsed_time += poll_interval

                print(f"[test_fun] Checking video status (elapsed: {elapsed_time}s)...")
                status_result = await video_provider.check_video_status(task_uuid)
                print(f"[test_fun] Status result: {status_result}")

                status = status_result.get("status")
                progress = status_result.get("progress", 0)

                print(f"[test_fun] Status: {status}, Progress: {progress}%, Elapsed: {elapsed_time}s")

                if status == "completed":
                    video_url = status_result.get("video_url")
                    print(f"[test_fun] Video generation completed! URL: {video_url}")
                    break
                elif status == "failed":
                    error_msg = status_result.get("error", "Unknown error")
                    print(f"[test_fun] Video generation failed with error: {error_msg}")
                    print(f"[test_fun] Full status result: {status_result}")
                    raise Exception(f"Video generation failed: {error_msg}")

            if video_url is None:
                raise Exception(f"Video generation timed out after {max_wait_time}s")

            # Step 4: 비디오 다운로드
            print(f"[test_fun] Downloading video from: {video_url}")
            video_bytes = await video_provider.download_video(video_url)
            video_size = len(video_bytes)
            print(f"[test_fun] Video downloaded. Size: {video_size} bytes ({video_size / 1024 / 1024:.2f} MB)")

            # Step 5: 로컬 저장
            timestamp = int(time.time() * 1000)
            temp_dir = os.path.join(os.path.dirname(__file__), "..", "..", "temp_videos")
            os.makedirs(temp_dir, exist_ok=True)

            temp_file_path = os.path.join(temp_dir, f"runware_test_video_{timestamp}.mp4")
            with open(temp_file_path, "wb") as f:
                f.write(video_bytes)

            print(f"[test_fun] Video saved to: {temp_file_path}")

            return {
                "status": "success",
                "video_size": video_size,
                "video_path": temp_file_path,
                "video_url": video_url,
                "mode": "image-to-video",
                "parameters": {
                    "prompt": prompt,
                    "duration": duration,
                    "width": width,
                    "height": height,
                },
                "processing_time": elapsed_time,
                "message": f"Video generated and saved! Size: {video_size} bytes ({video_size / 1024 / 1024:.2f} MB), Time: {elapsed_time}s"
            }

        except Exception as e:
            # 상세한 에러 정보 출력
            error_type = type(e).__name__
            error_message = str(e)
            error_traceback = traceback.format_exc()

            print(f"\n{'='*80}")
            print(f"[test_fun] ERROR DETAILS:")
            print(f"  Error Type: {error_type}")
            print(f"  Error Message: {error_message}")
            print(f"  Error Repr: {repr(e)}")
            print(f"\nFull Traceback:")
            print(error_traceback)
            print(f"{'='*80}\n")

            logger.error(f"[test_fun] Error during video generation: {error_type}: {error_message}")
            logger.error(f"Traceback: {error_traceback}")

            return {
                "status": "error",
                "video_size": 0,
                "video_path": None,
                "mode": "image-to-video",
                "parameters": {
                    "prompt": prompt,
                    "duration": duration,
                    "width": width,
                    "height": height,
                },
                "error_type": error_type,
                "error_details": error_message,
                "message": f"Video generation failed: {error_type}: {error_message}"
            }

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

    @log_process(step="Create Storybook", desc="동화책 생성 전체 프로세스 (스토리+이미지+오디오)")
    async def create_storybook(
        self,
        user_id: uuid.UUID,
        prompt: str,
        num_pages: int = 5,
        target_age: str = "5-7",
        theme: str = "adventure",
        is_public: bool = False,
        visibility: str = "private",
    ) -> Book:
        """
        동화책 생성 (스토리 -> 이미지 -> 오디오)
        """
        # 할당량 검사
        await self._check_book_quota(user_id)

        # 페이지 수 검증
        if num_pages < 1 or num_pages > settings.max_pages_per_book:
            raise InvalidPageCountException(
                page_count=num_pages, max_pages=settings.max_pages_per_book
            )

        # 1. 스토리 생성
        story_provider = self.ai_factory.get_story_provider()

        # 프롬프트 구성
        full_prompt = f"""
        Create a children's story for age {target_age} with theme '{theme}'.
        Topic: {prompt}
        Length: {num_pages} pages.
        Format: JSON with 'title', 'pages' (list of {{"content": "...", "image_prompt": "..."}}).
        """

        # JSON 파싱을 위해 AI가 JSON만 반환하도록 유도하거나, 파싱 로직이 필요함.
        # 여기서는 AI Provider가 구조화된 데이터를 반환한다고 가정하거나,
        # generate_story_with_images 메서드를 활용.

        try:
            generated_data = await story_provider.generate_story_with_images(
                prompt=full_prompt,
                num_images=num_pages,
                context={"target_age": target_age, "theme": theme},
            )
        except Exception as e:
            raise AIGenerationFailedException(stage="스토리", reason=str(e))

        # 2. 책 엔티티 생성
        book = await self.book_repo.create(
            user_id=user_id,
            title=generated_data.get("title", "Untitled Story"),
            target_age=target_age,
            theme=theme,
            status=BookStatus.CREATING,
            is_public=is_public,
            visibility=visibility,
        )

        try:
            pages_data = generated_data.get("pages", [])

            # 3. 페이지 및 이미지 생성 (병렬 처리 가능)
            image_provider = self.ai_factory.get_image_provider()

            for i, page_data in enumerate(pages_data):
                content = page_data.get("content", "")
                image_prompt = page_data.get("image_prompt", "")

                # 이미지 생성
                image_url = None
                if image_prompt:
                    try:
                        image_bytes = await image_provider.generate_image(
                            prompt=image_prompt, width=1024, height=1024
                        )
                    except Exception as e:
                        raise AIGenerationFailedException(stage="이미지", reason=str(e))

                    # 스토리지 저장 (Book의 base_path 사용)
                    try:
                        file_name = f"{book.base_path}/images/page_{i+1}.png"
                        image_url = await self.storage_service.save(
                            image_bytes, file_name, content_type="image/png"
                        )
                        # storage_service.save()가 반환하는 URL 그대로 사용
                        # Local: /api/v1/files/...
                        # S3: Pre-signed URL
                    except Exception as e:
                        raise ImageUploadFailedException(
                            filename=file_name, reason=str(e)
                        )

                # 페이지 저장
                page = await self.book_repo.add_page(
                    book_id=book.id,
                    page_data={
                        "sequence": i + 1,
                        "image_url": image_url,
                        "image_prompt": image_prompt,
                    },
                )

                # 4. (옵션) TTS 생성 - 대사가 있다면
                # 현재 구조에서는 Page content 전체를 읽거나, 별도 Dialogue 파싱이 필요
                # 여기서는 간단히 Page content 전체를 TTS로 변환하여 Page의 audio_url에 저장한다고 가정
                # 또는 Dialogue 모델을 사용

                # TTS Provider
                # tts_provider = self.ai_factory.get_tts_provider() # No longer needed here
                
                if content:
                    # Create dialogue with translations
                    dialogue = await self.book_repo.add_dialogue_with_translation(
                        page_id=page.id,
                        speaker="Narrator",
                        sequence=1,
                        translations=[
                            {"language_code": "en", "text": content, "is_primary": True}
                        ],
                    )

                    # TTS Background Generation (Concurrency Control)
                    try:
                        # 1. Pre-calculate path (where worker should save)
                        # We use relative path compatible with storage service
                        audio_file_name = f"{book.base_path}/audios/page_{i+1}.mp3"
                        # For local storage, user likely configured correct base path.
                        # We store the 'key' (relative path) in audio_url
                        
                        # 2. Add DB record with PENDING status
                        voice_id = (
                            settings.DEFAULT_VOICE_ID
                            if hasattr(settings, "DEFAULT_VOICE_ID")
                            else "default"
                        )
                        
                        dialogue_audio = await self.book_repo.add_dialogue_audio(
                            dialogue_id=dialogue.id,
                            language_code="en",
                            voice_id=voice_id,
                            audio_url=audio_file_name,
                            status="PENDING"
                        )
                        
                        # 3. Enqueue Task
                        if self.tts_producer:
                            await self.tts_producer.enqueue_tts_task(
                                dialogue_audio_id=dialogue_audio.id,
                                text=content
                            )
                        else:
                            # Fallback if producer not injected (shouldn't happen in prod)
                            # Maybe log warning or raise?
                            print("Warning: TTSProducer not injected, skipping TTS queueing.")
                            
                    except Exception as e:
                        # TTS queueing failed, but Book creation should succeed? 
                        # Or fail entire book? 
                        # Ideally log and continue (partial success), but user might expect audio.
                        # For now, we raise to signal failure early, or create FAILED record.
                        # Let's catch and update status if record exists?
                        # Simplest: Raise exception -> Book FAILED.
                        raise AIGenerationFailedException(stage="음성 큐 등록", reason=str(e))

            # 상태 업데이트
            book.status = BookStatus.COMPLETED
            await self.db_session.commit()

            return await self.book_repo.get_with_pages(book.id)

        except (
            AIGenerationFailedException,
            ImageUploadFailedException,
            InvalidPageCountException,
        ):
            # 커스텀 예외는 그대로 전파
            book.status = BookStatus.FAILED
            await self.db_session.commit()
            raise
        except Exception as e:
            # 예상치 못한 에러는 StorybookCreationFailedException으로 감싸기
            book.status = BookStatus.FAILED
            await self.db_session.commit()
            raise StorybookCreationFailedException(reason=str(e))

    async def create_storybook_async(
        self,
        user_id: uuid.UUID,
        stories: List[str],
        images: List[bytes],
        voice_id: str,
        level: int,

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
        await self._check_book_quota(user_id)

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
            pipeline_stage="init",
        )
        await self.db_session.commit()

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

        print(
            f"[BookService] Started async DAG for book {book.id}, "
            f"execution_id={task_ids.get('execution_id')}"
        )

        return book

    @log_process(step="Create Storybook (Image Implemented)", desc="이미지 기반 동화책 생성")
    async def create_storybook_with_images(
        self,
        user_id: uuid.UUID,
        stories: List[str],
        images: List[bytes],  # 이미지 바이너리 데이터
        image_content_types: List[str],
        voice_id: Optional[str] = None,
    ) -> Book:
        """
        이미지 기반 동화책 생성 (Image-to-Image)
        """
        # 할당량 검사
        await self._check_book_quota(user_id)

        # 스토리와 이미지 개수 검증
        if len(stories) != len(images):
            raise StoriesImagesMismatchException(
                stories_count=len(stories), images_count=len(images)
            )

        # 페이지 수 검증
        if len(stories) < 1 or len(stories) > settings.max_pages_per_book:
            raise InvalidPageCountException(
                page_count=len(stories), max_pages=settings.max_pages_per_book
            )

        # 1. 책 엔티티 생성 (기본값: is_public=False, visibility="private")
        book = await self.book_repo.create(
            user_id=user_id,
            title=(
                stories[0][:20] if stories else "Untitled Story"
            ),  # 첫 문장을 제목으로 임시 사용
            target_age="5-7",  # 기본값
            theme="custom",
            status=BookStatus.CREATING,
            is_public=False,  # 기본값
            visibility="private",  # 기본값
        )

        try:
            image_provider = self.ai_factory.get_image_provider()
            tts_provider = self.ai_factory.get_tts_provider()

            for i, (story, image_bytes, content_type) in enumerate(
                zip(stories, images, image_content_types)
            ):
                # 2. 이미지 생성 (Image-to-Image)
                # 원본 이미지를 먼저 저장 (옵션)
                # original_image_url = await self.storage_service.save(...)

                # AI 이미지 생성
                try:
                    generated_image_bytes = (
                        await image_provider.generate_image_from_image(
                            image_data=image_bytes,
                            prompt=story,  # 스토리를 프롬프트로 사용
                            style="cartoon",
                        )
                    )
                except Exception as e:
                    raise AIGenerationFailedException(stage="이미지", reason=str(e))

                # 생성된 이미지 저장 (Book의 base_path 사용)
                try:
                    file_name = f"{book.base_path}/images/page_{i+1}.png"
                    image_url = await self.storage_service.save(
                        generated_image_bytes, file_name, content_type="image/png"
                    )
                    # storage_service.save()가 반환하는 URL 그대로 사용
                except Exception as e:
                    raise ImageUploadFailedException(filename=file_name, reason=str(e))

                # 3. 페이지 저장
                page = await self.book_repo.add_page(
                    book_id=book.id,
                    page_data={
                        "sequence": i + 1,
                        "image_url": image_url,
                        "image_prompt": story,  # 프롬프트로 사용된 스토리 저장
                    },
                )

                # 4. TTS 생성
                if story:
                    # Create dialogue with translations
                    dialogue = await self.book_repo.add_dialogue_with_translation(
                        page_id=page.id,
                        speaker="Narrator",
                        sequence=1,
                        translations=[
                            {"language_code": "en", "text": story, "is_primary": True}
                        ],
                    )

                    # TTS Background Generation (Concurrency Control)
                    try:
                        # 1. Pre-calculate path
                        audio_file_name = f"{book.base_path}/audios/page_{i+1}.mp3"
                        
                        # 2. Add DB record PENDING
                        target_voice_id = voice_id or (
                            settings.DEFAULT_VOICE_ID
                            if hasattr(settings, "DEFAULT_VOICE_ID")
                            else "default"
                        )
                        
                        dialogue_audio = await self.book_repo.add_dialogue_audio(
                            dialogue_id=dialogue.id,
                            language_code="en",
                            voice_id=target_voice_id,
                            audio_url=audio_file_name,
                            status="PENDING"
                        )
                        
                        # 3. Enqueue Task
                        if self.tts_producer:
                            await self.tts_producer.enqueue_tts_task(
                                dialogue_audio_id=dialogue_audio.id,
                                text=story
                            )
                        else:
                             print("Warning: TTSProducer not injected in with-images.")

                    except Exception as e:
                        raise AIGenerationFailedException(stage="음성 큐 등록", reason=str(e))

            # 상태 업데이트
            book.status = BookStatus.COMPLETED
            await self.db_session.commit()

            return await self.book_repo.get_with_pages(book.id)

        except (
            StoriesImagesMismatchException,
            InvalidPageCountException,
            AIGenerationFailedException,
            ImageUploadFailedException,
        ):
            # 커스텀 예외는 그대로 전파
            book.status = BookStatus.FAILED
            await self.db_session.commit()
            raise
        except Exception as e:
            # 예상치 못한 에러는 StorybookCreationFailedException으로 감싸기
            book.status = BookStatus.FAILED
            await self.db_session.commit()
            raise StorybookCreationFailedException(reason=str(e))

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
