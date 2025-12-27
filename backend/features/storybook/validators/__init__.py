"""
Difficulty Validators
Provides language-specific difficulty validation using Strategy pattern

Currently supported:
- English: Flesch-Kincaid Grade Level (academically validated)

Other languages rely on prompt-based difficulty control.

Architecture:
- Auto-scan pattern: New validators are automatically discovered
- Deferred registration: Avoids circular imports
- Error isolation: Individual module failures don't crash the system
"""

import importlib
import pkgutil
import logging
from pathlib import Path

from .base import AbstractDifficultyValidator, ValidationResult, apply_registrations
from .factory import ValidatorFactory

logger = logging.getLogger(__name__)

# Auto-scan validator modules (exclude base, factory, __init__)
_EXCLUDED_MODULES = {"__init__", "base", "factory"}
_package_dir = Path(__file__).parent

for _module_info in pkgutil.iter_modules([str(_package_dir)]):
    if _module_info.name in _EXCLUDED_MODULES:
        continue
    try:
        importlib.import_module(f".{_module_info.name}", __package__)
        logger.debug(f"[Validators] Loaded module: {_module_info.name}")
    except Exception as e:
        # Individual module failure doesn't crash the system
        logger.error(f"[Validators] Failed to load {_module_info.name}: {e}")

# Apply deferred registrations to factory
apply_registrations(ValidatorFactory)

# Log registered validators at startup
logger.info(f"[Validators] Registered: {ValidatorFactory.get_supported_languages()}")

# Note: Other language validators (ko, zh, vi, ru, th) are not implemented
# because there are no academically validated readability formulas.
# For these languages, difficulty control relies on prompts.
# ValidatorFactory.get_validator() returns None for unsupported languages.

__all__ = [
    "AbstractDifficultyValidator",
    "ValidationResult",
    "ValidatorFactory",
]
