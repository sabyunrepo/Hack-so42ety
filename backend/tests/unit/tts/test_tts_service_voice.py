"""
TTSService Voice 관련 단위 테스트
"""
import pytest
import uuid
from unittest.mock import MagicMock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.tts.service import TTSService
from backend.features.tts.repository import AudioRepository, VoiceRepository
from backend.features.tts.models import VoiceVisibility, VoiceStatus
from backend.infrastructure.storage.base import AbstractStorageService
from backend.infrastructure.ai.factory import AIProviderFactory
from backend.core.cache.service import CacheService
from backend.core.events.bus import EventBus


@pytest.fixture
def mock_tts_provider():
    """Mock TTS Provider"""
    provider = MagicMock()
    provider.clone_voice = AsyncMock(return_value={
        "voice_id": "elevenlabs_voice_123",
        "name": "Test Voice",
        "language": "en",
        "gender": "male",
        "category": "cloned",
        "preview_url": None,  # 초기에는 None
        "description": "Test description",
        "labels": {"language": "en", "gender": "male"},
    })
    provider.get_available_voices = AsyncMock(return_value=[
        {
            "voice_id": "premade_1",
            "name": "Premade Voice 1",
            "language": "en",
            "gender": "female",
            "category": "premade",
            "preview_url": "https://example.com/preview1.mp3",
        }
    ])
    return provider


@pytest.fixture
def mock_ai_factory(mock_tts_provider):
    """Mock AI Factory"""
    factory = MagicMock()
    factory.get_tts_provider = MagicMock(return_value=mock_tts_provider)
    return factory


@pytest.fixture
def mock_storage_service():
    """Mock Storage Service"""
    return MagicMock(spec=AbstractStorageService)


@pytest.fixture
def mock_cache_service():
    """Mock Cache Service"""
    return MagicMock(spec=CacheService)


@pytest.fixture
def mock_event_bus():
    """Mock Event Bus"""
    return MagicMock(spec=EventBus)


@pytest.mark.asyncio
@pytest.mark.usefixtures("setup_test_database")
async def test_create_voice_clone(db_session: AsyncSession, mock_tts_provider, mock_ai_factory, mock_storage_service, mock_cache_service, mock_event_bus):
    """Voice Clone 생성 테스트"""
    user_id = uuid.uuid4()
    audio_file = b"fake audio data"
    
    service = TTSService(
        audio_repo=AudioRepository(db_session),
        voice_repo=VoiceRepository(db_session),
        storage_service=mock_storage_service,
        ai_factory=mock_ai_factory,
        db_session=db_session,
        cache_service=mock_cache_service,
        event_bus=mock_event_bus,
    )
    
    # Voice Clone 생성
    voice = await service.create_voice_clone(
        user_id=user_id,
        name="Test Voice",
        audio_file=audio_file,
        visibility=VoiceVisibility.PRIVATE,
    )
    
    await db_session.commit()
    
    # 검증
    assert voice is not None
    assert voice.user_id == user_id
    assert voice.elevenlabs_voice_id == "elevenlabs_voice_123"
    assert voice.name == "Test Voice"
    assert voice.language == "en"
    assert voice.gender == "male"
    assert voice.category == "cloned"
    assert voice.visibility == VoiceVisibility.PRIVATE
    assert voice.status == VoiceStatus.PROCESSING
    assert voice.preview_url is None  # 초기에는 None
    assert voice.meta_data is not None
    assert "description" in voice.meta_data
    assert "labels" in voice.meta_data
    
    # Redis 큐에 추가되었는지 확인
    queued_items = await service.voice_queue.get_all()
    assert str(voice.id) in queued_items
    
    # 정리
    await service.voice_queue.close()


