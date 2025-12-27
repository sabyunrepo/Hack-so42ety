"""
Thai Language Configuration
Prompts for Thai story generation using segment-based rules
"""

from . import register_language
from .base import BaseLanguageConfig, LanguageMetadata, LevelExample


@register_language("th")
class ThaiConfig(BaseLanguageConfig):
    """Thai language configuration with segment-based rules"""

    @property
    def metadata(self) -> LanguageMetadata:
        return LanguageMetadata(
            code="th",
            name="Thai",
            native_name="ไทย",
            first_person="ฉัน/ผม",
        )

    def get_level_examples(self, level: int) -> LevelExample:
        examples = {
            1: LevelExample(
                title="วันที่มีความสุข",
                stories=[
                    [
                        "ฉันเห็นสุนัข",
                        "โฮ่งโฮ่ง!",
                        "สุนัขตัวใหญ่",
                        "เราวิ่ง",
                        "สนุกมาก!",
                    ],
                ],
            ),
            2: LevelExample(
                title="สนุกที่สวนสาธารณะ",
                stories=[
                    [
                        "วันนี้ฉันไปสวนสาธารณะกับเพื่อน",
                        "เราเล่นชิงช้า",
                        "แดดอุ่นสบาย",
                        "สนุกมากเลย!",
                        "เยี่ยมเลย!",
                    ],
                ],
            ),
            3: LevelExample(
                title="การผจญภัยมหัศจรรย์",
                stories=[
                    [
                        "เช้านี้ ฉันตัดสินใจไปสำรวจป่าหลังบ้าน",
                        "ต้นไม้สูงใหญ่และนกร้องเพลงไพเราะ",
                        "ฉันเดินลึกเข้าไปในป่า รู้สึกตื่นเต้นมาก",
                        "การผจญภัยนี้สอนฉันว่าธรรมชาติเต็มไปด้วยสิ่งมหัศจรรย์!",
                        "น่าทึ่งมาก!",
                    ],
                ],
            ),
        }
        return examples.get(level, examples[1])

    # get_level_prompt uses default implementation from BaseLanguageConfig

    def get_difficulty_metrics(self, level: int) -> dict:
        """Thai-specific metrics based on character count (no spaces in Thai)"""
        return {
            1: {
                "chars_per_sentence": (10, 25),
                "sentence_count": (15, 25),
                "vocab_level": "basic",
            },
            2: {
                "chars_per_sentence": (25, 50),
                "sentence_count": (25, 40),
                "vocab_level": "intermediate",
            },
            3: {
                "chars_per_sentence": (50, 100),
                "sentence_count": (40, 60),
                "vocab_level": "advanced",
            },
        }.get(level, {})
