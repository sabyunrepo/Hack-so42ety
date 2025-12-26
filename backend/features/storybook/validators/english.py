"""
English Difficulty Validator
Using Flesch-Kincaid Grade Level with accurate sentence counting

FK Grade Level formula:
(0.39 x avg sentence length) + (11.8 x avg syllables/word) - 15.59

Lower scores indicate easier text.
"""

import logging
from typing import Dict, Any, List

import textstat

from backend.core.config import settings
from .base import AbstractDifficultyValidator, ValidationResult, register_validator

logger = logging.getLogger(__name__)


@register_validator("en")
class EnglishValidator(AbstractDifficultyValidator):
    """
    English validator using Flesch-Kincaid metrics

    Input: pages (List[List[str]]) - 2D array preserving original dialogues structure
    This allows accurate sentence counting without relying on punctuation parsing.
    """

    FK_RANGES = {
        1: (0.5, 1.5),  # Level 1 (4-5 years): Very easy text
        2: (2.0, 2.5),  # Level 2 (5-6 years): Easy text
        3: (3.0, 4.0),  # Level 3 (6-8 years): Medium level text
    }

    @property
    def language_code(self) -> str:
        return "en"

    def validate(self, pages: List[List[str]], level: int) -> ValidationResult:
        """
        Validate English text difficulty using Flesch-Kincaid Grade Level

        Args:
            pages: 2D array of sentences per page (original dialogues structure)
            level: Target difficulty level (1, 2, 3)

        Returns:
            ValidationResult with FK score and metrics
        """
        # Flatten and filter empty sentences
        all_sentences = [s for page in pages for s in page if s and s.strip()]
        sentence_count = len(all_sentences)

        if sentence_count == 0:
            logger.warning("[EnglishValidator] Empty pages provided")
            return ValidationResult(
                is_valid=True, score=0.0, metrics={}, message="Empty text"
            )

        # Join for word/syllable statistics (textstat needs full text)
        full_text = " ".join(all_sentences)
        word_count = textstat.lexicon_count(full_text, removepunct=True)
        syllable_count = textstat.syllable_count(full_text)

        if word_count == 0:
            logger.warning("[EnglishValidator] No words found in text")
            return ValidationResult(
                is_valid=True, score=0.0, metrics={}, message="No words"
            )

        # Calculate FK directly using accurate sentence count
        avg_sentence_length = word_count / sentence_count
        avg_syllables_per_word = syllable_count / word_count
        fk_score = 0.39 * avg_sentence_length + 11.8 * avg_syllables_per_word - 15.59

        # Level range validation with tolerance
        min_score, max_score = self.FK_RANGES.get(level, (0, 10))
        fk_tolerance = settings.fk_tolerance
        is_valid = (min_score - fk_tolerance) <= fk_score <= (max_score + fk_tolerance)

        metrics = {
            "sentence_count": sentence_count,
            "page_count": len(pages),
            "word_count": word_count,
            "syllable_count": syllable_count,
            "avg_sentence_length": round(avg_sentence_length, 2),
            "avg_syllables_per_word": round(avg_syllables_per_word, 2),
            "flesch_kincaid_grade": round(fk_score, 2),
        }

        logger.info(
            f"[EnglishValidator] Level: {level}, FK Score: {fk_score:.2f}, "
            f"Sentences: {sentence_count}, Target: {min_score}-{max_score}, "
            f"Valid: {is_valid}"
        )

        return ValidationResult(
            is_valid=is_valid,
            score=round(fk_score, 2),
            metrics=metrics,
            message=f"FK {fk_score:.2f} for level {level} (target: {min_score}-{max_score})",
        )

    def get_stats(self, pages: List[List[str]]) -> Dict[str, Any]:
        """
        Compute detailed text statistics for English

        Args:
            pages: 2D array of sentences per page

        Returns:
            dict with FK score, sentence count, word count, etc.
        """
        all_sentences = [s for page in pages for s in page if s and s.strip()]
        sentence_count = len(all_sentences)

        if sentence_count == 0:
            return {
                "sentence_count": 0,
                "page_count": len(pages),
                "word_count": 0,
                "syllable_count": 0,
                "avg_sentence_length": 0.0,
                "avg_syllables_per_word": 0.0,
                "flesch_kincaid_grade": 0.0,
            }

        full_text = " ".join(all_sentences)
        word_count = textstat.lexicon_count(full_text, removepunct=True)
        syllable_count = textstat.syllable_count(full_text)

        avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
        avg_syllables_per_word = syllable_count / word_count if word_count > 0 else 0
        fk_score = 0.39 * avg_sentence_length + 11.8 * avg_syllables_per_word - 15.59

        return {
            "sentence_count": sentence_count,
            "page_count": len(pages),
            "word_count": word_count,
            "syllable_count": syllable_count,
            "avg_sentence_length": round(avg_sentence_length, 2),
            "avg_syllables_per_word": round(avg_syllables_per_word, 2),
            "flesch_kincaid_grade": round(fk_score, 2),
        }

    def get_level_ranges(self, level: int) -> Dict[str, tuple]:
        """Return FK grade ranges for the level"""
        return {"fk_grade": self.FK_RANGES.get(level, (0, 10))}
