"""
Book Repository
동화책 데이터 접근 계층
"""

import uuid
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.book import Book, Page, Dialogue
from .base import AbstractRepository


class BookRepository(AbstractRepository[Book]):
    """
    동화책 Repository
    
    Book, Page, Dialogue 엔티티 관리
    """

    def __init__(self, db: AsyncSession):
        super().__init__(db, Book)

    async def get_with_pages(self, book_id: uuid.UUID) -> Optional[Book]:
        """
        동화책 상세 조회 (페이지 및 대사 포함)
        
        Args:
            book_id: 동화책 UUID
            
        Returns:
            Optional[Book]: 동화책 (페이지 포함) 또는 None
        """
        query = (
            select(Book)
            .options(
                selectinload(Book.pages).selectinload(Page.dialogues)
            )
            .where(Book.id == book_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_user_books(self, user_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[Book]:
        """
        사용자의 동화책 목록 조회
        
        Args:
            user_id: 사용자 UUID
            skip: 건너뛸 개수
            limit: 가져올 개수
            
        Returns:
            List[Book]: 동화책 목록
        """
        query = (
            select(Book)
            .where(Book.user_id == user_id)
            .order_by(Book.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def add_page(self, book_id: uuid.UUID, page_data: dict) -> Page:
        """
        페이지 추가
        
        Args:
            book_id: 동화책 UUID
            page_data: 페이지 데이터 (sequence, image_prompt 등)
            
        Returns:
            Page: 생성된 페이지
        """
        page = Page(book_id=book_id, **page_data)
        self.session.add(page)
        await self.session.flush()
        await self.session.refresh(page)
        return page

    async def add_dialogue(self, page_id: uuid.UUID, dialogue_data: dict) -> Dialogue:
        """
        대사 추가
        
        Args:
            page_id: 페이지 UUID
            dialogue_data: 대사 데이터 (sequence, speaker, text_en 등)
            
        Returns:
            Dialogue: 생성된 대사
        """
        dialogue = Dialogue(page_id=page_id, **dialogue_data)
        self.session.add(dialogue)
        await self.session.flush()
        await self.session.refresh(dialogue)
        return dialogue