@pytest.mark.asyncio
@pytest.mark.usefixtures("setup_test_database")
async def test_create_voice_clone_all_fields(db_session: AsyncSession, mock_tts_provider, mock_ai_factory, mock_storage_service, mock_cache_service, mock_event_bus):
    """Voice Clone 생성 시 모든 필드 기입 테스트"""
    user_id = uuid.uuid4()
    audio_file = b"fake audio data"
    
    # Mock Provider가 더 상세한 정보 반환
    mock_tts_provider.clone_voice = AsyncMock(return_value={
        "voice_id": "elevenlabs_voice_456",
        "name": "Complete Voice",
        "language": "ko",
        "gender": "female",
        "category": "cloned",
        "preview_url": None,
        "description": "Complete description",
        "labels": {
            "language": "ko",
            "gender": "female",
            "accent": "neutral",
        },
    })
    
    service = TTSService(
        audio_repo=AudioRepository(db_session),
        voice_repo=VoiceRepository(db_session),
        storage_service=mock_storage_service,
        ai_factory=mock_ai_factory,
        db_session=db_session,
        cache_service=mock_cache_service,
        event_bus=mock_event_bus,
    )
    
    voice = await service.create_voice_clone(
        user_id=user_id,
        name="Complete Voice",
        audio_file=audio_file,
        visibility=VoiceVisibility.PUBLIC,
        description="Custom description",
    )
    
    await db_session.commit()
    
    # 모든 필드가 올바르게 기입되었는지 확인
    assert voice.elevenlabs_voice_id == "elevenlabs_voice_456"
    assert voice.name == "Complete Voice"
    assert voice.language == "ko"
    assert voice.gender == "female"
    assert voice.category == "cloned"
    assert voice.visibility == VoiceVisibility.PUBLIC
    assert voice.meta_data["description"] == "Complete description"
    assert voice.meta_data["labels"]["accent"] == "neutral"
    
    await service.voice_queue.close()


@pytest.mark.asyncio
@pytest.mark.usefixtures("setup_test_database")
async def test_get_voices_user_specific(db_session: AsyncSession, mock_tts_provider, mock_ai_factory, mock_storage_service, mock_cache_service, mock_event_bus):
    """사용자별 Voice 조회 테스트"""
    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    
    voice_repo = VoiceRepository(db_session)
    
    # 사용자 개인 Voice
    private_voice = await voice_repo.create(
        user_id=user_id,
        elevenlabs_voice_id="private_voice",
        name="Private Voice",
        visibility=VoiceVisibility.PRIVATE,
        status=VoiceStatus.COMPLETED,
    )
    
    # 다른 사용자의 공개 Voice
    public_voice = await voice_repo.create(
        user_id=other_user_id,
        elevenlabs_voice_id="public_voice",
        name="Public Voice",
        visibility=VoiceVisibility.PUBLIC,
        status=VoiceStatus.COMPLETED,
    )
    
    # 기본 Voice
    default_voice = await voice_repo.create(
        user_id=other_user_id,
        elevenlabs_voice_id="default_voice",
        name="Default Voice",
        visibility=VoiceVisibility.DEFAULT,
        status=VoiceStatus.COMPLETED,
    )
    
    await db_session.commit()
    
    service = TTSService(
        audio_repo=AudioRepository(db_session),
        voice_repo=voice_repo,
        storage_service=mock_storage_service,
        ai_factory=mock_ai_factory,
        db_session=db_session,
        cache_service=mock_cache_service,
        event_bus=mock_event_bus,
    )
    
    # 사용자별 Voice 조회
    voices = await service.get_voices(user_id=user_id)
    
    # 개인 + 공개 + 기본 + Premade Voice 포함 확인
    voice_ids = {v["voice_id"] for v in voices}
    assert "private_voice" in voice_ids
    assert "public_voice" in voice_ids
    assert "default_voice" in voice_ids
    assert "premade_1" in voice_ids  # Mock에서 반환한 premade voice
    
    # 각 Voice의 속성 확인
    private_voice_data = next(v for v in voices if v["voice_id"] == "private_voice")
    assert private_voice_data["visibility"] == "private"
    assert private_voice_data["status"] == "completed"
    assert private_voice_data["is_custom"] is True
    
    premade_voice_data = next(v for v in voices if v["voice_id"] == "premade_1")
    assert premade_voice_data["visibility"] == "default"
    assert premade_voice_data["status"] == "completed"
    assert premade_voice_data["is_custom"] is False
    
    await service.voice_queue.close()

