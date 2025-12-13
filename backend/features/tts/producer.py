import uuid
import logging
from typing import Dict, Any

from backend.core.events.bus import EventBus
from backend.core.events.types import EventType

logger = logging.getLogger(__name__)

class TTSProducer:
    """
    TTS 작업 생성자 (Producer)
    Redis Streams에 TTS 생성 요청을 발행합니다.
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    async def enqueue_tts_task(self, dialogue_audio_id: uuid.UUID, text: str) -> None:
        """
        TTS 생성 작업 큐 등록
        
        Args:
            dialogue_audio_id: DialogueAudio 테이블의 PK (UUID)
            text: 변환할 텍스트
        """
        payload = {
            "uuid": str(dialogue_audio_id),
            "text": text
        }
        
        try:
            await self.event_bus.publish(EventType.TTS_CREATION, payload)
            logger.info(f"TTS Task Enqueued: uuid={dialogue_audio_id}")
        except Exception as e:
            logger.error(f"Failed to enqueue TTS task: {e}")
            raise
