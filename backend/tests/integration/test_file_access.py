"""
File Access API Integration Tests
파일 접근 API 통합 테스트
"""
import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.storybook.models import Book, BookStatus
from backend.features.storybook.repository import BookRepository
from backend.features.auth.models import User
from backend.features.auth.repository import UserRepository


@pytest.mark.asyncio
@pytest.mark.usefixtures("setup_test_database")
class TestFileAccessAPI:
    """파일 접근 API 통합 테스트"""

    async def test_public_book_file_access_without_auth(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """공개 책 파일 접근 테스트 (인증 없이)"""
        # 1. 사용자 생성
        user_repo = UserRepository(db_session)
        user = await user_repo.create(
            email="public@example.com",
            password="password123",
        )
        await db_session.commit()

        # 2. 공개 책 생성
        book_repo = BookRepository(db_session)
        book = await book_repo.create(
            user_id=user.id,
            title="Public Book",
            is_public=True,
            visibility="public",
            status=BookStatus.COMPLETED,
        )
        await db_session.commit()

        # 3. 테스트 파일 경로 생성
        file_path = f"users/{user.id}/books/{book.id}/images/page_1.png"
        
        # 4. 파일 접근 시도 (인증 없이)
        response = await client.get(f"/api/v1/files/{file_path}")
        
        # 파일이 실제로 존재하지 않으므로 404가 나올 수 있지만,
        # 접근 권한은 통과해야 함 (403이 아니어야 함)
        assert response.status_code in [200, 404]  # 파일 없음은 404, 권한 문제는 403
        assert response.status_code != 403

    async def test_private_book_file_access_without_auth(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """비공개 책 파일 접근 테스트 (인증 없이) - 실패해야 함"""
        # 1. 사용자 생성
        user_repo = UserRepository(db_session)
        user = await user_repo.create(
            email="private@example.com",
            password="password123",
        )
        await db_session.commit()

        # 2. 비공개 책 생성
        book_repo = BookRepository(db_session)
        book = await book_repo.create(
            user_id=user.id,
            title="Private Book",
            is_public=False,
            visibility="private",
            status=BookStatus.COMPLETED,
        )
        await db_session.commit()

        # 3. 테스트 파일 경로 생성
        file_path = f"users/{user.id}/books/{book.id}/images/page_1.png"
        
        # 4. 파일 접근 시도 (인증 없이) - 403이어야 함
        response = await client.get(f"/api/v1/files/{file_path}")
        
        assert response.status_code == 403
        assert "denied" in response.json()["detail"].lower() or "access" in response.json()["detail"].lower()

    async def test_private_book_file_access_with_owner(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """비공개 책 파일 접근 테스트 (소유자)"""
        # 1. 사용자 생성 및 로그인
        user_repo = UserRepository(db_session)
        user = await user_repo.create(
            email="owner@example.com",
            password="password123",
        )
        await db_session.commit()

        # 로그인
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "owner@example.com", "password": "password123"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. 비공개 책 생성
        book_repo = BookRepository(db_session)
        book = await book_repo.create(
            user_id=user.id,
            title="Private Book",
            is_public=False,
            visibility="private",
            status=BookStatus.COMPLETED,
        )
        await db_session.commit()

        # 3. 테스트 파일 경로 생성
        file_path = f"users/{user.id}/books/{book.id}/images/page_1.png"
        
        # 4. 파일 접근 시도 (소유자) - 404는 가능하지만 403은 아니어야 함
        response = await client.get(
            f"/api/v1/files/{file_path}",
            headers=headers
        )
        
        assert response.status_code != 403  # 권한 문제는 없어야 함
        assert response.status_code in [200, 404]  # 파일 없음은 404

    async def test_private_book_file_access_with_other_user(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """비공개 책 파일 접근 테스트 (다른 사용자) - 실패해야 함"""
        # 1. 책 소유자 생성
        user_repo = UserRepository(db_session)
        owner = await user_repo.create(
            email="owner2@example.com",
            password="password123",
        )
        
        # 2. 다른 사용자 생성 및 로그인
        other_user = await user_repo.create(
            email="other@example.com",
            password="password123",
        )
        await db_session.commit()

        # 다른 사용자로 로그인
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "other@example.com", "password": "password123"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. 소유자의 비공개 책 생성
        book_repo = BookRepository(db_session)
        book = await book_repo.create(
            user_id=owner.id,
            title="Private Book",
            is_public=False,
            visibility="private",
            status=BookStatus.COMPLETED,
        )
        await db_session.commit()

        # 4. 테스트 파일 경로 생성
        file_path = f"users/{owner.id}/books/{book.id}/images/page_1.png"
        
        # 5. 파일 접근 시도 (다른 사용자) - 403이어야 함
        response = await client.get(
            f"/api/v1/files/{file_path}",
            headers=headers
        )
        
        assert response.status_code == 403
        assert "denied" in response.json()["detail"].lower() or "access" in response.json()["detail"].lower()

