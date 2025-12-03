from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from backend.core.database.session import get_db
from backend.core.auth.dependencies import get_current_user_object as get_current_user
from backend.features.auth.models import User
from backend.infrastructure.storage.local import LocalStorageService
from backend.infrastructure.storage.s3 import S3StorageService
from backend.core.config import settings
from backend.features.tts.service import TTSService
from backend.features.tts.repository import AudioRepository
from backend.features.tts.schemas import GenerateSpeechRequest, AudioResponse, VoiceResponse
from backend.infrastructure.ai.factory import AIProviderFactory

router = APIRouter(prefix="/tts", tags=["tts"])

def get_storage_service():
    """스토리지 서비스 의존성"""
    if settings.storage_provider == "s3":
        return S3StorageService()
    return LocalStorageService()

def get_ai_factory():
    """AI Factory 의존성"""
    return AIProviderFactory()

def get_tts_service(
    db: AsyncSession = Depends(get_db),
    storage_service = Depends(get_storage_service),
    ai_factory = Depends(get_ai_factory),
) -> TTSService:
    """TTSService 의존성 주입"""
    audio_repo = AudioRepository(db)
    return TTSService(
        audio_repo=audio_repo,
        storage_service=storage_service,
        ai_factory=ai_factory,
        db_session=db,
    )

@router.post("/generate", response_model=AudioResponse, status_code=status.HTTP_201_CREATED)
async def generate_speech(
    request: GenerateSpeechRequest,
    current_user: User = Depends(get_current_user),
    service: TTSService = Depends(get_tts_service),
):
    """TTS 음성 생성"""
    audio = await service.generate_speech(
        user_id=current_user.id,
        text=request.text,
        voice_id=request.voice_id,
        model_id=request.model_id
    )
    return audio

@router.get("/voices", response_model=List[VoiceResponse])
async def list_voices(
    service: TTSService = Depends(get_tts_service),
):
    """사용 가능한 음성 목록 조회"""
    voices = await service.get_voices()
    return voices
