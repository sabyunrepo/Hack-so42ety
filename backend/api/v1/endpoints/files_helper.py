"""
File Access Helper Functions
파일 접근 헬퍼 함수
"""
import uuid
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.infrastructure.storage.base import AbstractStorageService

logger = logging.getLogger(__name__)


def extract_book_id_from_path(path: str) -> Optional[uuid.UUID]:
    """
    파일 경로에서 book_id 추출

    Args:
        path: 파일 경로 (예: shared/books/abc-123/videos/page_1.mp4)

    Returns:
        Optional[uuid.UUID]: book_id, 없으면 None
    """
    try:
        # shared/books/{book_id}/... 또는 users/{user_id}/books/{book_id}/... 패턴
        if "/books/" in path:
            parts = path.split("/books/")
            if len(parts) >= 2:
                book_id_part = parts[1].split("/")[0]
                return uuid.UUID(book_id_part)
    except (ValueError, IndexError) as e:
        logger.warning(f"Failed to extract book_id from path: {path}, error: {e}")

    return None


def get_content_type_from_path(path: str) -> str:
    """
    파일 경로에서 콘텐츠 타입 추출

    Args:
        path: 파일 경로

    Returns:
        str: 콘텐츠 타입 ('video', 'audio', 'image', 'metadata', 'default')
    """
    if "/videos/" in path or path.endswith(('.mp4', '.webm', '.mov')):
        return 'video'
    elif "/audios/" in path or "/words/" in path or path.endswith(('.mp3', '.wav', '.ogg')):
        return 'audio'
    elif "/images/" in path or path.endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')):
        return 'image'
    elif path.endswith('.json'):
        return 'metadata'
    else:
        return 'default'


async def get_cdn_url_with_permission(
    file_path: str,
    db: AsyncSession,
    storage: AbstractStorageService
) -> str:
    """
    파일의 공개/비공개 상태를 확인하고 올바른 CDN URL 생성

    Args:
        file_path: 파일 경로
        db: 데이터베이스 세션
        storage: 스토리지 서비스

    Returns:
        str: CDN URL (공개/비공개에 따라 토큰 포함 여부 다름)
    """
    # 1. 경로에서 book_id 추출
    book_id = extract_book_id_from_path(file_path)

    # book_id 없으면 공개로 간주
    if not book_id:
        content_type = get_content_type_from_path(file_path)
        return storage.get_url(
            file_path,
            is_shared=True,
            content_type=content_type
        )

    # 2. DB에서 book 조회
    from backend.features.storybook.repository import BookRepository
    book_repo = BookRepository(db)
    book = await book_repo.get(book_id)

    # book 없으면 공개로 간주 (Fail-safe)
    if not book:
        logger.warning(f"Book not found: {book_id}, treating as public")
        content_type = get_content_type_from_path(file_path)
        return storage.get_url(
            file_path,
            is_shared=True,
            content_type=content_type
        )

    # 3. is_shared 상태에 따라 URL 생성
    content_type = get_content_type_from_path(file_path)
    return storage.get_url(
        file_path,
        is_shared=book.is_shared,
        content_type=content_type
    )
