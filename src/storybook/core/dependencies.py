"""
Shared Dependencies Module
의존성 주입 및 공통 의존성 관리 (싱글톤 패턴)
"""

from functools import lru_cache
from typing import Optional
import asyncio
import httpx
from google import genai

from ..repositories import FileBookRepository, InMemoryBookRepository
from ..storage import LocalStorageService
from ..services import (
    BookOrchestratorService,
    TtsService,
    StoryGeneratorService,
    ImageGeneratorService,
    VideoGeneratorService,
)
from .config import settings
from .logging import get_logger

logger = get_logger(__name__)


# ================================================================
# 공유 클라이언트 (HTTP, GenAI)
# ================================================================


@lru_cache()
def get_http_client() -> httpx.AsyncClient:
    """
    공유 HTTP 클라이언트 싱글톤

    애플리케이션 전체에서 하나의 연결 풀 공유
    - Connection pooling으로 성능 최적화
    - 타임아웃 및 연결 제한 설정
    """
    return httpx.AsyncClient(
        timeout=httpx.Timeout(60.0, read=300.0),
        limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
    )


@lru_cache()
def get_genai_client() -> Optional[genai.Client]:
    """
    공유 GenAI 클라이언트 싱글톤

    Google Gemini API 클라이언트 (API 키 필요)
    """
    if settings.google_api_key:
        return genai.Client(api_key=settings.google_api_key)
    return None


@lru_cache()
def get_key_pool_manager():
    """
    Kling API 키 풀 매니저 싱글톤

    다중 API 키를 관리하고 Rate Limit 발생 시 자동으로 키를 전환합니다.

    Returns:
        KlingKeyPoolManager: 키 풀 관리자

    Raises:
        ValueError: 키 설정이 잘못된 경우
    """
    from .key_pool_manager import KlingKeyPoolManager

    access_keys = settings.kling_access_keys
    secret_keys = settings.kling_secret_keys

    if not access_keys or not secret_keys:
        raise ValueError(
            "Kling API 키가 설정되지 않았습니다. "
            "KLING_ACCESS_KEY 및 KLING_SECRET_KEY 환경변수를 설정하세요."
        )

    return KlingKeyPoolManager(
        access_keys=access_keys,
        secret_keys=secret_keys,
        cooldown_seconds=settings.kling_key_cooldown_seconds,
    )


@lru_cache()
def get_kling_jwt_auth():
    """
    Kling API JWT 인증 핸들러 싱글톤

    Returns:
        KlingJWTAuth: JWT 인증 핸들러
    """
    from .jwt_auth import KlingJWTAuth

    key_pool_manager = get_key_pool_manager()
    return KlingJWTAuth(key_pool_manager=key_pool_manager)


@lru_cache()
def get_kling_client() -> httpx.AsyncClient:
    """
    공유 Kling API 클라이언트 싱글톤

    Kling Image-to-Video API 클라이언트 (키 풀 기반)
    - JWT 토큰 자동 생성 및 갱신
    - Authorization 헤더 자동 주입 (httpx Auth 인터셉터)
    - 긴 타임아웃 (비디오 생성 대기)
    - 키 풀 매니저를 통한 자동 Failover
    """
    jwt_auth = get_kling_jwt_auth()

    return httpx.AsyncClient(
        auth=jwt_auth,  # JWT 인증 자동 주입
        timeout=httpx.Timeout(60.0, read=600.0),  # 비디오 생성 대기 시간
        limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
    )


# ================================================================
# Global Semaphore (Kling API Concurrency Control)
# ================================================================

# 애플리케이션 전역 세마포어 (모듈 레벨 변수)
_kling_semaphore: Optional[asyncio.Semaphore] = None


def get_kling_semaphore() -> asyncio.Semaphore:
    """
    Kling API 동시성 제어를 위한 전역 세마포어

    Kling API는 계정당 3개의 동시 작업만 허용하므로,
    애플리케이션 전체에서 하나의 세마포어를 공유하여 제한을 지킴.

    작업 시작(submitted) ~ 완료(succeed/failed)까지 세마포어 점유 유지.
    """
    global _kling_semaphore
    if _kling_semaphore is None:
        _kling_semaphore = asyncio.Semaphore(settings.kling_max_concurrent)
    return _kling_semaphore


# ================================================================
# Storage & Repository
# ================================================================


@lru_cache()
def get_storage_service() -> LocalStorageService:
    """StorageService 싱글톤 인스턴스 반환"""
    return LocalStorageService(
        image_data_dir=settings.image_data_dir,
        video_data_dir=settings.video_data_dir,
    )


@lru_cache()
def get_file_repository() -> FileBookRepository:
    """FileBookRepository 싱글톤 인스턴스 반환"""
    return FileBookRepository(
        book_data_dir=settings.book_data_dir,
        image_data_dir=settings.image_data_dir,
    )


@lru_cache()
def get_book_repository() -> InMemoryBookRepository:
    """InMemoryBookRepository 싱글톤 인스턴스 반환"""
    file_repository = get_file_repository()
    return InMemoryBookRepository(file_repository=file_repository)


# ================================================================
# 전문 서비스 (Feature Services)
# ================================================================


@lru_cache()
def get_tts_service() -> TtsService:
    """TtsService 싱글톤 인스턴스 반환"""
    return TtsService(
        tts_api_url=settings.tts_api_url,
        http_client=get_http_client(),  # 공유 HTTP 클라이언트
    )


@lru_cache()
def get_story_generator_service() -> StoryGeneratorService:
    """StoryGeneratorService 싱글톤 인스턴스 반환"""
    return StoryGeneratorService(
        genai_client=get_genai_client(),  # 공유 GenAI 클라이언트
    )


@lru_cache()
def get_image_generator_service() -> ImageGeneratorService:
    """ImageGeneratorService 싱글톤 인스턴스 반환"""
    return ImageGeneratorService(
        storage_service=get_storage_service(),
        image_data_dir=settings.image_data_dir,
        genai_client=get_genai_client(),  # 공유 GenAI 클라이언트
    )


@lru_cache()
def get_video_generator_service() -> VideoGeneratorService:
    """VideoGeneratorService 싱글톤 인스턴스 반환"""
    return VideoGeneratorService(
        storage_service=get_storage_service(),
        image_data_dir=settings.image_data_dir,
        video_data_dir=settings.video_data_dir,
        kling_client=get_kling_client(),  # 공유 Kling API 클라이언트
        kling_semaphore=get_kling_semaphore(),  # 전역 세마포어
        key_pool_manager=get_key_pool_manager(),  # 키 풀 매니저
        kling_jwt_auth=get_kling_jwt_auth(),  # JWT 인증 핸들러
    )


# ================================================================
# 오케스트레이션 서비스 (Orchestrator)
# ================================================================


@lru_cache()
def get_book_service() -> BookOrchestratorService:
    """
    BookOrchestratorService 싱글톤 인스턴스 반환

    모든 하위 서비스를 DI로 주입받아 조립
    """
    return BookOrchestratorService(
        storage_service=get_storage_service(),
        tts_service=get_tts_service(),
        story_generator=get_story_generator_service(),
        image_generator=get_image_generator_service(),
        video_generator=get_video_generator_service(),
    )
