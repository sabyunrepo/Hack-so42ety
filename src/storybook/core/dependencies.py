"""
Shared Dependencies Module
의존성 주입 및 공통 의존성 관리 (싱글톤 패턴)
"""

from functools import lru_cache
from ..repositories import FileBookRepository, InMemoryBookRepository
from ..storage import LocalStorageService
from ..services import BookOrchestratorService
from .config import settings
from .logging import get_logger

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
def get_book_service() -> BookOrchestratorService:
    """
    BookOrchestratorService 싱글톤 인스턴스 반환

    모든 하위 서비스를 DI로 주입받아 조립
    """
    return BookOrchestratorService(
        storage_service=get_storage_service(),
    )
