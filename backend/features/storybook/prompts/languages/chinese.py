"""
Chinese Language Configuration
Prompts for Chinese story generation using character-based rules
"""

from . import register_language
from .base import BaseLanguageConfig, LanguageMetadata, LevelExample


@register_language("zh")
class ChineseConfig(BaseLanguageConfig):
    """Chinese language configuration with character-based rules"""

    @property
    def metadata(self) -> LanguageMetadata:
        return LanguageMetadata(
            code="zh",
            name="Chinese",
            native_name="中文",
            first_person="我",
        )

    def get_level_examples(self, level: int) -> LevelExample:
        examples = {
            1: LevelExample(
                title="快乐的一天",
                stories=[
                    [
                        "我看到小狗。",
                        "汪汪!",
                        "小狗很大。",
                        "我们跑。",
                        "真开心!",
                    ],
                ],
            ),
            2: LevelExample(
                title="公园里玩耍",
                stories=[
                    [
                        "今天我和朋友去公园了。",
                        "我们荡秋千。",
                        "阳光很温暖。",
                        "玩得真开心!",
                        "太棒了!",
                    ],
                ],
            ),
            3: LevelExample(
                title="神奇的冒险",
                stories=[
                    [
                        "早上醒来的时候，我决定去探索房子后面的森林。",
                        "树木高大，鸟儿唱着美妙的歌。",
                        "我越走越深，心里越来越好奇和激动。",
                        "这次冒险让我明白了大自然充满了奇妙的惊喜!",
                        "太神奇了!",
                    ],
                ],
            ),
        }
        return examples.get(level, examples[1])

    # get_level_prompt uses default implementation from BaseLanguageConfig

    def get_difficulty_metrics(self, level: int) -> dict:
        """Chinese-specific metrics based on character count"""
        return {
            1: {
                "chars_per_sentence": (4, 10),
                "sentence_count": (15, 25),
                "vocab_level": "basic",
            },
            2: {
                "chars_per_sentence": (10, 20),
                "sentence_count": (25, 40),
                "vocab_level": "intermediate",
            },
            3: {
                "chars_per_sentence": (20, 35),
                "sentence_count": (40, 60),
                "vocab_level": "advanced",
            },
        }.get(level, {})
