import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Audio
from .repository import AudioRepository
from backend.infrastructure.ai.factory import AIProviderFactory
from backend.infrastructure.storage.base import AbstractStorageService
from .exceptions import (
    TTSGenerationFailedException,
    TTSUploadFailedException,
    TTSTextTooLongException,
    TTSAPIKeyNotConfiguredException,
    TTSAPIAuthenticationFailedException,
)

class TTSService:
    """
    TTS 서비스
    텍스트를 음성으로 변환하고 저장합니다.

    DI Pattern: 모든 의존성을 생성자를 통해 주입받습니다.
    """

    def __init__(
        self,
        audio_repo: AudioRepository,
        storage_service: AbstractStorageService,
        ai_factory: AIProviderFactory,
        db_session: AsyncSession,
    ):
        self.audio_repo = audio_repo
        self.storage_service = storage_service
        self.ai_factory = ai_factory
        self.db_session = db_session

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

        # 2. 스토리지 저장
        try:
            file_name = f"audios/{user_id}/{uuid.uuid4()}.mp3"
            file_url = await self.storage_service.save(
                audio_bytes,
                file_name,
                content_type="audio/mpeg"
            )
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

    async def get_voices(self) -> List[Dict[str, Any]]:
        """
        사용 가능한 음성 목록 조회
        
        Raises:
            TTSAPIKeyNotConfiguredException: API 키가 설정되지 않은 경우
            TTSAPIAuthenticationFailedException: API 인증 실패 시
            TTSGenerationFailedException: 기타 TTS 생성 실패 시
        """
        try:
            tts_provider = self.ai_factory.get_tts_provider()
        except TTSAPIKeyNotConfiguredException:
            # API 키가 없을 때는 그대로 전파
            raise
        except Exception as e:
            # Provider 생성 실패 시
            raise TTSGenerationFailedException(reason=f"TTS Provider 초기화 실패: {str(e)}")
        
        try:
            return await tts_provider.get_available_voices()
        except (TTSAPIKeyNotConfiguredException, TTSAPIAuthenticationFailedException):
            # API 키 관련 예외는 그대로 전파
            raise
        except Exception as e:
            # 기타 예외는 TTSGenerationFailedException으로 변환
            raise TTSGenerationFailedException(reason=f"음성 목록 조회 실패: {str(e)}")
