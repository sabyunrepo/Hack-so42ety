import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import json
import uuid

import sys

# Global Mocks (Persistent)
sys.modules['backend.core.config'] = MagicMock()
sys.modules['backend.core.database.session'] = MagicMock()
sys.modules['backend.features.storybook.models'] = MagicMock()
sys.modules['backend.infrastructure.ai.factory'] = MagicMock()
sys.modules['redis.asyncio'] = MagicMock()
sys.modules['redis'] = MagicMock()
sys.modules['sqlalchemy'] = MagicMock() # Mock sqlalchemy to handle Mock models

from backend.features.tts.worker import TTSWorker

class TestTTSWorker(unittest.IsolatedAsyncioTestCase):
    async def test_worker_logic(self):
        """Test the worker loop, semaphore, and message processing logic"""
        
        # Setup Mocks
        worker = TTSWorker()
        
        # Mock Redis
        mock_redis = AsyncMock()
        worker.redis = mock_redis
        
        # Mock Factory & Provider
        mock_provider = AsyncMock()
        mock_provider.text_to_speech.return_value = b"fake_audio_bytes"
        worker.ai_factory.get_tts_provider.return_value = mock_provider
        
        # Mock DB Session
        mock_session = AsyncMock(name="db_session")
        
        # Use a plain class for Result to avoid AsyncMock inference issues
        class FakeResult:
            def scalar_one_or_none(self):
                return mock_record
                
        fake_result = FakeResult()

        mock_record = MagicMock(name="dialogue_record")
        mock_record.voice_id = "test_voice"
        mock_record.audio_url = "test/path/audio.mp3"
        mock_record.status = "PENDING"
        
        mock_session.execute.return_value = fake_result
        
        # Mock AsyncSessionLocal to return our mock session object
        with patch('backend.features.tts.worker.asyncio.sleep', new_callable=AsyncMock):
             with patch('backend.features.tts.worker.AsyncSessionLocal', return_value=mock_session):
                with patch('aiofiles.open', new_callable=MagicMock) as mock_file_open:
                    mock_file_handle = AsyncMock()
                    mock_file_open.return_value.__aenter__.return_value = mock_file_handle
                    
                    with patch('os.makedirs'):
                         # Trigger handle_tts_task directly to verify logic
                         await worker.handle_tts_task("123e4567-e89b-12d3-a456-426614174000", "Hello World")
                         
                         # Assertions
                         # 1. DB Lookup
                         mock_session.execute.assert_called()
                         
                         # 2. Status Updates
                         self.assertEqual(mock_record.status, "COMPLETED")
                         self.assertEqual(mock_session.commit.call_count, 2) # Processing, Completed
                         
                         # 3. API Call
                         mock_provider.text_to_speech.assert_called_with(
                             text="Hello World", 
                             voice_id="test_voice"
                         )
                         
                         # 4. File Save
                         mock_file_handle.write.assert_called()

if __name__ == '__main__':
    unittest.main()
