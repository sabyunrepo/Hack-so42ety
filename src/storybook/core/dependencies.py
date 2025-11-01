"""
Shared Dependencies Module
의존성 주입 및 공통 의존성 관리 (싱글톤 패턴)
"""

from functools import lru_cache
from ..repositories import FileBookRepository, InMemoryBookRepository
from ..storage import LocalStorageService
from ..services import BookOrchestratorService, StoryGeneratorService, TtsService
from .config import settings
from .logging import get_logger
import httpx
from typing import Optional
from google import genai

logger = get_logger(__name__)


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
def get_book_service() -> BookOrchestratorService:
    """
    BookOrchestratorService 싱글톤 인스턴스 반환

    모든 하위 서비스를 DI로 주입받아 조립
    """
    return BookOrchestratorService(
        storage_service=get_storage_service(),
        tts_service=get_tts_service(),
        story_generator=get_story_generator_service(),
    )
