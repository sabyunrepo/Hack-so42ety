"""
Vietnamese Language Configuration
Prompts for Vietnamese story generation using word-based rules
"""

from . import register_language
from .base import BaseLanguageConfig, LanguageMetadata, LevelExample


@register_language("vi")
class VietnameseConfig(BaseLanguageConfig):
    """Vietnamese language configuration with word-based rules"""

    @property
    def metadata(self) -> LanguageMetadata:
        return LanguageMetadata(
            code="vi",
            name="Vietnamese",
            native_name="Tiếng Việt",
            first_person="Tôi/Con",
        )

    def get_level_examples(self, level: int) -> LevelExample:
        examples = {
            1: LevelExample(
                title="Một ngày vui vẻ",
                stories=[
                    [
                        "Tôi thấy con chó.",
                        "Gâu gâu!",
                        "Con chó to lắm.",
                        "Chúng tôi chạy.",
                        "Vui quá!",
                    ],
                ],
            ),
            2: LevelExample(
                title="Vui chơi ở công viên",
                stories=[
                    [
                        "Hôm nay tôi đi công viên với bạn.",
                        "Chúng tôi chơi xích đu.",
                        "Nắng ấm áp lắm.",
                        "Thật là vui!",
                        "Tuyệt vời!",
                    ],
                ],
            ),
            3: LevelExample(
                title="Cuộc phiêu lưu kỳ thú",
                stories=[
                    [
                        "Sáng nay, tôi quyết định khám phá khu rừng sau nhà.",
                        "Cây cối cao lớn và chim hót những bài ca hay.",
                        "Tôi đi sâu vào rừng, cảm thấy tò mò và hào hứng.",
                        "Cuộc phiêu lưu dạy tôi rằng thiên nhiên thật kỳ diệu!",
                        "Thật tuyệt vời!",
                    ],
                ],
            ),
        }
        return examples.get(level, examples[1])

    # get_level_prompt uses default implementation from BaseLanguageConfig

    def get_difficulty_metrics(self, level: int) -> dict:
        """Vietnamese-specific metrics based on word count"""
        return {
            1: {
                "words_per_sentence": (4, 8),
                "sentence_count": (15, 25),
                "vocab_level": "basic",
            },
            2: {
                "words_per_sentence": (8, 15),
                "sentence_count": (25, 40),
                "vocab_level": "intermediate",
            },
            3: {
                "words_per_sentence": (15, 25),
                "sentence_count": (40, 60),
                "vocab_level": "advanced",
            },
        }.get(level, {})
