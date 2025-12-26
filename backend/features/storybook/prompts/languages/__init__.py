"""
Language Configuration Registry
Multi-language prompt support with per-language modules
"""

from typing import Dict, Type

from .base import BaseLanguageConfig, LanguageMetadata, LevelExample

# Registry for all language configurations
LANGUAGE_REGISTRY: Dict[str, Type[BaseLanguageConfig]] = {}


def register_language(code: str):
    """
    Decorator to register a language configuration

    Usage:
        @register_language("ko")
        class KoreanConfig(BaseLanguageConfig):
            ...
    """

    def decorator(cls: Type[BaseLanguageConfig]):
        LANGUAGE_REGISTRY[code] = cls
        return cls

    return decorator


def get_language_config(code: str) -> BaseLanguageConfig:
    """
    Get language configuration instance by code
    Falls back to English if not found
    """
    config_cls = LANGUAGE_REGISTRY.get(code)
    if config_cls is None:
        from .english import EnglishConfig

        return EnglishConfig()
    return config_cls()


def get_supported_languages() -> list[str]:
    """Return list of supported language codes"""
    return list(LANGUAGE_REGISTRY.keys())


# Public exports
__all__ = [
    "BaseLanguageConfig",
    "LanguageMetadata",
    "LevelExample",
    "LANGUAGE_REGISTRY",
    "register_language",
    "get_language_config",
    "get_supported_languages",
]

# Auto-import all language modules to trigger registration
from . import english, korean, chinese, vietnamese, russian, thai
