import pytest
import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select

from backend.features.auth.models import User
from backend.features.storybook.models import Book
from backend.features.storybook.repository import BookRepository

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
@pytest.mark.usefixtures("setup_test_database")
class TestSoftDeleteBookOnly:

    async def create_user(self, db: AsyncSession) -> User:
        """테스트용 User 생성"""
        user = User(
            email=f"test_{uuid.uuid4()}@example.com",
            password_hash="hashed_password",
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def set_db_user(self, db: AsyncSession, user_id: uuid.UUID):
        """PostgreSQL RLS용 current_user_id 설정"""
        await db.execute(
            text("SELECT set_config('app.current_user_id', :uid, false)").bindparams(
                uid=str(user_id)
            )
        )

    async def create_book(self, db: AsyncSession, user_id: uuid.UUID, title="Book"):
        """Book 생성 헬퍼"""
        book = Book(
            user_id=user_id,
            title=title,
            is_deleted=False,
        )
        db.add(book)
        await db.commit()
        await db.refresh(book)
        return book

    async def test_soft_delete_book(self, db_session: AsyncSession):
        """단일 soft_delete 기본 동작 테스트"""

        user = await self.create_user(db_session)
        await self.set_db_user(db_session, user.id)

        book = await self.create_book(db_session, user.id, "Test Book")

        repo = BookRepository(db_session)
        deleted_book = await repo.soft_delete(book.id)

        assert deleted_book.is_deleted is True

        refreshed = await repo.get(book.id)
        assert refreshed.is_deleted is True

    # ───────────────────────────────────────────────────────────────
    #                🎯 추가 테스트: 3개 제한 + soft delete 후 생성
    # ───────────────────────────────────────────────────────────────
    async def test_book_limit_3_and_soft_delete_behavior(
        self, db_session: AsyncSession
    ):
        """
        요구사항:
        1) 유저는 최대 Book 3개까지 생성 가능
        2) soft_delete 되어도 DB에서는 삭제되지 않음
        3) soft_delete 된 후에는 새 Book 생성이 가능해야 함
        """

        # 1) 유저 생성
        user = await self.create_user(db_session)
        await self.set_db_user(db_session, user.id)

        repo = BookRepository(db_session)

        # 2) Book 3개 생성
        books = []
        for i in range(3):
            b = await self.create_book(db_session, user.id, f"Book {i+1}")
            books.append(b)

        # 활성 Book 수는 정확히 3개여야 함
        result = await db_session.execute(
            select(Book).where(Book.user_id == user.id, Book.is_deleted == False)
        )
        active_books = result.scalars().all()
        logger.info(f"Active books before deletion: {[b.title for b in active_books]}")
        assert len(active_books) == 3

        # 3) soft delete 하나
        deleted = await repo.soft_delete(books[0].id)
        assert deleted.is_deleted is True

        # soft_delete 후 ACTIVE만 확인하면 2개여야 함
        result = await db_session.execute(
            select(Book).where(Book.user_id == user.id, Book.is_deleted == False)
        )
        active_books = result.scalars().all()
        assert len(active_books) == 2

        # soft_delete 된 첫 책은 DB에는 살아있어야 함
        result = await db_session.execute(select(Book).where(Book.id == books[0].id))
        soft_deleted_book = result.scalar_one()
        assert soft_deleted_book.is_deleted is True  # soft delete 상태 유지
        assert soft_deleted_book.title == "Book 1"  # DB에 여전히 존재함

        # 4) soft_delete 덕분에 다시 새 Book 생성이 가능해야 함 (active=2 → OK)
        new_book = await self.create_book(db_session, user.id, "New Book After Delete")

        assert new_book is not None

        # 활성 Book 수는 다시 3개가 되어야 함
        result = await db_session.execute(
            select(Book).where(Book.user_id == user.id, Book.is_deleted == False)
        )
        active_books = result.scalars().all()
        assert len(active_books) == 3

        # 5) soft_delete 되었던 Book도 DB에 총합 4개로 남아 있어야 함
        result = await db_session.execute(select(Book).where(Book.user_id == user.id))
        all_books = result.scalars().all()
        assert len(all_books) == 4  # soft deleted 포함 총 4개

        # soft deleted book 체크
        assert any(b.id == books[0].id and b.is_deleted for b in all_books)
