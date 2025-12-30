"""
Abstract Difficulty Validator Interface
Base class for all language-specific validators
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Type

# Deferred registration to avoid circular imports
_PENDING_REGISTRATIONS: List[tuple] = []


def register_validator(code: str):
    """
    Decorator for auto-registration of validators

    Usage:
        @register_validator("ko")
        class KoreanValidator(AbstractDifficultyValidator):
            ...
    """

    def decorator(cls: Type["AbstractDifficultyValidator"]):
        _PENDING_REGISTRATIONS.append((code, cls))
        return cls

    return decorator


def apply_registrations(factory_cls):
    """
    Apply pending registrations to factory
    Called after factory is initialized to avoid circular imports
    """
    for code, cls in _PENDING_REGISTRATIONS:
        factory_cls.register(code, cls)
    _PENDING_REGISTRATIONS.clear()


@dataclass
class ValidationResult:
    """Validation result with metrics"""

    is_valid: bool
    score: float  # Primary metric score
    metrics: Dict[str, Any]  # All computed metrics
    message: Optional[str] = None  # Human-readable message


class AbstractDifficultyValidator(ABC):
    """
    Abstract base class for language-specific validators

    Each validator implements language-appropriate metrics:
    - English: Flesch-Kincaid Grade Level
    - etc.

    Input format: pages (List[List[str]]) - 2D array of sentences per page
    This preserves the original dialogues structure and allows accurate sentence counting.
    """

    @property
    @abstractmethod
    def language_code(self) -> str:
        """Return the language code this validator handles"""
        pass

    @abstractmethod
    def validate(self, pages: List[List[str]], level: int) -> ValidationResult:
        """
        Validate text difficulty against expected level

        Args:
            pages: 2D array of sentences per page (original dialogues structure)
            level: Expected difficulty level (1, 2, 3)

        Returns:
            ValidationResult with is_valid and detailed metrics
        """
        pass

    @abstractmethod
    def get_stats(self, pages: List[List[str]]) -> Dict[str, Any]:
        """
        Compute text statistics for debugging/logging

        Returns language-specific metrics
        """
        pass

    def get_level_ranges(self, level: int) -> Dict[str, tuple]:
        """
        Return expected metric ranges for the level
        Override in subclass
        """
        return {}
