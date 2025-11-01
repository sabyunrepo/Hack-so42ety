"""
Word TTS API
단어 TTS 생성 엔드포인트
"""

from fastapi import APIRouter, HTTPException, Depends
from features.word_tts.schemas import WordTTSResponse
from features.word_tts.service import WordTTSService
from shared.dependencies import get_tts_generator
from src.tts_generator import TtsGenerator
from core.registry import RouterRegistry

router = APIRouter(prefix="/tts", tags=["Word TTS"])

# Router 자동 등록
RouterRegistry.register(
    router,
    priority=40,  # 일반 기능
    tags=["tts", "word", "cache"],
    name="word_tts",
)


def get_word_tts_service(
    tts_generator: TtsGenerator = Depends(get_tts_generator),
) -> WordTTSService:
    """WordTTSService 의존성 주입"""
    return WordTTSService(tts_generator)


@router.get("/word/generate/{book_id}/{word}", response_model=WordTTSResponse)
async def generate_word_tts(
    book_id: str,
    word: str,
    service: WordTTSService = Depends(get_word_tts_service),
):
    """
    Book별 단어 TTS 생성 엔드포인트 (캐싱 지원)

    Book 메타데이터에서 voice_id를 읽어 해당 음성으로 TTS를 생성합니다.
    파일이 이미 존재하면 기존 파일을 재사용하고,
    없으면 ElevenLabs API로 새로 생성합니다.

    저장 경로: /data/sound/word/{book_id}/{word}.mp3

    Args:
        book_id: Book ID (메타데이터 참조)
        word: 변환할 단어 (최대 50자)
        service: 단어 TTS 서비스 (DI)

    Returns:
        WordTTSResponse: 생성된 파일 경로, voice_id 및 통계

    Raises:
        HTTPException:
            - 400: 유효하지 않은 단어 (길이 초과, 특수문자 포함)
            - 404: Book을 찾을 수 없음
            - 500: TTS 생성 실패 또는 voice_id 누락
    """
    try:
        result = await service.generate_word(book_id, word)
        return WordTTSResponse(success=True, **result)

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"TTS 생성 중 오류가 발생했습니다: {str(e)}"
        )
