import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.config import settings

@pytest.mark.asyncio
@pytest.mark.usefixtures("setup_test_database")
class TestBookCreationFlow:
    """
    동화책 생성 전체 흐름 E2E 테스트
    회원가입 -> 로그인 -> 동화책 생성 -> 조회 -> 삭제
    """

    async def test_book_creation_flow(self, client: AsyncClient, db_session: AsyncSession):
        # 1. 회원가입
        email = "parent@example.com"
        password = "password123"
        
        response = await client.post("/api/v1/auth/register", json={
            "email": email,
            "password": password
        })
        assert response.status_code == 201
        
        # 2. 로그인 (토큰이 httpOnly 쿠키로 자동 설정됨)
        response = await client.post("/api/v1/auth/login", json={
            "email": email,
            "password": password
        })
        assert response.status_code == 200
        # 토큰은 쿠키로 설정되므로 응답 본문에 없음
        assert "access_token" in response.cookies
        # httpx AsyncClient는 쿠키를 자동으로 유지하므로 headers 불필요
        
        # 3. 동화책 생성 요청
        # Mocking AI Providers is necessary here unless we want to call real APIs (costly/slow)
        # For E2E, we might want to mock the AI Factory or Providers.
        # However, since we are in a test environment, we can rely on the fact that 
        # we might be using Mock providers or we should mock them using pytest-mock.
        # Let's assume we need to mock them.
        
        # But wait, `conftest.py` might not have mocking for AI providers setup globally.
        # I should check if I can mock `AIProviderFactory` methods.
        
        # For now, let's try to run it. If it calls real APIs, it might fail if keys are missing.
        # But `AIProviderFactory` reads env vars. If `AI_STORY_PROVIDER` is not set, it defaults to something.
        # Let's check `backend/infrastructure/ai/factory.py`.
        # It defaults to `google` for story.
        
        # To avoid external calls, I should mock the providers.
        # I'll use `unittest.mock.patch` in the test method.
        
        from unittest.mock import patch, MagicMock, AsyncMock
        
        # Mock Story Provider
        mock_story_provider = MagicMock()
        mock_story_provider.generate_story_with_images = AsyncMock(return_value={
            "title": "The Brave Little Toaster",
            "pages": [
                {"content": "Once upon a time...", "image_prompt": "A toaster"},
                {"content": "He went to space...", "image_prompt": "Toaster in space"}
            ]
        })
        
        # Mock Image Provider
        mock_image_provider = MagicMock()
        mock_image_provider.generate_image = AsyncMock(return_value=b"fake_image_bytes")
        
        # Mock TTS Provider
        mock_tts_provider = MagicMock()
        mock_tts_provider.text_to_speech = AsyncMock(return_value=b"fake_audio_bytes")
        
        with patch("backend.infrastructure.ai.factory.AIProviderFactory.get_story_provider", return_value=mock_story_provider), \
             patch("backend.infrastructure.ai.factory.AIProviderFactory.get_image_provider", return_value=mock_image_provider), \
             patch("backend.infrastructure.ai.factory.AIProviderFactory.get_tts_provider", return_value=mock_tts_provider):
             
            # 쿠키가 자동으로 전송되므로 headers 불필요
            response = await client.post("/api/v1/storybook/create", json={
                "prompt": "A toaster in space",
                "num_pages": 2,
                "target_age": "5-7",
                "theme": "sci-fi"
            })
            
            assert response.status_code == 201
            book_data = response.json()
            assert book_data["title"] == "The Brave Little Toaster"
            assert len(book_data["pages"]) == 2
            assert book_data["pages"][0]["sequence"] == 1
            assert len(book_data["pages"][0]["dialogues"]) > 0
            book_id = book_data["id"]
            
            # 4. 동화책 목록 조회 (쿠키 자동 전송)
            response = await client.get("/api/v1/storybook/books")
            assert response.status_code == 200
            books = response.json()
            assert len(books) == 1
            assert books[0]["id"] == book_id

            # 5. 동화책 상세 조회 (쿠키 자동 전송)
            response = await client.get(f"/api/v1/storybook/books/{book_id}")
            assert response.status_code == 200
            book_detail = response.json()
            assert book_detail["id"] == book_id
            assert len(book_detail["pages"]) == 2

            # 6. 동화책 삭제 (쿠키 자동 전송)
            response = await client.delete(f"/api/v1/storybook/books/{book_id}")
            assert response.status_code == 204

            # 7. 삭제 확인 (쿠키 자동 전송)
            response = await client.get(f"/api/v1/storybook/books/{book_id}")
            assert response.status_code == 404
