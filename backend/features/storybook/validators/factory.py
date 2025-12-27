"""
Validator Factory
Creates appropriate validator based on language code using Strategy pattern
"""

from typing import Dict, Type, Optional
import logging

from .base import AbstractDifficultyValidator

logger = logging.getLogger(__name__)


class ValidatorFactory:
    """
    Factory for creating language-specific validators

    Usage:
        validator = ValidatorFactory.get_validator("ko")
        if validator:
            result = validator.validate(text, level=2)
    """

    _validators: Dict[str, Type[AbstractDifficultyValidator]] = {}
    _instances: Dict[str, AbstractDifficultyValidator] = {}

    @classmethod
    def register(cls, code: str, validator_class: Type[AbstractDifficultyValidator]):
        """Register a new validator type"""
        cls._validators[code] = validator_class
        logger.debug(f"[ValidatorFactory] Registered validator for '{code}'")

    @classmethod
    def get_validator(
        cls, language_code: str
    ) -> Optional[AbstractDifficultyValidator]:
        """
        Get validator instance for language

        Args:
            language_code: Language code (en, ko, zh, vi, ru, th)

        Returns:
            Validator instance or None if language not supported
            (caller should skip validation if None)
        """
        if language_code not in cls._validators:
            logger.warning(
                f"[ValidatorFactory] No validator registered for language: {language_code}"
            )
            return None

        # Singleton pattern for validators
        if language_code not in cls._instances:
            cls._instances[language_code] = cls._validators[language_code]()
            logger.debug(
                f"[ValidatorFactory] Created validator instance for '{language_code}'"
            )

        return cls._instances[language_code]

    @classmethod
    def get_supported_languages(cls) -> list[str]:
        """Return list of languages with registered validators"""
        return list(cls._validators.keys())

    @classmethod
    def is_supported(cls, language_code: str) -> bool:
        """Check if a language has a registered validator"""
        return language_code in cls._validators
