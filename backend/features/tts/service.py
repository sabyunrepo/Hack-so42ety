import uuid
import logging
import time
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path

from .models import Audio, Voice, VoiceVisibility, VoiceStatus
from .repository import AudioRepository, VoiceRepository
from backend.core.utils.trace import log_process
from backend.infrastructure.ai.factory import AIProviderFactory
from backend.infrastructure.storage.base import AbstractStorageService
from backend.core.cache.service import cache_result, invalidate_cache
from backend.core.events.bus import EventBus
from backend.core.events.types import EventType
from backend.core.tasks.voice_queue import VoiceSyncQueue
from .exceptions import (
    TTSGenerationFailedException,
    TTSUploadFailedException,
    TTSTextTooLongException,
    TTSAPIKeyNotConfiguredException,
    TTSAPIAuthenticationFailedException,
    WordTooLongException,
    WordInvalidException,
    BookVoiceNotConfiguredException,
    VoiceCloneLimitExceededException,
)
from backend.features.storybook.exceptions import StorybookNotFoundException

logger = logging.getLogger(__name__)

class TTSService:
    """
    TTS 서비스
    텍스트를 음성으로 변환하고 저장합니다.

    DI Pattern: 모든 의존성을 생성자를 통해 주입받습니다.
    """

    def __init__(
        self,
        audio_repo: AudioRepository,
        voice_repo: VoiceRepository,
        storage_service: AbstractStorageService,
        ai_factory: AIProviderFactory,
        db_session: AsyncSession,
        cache_service,  # CacheService (순환 참조 방지)
        event_bus: EventBus,  # EventBus
    ):
        self.audio_repo = audio_repo
        self.voice_repo = voice_repo
        self.storage_service = storage_service
        self.ai_factory = ai_factory
        self.db_session = db_session
        self.cache_service = cache_service  # 데코레이터에서 사용
        self.event_bus = event_bus
        self.voice_queue = VoiceSyncQueue()  # Redis 작업 큐

    @log_process(step="Generate Speech", desc="TTS 음성 생성 및 업로드")
    async def generate_speech(
        self,
        user_id: uuid.UUID,
        text: str,
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> Audio:
        """
        음성 생성 및 저장
        """
        # 텍스트 길이 검증
        max_length = 5000
        if len(text) > max_length:
            raise TTSTextTooLongException(text_length=len(text), max_length=max_length)

        # TTS Provider 가져오기
        try:
            tts_provider = self.ai_factory.get_tts_provider()
        except TTSAPIKeyNotConfiguredException:
            # API 키가 없을 때는 그대로 전파
            raise
        except Exception as e:
            # Provider 생성 실패 시
            raise TTSGenerationFailedException(reason=f"TTS Provider 초기화 실패: {str(e)}")

        # 1. TTS 생성
        try:
            audio_bytes = await tts_provider.text_to_speech(
                text=text,
                voice_id=voice_id,
                model_id=model_id
            )
        except (TTSAPIKeyNotConfiguredException, TTSAPIAuthenticationFailedException):
            # API 키 관련 예외는 그대로 전파
            raise
        except Exception as e:
            raise TTSGenerationFailedException(reason=str(e))

        # 2. 스토리지 저장 (경로 변경: users/{user_id}/audios/standalone/{uuid}.mp3)
        try:
            file_name = f"users/{user_id}/audios/standalone/{uuid.uuid4()}.mp3"
            storage_url = await self.storage_service.save(
                audio_bytes,
                file_name,
                content_type="audio/mpeg"
            )
            # DB에 저장할 URL: API 경로 변환 없이 순수 경로 저장 (API에서 동적 생성)
            file_url = file_name
        except Exception as e:
            raise TTSUploadFailedException(filename=file_name, reason=str(e))

        # 3. 메타데이터 저장
        audio = await self.audio_repo.create(
            user_id=user_id,
            file_url=file_url,
            file_path=file_name,
            text_content=text,
            voice_id=voice_id or "default",
            provider="elevenlabs", # TODO: Provider에서 가져오거나 설정에서 확인
            file_size=len(audio_bytes),
            mime_type="audio/mpeg"
        )

        return audio

    @invalidate_cache("tts:voices:{user_id}")
    @log_process(step="Create Voice Clone", desc="Voice Cloning 요청")
    async def create_voice_clone(
        self,
        user_id: uuid.UUID,
        name: str,
        audio_file: bytes,
        visibility: VoiceVisibility = VoiceVisibility.PRIVATE,
        description: Optional[str] = None,
    ) -> Voice:
        """
        Voice Clone 생성
        
        ElevenLabs API를 통해 Voice Clone을 생성하고,
        DB에 모든 정보를 저장한 후 Redis 큐에 작업 추가
        
        Args:
            user_id: 사용자 UUID
            name: Voice 이름
            audio_file: 오디오 파일 (bytes)
            visibility: 공개 범위 (기본값: PRIVATE)
            description: Voice 설명 (선택)
        
        Returns:
            Voice: 생성된 Voice 객체
        
        Raises:
            TTSAPIKeyNotConfiguredException: API 키가 설정되지 않은 경우
            TTSAPIAuthenticationFailedException: API 인증 실패 시
            TTSGenerationFailedException: 기타 TTS 생성 실패 시
        """
        # TTS Provider 가져오기
        try:
            tts_provider = self.ai_factory.get_tts_provider()
        except TTSAPIKeyNotConfiguredException:
            raise
        except Exception as e:
            raise TTSGenerationFailedException(
                reason=f"TTS Provider 초기화 실패: {str(e)}"
            )

        # 0. Voice Clone 생성 한도 확인
        from backend.core.config import settings
        
        current_count = await self.voice_repo.count_user_voices(user_id)
        if current_count >= settings.max_voice_clones_per_user:
            raise VoiceCloneLimitExceededException(
                current_count=current_count,
                max_limit=settings.max_voice_clones_per_user
            )
        
        # ElevenLabs API 호출 - Voice Clone 생성
        try:
            elevenlabs_voice = await tts_provider.clone_voice(
                name=name,
                audio_file=audio_file,
                description=description,
            )
        except (TTSAPIKeyNotConfiguredException, TTSAPIAuthenticationFailedException):
            raise
        except Exception as e:
            raise TTSGenerationFailedException(
                reason=f"Voice Clone 생성 실패: {str(e)}"
            )
        
        # DB에 모든 정보 저장 (모든 필드 기입)
        voice = await self.voice_repo.create(
            user_id=user_id,
            elevenlabs_voice_id=elevenlabs_voice["voice_id"],
            name=elevenlabs_voice.get("name", name),
            language=elevenlabs_voice.get("language", "en"),
            gender=elevenlabs_voice.get("gender", "unknown"),
            category=elevenlabs_voice.get("category", "cloned"),
            visibility=visibility,
            status=VoiceStatus.PROCESSING,  # 초기에는 processing
            preview_url=elevenlabs_voice.get("preview_url"),  # 초기에는 None일 수 있음
            meta_data={
                "description": elevenlabs_voice.get("description", description),
                "labels": elevenlabs_voice.get("labels", {}),
            },
        )
        
        # Redis 큐에 작업 추가
        await self.voice_queue.enqueue(voice.id)
        logger.info(f"Voice {voice.id} created and added to sync queue")
        
        return voice
    
    @cache_result(key="tts:voices:{user_id}", ttl=3600)
    async def get_voices(self, user_id: uuid.UUID) -> List[Dict[str, Any]]:
        """
        사용자별 Voice 목록 조회 (캐싱 적용)
        
        Args:
            user_id: 사용자 UUID
        
        Returns:
            List[Dict[str, Any]]: Voice 목록
                - 사용자 개인 Voice (private)
                - 공개 Voice (public)
                - 기본 Voice (default)
        """
        # DB에서 사용자별 Voice 조회
        voices = await self.voice_repo.get_user_voices(
            user_id=user_id,
            include_public=True,
            include_default=True,
        )
        
        # 기본 Voice (ElevenLabs premade) 추가
        tts_provider = self.ai_factory.get_tts_provider()
        try:
            premade_voices = await tts_provider.get_available_voices()
            premade_voices = [
                v for v in premade_voices 
                if v.get("category") == "premade"
            ]
        except Exception as e:
            logger.warning(f"Failed to fetch premade voices: {e}")
            premade_voices = []
        
        # DB Voice + Premade Voice 합치기
        result = []
        
        # DB Voice 변환
        for voice in voices:
            result.append({
                "voice_id": voice.elevenlabs_voice_id,
                "name": voice.name,
                "language": voice.language,
                "gender": voice.gender,
                "preview_url": voice.preview_url,
                "category": voice.category,
                "visibility": voice.visibility.value,
                "status": voice.status.value,
                "is_custom": True,
            })
        
        # Premade Voice 추가
        for voice in premade_voices:
            result.append({
                "voice_id": voice["voice_id"],
                "name": voice["name"],
                "language": voice.get("language", "en"),
                "gender": voice.get("gender", "unknown"),
                "preview_url": voice.get("preview_url"),
                "category": "premade",
                "visibility": "default",
                "status": "completed",
                "is_custom": False,
            })
        
        return result
    
    async def generate_word_tts(
        self,
        book_id: uuid.UUID,
        word: str,
    ) -> Dict[str, Any]:
        """
        Book별 단어 TTS 생성 (캐싱 지원)
        
        Args:
            book_id: Book UUID
            word: 변환할 단어
        
        Returns:
            Dict[str, Any]: 생성 결과
                - success: bool
                - word: str
                - file_path: str (파일 시스템 경로)
                - audio_url: str (API 경로)
                - cached: bool
                - duration_ms: Optional[int]
                - voice_id: str
        
        Raises:
            StorybookNotFoundException: Book이 존재하지 않음
            BookVoiceNotConfiguredException: Book에 voice_id가 설정되지 않음
            WordTooLongException: 단어가 너무 김 (50자 초과)
            WordInvalidException: 유효하지 않은 단어 (특수문자 등)
            TTSGenerationFailedException: TTS 생성 실패
        """
        # 1. 단어 유효성 검증
        self._validate_word(word)
        
        # 2. Book 조회 및 voice_id 가져오기
        from backend.features.storybook.repository import BookRepository
        book_repo = BookRepository(self.db_session)
        book = await book_repo.get(book_id)
        
        if not book:
            raise StorybookNotFoundException(storybook_id=str(book_id))
        
        if not book.voice_id:
            raise BookVoiceNotConfiguredException(book_id=str(book_id))
        
        voice_id = book.voice_id
        
        # 3. 파일 경로 설정 (Book의 base_path 사용)
        file_path = Path(f"{book.base_path}/words/{word}.mp3")
        
        # 4. 캐시 확인 (파일 존재 여부)
        try:
            # 스토리지에서 파일 존재 여부 확인
            file_exists = await self.storage_service.exists(str(file_path))
        except Exception:
            file_exists = False
        
        # 캐시된 파일이 있으면 바로 반환
        if file_exists:
            # storage_service.get_url()을 사용하여 URL 생성
            # Local: /api/v1/files/... 상대 경로
            # S3: Pre-signed URL
            audio_url = self.storage_service.get_url(str(file_path))
            
            logger.info(f"Word TTS 캐시 사용: book={book_id}, word={word}")
            return {
                "success": True,
                "word": word,
                "file_path": f"/{file_path}",
                "audio_url": audio_url,
                "cached": True,
                "duration_ms": None,
                "voice_id": voice_id,
            }
        
        # 5. TTS 생성
        start_time = time.time()
        
        try:
            tts_provider = self.ai_factory.get_tts_provider()
        except TTSAPIKeyNotConfiguredException:
            raise
        except Exception as e:
            raise TTSGenerationFailedException(
                reason=f"TTS Provider 초기화 실패: {str(e)}"
            )
        
        try:
            audio_bytes = await tts_provider.text_to_speech(
                text=word,
                voice_id=voice_id,
                model_id="eleven_v3",
            )
        except (TTSAPIKeyNotConfiguredException, TTSAPIAuthenticationFailedException):
            raise
        except Exception as e:
            raise TTSGenerationFailedException(
                reason=f"Word TTS 생성 실패: {str(e)}"
            )
        
        # 6. 파일 저장
        try:
            audio_path = await self.storage_service.save(
                audio_bytes,
                str(file_path),
                content_type="audio/mpeg"
            )
            # ✅ 경로만 저장됨
            # Local: "shared/books/{id}/words/word.mp3"
            # S3: "shared/books/{id}/words/word.mp3"
            
            # ✅ API 응답용 URL 생성
            audio_url = self.storage_service.get_url(audio_path)
            # Local: "/api/v1/files/shared/books/{id}/words/word.mp3"
            # S3: "https://bucket.s3.amazonaws.com/.../word.mp3?Signature=..."
        except Exception as e:
            raise TTSUploadFailedException(
                filename=str(file_path),
                reason=str(e)
            )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        logger.info(
            f"Word TTS 생성 완료: book={book_id}, word={word}, "
            f"voice_id={voice_id}, duration={duration_ms}ms"
        )
        
        return {
            "success": True,
            "word": word,
            "file_path": f"/{file_path}",
            "audio_url": audio_url,
            "cached": False,
            "duration_ms": duration_ms,
            "voice_id": voice_id,
        }
    
    def _validate_word(self, word: str) -> None:
        """
        단어 유효성 검증
        
        Args:
            word: 검증할 단어
        
        Raises:
            WordTooLongException: 단어가 너무 김
            WordInvalidException: 유효하지 않은 단어
        """
        # 단어 길이 검증 (최대 50자)
        if len(word) > 50:
            raise WordTooLongException(word_length=len(word), max_length=50)
        
        # 빈 문자열 검증
        if not word.strip():
            raise WordInvalidException(word=word, reason="단어는 비어있을 수 없습니다")
        
        # 특수문자 검증 (경로 조작 문자 차단)
        if any(char in word for char in [".", "/", "\\", ".."]):
            raise WordInvalidException(
                word=word,
                reason="단어에 경로 조작 문자(., /, \\)를 포함할 수 없습니다"
            )
