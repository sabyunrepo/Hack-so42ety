"""
Book Repository Unit Tests
BookRepository CRUD 및 관계 테스트
"""

import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.auth.models import User
from backend.features.storybook.models import Book
from backend.features.storybook.repository import BookRepository


@pytest.mark.asyncio
@pytest.mark.usefixtures("setup_test_database")
class TestBookRepository:
    """BookRepository 단위 테스트"""

    async def create_user(self, db_session: AsyncSession) -> User:
        """테스트 사용자 생성"""
        user = User(
            email=f"test_{uuid.uuid4()}@example.com",
            password_hash="hashed_password",
            is_active=True
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    async def set_db_user(self, db_session: AsyncSession, user_id: uuid.UUID):
        """DB 세션에 사용자 컨텍스트 설정"""
        from sqlalchemy import text
        await db_session.execute(
            text(f"SELECT set_config('app.current_user_id', '{user_id}', false)")
        )

    async def test_create_and_get_book(self, db_session: AsyncSession):
        """책 생성 및 조회 테스트"""
        user = await self.create_user(db_session)
        await self.set_db_user(db_session, user.id)
        
        repo = BookRepository(db_session)

        # 책 생성
        book = await repo.create(
            user_id=user.id,
            title="Test Book",
            status="draft"
        )
        assert book.id is not None
        assert book.title == "Test Book"

        # 조회
        fetched_book = await repo.get(book.id)
        assert fetched_book is not None
        assert fetched_book.id == book.id
        assert fetched_book.user_id == user.id

    async def test_add_page_and_dialogue(self, db_session: AsyncSession):
        """페이지 및 대사 추가 테스트"""
        user = await self.create_user(db_session)
        await self.set_db_user(db_session, user.id)
        repo = BookRepository(db_session)
        book = await repo.create(user_id=user.id, title="Story Book", status="draft")

        # 페이지 추가
        page = await repo.add_page(book.id, {"sequence": 1, "image_prompt": "A sunny day"})
        assert page.id is not None
        assert page.book_id == book.id
        assert page.sequence == 1

        # 대사 추가
        dialogue = await repo.add_dialogue(
            page.id, 
            {"sequence": 1, "speaker": "Narrator", "text_en": "Once upon a time"}
        )
        assert dialogue.id is not None
        assert dialogue.page_id == page.id
        assert dialogue.text_en == "Once upon a time"

        # Eager Loading 테스트
        # 세션 캐시 비우기
        db_session.expunge_all()
        
        book_with_pages = await repo.get_with_pages(book.id)
        assert book_with_pages is not None
        assert len(book_with_pages.pages) == 1
        assert len(book_with_pages.pages[0].dialogues) == 1
        assert book_with_pages.pages[0].dialogues[0].text_en == "Once upon a time"

    async def test_cascade_delete(self, db_session: AsyncSession):
        """Cascade 삭제 테스트"""
        user = await self.create_user(db_session)
        await self.set_db_user(db_session, user.id)
        repo = BookRepository(db_session)
        book = await repo.create(user_id=user.id, title="Delete Me", status="draft")
        page = await repo.add_page(book.id, {"sequence": 1})
        await repo.add_dialogue(page.id, {"sequence": 1, "speaker": "N", "text_en": "Hi"})

        # 책 삭제
        await repo.delete(book.id)
        
        # 확인
        assert await repo.get(book.id) is None
        
        # 페이지도 삭제되었는지 확인 (직접 쿼리)
        from backend.domain.models.book import Page
        result = await db_session.get(Page, page.id)
        assert result is None
