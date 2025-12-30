"""
Base Language Configuration
Abstract base class for all language-specific configurations
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class LevelExample:
    """Level-specific story example"""

    title: str
    stories: List[List[str]]  # Pages containing sentences


@dataclass
class LanguageMetadata:
    """Language metadata"""

    code: str
    name: str
    native_name: str
    first_person: str


# Universal level prompts for languages without detailed prompts
# Languages with detailed prompts (English, Korean) override get_level_prompt()
UNIVERSAL_LEVEL_PROMPTS: Dict[int, str] = {
    1: """
**[난이도: 레벨 1 - 초보 단계 (3~5세)]**

**[문장 규칙]**
- 문장당 3~7 단어/어절
- 단순 구조: 주어 + 동사 (+목적어)
- 현재형 위주, 과거형 최소화
- 접속사 없음 또는 "그리고/and/和/và/и/และ" 1개만

**[어휘 규칙]**
- 일상적이고 구체적인 단어만 (추상 개념 금지)
- 같은 단어 5~10회 반복
- 의성어/감탄사 적극 활용

**[구조]**
- 페이지당 2~3개 짧은 문장
- 반복적 패턴 사용
- 간단한 감정 표현 (기쁨, 슬픔)
""",
    2: """
**[난이도: 레벨 2 - 기초 단계 (5~7세)]**

**[문장 규칙]**
- 문장당 6~10 단어/어절
- 간단한 접속사 허용 ("그리고", "하지만" / "and", "but" / "和", "但是")
- 현재형 60%, 과거형 30%, 진행형 10%

**[어휘 규칙]**
- 2~3음절/글자 단어 자유롭게 사용
- 같은 단어 3~5회 반복
- 기본 감정 표현 (기쁨, 슬픔, 신남, 무서움)

**[구조]**
- 페이지당 3~5개 문장
- 간단한 인과관계 표현
- 의문문 일부 허용
""",
    3: """
**[난이도: 레벨 3 - 심화 단계 (7~9세)]**

**[문장 규칙]**
- 문장당 9~15 단어/어절
- 모든 접속사 자유 (이유, 조건, 시간 표현)
- 복문 구조와 종속절 허용

**[어휘 규칙]**
- 추상적 개념 일부 허용 (용기, 우정, 노력)
- 복잡한 감정 표현 (자랑스러움, 실망, 감사)
- 비유적 표현 일부 허용

**[구조]**
- 페이지당 5~8개 문장
- 문제-해결 구조
- 캐릭터 감정 변화 묘사
- 교훈적 메시지 포함
""",
}


class BaseLanguageConfig(ABC):
    """
    Abstract base class for language configurations

    Each language must implement:
    - metadata: Language identification
    - level_examples: Per-level story examples

    Optional override:
    - level_prompts: Per-level detailed rules (defaults to UNIVERSAL_LEVEL_PROMPTS)
    """

    @property
    @abstractmethod
    def metadata(self) -> LanguageMetadata:
        """Return language metadata"""
        pass

    @abstractmethod
    def get_level_examples(self, level: int) -> LevelExample:
        """
        Return level-specific examples

        Args:
            level: Difficulty level (1, 2, 3)

        Returns:
            LevelExample with title and stories
        """
        pass

    def get_level_prompt(self, level: int) -> str:
        """
        Return level-specific prompt template

        Default implementation returns universal prompts.
        Override in subclass for language-specific detailed prompts.

        Args:
            level: Difficulty level (1, 2, 3)

        Returns:
            Detailed prompt template for the level
        """
        return UNIVERSAL_LEVEL_PROMPTS.get(level, UNIVERSAL_LEVEL_PROMPTS[1])

    def get_difficulty_metrics(self, level: int) -> Dict[str, Any]:
        """
        Return expected difficulty metrics for validation
        Override in subclass for language-specific metrics
        """
        return {}
