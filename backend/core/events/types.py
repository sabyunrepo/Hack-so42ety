"""
Event Types
이벤트 타입 정의
"""

from enum import Enum
from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any
import uuid


class EventType(str, Enum):
    """이벤트 타입"""
    VOICE_CREATED = "voice.created"
    VOICE_UPDATED = "voice.updated"
    VOICE_DELETED = "voice.deleted"
    TTS_CREATION = "tts.creation"
    MEDIA_OPTIMIZATION = "media.optimization"


class Event(BaseModel):
    """이벤트 기본 구조"""
    type: EventType
    payload: Dict[str, Any]
    timestamp: datetime
    source: str
    event_id: str
    
    @classmethod
    def create(
        cls,
        event_type: EventType,
        payload: Dict[str, Any],
        source: str = "unknown"
    ) -> "Event":
        """
        이벤트 생성
        
        Args:
            event_type: 이벤트 타입
            payload: 이벤트 페이로드
            source: 이벤트 발생 소스
        
        Returns:
            Event: 생성된 이벤트
        """
        return cls(
            type=event_type,
            payload=payload,
            timestamp=datetime.utcnow(),
            source=source,
            event_id=str(uuid.uuid4())
        )

