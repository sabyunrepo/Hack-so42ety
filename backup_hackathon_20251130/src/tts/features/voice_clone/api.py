"""
Voice Clone API
클론 보이스 생성 엔드포인트
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks, Response
from features.voice_clone.service import VoiceCloneService
from shared.dependencies import get_tts_generator
from src.tts_generator import TtsGenerator
from core.registry import RouterRegistry
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/tts/clone", tags=["Voice Clone"])

# Router 자동 등록
RouterRegistry.register(
    router,
    priority=40,  # 일반 기능
    tags=["tts", "clone", "voice"],
    name="voice_clone",
)


def get_voice_clone_service(
    tts_generator: TtsGenerator = Depends(get_tts_generator),
) -> VoiceCloneService:
    """VoiceCloneService 의존성 주입"""
    return VoiceCloneService(tts_generator)


async def _process_clone_voice(
    name: str, temp_file_path, description: str, service: VoiceCloneService
):
    """백그라운드에서 클론 보이스 생성 처리"""
    try:
        result = await service.create_clone_voice_from_path(
            name=name.strip(),
            temp_file_path=temp_file_path,
            description=description.strip(),
        )
        logger.info(f"클론 보이스 생성 완료: {result['voice_id']}")
    except Exception as e:
        logger.error(f"백그라운드 클론 보이스 생성 실패: {str(e)}")


@router.post("/create", status_code=201)
async def create_clone_voice(
    background_tasks: BackgroundTasks,
    name: str = Form(..., description="클론 보이스 이름"),
    file: UploadFile = File(..., description="오디오 파일 (mp3, wav, m4a, flac, ogg)"),
    description: str = Form("", description="보이스 설명 (선택)"),
    service: VoiceCloneService = Depends(get_voice_clone_service),
):
    """
    클론 보이스 생성 엔드포인트 (동기 사전 검증 + 비동기 처리)

    Args:
        background_tasks: FastAPI 백그라운드 태스크
        name: 클론 보이스 이름 (필수)
        file: 오디오 파일 (필수, 최대 30MB, 2분30초~3분)
        description: 보이스 설명 (선택)
        service: VoiceCloneService (DI)

    Returns:
        201 Accepted (검증 통과 후 즉시 반환)

    Raises:
        HTTPException:
            - 400: 파일 누락, 이름 누락, 잘못된 파일 형식, 중복 이름, 오디오 길이 부족
            - 500: 서버 내부 오류
    """
    try:
        # 이름 검증
        if not name or not name.strip():
            raise HTTPException(
                status_code=400, detail="보이스 이름을 입력하세요."
            )

        # 파일 검증
        if not file:
            raise HTTPException(
                status_code=400, detail="오디오 파일을 업로드하세요."
            )

        logger.info(f"클론 보이스 생성 요청 접수: name={name}, file={file.filename}")

        # 🆕 동기 사전 검증 (파일 저장 + 오디오 길이 검증)
        temp_file_path = await service.validate_audio_before_background(name, file)
        logger.info(f"사전 검증 완료. 백그라운드 처리 시작")

        # 백그라운드 태스크 추가 (파일 경로로 전달)
        background_tasks.add_task(
            _process_clone_voice, name, temp_file_path, description, service
        )

        # 즉시 201 Accepted 반환
        return Response(status_code=201)

    except ValueError as e:
        logger.warning(f"클론 보이스 생성 검증 실패: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"클론 보이스 생성 요청 처리 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"클론 보이스 생성 요청 처리 중 오류가 발생했습니다: {str(e)}",
        )
