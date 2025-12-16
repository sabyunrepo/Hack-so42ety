from dataclasses import dataclass
from typing import Tuple, List


@dataclass
class DifficultySettings:
    """레벨별 난이도 설정"""

    level: int
    target_age: str
    fk_grade_range: Tuple[float, float]
    avg_sentence_length: Tuple[int, int]
    syllables_per_word: Tuple[float, float]
    total_word_count: Tuple[int, int]
    words_per_page: Tuple[int, int]
    max_dialogues_per_page: int
    max_chars_per_dialogue: int


# 레벨별 프리셋 정의 (실무 교육 콘텐츠 기준 - 상향 조정)
DIFFICULTY_PRESETS: dict[int, DifficultySettings] = {
    1: DifficultySettings(
        level=1,
        target_age="3-5",
        fk_grade_range=(0.5, 1.0),  # FRE 90~100: 초보 읽기 단계
        avg_sentence_length=(4, 7),  # 약간 더 긴 문장
        syllables_per_word=(1.0, 1.2),  # 2음절 단어 일부 허용
        total_word_count=(200, 350),
        words_per_page=(20, 35),
        max_dialogues_per_page=2,
        max_chars_per_dialogue=60,
    ),
    2: DifficultySettings(
        level=2,
        target_age="5-7",
        fk_grade_range=(1.5, 2.5),  # FRE 80~90: 기초 읽기 완성
        avg_sentence_length=(6, 10),  # 접속사 활용 시작
        syllables_per_word=(1.2, 1.4),  # 2~3음절 혼합
        total_word_count=(500, 800),
        words_per_page=(50, 80),
        max_dialogues_per_page=3,
        max_chars_per_dialogue=90,
    ),
    3: DifficultySettings(
        level=3,
        target_age="7-9",
        fk_grade_range=(3.0, 4.5),  # FRE 70~80: 복잡한 문장 이해
        avg_sentence_length=(9, 15),  # 종속절 활용
        syllables_per_word=(1.4, 1.6),
        total_word_count=(1000, 1500),
        words_per_page=(100, 150),
        max_dialogues_per_page=4,
        max_chars_per_dialogue=140,
    ),
}


