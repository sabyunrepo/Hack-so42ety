"""
AI Provider Factory Unit Tests
"""

import pytest
from unittest.mock import patch, MagicMock

from backend.infrastructure.ai.factory import AIProviderFactory, get_ai_factory
from backend.infrastructure.ai.base import (
    AIProviderType,
    TTSProviderType,
    VideoProviderType,
)
from backend.infrastructure.ai.providers.google_ai import GoogleAIProvider
from backend.infrastructure.ai.providers.elevenlabs_tts import ElevenLabsTTSProvider
from backend.infrastructure.ai.providers.kling import KlingVideoProvider
from backend.infrastructure.ai.providers.custom_model import CustomModelProvider


class TestAIProviderFactory:
    def test_get_story_provider_google(self):
        provider = AIProviderFactory.get_story_provider(AIProviderType.GOOGLE)
        assert isinstance(provider, GoogleAIProvider)

    def test_get_story_provider_custom(self):
        provider = AIProviderFactory.get_story_provider(AIProviderType.CUSTOM)
        assert isinstance(provider, CustomModelProvider)

    def test_get_story_provider_default(self):
        # Default should be Google (as per implementation)
        provider = AIProviderFactory.get_story_provider()
        assert isinstance(provider, GoogleAIProvider)

    def test_get_image_provider(self):
        provider = AIProviderFactory.get_image_provider(AIProviderType.GOOGLE)
        assert isinstance(provider, GoogleAIProvider)

    def test_get_tts_provider(self):
        provider = AIProviderFactory.get_tts_provider(TTSProviderType.ELEVENLABS)
        assert isinstance(provider, ElevenLabsTTSProvider)

    def test_get_video_provider(self):
        provider = AIProviderFactory.get_video_provider(VideoProviderType.KLING)
        assert isinstance(provider, KlingVideoProvider)

    def test_singleton_factory(self):
        factory1 = get_ai_factory()
        factory2 = get_ai_factory()
        assert factory1 is factory2
