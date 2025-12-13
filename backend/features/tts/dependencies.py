from fastapi import Depends
from backend.core.dependencies import get_event_bus
from backend.core.events.redis_streams_bus import RedisStreamsEventBus
from backend.features.tts.producer import TTSProducer

def get_tts_producer(
    event_bus: RedisStreamsEventBus = Depends(get_event_bus)
) -> TTSProducer:
    """TTS Producer 의존성 주입"""
    return TTSProducer(event_bus=event_bus)
