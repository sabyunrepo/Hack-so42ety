"""
File Caching Integration Tests
파일 캐싱 통합 테스트
"""
import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.storybook.models import Book, BookStatus
from backend.features.storybook.repository import BookRepository
from backend.features.auth.models import User
from backend.features.auth.repository import UserRepository
from backend.infrastructure.storage.local import LocalStorageService
from backend.core.cache.service import CacheService
from backend.core.events.redis_streams_bus import RedisStreamsEventBus
from backend.core.services.file_cache import FileCacheService


@pytest.mark.asyncio
@pytest.mark.usefixtures("setup_test_database")
class TestFileCaching:
    """파일 캐싱 통합 테스트"""

    async def test_public_file_caching(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """공개 파일 캐싱 테스트"""
        # 1. 사용자 및 공개 책 생성
        user_repo = UserRepository(db_session)
        user = await user_repo.create(
            email="cache@example.com",
            password="password123",
        )
        await db_session.commit()

        book_repo = BookRepository(db_session)
        book = await book_repo.create(
            user_id=user.id,
            title="Cached Book",
            is_public=True,
            visibility="public",
            status=BookStatus.COMPLETED,
        )
        await db_session.commit()

        # 2. 테스트 파일 생성
        storage_service = LocalStorageService()
        file_path = f"users/{user.id}/books/{book.id}/images/page_1.png"
        test_file_data = b"test image data"
        
        await storage_service.save(
            test_file_data,
            file_path,
            content_type="image/png"
        )

        # 3. 첫 번째 요청 (캐시 미스)
        response1 = await client.get(f"/api/v1/files/{file_path}")
        assert response1.status_code == 200
        assert response1.headers.get("X-Cache") == "MISS"
        assert "ETag" in response1.headers

        # 4. 두 번째 요청 (캐시 히트)
        etag = response1.headers.get("ETag")
        response2 = await client.get(
            f"/api/v1/files/{file_path}",
            headers={"If-None-Match": etag}
        )
        
        # 캐시 히트 또는 304 Not Modified
        assert response2.status_code in [200, 304]
        if response2.status_code == 200:
            assert response2.headers.get("X-Cache") == "HIT"
        else:
            assert response2.status_code == 304

    async def test_private_file_no_caching(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """비공개 파일은 캐싱하지 않음 테스트"""
        # 1. 사용자 생성 및 로그인
        user_repo = UserRepository(db_session)
        user = await user_repo.create(
            email="private_cache@example.com",
            password="password123",
        )
        await db_session.commit()

        # 로그인
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "private_cache@example.com", "password": "password123"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. 비공개 책 생성
        book_repo = BookRepository(db_session)
        book = await book_repo.create(
            user_id=user.id,
            title="Private Cached Book",
            is_public=False,
            visibility="private",
            status=BookStatus.COMPLETED,
        )
        await db_session.commit()

        # 3. 테스트 파일 생성
        storage_service = LocalStorageService()
        file_path = f"users/{user.id}/books/{book.id}/images/page_1.png"
        test_file_data = b"test private image data"
        
        await storage_service.save(
            test_file_data,
            file_path,
            content_type="image/png"
        )

        # 4. 첫 번째 요청 (인증된 사용자)
        response1 = await client.get(
            f"/api/v1/files/{file_path}",
            headers=headers
        )
        assert response1.status_code == 200
        assert response1.headers.get("X-Cache") == "MISS"  # 비공개 파일은 캐싱 안 함
        assert "Cache-Control" in response1.headers
        assert "private" in response1.headers.get("Cache-Control", "")

