"""
Story Generation Prompt
Generates prompts for LLM-based story creation with multi-language support
"""

from dataclasses import dataclass
from typing import Dict, Any

from backend.core.config import settings
from .languages import get_language_config


@dataclass
class GenerateStoryPrompt:
    """
    Story generation prompt with multi-language and difficulty support

    Args:
        diary_entries: List of diary entries to base the story on
        level: Difficulty level (1, 2, 3)
        target_language: Target language code (en, ko, zh, vi, ru, th)
    """

    diary_entries: list[str]
    level: int = 1
    target_language: str = "en"

    def render(self) -> str:
        """Render the complete prompt for story generation"""
        diary_text = "\n".join(f"* {entry}" for entry in self.diary_entries)
        target_age = settings.get_target_age(self.level)
        lang_config = get_language_config(self.target_language)
        meta = lang_config.metadata

        # All languages now get detailed prompts from their config
        level_prompt = lang_config.get_level_prompt(self.level)
        example_section = self._format_level_example(lang_config)

        return f"""
**[역할]**
당신은 아이들({target_age}세)을 위한 **{meta.native_name}** 동화를 작성하는 전문 작가입니다.

{level_prompt}

**[목표]**
아래 [오늘의 일기]에 나열된 사건들을 바탕으로, 1인칭 주인공 시점('{meta.first_person}')의 즐거운 **{meta.native_name}** 동화를 만들고, 동화에 어울리는 짧은 **{meta.native_name}** 제목(최대 20자)을 생성해야 합니다.

**[필수 규칙]**
1. **제목:** 동화 내용을 요약하는 간단한 **{meta.native_name}** 제목 (최대 20자)
2. **페이지 수:** 반드시 **정확히 {len(self.diary_entries)}페이지**로 생성 (일기 항목 수와 동일)
3. **형식:** 모든 문장은 마침표로 끝나야 함
4. **언어:** 반드시 **{meta.native_name}**로만 작성 (다른 언어 사용 금지)
5. **입력 언어:** 입력은 어떤 언어든 가능 (AI가 {meta.native_name}로 변환)
6. **출력 형식:** 아래 JSON 형식 준수

{example_section}

---

**[오늘의 일기]**
{diary_text}
"""

    def _format_level_example(self, lang_config) -> str:
        """Format level-specific examples for the prompt"""
        example = lang_config.get_level_examples(self.level)
        meta = lang_config.metadata

        # Format stories as JSON
        stories_json = []
        for page in example.stories:
            page_json = ", ".join(f'"{s}"' for s in page)
            stories_json.append(f"[{page_json}]")

        return f"""**[{meta.native_name} 예시 - 레벨 {self.level}]**

```json
{{
    "title": "{example.title}",
    "stories": [
        {', '.join(stories_json)}
    ]
}}
```"""
