"""
Media URL Refresh API
미디어 URL 갱신 API

프론트엔드에서 URL 만료 시 새로운 Signed URL을 받기 위한 경량 API
"""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from backend.core.database.session import get_db_readonly
from backend.core.auth.dependencies import get_current_user_object
from backend.core.dependencies import get_storage_service
from backend.core.exceptions import NotFoundException, ErrorCode
from backend.features.auth.models import User
from backend.infrastructure.storage.base import AbstractStorageService
from backend.api.v1.endpoints.files_helper import get_content_type_from_path

logger = logging.getLogger(__name__)

router = APIRouter()


class MediaUrlsResponse(BaseModel):
    """미디어 URL 응답"""
    page_id: str
    urls: dict
    expires_at: datetime


@router.post(
    "/books/{book_id}/pages/{page_id}/refresh-urls",
    response_model=MediaUrlsResponse,
    summary="페이지 미디어 URL 갱신",
    description="만료된 미디어 URL을 새로운 Signed URL로 갱신합니다 (비공개 콘텐츠 전용).",
    responses={
        200: {"description": "URL 갱신 성공"},
        403: {"description": "접근 권한 없음"},
        404: {"description": "책 또는 페이지를 찾을 수 없음"},
    },
)
async def refresh_page_media_urls(
    book_id: str,
    page_id: str,
    current_user: User = Depends(get_current_user_object),
    db: AsyncSession = Depends(get_db_readonly),
    storage: AbstractStorageService = Depends(get_storage_service),
):
    """
    페이지의 모든 미디어 URL을 새로운 토큰으로 갱신

    - 비디오, 이미지, 오디오 URL에 새로운 만료시간과 토큰 부여
    - 가볍고 빠른 응답 (전체 책 정보 불필요)
    - 공개 콘텐츠는 갱신 불필요 (토큰 없음)

    Args:
        book_id: 책 ID
        page_id: 페이지 ID
        current_user: 현재 사용자
        db: 데이터베이스 세션
        storage: 스토리지 서비스

    Returns:
        MediaUrlsResponse: 갱신된 URL 정보
    """
    from backend.features.storybook.repository import BookRepository, PageRepository

    # 1. 책 존재 및 권한 확인
    book_repo = BookRepository(db)
    book = await book_repo.get(book_id)

    if not book:
        raise NotFoundException(
            error_code=ErrorCode.BIZ_RESOURCE_NOT_FOUND,
            message=f"Book not found: {book_id}"
        )

    # 2. 비공개 책이면 소유자 확인
    if not book.is_shared and book.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied: You are not the owner of this book")

    # 3. 공개 책이면 URL 갱신 불필요 (토큰 없는 URL이므로)
    if book.is_shared:
        raise HTTPException(
            status_code=400,
            detail="Public content does not require URL refresh (no token expiration)"
        )

    # 4. 페이지 찾기
    page_repo = PageRepository(db)
    page = await page_repo.get(page_id)

    if not page or str(page.book_id) != book_id:
        raise NotFoundException(
            error_code=ErrorCode.BIZ_RESOURCE_NOT_FOUND,
            message=f"Page not found: {page_id}"
        )

    # 5. 새로운 URL 생성 (새 토큰 포함)
    is_shared = book.is_shared

    refreshed_urls = {}

    # 비디오 URL
    if page.video_path:
        refreshed_urls["video_url"] = storage.get_url(
            page.video_path,
            is_shared=is_shared,
            content_type='video'
        )

    # 이미지 URL
    if page.image_path:
        refreshed_urls["image_url"] = storage.get_url(
            page.image_path,
            is_shared=is_shared,
            content_type='image'
        )

    # 오디오 URL들
    audios = []
    for dialogue in page.dialogues:
        for audio in dialogue.audios:
            if audio.audio_path:
                audios.append({
                    "dialogue_id": str(dialogue.id),
                    "language_code": audio.language_code,
                    "audio_url": storage.get_url(
                        audio.audio_path,
                        is_shared=is_shared,
                        content_type='audio'
                    )
                })

    if audios:
        refreshed_urls["audios"] = audios

    # 6. 만료 시간 (비디오 기준 6시간)
    expires_at = datetime.utcnow() + timedelta(hours=6)

    logger.info(
        f"Refreshed media URLs for book={book_id}, page={page_id}, "
        f"user={current_user.id}, urls_count={len(refreshed_urls)}"
    )

    return MediaUrlsResponse(
        page_id=page_id,
        urls=refreshed_urls,
        expires_at=expires_at
    )
