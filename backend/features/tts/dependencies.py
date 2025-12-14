"""
TTS Dependencies
TTSProducer 의존성 주입 (storybook.dependencies에서 관리)

Note: TTSProducer는 storybook feature에서 주로 사용되므로,
      실제 싱글톤 관리는 backend.features.storybook.dependencies에서 수행합니다.
      이 모듈은 하위 호환성을 위한 re-export만 제공합니다.
"""

from backend.features.storybook.dependencies import (
    get_tts_producer,
    set_tts_producer,
)

__all__ = ["get_tts_producer", "set_tts_producer"]
