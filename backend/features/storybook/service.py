import uuid
import asyncio
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    Book, Page, Dialogue, DialogueTranslation, DialogueAudio, BookStatus
)
from .repository import BookRepository
from backend.infrastructure.ai.factory import AIProviderFactory
from backend.infrastructure.storage.base import AbstractStorageService
from backend.core.config import settings
from .exceptions import (
    StorybookNotFoundException,
    StorybookUnauthorizedException,
    StorybookCreationFailedException,
    ImageUploadFailedException,
    StoriesImagesMismatchException,
    AIGenerationFailedException,
    InvalidPageCountException,
)

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
    ):
        self.book_repo = book_repo
        self.storage_service = storage_service
        self.ai_factory = ai_factory
        self.db_session = db_session

    async def create_storybook(
        self,
        user_id: uuid.UUID,
        prompt: str,
        num_pages: int = 5,
        target_age: str = "5-7",
        theme: str = "adventure",
    ) -> Book:
        """
        동화책 생성 (스토리 -> 이미지 -> 오디오)
        """
        # 페이지 수 검증
        if num_pages < 1 or num_pages > 20:
            raise InvalidPageCountException(page_count=num_pages)

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
                context={"target_age": target_age, "theme": theme}
            )
        except Exception as e:
            raise AIGenerationFailedException(stage="스토리", reason=str(e))
        
        # 2. 책 엔티티 생성
        book = await self.book_repo.create(
            user_id=user_id,
            title=generated_data.get("title", "Untitled Story"),
            target_age=target_age,
            theme=theme,
            status=BookStatus.CREATING
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
                            prompt=image_prompt,
                            width=1024,
                            height=1024
                        )
                    except Exception as e:
                        raise AIGenerationFailedException(stage="이미지", reason=str(e))

                    # 스토리지 저장
                    try:
                        file_name = f"books/{book.id}/pages/{i+1}.png"
                        image_url = await self.storage_service.save(
                            image_bytes,
                            file_name,
                            content_type="image/png"
                        )
                    except Exception as e:
                        raise ImageUploadFailedException(filename=file_name, reason=str(e))
                
                # 페이지 저장
                page = await self.book_repo.add_page(
                    book_id=book.id,
                    page_data={
                        "sequence": i + 1,
                        "image_url": image_url,
                        "image_prompt": image_prompt
                    }
                )
                
                # 4. (옵션) TTS 생성 - 대사가 있다면
                # 현재 구조에서는 Page content 전체를 읽거나, 별도 Dialogue 파싱이 필요
                # 여기서는 간단히 Page content 전체를 TTS로 변환하여 Page의 audio_url에 저장한다고 가정
                # 또는 Dialogue 모델을 사용

                # TTS Provider
                tts_provider = self.ai_factory.get_tts_provider()
                if content:
                    # Create dialogue with translations
                    dialogue = await self.book_repo.add_dialogue_with_translation(
                        page_id=page.id,
                        speaker="Narrator",
                        sequence=1,
                        translations=[
                            {
                                "language_code": "en",
                                "text": content,
                                "is_primary": True
                            }
                        ]
                    )

                    # Generate and add audio
                    try:
                        audio_bytes = await tts_provider.text_to_speech(content)
                    except Exception as e:
                        raise AIGenerationFailedException(stage="음성", reason=str(e))

                    try:
                        audio_file_name = f"books/{book.id}/pages/{i+1}.mp3"
                        audio_url = await self.storage_service.save(
                            audio_bytes,
                            audio_file_name,
                            content_type="audio/mpeg"
                        )
                    except Exception as e:
                        raise ImageUploadFailedException(filename=audio_file_name, reason=str(e))

                    await self.book_repo.add_dialogue_audio(
                        dialogue_id=dialogue.id,
                        language_code="en",
                        voice_id=settings.DEFAULT_VOICE_ID if hasattr(settings, 'DEFAULT_VOICE_ID') else "default",
                        audio_url=audio_url
                    )

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
        # 스토리와 이미지 개수 검증
        if len(stories) != len(images):
            raise StoriesImagesMismatchException(
                stories_count=len(stories),
                images_count=len(images)
            )

        # 페이지 수 검증
        if len(stories) < 1 or len(stories) > 20:
            raise InvalidPageCountException(page_count=len(stories))

        # 1. 책 엔티티 생성
        book = await self.book_repo.create(
            user_id=user_id,
            title=stories[0][:20] if stories else "Untitled Story", # 첫 문장을 제목으로 임시 사용
            target_age="5-7", # 기본값
            theme="custom",
            status=BookStatus.CREATING
        )
        
        try:
            image_provider = self.ai_factory.get_image_provider()
            tts_provider = self.ai_factory.get_tts_provider()
            
            for i, (story, image_bytes, content_type) in enumerate(zip(stories, images, image_content_types)):
                # 2. 이미지 생성 (Image-to-Image)
                # 원본 이미지를 먼저 저장 (옵션)
                # original_image_url = await self.storage_service.save(...)

                # AI 이미지 생성
                try:
                    generated_image_bytes = await image_provider.generate_image_from_image(
                        image_data=image_bytes,
                        prompt=story, # 스토리를 프롬프트로 사용
                        style="cartoon"
                    )
                except Exception as e:
                    raise AIGenerationFailedException(stage="이미지", reason=str(e))

                # 생성된 이미지 저장
                try:
                    file_name = f"books/{book.id}/pages/{i+1}.png"
                    image_url = await self.storage_service.save(
                        generated_image_bytes,
                        file_name,
                        content_type="image/png"
                    )
                except Exception as e:
                    raise ImageUploadFailedException(filename=file_name, reason=str(e))
                
                # 3. 페이지 저장
                page = await self.book_repo.add_page(
                    book_id=book.id,
                    page_data={
                        "sequence": i + 1,
                        "image_url": image_url,
                        "image_prompt": story # 프롬프트로 사용된 스토리 저장
                    }
                )
                
                # 4. TTS 생성
                if story:
                    # Create dialogue with translations
                    dialogue = await self.book_repo.add_dialogue_with_translation(
                        page_id=page.id,
                        speaker="Narrator",
                        sequence=1,
                        translations=[
                            {
                                "language_code": "en",
                                "text": story,
                                "is_primary": True
                            }
                        ]
                    )

                    # Generate and add audio
                    try:
                        audio_bytes = await tts_provider.text_to_speech(story, voice_id=voice_id)
                    except Exception as e:
                        raise AIGenerationFailedException(stage="음성", reason=str(e))

                    try:
                        audio_file_name = f"books/{book.id}/pages/{i+1}.mp3"
                        audio_url = await self.storage_service.save(
                            audio_bytes,
                            audio_file_name,
                            content_type="audio/mpeg"
                        )
                    except Exception as e:
                        raise ImageUploadFailedException(filename=audio_file_name, reason=str(e))

                    await self.book_repo.add_dialogue_audio(
                        dialogue_id=dialogue.id,
                        language_code="en",
                        voice_id=voice_id or (settings.DEFAULT_VOICE_ID if hasattr(settings, 'DEFAULT_VOICE_ID') else "default"),
                        audio_url=audio_url
                    )

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

    async def get_book(self, book_id: uuid.UUID) -> Book:
        """책 상세 조회"""
        book = await self.book_repo.get_with_pages(book_id)
        if not book:
            raise StorybookNotFoundException(storybook_id=str(book_id))
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
                storybook_id=str(book_id),
                user_id=str(user_id)
            )

        # 스토리지 파일 삭제 로직 추가 필요 (S3 비용 절감)
        # ...

        result = await self.book_repo.delete(book_id)
        if result:
            await self.db_session.commit()
        return result
