"""
Book Orchestrator Service Module
동화책 생성 전체 프로세스 조율
"""

import asyncio
import re
from typing import List, Optional

from ..core.logging import get_logger
from ..domain.models import Book
from ..storage import AbstractStorageService

logger = get_logger(__name__)


class BookOrchestratorService:

    def __init__(
        self,
        storage_service: AbstractStorageService,
    ):
        self.storage = storage_service

        logger.info("BookOrchestratorService initialized (DI mode)")

    async def create_book_with_tts(
        self,
        stories: List[str],
        images: List[dict],
        book_id: Optional[str] = None,
    ) -> Book:
        # 입력 검증
        if not stories or not images:
            raise ValueError("At least one page is required")

        if len(stories) != len(images):
            raise ValueError(
                f"Stories and images count mismatch: {len(stories)} vs {len(images)}"
            )

        # Book 객체 초기화 (status='process')
        if book_id:
            # 기존 Book ID 사용 (BackgroundTasks에서 호출 시)
            book = Book(
                id=book_id,
                title="",  # 기본 제목 (나중에 업데이트 가능)
                cover_image="",
                status="success",
                pages=[],
            )
        else:
            # 새 Book 생성 (일반 호출 시)
            book = Book(title="", cover_image="", status="success", pages=[])

        return book