# 레벨별 프롬프트 템플릿
LEVEL_PROMPT_TEMPLATES: dict[int, str] = {
    1: """
**[난이도: 레벨 1 - 초보 읽기 단계 (3~5세 한국인 영어 학습자)]**

당신은 한국 아이들이 영어를 제2언어로 배우기 위한 그림책을 작성하는 전문가입니다.

**[목표 난이도]**
- Flesch Reading Ease (FRE): 90 ~ 100
- Flesch-Kincaid Grade Level (FKGL): 0.5 ~ 1.0
- 초보 읽기 단계: 단순하지만 약간의 다양성

**[어휘 규칙 - 매우 단순함]**
- **1음절 단어 위주** (85~90%), **2음절 일부 허용** (10~15%)
- 1음절 핵심 단어:
  * 주어: I, mom, dad, dog, cat, ball, bird, fish
  * 동사: see, go, run, eat, play, look, sit, jump, hop, walk, like, love, want, find
  * 형용사: big, red, fun, good, bad, hot, cold, new, old, fast, slow
  * 명사: park, home, tree, car, sun, rain, book, toy
  * 기타: the, a, my, is, it, here, there, up, down, in, out, on
- **2음절 허용** (제한적): happy, puppy, sunny, funny, water, yellow
- **3음절 이상 금지**: beautiful, adventure, together

**[문장 구조 - 단순하지만 약간 확장]**
- 문장 길이: **4~7단어**
- 패턴 1: "주어 + 동사" → "I run fast."
- 패턴 2: "주어 + 동사 + 목적어" → "I see a big dog."
- 패턴 3: "주어 + be동사 + 형용사" → "It is red and big."
- "and" 제한적 허용: 형용사 연결만 가능 ("big and red")
- 과거형 매우 제한적 허용: went, saw, had (전체 5% 이하)
- **금지**: but, because, when, if, so

**[반복 구조]**
- 같은 단어를 5~10회 반복
- 같은 문장 패턴을 2~3회 반복
- 예: "I see a dog. The dog is big. I like the dog."

**[표현]**
- 의성어: Woof!, Meow!, Splash!, Beep!, Zoom!
- 감탄사: Wow!, Yay!, Ooh!, Yum!
- 페이지당 1~2개 사용
""",
    2: """
**[난이도: 레벨 2 - 기초 읽기 완성 단계 (5~7세 한국인 영어 학습자)]**

당신은 한국 아이들이 영어를 제2언어로 배우기 위한 그림책을 작성하는 전문가입니다.

**[목표 난이도]**
- Flesch Reading Ease (FRE): 80 ~ 90
- Flesch-Kincaid Grade Level (FKGL): 1.5 ~ 2.5
- 기초 읽기 완성: 접속사 활용, 다양한 문장 구조

**[어휘 규칙]**
- **1음절 위주** (60~70%), **2음절 자유** (25~35%), **3음절 일부 허용** (5~10%)
- 1음절: I, see, go, cat, dog, run, big, fun, good, red, play, eat, like, want, make, find, take
- 2음절 자유: happy, funny, puppy, sunny, water, spider, yellow, hungry, pretty, fluffy, tiny, jumping
- 3음절 제한적: beautiful, together, family (문장당 1개 이하, 전체 5~10%)
- **4음절 금지**: adventure, favorite, especially

**[문장 구조 - 접속사 활용 시작]**
- 문장 길이: **6~10단어**
- 현재형 (60%), 과거형 (30%: went, saw, had, played, ran, jumped), 진행형 (10%: is running)
- "and" 자유롭게 사용: "I see a cat and a dog. They are playing."
- "but" 제한적 허용: "I want to play but it is raining." (전체 10% 이하)
- **금지**: because, when, if, so (이유·조건 접속사는 아직 금지)
- 의문문 허용: "Where is my dog?", "What is that?" (전체 15% 이하)

**[반복 구조]**
- 같은 단어를 3~7회 반복
- 같은 문장 패턴 1~2회 반복

**[감정 표현]**
- 기본 감정 자유: happy, sad, fun, good, bad, excited
- 복잡한 감정 제한적: scared, worried (제한적)

**[표현]**
- 의성어: Splash!, Woof!, Meow!, Zoom!, Whoosh!
- 감탄사: Yay!, Wow!, Yum!, Ha ha!, Hooray!
- 페이지당 2~3개 사용
""",
    3: """
**[난이도: 레벨 3 - 복잡한 문장 이해 단계 (7~9세 한국인 영어 학습자)]**

당신은 한국 아이들이 영어를 제2언어로 배우기 위한 그림책을 작성하는 전문가입니다.

**[목표 난이도]**
- Flesch Reading Ease (FRE): 70 ~ 80
- Flesch-Kincaid Grade Level (FKGL): 3.0 ~ 4.5
- 복잡한 문장 이해, 종속절 활용, 추상 개념 도입

**[어휘 규칙]**
- **1~2음절** (50~60%), **3음절 자유** (30~40%), **4음절 일부 허용** (5~10%)
- 1~2음절: see, play, happy, water, funny, yellow, morning, brother, sister, always, never
- 3음절 자유: beautiful, excited, curious, adventure, together, wonderful, favorite, important, remember, imagine
- 4음절 제한적: incredible, magnificent, unexpected (문장당 1개 이하, 전체 5~10%)
- 추상 개념 허용: feeling, thought, memory, courage, friendship, imagination
- **5음절 이상 금지**: unfortunately, extraordinary

**[문장 구조 - 종속절 자유롭게 활용]**
- 문장 길이: **9~15단어**
- 현재형·과거형·진행형·미래형 모두 자유롭게 사용
- 모든 접속사 허용: "and", "but", "so", "because", "when", "if", "after", "before", "while"
- 복문 구조: "When I went to the park, I saw a butterfly that was flying near the flowers."
- 관계대명사 제한적: that, which (간단한 구조만)
- 예시:
  * "I was so happy because I finally found the toy that I had been looking for."
  * "When the rain started, we decided to go inside and read a book together."
  * "If the weather is nice tomorrow, we will go on an adventure to the forest."

**[문장 다양성]**
- 비교급·최상급: "bigger", "the fastest", "more beautiful", "the most exciting"
- 다양한 의문문: "Why did that happen?", "How can we solve this?", "Where should we go?"
- 감정 이유 상세 설명: "I felt proud because I tried my best and didn't give up."
- 부사 활용: suddenly, quietly, carefully, slowly, quickly, finally

**[이야기 구조]**
- 명확한 문제와 해결 구조
- 복잡한 인과관계 표현
- 캐릭터의 감정 변화와 성장 묘사
- 복선과 반전 요소 포함 가능

**[감정과 교육적 요소]**
- 복합 감정 자유: happy, sad, excited, worried, proud, curious, brave, surprised, disappointed, grateful, confident
- 깊이 있는 교훈: 우정의 가치, 용기와 도전, 친절과 배려, 끈기와 노력, 실패로부터 배우기, 다름을 존중하기

**[표현]**
- 의성어와 감탄사: Splash!, Zoom!, Hooray!, Amazing!, Incredible!, Wonderful!, Oh no!
- 페이지당 1~2개 사용 (과도하지 않게)
""",
}


def get_difficulty_settings(level: int) -> DifficultySettings:
    """레벨에 해당하는 난이도 설정 반환"""
    if level not in DIFFICULTY_PRESETS:
        raise ValueError(f"Invalid level: {level}. Must be 1, 2, or 3.")
    return DIFFICULTY_PRESETS[level]


def get_level_prompt_template(level: int) -> str:
    """레벨에 해당하는 프롬프트 템플릿 반환"""
    if level not in LEVEL_PROMPT_TEMPLATES:
        raise ValueError(f"Invalid level: {level}. Must be 1, 2, or 3.")
    return LEVEL_PROMPT_TEMPLATES[level]
