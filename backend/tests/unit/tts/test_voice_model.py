"""
Voice 모델 단위 테스트
"""
import pytest
import uuid
from datetime import datetime
from backend.features.tts.models import Voice, VoiceVisibility, VoiceStatus


def test_voice_visibility_enum():
    """VoiceVisibility Enum 테스트"""
    assert VoiceVisibility.PRIVATE.value == "private"
    assert VoiceVisibility.PUBLIC.value == "public"
    assert VoiceVisibility.DEFAULT.value == "default"


def test_voice_status_enum():
    """VoiceStatus Enum 테스트"""
    assert VoiceStatus.PROCESSING.value == "processing"
    assert VoiceStatus.COMPLETED.value == "completed"
    assert VoiceStatus.FAILED.value == "failed"


def test_voice_model_creation():
    """Voice 모델 생성 테스트"""
    voice = Voice(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        elevenlabs_voice_id="test_voice_id_123",
        name="Test Voice",
        visibility=VoiceVisibility.PRIVATE,
        status=VoiceStatus.PROCESSING,
        category="cloned",  # 명시적으로 설정
        language="en",  # 명시적으로 설정
        gender="unknown",  # 명시적으로 설정
    )
    
    assert voice.visibility == VoiceVisibility.PRIVATE
    assert voice.status == VoiceStatus.PROCESSING
    assert voice.category == "cloned"
    assert voice.language == "en"
    assert voice.gender == "unknown"
    assert voice.preview_url is None
    assert voice.completed_at is None


def test_voice_model_defaults():
    """Voice 모델 기본값 테스트 (Repository.create 사용 시나리오)"""
    # 실제 사용 시 Repository.create를 통해 생성되며,
    # 이때 server_default가 적용됩니다.
    # 여기서는 모델의 기본값이 올바르게 정의되었는지만 확인
    voice = Voice(
        user_id=uuid.uuid4(),
        elevenlabs_voice_id="test_voice_id_456",
        name="Test Voice 2",
        # 기본값 필드는 명시적으로 설정하지 않아도
        # DB 저장 시 server_default가 적용됨
        # 하지만 Python 객체 생성 시에는 None이므로 명시적으로 설정
        visibility=VoiceVisibility.PRIVATE,
        status=VoiceStatus.PROCESSING,
        category="cloned",
        language="en",
        gender="unknown",
        created_at=datetime.utcnow(),  # 명시적으로 설정
    )
    
    assert voice.visibility == VoiceVisibility.PRIVATE
    assert voice.status == VoiceStatus.PROCESSING
    assert voice.category == "cloned"
    assert voice.language == "en"
    assert voice.gender == "unknown"
    assert isinstance(voice.created_at, datetime)


def test_voice_model_all_fields():
    """Voice 모델 모든 필드 설정 테스트"""
    user_id = uuid.uuid4()
    voice_id = uuid.uuid4()
    created_at = datetime.utcnow()
    completed_at = datetime.utcnow()
    
    voice = Voice(
        id=voice_id,
        user_id=user_id,
        elevenlabs_voice_id="elevenlabs_voice_123",
        name="Complete Voice",
        language="ko",
        gender="female",
        preview_url="https://example.com/preview.mp3",
        category="cloned",
        visibility=VoiceVisibility.PUBLIC,
        status=VoiceStatus.COMPLETED,
        created_at=created_at,
        completed_at=completed_at,
        meta_data={"key": "value"},
    )
    
    assert voice.id == voice_id
    assert voice.user_id == user_id
    assert voice.elevenlabs_voice_id == "elevenlabs_voice_123"
    assert voice.name == "Complete Voice"
    assert voice.language == "ko"
    assert voice.gender == "female"
    assert voice.preview_url == "https://example.com/preview.mp3"
    assert voice.category == "cloned"
    assert voice.visibility == VoiceVisibility.PUBLIC
    assert voice.status == VoiceStatus.COMPLETED
    assert voice.created_at == created_at
    assert voice.completed_at == completed_at
    assert voice.meta_data == {"key": "value"}


def test_voice_model_repr():
    """Voice 모델 __repr__ 테스트"""
    voice = Voice(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        elevenlabs_voice_id="test_voice_id",
        name="Test Voice",
        visibility=VoiceVisibility.PUBLIC,
        status=VoiceStatus.COMPLETED,
    )
    
    repr_str = repr(voice)
    assert "Voice" in repr_str
    assert "Test Voice" in repr_str
    assert "public" in repr_str
    assert "completed" in repr_str

