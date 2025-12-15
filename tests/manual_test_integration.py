import sys
import asyncio
import uuid
from unittest.mock import MagicMock, AsyncMock

# Global Mocks
sys.modules['backend.core.config'] = MagicMock()
sys.modules['backend.infrastructure.storage.base'] = MagicMock()
sys.modules['backend.infrastructure.ai.factory'] = MagicMock()
sys.modules['backend.core.events.redis_streams_bus'] = MagicMock()
# We need to ensure models are mocked or importable
sys.modules['sqlalchemy.ext.asyncio'] = MagicMock()

# Configure Settings Mock BEFORE importing service
mock_settings = MagicMock()
mock_settings.max_books_per_user = 10
mock_settings.max_pages_per_book = 20
mock_settings.DEFAULT_VOICE_ID = "default_voice"
sys.modules['backend.core.config'].settings = mock_settings

# Models might need more care if they are used
sys.modules['backend.features.storybook.models'] = MagicMock()

# Import Service
from backend.features.storybook.service import BookOrchestratorService
from backend.features.tts.producer import TTSProducer

async def test_integration():
    print("Starting Integration Test...")
    
    # Setup Mocks
    mock_repo = AsyncMock()
    mock_storage = AsyncMock()
    mock_ai_factory = MagicMock()
    mock_db = AsyncMock()
    mock_event_bus = AsyncMock()
    
    # Producer
    producer = TTSProducer(mock_event_bus)
    
    # Service
    service = BookOrchestratorService(
        book_repo=mock_repo,
        storage_service=mock_storage,
        ai_factory=mock_ai_factory,
        db_session=mock_db,
        tts_producer=producer
    )
    
    # Mock Repo Returns
    mock_book = MagicMock()
    mock_book.id = uuid.uuid4()
    mock_book.base_path = "users/123/books/456"
    mock_repo.create.return_value = mock_book
    
    mock_page = MagicMock()
    mock_page.id = uuid.uuid4()
    mock_repo.add_page.return_value = mock_page
    
    mock_dialogue = MagicMock()
    mock_dialogue.id = uuid.uuid4()
    mock_repo.add_dialogue_with_translation.return_value = mock_dialogue
    
    mock_audio = MagicMock()
    mock_audio.id = uuid.uuid4()
    mock_repo.add_dialogue_audio.return_value = mock_audio
    
    # Mock AI
    mock_story_provider = AsyncMock()
    mock_story_provider.generate_story_with_images.return_value = {
        "title": "Test Book",
        "pages": [{"content": "Hello World", "image_prompt": "A cat"}]
    }
    mock_ai_factory.get_story_provider.return_value = mock_story_provider
    
    mock_image_provider = AsyncMock()
    mock_image_provider.generate_image.return_value = b"fake_image"
    mock_ai_factory.get_image_provider.return_value = mock_image_provider
    
    # Run Create Storybook
    print("Calling create_storybook...")
    await service.create_storybook(
        user_id=uuid.uuid4(),
        prompt="Test Prompt"
    )
    
    # Verifications
    print("Verifying calls...")
    
    # 1. Check if add_dialogue_audio was called with PENDING
    mock_repo.add_dialogue_audio.assert_called()
    call_args = mock_repo.add_dialogue_audio.call_args[1]
    if call_args.get("status") != "PENDING":
        print(f"FAILED: Status should be PENDING, got {call_args.get('status')}")
        return

    # 2. Check if producer enqueued task
    mock_event_bus.publish.assert_called()
    published_payload = mock_event_bus.publish.call_args[0][1] # (event_type, payload)
    
    if published_payload["text"] != "Hello World":
        print(f"FAILED: Payload text mismatch. Got {published_payload['text']}")
        return
        
    if published_payload["uuid"] != str(mock_audio.id):
        print(f"FAILED: Payload UUID mismatch.")
        return
        
    print("SUCCESS: Service correctly calls Producer and Repo!")

if __name__ == "__main__":
    asyncio.run(test_integration())
