import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.models.audio import Audio
from backend.domain.repositories.audio_repository import AudioRepository
from backend.infrastructure.ai.factory import AIProviderFactory
from backend.infrastructure.storage.base import AbstractStorageService

class TTSService:
    """
    TTS 서비스
    텍스트를 음성으로 변환하고 저장합니다.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        storage_service: AbstractStorageService,
    ):
        self.db_session = db_session
        self.audio_repo = AudioRepository(db_session)
        self.storage_service = storage_service
        self.ai_factory = AIProviderFactory()

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
        tts_provider = self.ai_factory.get_tts_provider()
        
        # 1. TTS 생성
        audio_bytes = await tts_provider.text_to_speech(
            text=text,
            voice_id=voice_id,
            model_id=model_id
        )
        
        # 2. 스토리지 저장
        file_name = f"audios/{user_id}/{uuid.uuid4()}.mp3"
        file_url = await self.storage_service.save(
            audio_bytes,
            file_name,
            content_type="audio/mpeg"
        )
        
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
        """사용 가능한 음성 목록 조회"""
        tts_provider = self.ai_factory.get_tts_provider()
        return await tts_provider.get_available_voices()
