"""
[DEPRECATED] Flesch-Kincaid Grade Level 기반 난이도 검증 유틸리티

이 모듈은 더 이상 사용되지 않습니다.
새로운 다국어 검증 시스템을 사용하세요:

    from backend.features.storybook.validators import ValidatorFactory

    validator = ValidatorFactory.get_validator("en")  # or "ko", etc.
    result = validator.validate(text, level=1)
    if result.is_valid:
        ...

이 파일은 하위 호환성을 위해 유지되며, 향후 버전에서 제거될 예정입니다.

---
(Legacy) Flesch-Kincaid Grade Level 공식:
(0.39 × 평균 문장 길이) + (11.8 × 평균 음절/단어) - 15.59

점수가 낮을수록 쉬운 텍스트를 의미함
"""

import warnings

warnings.warn(
    "difficulty_validator 모듈은 deprecated되었습니다. "
    "backend.features.storybook.validators.ValidatorFactory를 사용하세요.",
    DeprecationWarning,
    stacklevel=2,
)

import logging
from typing import Tuple

import textstat

from core.config import settings

logger = logging.getLogger(__name__)


# 레벨별 Flesch-Kincaid Grade Level 허용 범위
FK_RANGES: dict[int, Tuple[float, float]] = {
    1: (0.5, 1.5),  # 레벨 1 (4-5세): 매우 쉬운 텍스트
    2: (2.0, 2.5),  # 레벨 2 (5-6세): 쉬운 텍스트
    3: (3.0, 4.0),  # 레벨 3 (6-8세): 중간 수준 텍스트
}


def validate_difficulty(text: str, level: int) -> Tuple[bool, float]:
    """
    생성된 텍스트의 Flesch-Kincaid Grade Level 검증

    Args:
        text: 검증할 영어 텍스트
        level: 목표 난이도 레벨 (1, 2, 3)

    Returns:
        Tuple[bool, float]: (검증 통과 여부, 실제 FK 점수)

    Raises:
        ValueError: 유효하지 않은 레벨
    """
    if level not in FK_RANGES:
        raise ValueError(f"Invalid level: {level}. Must be 1, 2, or 3.")

    # 텍스트가 비어있으면 검증 통과
    if not text or not text.strip():
        logger.warning("[FK Validator] Empty text provided")
        return True, 0.0

    # Flesch-Kincaid Grade Level 계산
    fk_score = textstat.flesch_kincaid_grade(text)

    min_score, max_score = FK_RANGES[level]

    # 여유분을 포함하여 검증 (LLM 특성상 정확한 범위 맞추기 어려움)
    fk_tolerance = settings.fk_tolerance
    is_valid = (min_score - fk_tolerance) <= fk_score <= (max_score + fk_tolerance)

    logger.info(
        f"[FK Validator] Level: {level}, Score: {fk_score:.2f}, "
        f"Target: {min_score}-{max_score}, Valid: {is_valid}"
    )

    return is_valid, fk_score


def get_text_stats(text: str) -> dict:
    """
    텍스트의 상세 통계 반환 (디버깅/로깅용)

    Returns:
        dict: {
            'flesch_kincaid_grade': FK 점수,
            'flesch_reading_ease': 읽기 쉬움 점수 (높을수록 쉬움),
            'sentence_count': 문장 수,
            'word_count': 단어 수,
            'avg_sentence_length': 평균 문장 길이,
            'syllable_count': 총 음절 수,
            'avg_syllables_per_word': 평균 음절/단어
        }
    """
    if not text or not text.strip():
        return {
            "flesch_kincaid_grade": 0.0,
            "flesch_reading_ease": 100.0,
            "sentence_count": 0,
            "word_count": 0,
            "avg_sentence_length": 0.0,
            "syllable_count": 0,
            "avg_syllables_per_word": 0.0,
        }

    sentence_count = textstat.sentence_count(text)
    word_count = textstat.lexicon_count(text, removepunct=True)
    syllable_count = textstat.syllable_count(text)

    avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
    avg_syllables_per_word = syllable_count / word_count if word_count > 0 else 0

    return {
        "flesch_kincaid_grade": textstat.flesch_kincaid_grade(text),
        "flesch_reading_ease": textstat.flesch_reading_ease(text),
        "sentence_count": sentence_count,
        "word_count": word_count,
        "avg_sentence_length": round(avg_sentence_length, 2),
        "syllable_count": syllable_count,
        "avg_syllables_per_word": round(avg_syllables_per_word, 2),
    }
