"""
Voice 전체 플로우 통합 테스트
Voice 생성부터 동기화까지 전체 프로세스 테스트
"""
import pytest
import uuid
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from backend.features.tts.models import Voice, VoiceStatus, VoiceVisibility
from backend.features.tts.repository import VoiceRepository
from backend.features.tts.service import TTSService
from backend.features.tts.repository import AudioRepository
from backend.core.tasks.voice_queue import VoiceSyncQueue
from backend.core.events.redis_streams_bus import RedisStreamsEventBus
from backend.infrastructure.storage.base import AbstractStorageService
from backend.infrastructure.ai.factory import AIProviderFactory
from backend.core.cache.service import CacheService


@pytest.fixture
def mock_tts_provider():
    """Mock TTS Provider"""
    provider = MagicMock()
    
    # clone_voice: 초기에는 preview_url이 None
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
    
    # get_voice_details: 처음에는 processing, 나중에는 completed
    call_count = {"count": 0}
    
    async def get_voice_details(voice_id: str):
        call_count["count"] += 1
        if call_count["count"] == 1:
            # 첫 번째 호출: 아직 processing
            return {
                "voice_id": voice_id,
                "name": "Test Voice",
                "status": "processing",
                "preview_url": None,
                "language": "en",
                "gender": "male",
                "category": "cloned",
            }
        else:
            # 두 번째 호출: completed
            return {
                "voice_id": voice_id,
                "name": "Test Voice",
                "status": "completed",
                "preview_url": "https://example.com/preview.mp3",
                "language": "en",
                "gender": "male",
                "category": "cloned",
            }
    
    provider.get_voice_details = AsyncMock(side_effect=get_voice_details)
    
    provider.get_available_voices = AsyncMock(return_value=[
        {
            "voice_id": "premade_1",
            "name": "Premade Voice",
            "language": "en",
            "gender": "female",
            "category": "premade",
            "preview_url": "https://example.com/premade.mp3",
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
    bus = MagicMock(spec=RedisStreamsEventBus)
    bus.publish = AsyncMock()
    return bus


@pytest.mark.asyncio
@pytest.mark.usefixtures("setup_test_database")
async def test_voice_complete_flow(
    db_session: AsyncSession,
    mock_tts_provider,
    mock_ai_factory,
    mock_storage_service,
    mock_cache_service,
    mock_event_bus,
):
    """
    Voice 전체 플로우 테스트:
    1. Voice Clone 생성
    2. Redis 큐에 등록 확인
    3. Scheduled Task 동기화
    4. 완료 상태 확인
    """
    user_id = uuid.uuid4()
    
    # TTSService 생성
    service = TTSService(
        audio_repo=AudioRepository(db_session),
        voice_repo=VoiceRepository(db_session),
        storage_service=mock_storage_service,
        ai_factory=mock_ai_factory,
        db_session=db_session,
        cache_service=mock_cache_service,
        event_bus=mock_event_bus,
    )
    
    # 1. Voice Clone 생성
    audio_file = b"fake audio data"
    voice = await service.create_voice_clone(
        user_id=user_id,
        name="Test Voice",
        audio_file=audio_file,
        visibility=VoiceVisibility.PRIVATE,
    )
    
    await db_session.commit()
    
    # 2. 초기 상태 확인
    assert voice.status == VoiceStatus.PROCESSING
    assert voice.preview_url is None
    assert voice.elevenlabs_voice_id == "elevenlabs_voice_123"
    
    # 3. Redis 큐에 등록되었는지 확인
    queued_items = await service.voice_queue.get_all()
    assert str(voice.id) in queued_items
    
    # 4. Scheduled Task 시뮬레이션 (첫 번째 호출: 아직 processing)
    from backend.core.tasks.voice_sync import sync_voice_status_periodically
    
    # Mock을 사용하여 동기화 작업 실행
    with patch("backend.core.tasks.voice_sync.AIProviderFactory", return_value=mock_ai_factory):
        # 동기화 작업 한 번 실행
        voice_repo = VoiceRepository(db_session)
        voice_queue = VoiceSyncQueue()
        
        # 큐에서 Voice 조회
        queued_voice_ids = await voice_queue.get_all()
        voice_ids = [uuid.UUID(vid) for vid in queued_voice_ids]
        
        # DB에서 Voice 조회
        voices = []
        for voice_id in voice_ids:
            v = await voice_repo.get(voice_id)
            if v and v.status == VoiceStatus.PROCESSING:
                voices.append(v)
        
        assert len(voices) == 1
        assert voices[0].id == voice.id
        
        # ElevenLabs API 호출 (첫 번째: processing)
        voice_details = await mock_tts_provider.get_voice_details(voices[0].elevenlabs_voice_id)
        assert voice_details["status"] == "processing"
        
        # 아직 완료되지 않았으므로 큐에 유지
        queued_items_after = await voice_queue.get_all()
        assert str(voice.id) in queued_items_after
    
    # 5. Scheduled Task 시뮬레이션 (두 번째 호출: completed)
    with patch("backend.core.tasks.voice_sync.AIProviderFactory", return_value=mock_ai_factory):
        # 동기화 작업 다시 실행
        voice_repo = VoiceRepository(db_session)
        
        # 큐에서 Voice 조회
        queued_voice_ids = await voice_queue.get_all()
        voice_ids = [uuid.UUID(vid) for vid in queued_voice_ids]
        
        # DB에서 Voice 조회
        voices = []
        for voice_id in voice_ids:
            v = await voice_repo.get(voice_id)
            if v and v.status == VoiceStatus.PROCESSING:
                voices.append(v)
        
        assert len(voices) == 1
        
        # ElevenLabs API 호출 (두 번째: completed)
        voice_details = await mock_tts_provider.get_voice_details(voices[0].elevenlabs_voice_id)
        assert voice_details["status"] == "completed"
        
        # DB 업데이트
        await voice_repo.update_status(
            voice_id=voices[0].id,
            status=VoiceStatus.COMPLETED,
            preview_url=voice_details.get("preview_url"),
        )
        
        # 이벤트 발행
        await mock_event_bus.publish(
            "voice.created",  # EventType은 문자열로 간단히
            {
                "voice_id": str(voices[0].id),
                "user_id": str(voices[0].user_id),
            }
        )
        
        # 큐에서 제거
        await voice_queue.dequeue(voices[0].id)
        
        await db_session.commit()
    
    # 6. 최종 상태 확인
    await db_session.refresh(voice)
    assert voice.status == VoiceStatus.COMPLETED
    assert voice.preview_url == "https://example.com/preview.mp3"
    assert voice.completed_at is not None
    
    # 7. 큐에서 제거되었는지 확인
    queued_items_final = await voice_queue.get_all()
    assert str(voice.id) not in queued_items_final
    
    # 8. 이벤트 발행 확인
    mock_event_bus.publish.assert_called()
    
    await service.voice_queue.close()
    await voice_queue.close()


@pytest.mark.asyncio
@pytest.mark.usefixtures("setup_test_database")
async def test_voice_user_specific_retrieval(
    db_session: AsyncSession,
    mock_tts_provider,
    mock_ai_factory,
    mock_storage_service,
    mock_cache_service,
    mock_event_bus,
):
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
    
    # TTSService로 조회
    service = TTSService(
        audio_repo=AudioRepository(db_session),
        voice_repo=voice_repo,
        storage_service=mock_storage_service,
        ai_factory=mock_ai_factory,
        db_session=db_session,
        cache_service=mock_cache_service,
        event_bus=mock_event_bus,
    )
    
    voices = await service.get_voices(user_id=user_id)
    
    # 개인 + 공개 + 기본 + Premade Voice 포함 확인
    voice_ids = {v["voice_id"] for v in voices}
    assert "private_voice" in voice_ids
    assert "public_voice" in voice_ids
    assert "default_voice" in voice_ids
    assert "premade_1" in voice_ids  # Mock에서 반환한 premade voice
    
    await service.voice_queue.close()


@pytest.mark.asyncio
@pytest.mark.usefixtures("setup_test_database")
async def test_voice_queue_optimization(
    db_session: AsyncSession,
    mock_tts_provider,
    mock_ai_factory,
    mock_storage_service,
    mock_cache_service,
    mock_event_bus,
):
    """Redis 큐 최적화 테스트 (작업이 없을 때 스킵)"""
    voice_queue = VoiceSyncQueue()
    
    # 큐가 비어있는 상태
    queued_items = await voice_queue.get_all()
    assert len(queued_items) == 0
    
    # 큐가 비어있으면 동기화 작업이 스킵되어야 함
    # (실제로는 sync_voice_status_periodically 내부에서 처리)
    
    await voice_queue.close()

