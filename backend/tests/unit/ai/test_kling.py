"""
Kling Video Provider Unit Tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from backend.infrastructure.ai.providers.kling import KlingVideoProvider


class TestKlingVideoProvider:
    @pytest.fixture
    def provider(self):
        return KlingVideoProvider(api_key="test_key")

    @pytest.mark.asyncio
    async def test_generate_video(self, provider):
        image_data = b"fake_image_data"
        mock_response = MagicMock()
        mock_response.json.return_value = {"task_id": "test_task_id"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            task_id = await provider.generate_video(image_data, prompt="test prompt")
            
            assert task_id == "test_task_id"
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert kwargs["data"]["prompt"] == "test prompt"

    @pytest.mark.asyncio
    async def test_check_video_status(self, provider):
        task_id = "test_task_id"
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "succeeded",
            "progress": 100,
            "output": {"url": "http://example.com/video.mp4"}
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            status = await provider.check_video_status(task_id)
            
            assert status["status"] == "completed"
            assert status["video_url"] == "http://example.com/video.mp4"
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_video(self, provider):
        video_url = "http://example.com/video.mp4"
        video_content = b"fake_video_content"
        mock_response = MagicMock()
        mock_response.content = video_content
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            content = await provider.download_video(video_url)
            
            assert content == video_content
            mock_get.assert_called_once_with(video_url)
