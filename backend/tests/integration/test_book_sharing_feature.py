"""
Integration Tests for Book Sharing Feature
동화책 공유 기능(Google Drive Style) 검증
"""

import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from backend.features.auth.models import User
from backend.core.auth.jwt_manager import JWTManager


@pytest.mark.asyncio
@pytest.mark.usefixtures("setup_test_database")
class TestBookSharingMain:
    
    async def create_user(self, db_session: AsyncSession, email: str) -> User:
        """Create a test user and return it."""
        user = User(
            email=email,
            password_hash="hashed_password",
            is_active=True
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    def get_auth_headers(self, user: User) -> dict:
        """Generate auth headers for the user."""
        token = JWTManager.create_access_token(data={"sub": str(user.id), "email": user.email})
        return {"Authorization": f"Bearer {token}"}

    async def test_book_sharing_lifecycle(self, client: AsyncClient, db_session: AsyncSession):
        """
        Test the full lifecycle of book sharing:
        1. Create private book
        2. Verify private access (Owner OK, Anon Fail)
        3. Toggle share (is_shared=True)
        4. Verify public access (Anon OK)
        5. Verify TTS access (Anon OK)
        6. Toggle share off (is_shared=False)
        7. Verify access revoked (Anon Fail)
        """
        
        # 1. Setup User
        user = await self.create_user(db_session, f"sharer_{uuid.uuid4()}@example.com")
        headers = self.get_auth_headers(user)
        
        # 2. Create Book (Private by default)
        
        # Insert Book directly to bypass AI generation delay/mocking issues
        from backend.features.storybook.models import Book, BookStatus
        book_id = uuid.uuid4()
        book = Book(
            id=book_id,
            user_id=user.id,
            title="My Private Book",
            status=BookStatus.COMPLETED, # Completed to allow viewing
            is_shared=False,
            is_default=False,
            voice_id="voice123"
        )
        db_session.add(book)
        await db_session.commit()
        
        # Verify book exists via endpoint (Owner)
        resp = await client.get(f"/api/v1/storybook/books/{book_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_shared"] is False
        assert data["title"] == "My Private Book"
        
        # 3. Verify Anonymous Access (Should Fail)
        resp_anon = await client.get(f"/api/v1/storybook/books/{book_id}")
        # Expect 401 Unauthorized or 403 Forbidden or 404 (if we hide existence)
        print(f"Anon access status: {resp_anon.status_code}")
        assert resp_anon.status_code in [401, 403]
        
        # 4. Toggle Share to True
        # PATCH /books/{book_id}/share
        resp_share = await client.patch(
            f"/api/v1/storybook/books/{book_id}/share",
            headers=headers,
            data={"is_shared": True} 
        )
        assert resp_share.status_code == 200
        assert resp_share.json()["is_shared"] is True
        
        # 5. Verify Anonymous Access (Should Succeed)
        resp_anon_shared = await client.get(f"/api/v1/storybook/books/{book_id}")
        assert resp_anon_shared.status_code == 200
        assert resp_anon_shared.json()["title"] == "My Private Book"
        
        # 6. Verify TTS Access (Should Succeed)
        # /api/v1/tts/words/{book_id}/{word}
        resp_tts = await client.get(f"/api/v1/tts/words/{book_id}/hello")
        print(f"TTS access status: {resp_tts.status_code}")
        assert resp_tts.status_code not in [401, 403]
        
        # 7. Toggle Share OFF
        resp_unshare = await client.patch(
            f"/api/v1/storybook/books/{book_id}/share",
            headers=headers,
            data={"is_shared": False} 
        )
        assert resp_unshare.status_code == 200
        assert resp_unshare.json()["is_shared"] is False
        
        # 8. Verify Access Revoked
        resp_anon_revoked = await client.get(f"/api/v1/storybook/books/{book_id}")
        assert resp_anon_revoked.status_code in [401, 403]
