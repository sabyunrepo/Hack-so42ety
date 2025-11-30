"""
AI Provider Switching Integration Test
"""

import pytest
import os
from unittest.mock import patch

from backend.infrastructure.ai.factory import AIProviderFactory
from backend.infrastructure.ai.base import AIProviderType
from backend.infrastructure.ai.providers.google_ai import GoogleAIProvider
from backend.infrastructure.ai.providers.custom_model import CustomModelProvider
from backend.core.config import settings


class TestAIProviderSwitching:
    def test_provider_switching_via_env(self):
        # Mock settings to simulate env var change
        with patch.object(settings, "ai_story_provider", "google"):
            provider = AIProviderFactory.get_story_provider()
            assert isinstance(provider, GoogleAIProvider)

        with patch.object(settings, "ai_story_provider", "custom"):
            provider = AIProviderFactory.get_story_provider()
            assert isinstance(provider, CustomModelProvider)
