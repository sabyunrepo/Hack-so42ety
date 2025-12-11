"""
AI Provider Factory
설정에 따라 적절한 AI Provider 인스턴스를 생성
"""

from functools import lru_cache
from typing import Optional

from ...core.config import settings
from .base import (
    StoryGenerationProvider,
    ImageGenerationProvider,
    TTSProvider,
    VideoGenerationProvider,
    AIProviderType,
    TTSProviderType,
    VideoProviderType,
)
from .providers.google_ai import GoogleAIProvider
from .providers.elevenlabs_tts import ElevenLabsTTSProvider
from .providers.kling import KlingVideoProvider
from .providers.runware_video import RunwareVideoProvider
from .providers.custom_model import CustomModelProvider


class AIProviderFactory:
    """AI Provider Factory"""

    @staticmethod
    def get_story_provider(provider_type: Optional[str] = None) -> StoryGenerationProvider:
        """스토리 생성 Provider 반환"""
        ptype = provider_type or settings.ai_story_provider
        
        if ptype == AIProviderType.GOOGLE:
            return GoogleAIProvider()
        elif ptype == AIProviderType.CUSTOM:
            return CustomModelProvider()
        else:
            # Default to Google if unknown or not specified
            return GoogleAIProvider()

    @staticmethod
    def get_image_provider(provider_type: Optional[str] = None) -> ImageGenerationProvider:
        """이미지 생성 Provider 반환"""
        ptype = provider_type or settings.ai_image_provider
        
        if ptype == AIProviderType.GOOGLE:
            return GoogleAIProvider()
        else:
            return GoogleAIProvider()

    @staticmethod
    def get_tts_provider(provider_type: Optional[str] = None) -> TTSProvider:
        """TTS Provider 반환"""
        ptype = provider_type or settings.ai_tts_provider
        
        if ptype == TTSProviderType.ELEVENLABS:
            return ElevenLabsTTSProvider()
        else:
            return ElevenLabsTTSProvider()

    @staticmethod
    def get_video_provider(provider_type: Optional[str] = None) -> VideoGenerationProvider:
        """비디오 생성 Provider 반환"""
        ptype = provider_type or settings.ai_video_provider

        if ptype == VideoProviderType.KLING:
            return KlingVideoProvider()
        elif ptype == VideoProviderType.RUNWARE:
            return RunwareVideoProvider()
        else:
            return KlingVideoProvider()


@lru_cache()
def get_ai_factory() -> AIProviderFactory:
    """Factory 싱글톤 반환"""
    return AIProviderFactory()
