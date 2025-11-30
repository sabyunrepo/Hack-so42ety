from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from backend.core.database.session import get_db
from backend.core.auth.dependencies import get_current_user_object as get_current_user
from backend.domain.models.user import User
from backend.infrastructure.storage.local import LocalStorageService
from backend.infrastructure.storage.s3 import S3StorageService
from backend.core.config import settings
from backend.features.tts.service import TTSService
from backend.features.tts.schemas import GenerateSpeechRequest, AudioResponse, VoiceResponse

router = APIRouter(prefix="/tts", tags=["tts"])

def get_storage_service():
    if settings.storage_provider == "s3":
        return S3StorageService()
    return LocalStorageService()

@router.post("/generate", response_model=AudioResponse, status_code=status.HTTP_201_CREATED)
async def generate_speech(
    request: GenerateSpeechRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """TTS 음성 생성"""
    storage_service = get_storage_service()
    service = TTSService(db, storage_service)
    
    try:
        audio = await service.generate_speech(
            user_id=current_user.id,
            text=request.text,
            voice_id=request.voice_id,
            model_id=request.model_id
        )
        return audio
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate speech: {str(e)}"
        )

@router.get("/voices", response_model=List[VoiceResponse])
async def list_voices(
    db: AsyncSession = Depends(get_db),
):
    """사용 가능한 음성 목록 조회"""
    # Storage service is not needed for listing voices, but service init requires it.
    # We can pass a dummy or just use LocalStorageService as it's lightweight.
    storage_service = LocalStorageService() 
    service = TTSService(db, storage_service)
    
    voices = await service.get_voices()
    return voices
