"""
Russian Language Configuration
Prompts for Russian story generation using word-based rules
"""

from . import register_language
from .base import BaseLanguageConfig, LanguageMetadata, LevelExample


@register_language("ru")
class RussianConfig(BaseLanguageConfig):
    """Russian language configuration with word-based rules"""

    @property
    def metadata(self) -> LanguageMetadata:
        return LanguageMetadata(
            code="ru",
            name="Russian",
            native_name="Русский",
            first_person="Я",
        )

    def get_level_examples(self, level: int) -> LevelExample:
        examples = {
            1: LevelExample(
                title="Счастливый день",
                stories=[
                    [
                        "Я вижу собаку.",
                        "Гав-гав!",
                        "Собака большая.",
                        "Мы бежим.",
                        "Весело!",
                    ],
                ],
            ),
            2: LevelExample(
                title="Веселье в парке",
                stories=[
                    [
                        "Сегодня я пошёл в парк с другом.",
                        "Мы качались на качелях.",
                        "Солнце было тёплым.",
                        "Было очень весело!",
                        "Ура!",
                    ],
                ],
            ),
            3: LevelExample(
                title="Удивительное приключение",
                stories=[
                    [
                        "Утром я решил исследовать лес за домом.",
                        "Деревья были высокими, и птицы пели красиво.",
                        "Чем глубже я заходил в лес, тем интереснее было.",
                        "Это приключение показало мне, что природа полна чудес!",
                        "Удивительно!",
                    ],
                ],
            ),
        }
        return examples.get(level, examples[1])

    # get_level_prompt uses default implementation from BaseLanguageConfig

    def get_difficulty_metrics(self, level: int) -> dict:
        """Russian-specific metrics based on word count"""
        return {
            1: {
                "words_per_sentence": (3, 6),
                "sentence_count": (15, 25),
                "vocab_level": "basic",
            },
            2: {
                "words_per_sentence": (6, 10),
                "sentence_count": (25, 40),
                "vocab_level": "intermediate",
            },
            3: {
                "words_per_sentence": (10, 15),
                "sentence_count": (40, 60),
                "vocab_level": "advanced",
            },
        }.get(level, {})
