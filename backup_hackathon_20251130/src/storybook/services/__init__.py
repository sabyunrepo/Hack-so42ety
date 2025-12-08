"""
Services Module
Feature-first architecture for service layer
"""

from .book_orchestrator_service import BookOrchestratorService
from .tts_service import TtsService
from .story_generator_service import StoryGeneratorService
from .image_generator_service import ImageGeneratorService
from .video_generator_service import VideoGeneratorService

# Backward compatibility alias
BookService = BookOrchestratorService

__all__ = [
    "BookOrchestratorService",
    "TtsService",
    "StoryGeneratorService",
    "ImageGeneratorService",
    "VideoGeneratorService",
    "BookService",
]
