"""
English Language Configuration
Detailed prompts for English story generation using Flesch-Kincaid based rules
"""

from . import register_language
from .base import BaseLanguageConfig, LanguageMetadata, LevelExample


@register_language("en")
class EnglishConfig(BaseLanguageConfig):
    """English language configuration with detailed FK-based rules"""

    @property
    def metadata(self) -> LanguageMetadata:
        return LanguageMetadata(
            code="en",
            name="English",
            native_name="English",
            first_person="I",
        )

    def get_level_examples(self, level: int) -> LevelExample:
        examples = {
            1: LevelExample(
                title="A Happy Day",
                stories=[
                    [
                        "I see my dog.",
                        "Woof!",
                        "My dog is big.",
                        "We run.",
                        "So fun!",
                    ],
                ],
            ),
            2: LevelExample(
                title="Fun at the Park",
                stories=[
                    [
                        "Today I went to the park with my friend.",
                        "We played on the swings.",
                        "The sun was warm and bright.",
                        "It was so much fun!",
                        "Hooray!",
                    ],
                ],
            ),
            3: LevelExample(
                title="An Amazing Adventure",
                stories=[
                    [
                        "This morning, I decided to explore the forest behind my house.",
                        "The trees were tall and the birds sang beautiful songs.",
                        "I felt curious and excited as I walked deeper into the woods.",
                        "This adventure showed me that nature is full of surprises!",
                        "Amazing!",
                    ],
                ],
            ),
        }
        return examples.get(level, examples[1])

    def get_level_prompt(self, level: int) -> str:
        """Return the detailed English prompts (migrated from LEVEL_PROMPT_TEMPLATES)"""
        prompts = {
            1: """
**[Difficulty: Level 1 - Beginner Reading Stage (Ages 3-5, Korean English Learners)]**

You are an expert at writing picture books for Korean children learning English as a second language.

**[Target Difficulty]**
- Flesch Reading Ease (FRE): 90 ~ 100
- Flesch-Kincaid Grade Level (FKGL): 0.5 ~ 1.0
- Beginner reading stage: Simple with slight variety

**[Vocabulary Rules - Very Simple]**
- **1-syllable words mainly** (85~90%), **some 2-syllable allowed** (10~15%)
- 1-syllable core words:
  * Subjects: I, mom, dad, dog, cat, ball, bird, fish
  * Verbs: see, go, run, eat, play, look, sit, jump, hop, walk, like, love, want, find
  * Adjectives: big, red, fun, good, bad, hot, cold, new, old, fast, slow
  * Nouns: park, home, tree, car, sun, rain, book, toy
  * Others: the, a, my, is, it, here, there, up, down, in, out, on
- **2-syllable allowed** (limited): happy, puppy, sunny, funny, water, yellow
- **3+ syllables forbidden**: beautiful, adventure, together

**[Sentence Structure - Simple with slight extension]**
- Sentence length: **4~7 words**
- Pattern 1: "Subject + Verb" -> "I run fast."
- Pattern 2: "Subject + Verb + Object" -> "I see a big dog."
- Pattern 3: "Subject + be verb + Adjective" -> "It is red and big."
- "and" limited use: only for connecting adjectives ("big and red")
- Past tense very limited: went, saw, had (less than 5% of total)
- **Forbidden**: but, because, when, if, so

**[Repetition Structure]**
- Same word repeated 5~10 times
- Same sentence pattern repeated 2~3 times
- Example: "I see a dog. The dog is big. I like the dog."

**[Expressions]**
- Onomatopoeia: Woof!, Meow!, Splash!, Beep!, Zoom!
- Exclamations: Wow!, Yay!, Ooh!, Yum!
- Use 1~2 per page
""",
            2: """
**[Difficulty: Level 2 - Basic Reading Completion Stage (Ages 5-7, Korean English Learners)]**

You are an expert at writing picture books for Korean children learning English as a second language.

**[Target Difficulty]**
- Flesch Reading Ease (FRE): 80 ~ 90
- Flesch-Kincaid Grade Level (FKGL): 1.5 ~ 2.5
- Basic reading completion: Conjunction usage begins, varied sentence structures

**[Vocabulary Rules]**
- **1-syllable mainly** (60~70%), **2-syllable freely** (25~35%), **some 3-syllable allowed** (5~10%)
- 1-syllable: I, see, go, cat, dog, run, big, fun, good, red, play, eat, like, want, make, find, take
- 2-syllable freely: happy, funny, puppy, sunny, water, spider, yellow, hungry, pretty, fluffy, tiny, jumping
- 3-syllable limited: beautiful, together, family (max 1 per sentence, 5~10% total)
- **4+ syllables forbidden**: adventure, favorite, especially

**[Sentence Structure - Conjunction usage begins]**
- Sentence length: **6~10 words**
- Present (60%), Past (30%: went, saw, had, played, ran, jumped), Progressive (10%: is running)
- "and" used freely: "I see a cat and a dog. They are playing."
- "but" limited: "I want to play but it is raining." (less than 10% total)
- **Forbidden**: because, when, if, so (reason/condition conjunctions still forbidden)
- Questions allowed: "Where is my dog?", "What is that?" (less than 15% total)

**[Repetition Structure]**
- Same word repeated 3~7 times
- Same sentence pattern repeated 1~2 times

**[Emotional Expressions]**
- Basic emotions freely: happy, sad, fun, good, bad, excited
- Complex emotions limited: scared, worried (limited)

**[Expressions]**
- Onomatopoeia: Splash!, Woof!, Meow!, Zoom!, Whoosh!
- Exclamations: Yay!, Wow!, Yum!, Ha ha!, Hooray!
- Use 2~3 per page
""",
            3: """
**[Difficulty: Level 3 - Complex Sentence Understanding Stage (Ages 7-9, Korean English Learners)]**

You are an expert at writing picture books for Korean children learning English as a second language.

**[Target Difficulty]**
- Flesch Reading Ease (FRE): 70 ~ 80
- Flesch-Kincaid Grade Level (FKGL): 3.0 ~ 4.5
- Complex sentence understanding, subordinate clause usage, abstract concepts introduced

**[Vocabulary Rules]**
- **1~2 syllables** (50~60%), **3 syllables freely** (30~40%), **some 4-syllable allowed** (5~10%)
- 1~2 syllables: see, play, happy, water, funny, yellow, morning, brother, sister, always, never
- 3 syllables freely: beautiful, excited, curious, adventure, together, wonderful, favorite, important, remember, imagine
- 4 syllables limited: incredible, magnificent, unexpected (max 1 per sentence, 5~10% total)
- Abstract concepts allowed: feeling, thought, memory, courage, friendship, imagination
- **5+ syllables forbidden**: unfortunately, extraordinary

**[Sentence Structure - Subordinate clauses used freely]**
- Sentence length: **9~15 words**
- All tenses used freely: present, past, progressive, future
- All conjunctions allowed: "and", "but", "so", "because", "when", "if", "after", "before", "while"
- Complex sentence structures: "When I went to the park, I saw a butterfly that was flying near the flowers."
- Relative pronouns limited: that, which (simple structures only)
- Examples:
  * "I was so happy because I finally found the toy that I had been looking for."
  * "When the rain started, we decided to go inside and read a book together."
  * "If the weather is nice tomorrow, we will go on an adventure to the forest."

**[Sentence Variety]**
- Comparatives/Superlatives: "bigger", "the fastest", "more beautiful", "the most exciting"
- Varied questions: "Why did that happen?", "How can we solve this?", "Where should we go?"
- Detailed emotion reasoning: "I felt proud because I tried my best and didn't give up."
- Adverb usage: suddenly, quietly, carefully, slowly, quickly, finally

**[Story Structure]**
- Clear problem and solution structure
- Complex cause-and-effect relationships
- Character emotion changes and growth
- Foreshadowing and plot twists possible

**[Emotions and Educational Elements]**
- Complex emotions freely: happy, sad, excited, worried, proud, curious, brave, surprised, disappointed, grateful, confident
- Deep lessons: value of friendship, courage and challenge, kindness and consideration, perseverance and effort, learning from failure, respecting differences

**[Expressions]**
- Onomatopoeia and exclamations: Splash!, Zoom!, Hooray!, Amazing!, Incredible!, Wonderful!, Oh no!
- Use 1~2 per page (not excessive)
""",
        }
        return prompts.get(level, prompts[1])

    def get_difficulty_metrics(self, level: int) -> dict:
        """English-specific FK metrics"""
        return {
            1: {
                "fk_range": (0.5, 1.5),
                "word_count": (200, 350),
                "sentence_length": (4, 7),
            },
            2: {
                "fk_range": (1.5, 2.5),
                "word_count": (500, 800),
                "sentence_length": (6, 10),
            },
            3: {
                "fk_range": (3.0, 4.5),
                "word_count": (1000, 1500),
                "sentence_length": (9, 15),
            },
        }.get(level, {})
