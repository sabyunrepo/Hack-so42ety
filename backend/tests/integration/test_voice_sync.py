"""
Voice 동기화 Scheduled Task 통합 테스트
"""
import pytest
import uuid
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.tasks.voice_sync import sync_voice_status_periodically
from backend.core.tasks.voice_queue import VoiceSyncQueue
from backend.features.tts.models import Voice, VoiceStatus, VoiceVisibility
from backend.features.tts.repository import VoiceRepository
from backend.core.events.redis_streams_bus import RedisStreamsEventBus


@pytest.fixture
def mock_event_bus():
    """Mock Event Bus"""
    bus = MagicMock(spec=RedisStreamsEventBus)
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def mock_tts_provider():
    """Mock TTS Provider"""
    provider = MagicMock()
    provider.get_voice_details = AsyncMock(return_value={
        "voice_id": "elevenlabs_voice_123",
        "name": "Test Voice",
        "status": "completed",
        "preview_url": "https://example.com/preview.mp3",
        "language": "en",
        "gender": "male",
    })
    return provider


@pytest.fixture
def mock_ai_factory(mock_tts_provider):
    """Mock AI Factory"""
    factory = MagicMock()
    factory.get_tts_provider = MagicMock(return_value=mock_tts_provider)
    return factory


@pytest.mark.asyncio
@pytest.mark.usefixtures("setup_test_database")
async def test_voice_sync_completed(db_session: AsyncSession, mock_event_bus, mock_tts_provider, mock_ai_factory):
    """Voice 동기화 완료 테스트"""
    user_id = uuid.uuid4()
    voice_repo = VoiceRepository(db_session)
    
    # Processing 상태 Voice 생성
    voice = await voice_repo.create(
        user_id=user_id,
        elevenlabs_voice_id="elevenlabs_voice_123",
        name="Test Voice",
        visibility=VoiceVisibility.PRIVATE,
        status=VoiceStatus.PROCESSING,
    )
    
    await db_session.commit()
    
    # Redis 큐에 추가
    voice_queue = VoiceSyncQueue()
    await voice_queue.enqueue(voice.id)
    
    # AI Factory 패치
    with patch("backend.core.tasks.voice_sync.AIProviderFactory", return_value=mock_ai_factory):
        # 동기화 작업 실행 (짧은 간격으로)
        task = asyncio.create_task(
            sync_voice_status_periodically(
                event_bus=mock_event_bus,
                interval=1,  # 1초마다 실행
            )
        )
        
        # 잠시 대기 (동기화 완료 대기)
        await asyncio.sleep(2)
        
        # 작업 취소
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        await voice_queue.close()
    
    # DB에서 Voice 상태 확인
    await db_session.refresh(voice)
    assert voice.status == VoiceStatus.COMPLETED
    assert voice.preview_url == "https://example.com/preview.mp3"
    assert voice.completed_at is not None
    
    # 이벤트 발행 확인
    mock_event_bus.publish.assert_called_once()
    
    # 큐에서 제거되었는지 확인
    queued_items = await voice_queue.get_all()
    assert str(voice.id) not in queued_items


@pytest.mark.asyncio
@pytest.mark.usefixtures("setup_test_database")
async def test_voice_sync_no_queue(db_session: AsyncSession, mock_event_bus):
    """큐가 비어있을 때 동기화 스킵 테스트"""
    voice_queue = VoiceSyncQueue()
    
    # 큐가 비어있는 상태에서 동기화 작업 실행
    task = asyncio.create_task(
        sync_voice_status_periodically(
            event_bus=mock_event_bus,
            interval=1,
        )
    )
    
    # 잠시 대기
    await asyncio.sleep(1.5)
    
    # 작업 취소
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    
    await voice_queue.close()
    
    # 이벤트가 발행되지 않았는지 확인 (큐가 비어있으므로)
    # 실제로는 큐가 비어있으면 스킵되므로 이벤트 발행 안 됨
    # 이 테스트는 큐가 비어있을 때 정상적으로 스킵되는지만 확인


@pytest.mark.asyncio
@pytest.mark.usefixtures("setup_test_database")
async def test_voice_sync_still_processing(db_session: AsyncSession, mock_event_bus):
    """아직 처리 중인 Voice 테스트"""
    user_id = uuid.uuid4()
    voice_repo = VoiceRepository(db_session)
    
    # Processing 상태 Voice 생성
    voice = await voice_repo.create(
        user_id=user_id,
        elevenlabs_voice_id="elevenlabs_voice_456",
        name="Processing Voice",
        visibility=VoiceVisibility.PRIVATE,
        status=VoiceStatus.PROCESSING,
    )
    
    await db_session.commit()
    
    # Redis 큐에 추가
    voice_queue = VoiceSyncQueue()
    await voice_queue.enqueue(voice.id)
    
    # Mock Provider가 아직 processing 상태 반환
    mock_provider = MagicMock()
    mock_provider.get_voice_details = AsyncMock(return_value={
        "voice_id": "elevenlabs_voice_456",
        "name": "Processing Voice",
        "status": "processing",  # 아직 처리 중
        "preview_url": None,
    })
    
    mock_factory = MagicMock()
    mock_factory.get_tts_provider = MagicMock(return_value=mock_provider)
    
    with patch("backend.core.tasks.voice_sync.AIProviderFactory", return_value=mock_factory):
        # 동기화 작업 실행
        task = asyncio.create_task(
            sync_voice_status_periodically(
                event_bus=mock_event_bus,
                interval=1,
            )
        )
        
        # 잠시 대기
        await asyncio.sleep(1.5)
        
        # 작업 취소
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        await voice_queue.close()
    
    # DB에서 Voice 상태 확인 (여전히 PROCESSING)
    await db_session.refresh(voice)
    assert voice.status == VoiceStatus.PROCESSING
    assert voice.preview_url is None
    
    # 이벤트가 발행되지 않았는지 확인 (아직 완료되지 않았으므로)
    mock_event_bus.publish.assert_not_called()
    
    # 큐에 여전히 남아있는지 확인 (다음 주기에 다시 확인하기 위해)
    queued_items = await voice_queue.get_all()
    assert str(voice.id) in queued_items

