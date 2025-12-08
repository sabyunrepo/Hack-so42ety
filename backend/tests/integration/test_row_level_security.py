"""
Row Level Security Integration Tests
RLS 정책이 올바르게 작동하는지 검증
"""

import pytest
import uuid
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.auth.models import User
from backend.domain.models.book import Book
from backend.core.auth.providers.credentials import CredentialsAuthProvider


@pytest.mark.asyncio
@pytest.mark.usefixtures("setup_test_database")
class TestRowLevelSecurity:
    """RLS 통합 테스트"""

    async def create_user(self, db_session: AsyncSession, email: str) -> User:
        """테스트 사용자 생성"""
        user = User(
            email=email,
            password_hash="hashed_password",
            is_active=True
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    async def set_db_user(self, db_session: AsyncSession, user_id: uuid.UUID):
        """DB 세션에 사용자 컨텍스트 설정 (RLS용)"""
        await db_session.execute(
            text(f"SELECT set_config('app.current_user_id', '{user_id}', false)")
        )

    async def apply_rls_policies(self, db_session: AsyncSession):
        """RLS 정책 수동 적용 (create_all은 정책을 생성하지 않으므로)"""
        # 1. Enable & Force RLS
        await db_session.execute(text("ALTER TABLE books ENABLE ROW LEVEL SECURITY"))
        await db_session.execute(text("ALTER TABLE books FORCE ROW LEVEL SECURITY"))
        
        # 2. Create Policy
        # Check if policy exists to avoid error? Or just try-except?
        # Since tests might run multiple times in session, policies might exist if tables weren't dropped.
        # But setup_test_database drops tables.
        
        await db_session.execute(text("""
            CREATE POLICY books_isolation_policy ON books
            USING (user_id = current_setting('app.current_user_id', true)::uuid)
            WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid)
        """))
        
        await db_session.commit()

    async def test_rls_book_isolation(self, db_session: AsyncSession):
        """
        사용자 간 동화책 데이터 격리 테스트
        User A가 생성한 책을 User B가 조회/수정/삭제할 수 없어야 함
        """
        # 0. RLS 정책 적용
        await self.apply_rls_policies(db_session)

        # 1. 사용자 생성
        user_a = await self.create_user(db_session, "user_a@example.com")
        user_b = await self.create_user(db_session, "user_b@example.com")

        # 2. User A로 로그인 (DB 컨텍스트 설정)
        await self.set_db_user(db_session, user_a.id)

        # 3. User A가 책 생성
        book_a = Book(
            user_id=user_a.id,
            title="User A's Book",
            status="draft"
        )
        db_session.add(book_a)
        await db_session.commit()
        await db_session.refresh(book_a)
        book_id = book_a.id

        # 4. User A는 본인 책 조회 가능
        result = await db_session.get(Book, book_id)
        assert result is not None
        assert result.title == "User A's Book"

        # 5. User B로 전환
        await self.set_db_user(db_session, user_b.id)
        
        # 세션 캐시 비우기 (중요: 메모리에 있는 객체를 반환하지 않고 DB에서 다시 조회하도록 함)
        db_session.expunge_all()

        # 6. User B는 User A의 책을 조회할 수 없어야 함 (RLS에 의해 필터링됨)
        # SQLAlchemy get() might return None if row is not visible
        result_b = await db_session.get(Book, book_id)
        assert result_b is None

        # 7. User B가 User A의 책 ID로 Update 시도 -> 영향받은 행 0이어야 함
        # ORM update usually fetches first, so let's try direct update
        from sqlalchemy import update
        stmt = (
            update(Book)
            .where(Book.id == book_id)
            .values(title="Hacked by B")
        )
        result_update = await db_session.execute(stmt)
        assert result_update.rowcount == 0

        # 8. User B가 User A의 책 ID로 Delete 시도 -> 영향받은 행 0이어야 함
        from sqlalchemy import delete
        stmt = delete(Book).where(Book.id == book_id)
        result_delete = await db_session.execute(stmt)
        assert result_delete.rowcount == 0

        # 9. 다시 User A로 전환하여 책이 그대로 있는지 확인
        await self.set_db_user(db_session, user_a.id)
        # 세션 캐시 비우기 (중요)
        db_session.expire_all()
        
        result_final = await db_session.get(Book, book_id)
        assert result_final is not None
        assert result_final.title == "User A's Book"
