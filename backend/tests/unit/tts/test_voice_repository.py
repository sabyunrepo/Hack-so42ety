"""
VoiceRepository 단위 테스트
"""
import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from backend.features.tts.repository import VoiceRepository
from backend.features.tts.models import Voice, VoiceVisibility, VoiceStatus


@pytest.mark.asyncio
@pytest.mark.usefixtures("setup_test_database")
async def test_get_user_voices(db_session: AsyncSession):
    """사용자별 Voice 조회 테스트"""
    user_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    
    repo = VoiceRepository(db_session)
    
    # 사용자 개인 Voice 생성
    private_voice = await repo.create(
        user_id=user_id,
        elevenlabs_voice_id="private_voice_id",
        name="Private Voice",
        visibility=VoiceVisibility.PRIVATE,
        status=VoiceStatus.COMPLETED,
    )
    
    # 다른 사용자의 공개 Voice 생성
    public_voice = await repo.create(
        user_id=other_user_id,
        elevenlabs_voice_id="public_voice_id",
        name="Public Voice",
        visibility=VoiceVisibility.PUBLIC,
        status=VoiceStatus.COMPLETED,
    )
    
    # 기본 Voice 생성
    default_voice = await repo.create(
        user_id=other_user_id,
        elevenlabs_voice_id="default_voice_id",
        name="Default Voice",
        visibility=VoiceVisibility.DEFAULT,
        status=VoiceStatus.COMPLETED,
    )
    
    # 처리 중인 Voice는 제외되어야 함
    processing_voice = await repo.create(
        user_id=user_id,
        elevenlabs_voice_id="processing_voice_id",
        name="Processing Voice",
        visibility=VoiceVisibility.PRIVATE,
        status=VoiceStatus.PROCESSING,
    )
    
    await db_session.commit()
    
    # 사용자 Voice 조회
    voices = await repo.get_user_voices(user_id)
    
    # 개인 + 공개 + 기본 Voice 모두 포함되어야 함
    voice_ids = {v.elevenlabs_voice_id for v in voices}
    assert "private_voice_id" in voice_ids
    assert "public_voice_id" in voice_ids
    assert "default_voice_id" in voice_ids
    # 처리 중인 Voice는 제외되어야 함 (COMPLETED만 조회)
    assert "processing_voice_id" not in voice_ids


@pytest.mark.asyncio
@pytest.mark.usefixtures("setup_test_database")
async def test_get_by_status(db_session: AsyncSession):
    """상태별 Voice 조회 테스트"""
    user_id = uuid.uuid4()
    repo = VoiceRepository(db_session)
    
    # 다양한 상태의 Voice 생성
    processing_voice = await repo.create(
        user_id=user_id,
        elevenlabs_voice_id="processing_1",
        name="Processing 1",
        status=VoiceStatus.PROCESSING,
    )
    
    completed_voice = await repo.create(
        user_id=user_id,
        elevenlabs_voice_id="completed_1",
        name="Completed 1",
        status=VoiceStatus.COMPLETED,
    )
    
    failed_voice = await repo.create(
        user_id=user_id,
        elevenlabs_voice_id="failed_1",
        name="Failed 1",
        status=VoiceStatus.FAILED,
    )
    
    await db_session.commit()
    
    # 상태별 조회
    processing_voices = await repo.get_by_status(VoiceStatus.PROCESSING)
    assert len(processing_voices) >= 1
    assert any(v.elevenlabs_voice_id == "processing_1" for v in processing_voices)
    
    completed_voices = await repo.get_by_status(VoiceStatus.COMPLETED)
    assert len(completed_voices) >= 1
    assert any(v.elevenlabs_voice_id == "completed_1" for v in completed_voices)
    
    failed_voices = await repo.get_by_status(VoiceStatus.FAILED)
    assert len(failed_voices) >= 1
    assert any(v.elevenlabs_voice_id == "failed_1" for v in failed_voices)


@pytest.mark.asyncio
@pytest.mark.usefixtures("setup_test_database")
async def test_get_by_elevenlabs_id(db_session: AsyncSession):
    """ElevenLabs Voice ID로 조회 테스트"""
    user_id = uuid.uuid4()
    repo = VoiceRepository(db_session)
    
    voice = await repo.create(
        user_id=user_id,
        elevenlabs_voice_id="test_elevenlabs_id_123",
        name="Test Voice",
    )
    
    await db_session.commit()
    
    # ElevenLabs ID로 조회
    found_voice = await repo.get_by_elevenlabs_id("test_elevenlabs_id_123")
    assert found_voice is not None
    assert found_voice.id == voice.id
    assert found_voice.elevenlabs_voice_id == "test_elevenlabs_id_123"
    
    # 존재하지 않는 ID 조회
    not_found = await repo.get_by_elevenlabs_id("non_existent_id")
    assert not_found is None


@pytest.mark.asyncio
@pytest.mark.usefixtures("setup_test_database")
async def test_update_status(db_session: AsyncSession):
    """Voice 상태 업데이트 테스트"""
    user_id = uuid.uuid4()
    repo = VoiceRepository(db_session)
    
    voice = await repo.create(
        user_id=user_id,
        elevenlabs_voice_id="test_voice_update",
        name="Test Voice",
        status=VoiceStatus.PROCESSING,
    )
    
    await db_session.commit()
    
    # 상태 업데이트
    updated_voice = await repo.update_status(
        voice_id=voice.id,
        status=VoiceStatus.COMPLETED,
        preview_url="https://example.com/preview.mp3",
    )
    
    assert updated_voice is not None
    assert updated_voice.status == VoiceStatus.COMPLETED
    assert updated_voice.preview_url == "https://example.com/preview.mp3"
    assert updated_voice.completed_at is not None
    
    await db_session.commit()
    
    # DB에서 다시 조회하여 확인
    refreshed_voice = await repo.get(voice.id)
    assert refreshed_voice.status == VoiceStatus.COMPLETED
    assert refreshed_voice.preview_url == "https://example.com/preview.mp3"

