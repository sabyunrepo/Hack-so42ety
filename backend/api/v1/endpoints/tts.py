from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from backend.core.database.session import get_db
from backend.core.auth.dependencies import get_current_user_object as get_current_user
from backend.core.dependencies import (
    get_storage_service,
    get_ai_factory,
    get_cache_service,
    get_event_bus,
)
from backend.features.auth.models import User
from backend.features.tts.service import TTSService
from backend.features.tts.repository import AudioRepository
from backend.features.tts.schemas import GenerateSpeechRequest, AudioResponse, VoiceResponse

router = APIRouter()

def get_tts_service(
    db: AsyncSession = Depends(get_db),
    storage_service = Depends(get_storage_service),
    ai_factory = Depends(get_ai_factory),
    cache_service = Depends(get_cache_service),
    event_bus = Depends(get_event_bus),
) -> TTSService:
    """TTSService 의존성 주입"""
    audio_repo = AudioRepository(db)
    return TTSService(
        audio_repo=audio_repo,
        storage_service=storage_service,
        ai_factory=ai_factory,
        db_session=db,
        cache_service=cache_service,
        event_bus=event_bus,
    )

@router.post(
    "/generate",
    response_model=AudioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="TTS 음성 생성",
    responses={
        201: {"description": "음성 생성 성공"},
        401: {"description": "인증 실패"},
        500: {"description": "서버 오류 (ElevenLabs API 실패)"},
    },
)
async def generate_speech(
    request: GenerateSpeechRequest,
    current_user: User = Depends(get_current_user),
    service: TTSService = Depends(get_tts_service),
):
    """
    텍스트를 음성으로 변환 (ElevenLabs API)

    지정된 음성과 텍스트로 자연스러운 음성 파일을 생성합니다.

    Args:
        request (GenerateSpeechRequest): 음성 생성 요청
            - text: 변환할 텍스트 (최대 5000자)
            - voice_id: 음성 ID (선택, 기본값: Rachel)
            - model_id: 모델 ID (선택, 기본값: eleven_multilingual_v2)
        current_user: 인증된 사용자 정보
        service: TTSService (의존성 주입)

    Returns:
        AudioResponse: 생성된 음성 파일 정보
            - id: 오디오 고유 ID (UUID)
            - audio_url: 다운로드 가능한 URL
            - duration: 재생 시간 (초)
            - text: 변환된 텍스트
            - voice_id: 사용된 음성 ID
            - created_at: 생성 시간

    Raises:
        HTTPException 401: 인증 실패
        HTTPException 500: ElevenLabs API 호출 실패

    Note:
        - 최대 텍스트 길이: 5000자
        - 지원 언어: 다국어 (한국어, 영어, 일본어, 중국어 등)
        - 사용 가능한 음성 목록은 GET /voices에서 확인

    Example:
        ```
        POST /api/v1/tts/generate
        {
          "text": "안녕하세요. 오늘 날씨가 참 좋네요.",
          "voice_id": "21m00Tcm4TlvDq8ikWAM",
          "model_id": "eleven_multilingual_v2"
        }
        ```
    """
    audio = await service.generate_speech(
        user_id=current_user.id,
        text=request.text,
        voice_id=request.voice_id,
        model_id=request.model_id
    )
    return audio

@router.get(
    "/voices",
    response_model=List[VoiceResponse],
    summary="사용 가능한 음성 목록 조회",
    responses={
        200: {"description": "조회 성공"},
    },
)
async def list_voices(
    service: TTSService = Depends(get_tts_service),
):
    """
    사용 가능한 음성 목록 조회

    ElevenLabs에서 사용 가능한 모든 음성 목록을 조회합니다.

    Args:
        service: TTSService (의존성 주입)

    Returns:
        List[VoiceResponse]: 음성 목록
            - voice_id: 음성 고유 ID
            - name: 음성 이름
            - preview_url: 미리듣기 URL (선택)
            - language: 지원 언어
            - gender: 성별 (male/female/neutral)

    Note:
        - 인증 불필요 (공개 API)
        - TTS 생성 시 voice_id를 사용하여 음성 지정
        - 각 음성마다 특징과 음색이 다름

    Example:
        ```
        GET /api/v1/tts/voices

        Response:
        [
          {
            "voice_id": "21m00Tcm4TlvDq8ikWAM",
            "name": "Rachel",
            "language": "en-US",
            "gender": "female"
          },
          ...
        ]
        ```
    """
    voices = await service.get_voices()
    return voices
