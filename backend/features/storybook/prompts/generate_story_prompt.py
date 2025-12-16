from dataclasses import dataclass

from .difficulty_settings import get_level_prompt_template, get_difficulty_settings


@dataclass
class GenerateStoryPrompt:
    diary_entries: list[str]
    level: int = 1  # 기본값 레벨 1 (4-5세)

    def render(self) -> str:
        diary_text = "\n".join(f"* {entry}" for entry in self.diary_entries)
        settings = get_difficulty_settings(self.level)
        level_prompt = get_level_prompt_template(self.level)

        # 레벨별 예시 설정
        examples = self._get_level_examples()
        # 2. **시점:** 1인칭 주인공 시점('I')으로 작성

        return f"""
**[역할]**
당신은 한국인 아이들({settings.target_age}세)을 위한 영어 제2언어 학습용 동화를 작성하는 전문 작가입니다.

{level_prompt}

**[목표]**
아래 [오늘의 일기]에 나열된 사건들을 바탕으로, 1인칭 주인공 시점('I')의 즐거운 영어 동화를 만들고, 동화에 어울리는 짧은 영어 제목(최대 20자)을 생성해야 합니다.

**[필수 규칙]**
1. **제목:** 동화 내용을 요약하는 간단한 영어 제목 (최대 20자)
3. **형식:** 모든 문장은 마침표(`.`)로 끝나야 함
4. **언어:** 영어로만 작성 (한글 사용 금지)
5. **출력 형식:** 아래 JSON 형식 준수
```json
{{
    "title": "동화 제목",
    "stories": [
        ["문장1", "문장2", "..."],  # 첫 번째 일기 내용에 대한 동화
        ["문장1", "문장2", "..."],  # 두 번째 일기 내용에 대한 동화
        ...
    ]
}}
```

{examples}

---

**[오늘의 일기]**
{diary_text}
"""

    def _get_level_examples(self) -> str:
        """레벨별 예시 반환"""
        if self.level == 1:
            return """
**[예시 - 레벨 1 (3~5세)]**

* **입력:**
    ["오늘 강아지와 공원에 갔다."]

* **출력:**
    {{
        "title": "A Happy Day",
        "stories": [
            ["I see my puppy. Woof! My puppy is big and brown. I go to the park. We run fast. Yay!", "So fun!"]
        ]
    }}

* **입력:**
    [
        "아침에 일어났다.",
        "아침밥을 먹었다.",
        "공원에 갔다."
    ]

* **출력:**
    {{
        "title": "My Sunny Day",
        "stories": [
            ["I wake up. The sun is up. It is sunny. Good!", "Yay!"],
            ["I eat my food. Yum! The food is good. I like it.", "Happy!"],
            ["I go to the park. I run and jump. I play. So fun!", "Wow!"]
        ]
    }}

**[주의사항]**
- 1음절 위주 (85~90%), 2음절 일부 허용 (puppy, happy, sunny)
- 문장 길이 4~7단어
- "and" 형용사 연결만 가능 ("big and brown")
- 같은 단어를 5~10회 반복
"""
        elif self.level == 2:
            return """
**[예시 - 레벨 2 (5~7세)]**

* **입력:**
    ["오늘 친구와 수영장에 갔다.", "아이스크림을 먹었다."]

* **출력:**
    {{
        "title": "Fun at the Pool",
        "stories": [
            ["Today I went to the pool with my best friend. Splash! The water was cold but it felt good. We jumped in and played together. We were swimming and laughing. It was so much fun!", "Hooray!"],
            ["After swimming, I ate ice cream. Yum! It was pink and sweet. My friend had a yellow one. We sat together and enjoyed our treats. It was a beautiful day!", "Yummy!"]
        ]
    }}

* **입력:**
    ["강아지를 산책시켰다.", "공원에서 놀았다."]

* **출력:**
    {{
        "title": "Walking My Puppy",
        "stories": [
            ["I have a fluffy puppy. His name is Max. He is brown and white. I took him for a walk. We went to the pretty park. Woof woof!", "Excited!"],
            ["We played in the park. Max ran very fast. I tried to catch him but he was too quick. We had so much fun together. What a happy day!", "Amazing!"]
        ]
    }}

**[주의사항]**
- 1음절 (60~70%), 2음절 자유, 3음절 일부 허용 (beautiful, together)
- 문장 길이 6~10단어
- "and", "but" 사용 가능
- 과거형 자유롭게 사용 (went, was, had, played)
"""
        else:  # level 3
            return """
**[예시 - 레벨 3 (7~9세)]**

* **입력:**
    ["오늘 친구들과 숲속 탐험을 했다.", "예쁜 나비를 발견했다."]

* **출력:**
    {{
        "title": "An Incredible Forest Adventure",
        "stories": [
            ["Today was the most exciting day because I went on an adventure to the mysterious forest with my closest friends. As we walked along the winding path, we discovered the tallest trees I had ever seen. The forest was filled with beautiful sounds of birds singing their cheerful songs. We felt so curious and brave as we explored deeper into the wonderful woods!", "Amazing!"],
            ["Suddenly, I saw something incredible flying near the colorful flowers! It was a magnificent butterfly with the most beautiful wings I had ever seen. The butterfly had so many different colors that sparkled in the sunlight. I watched it very carefully because I didn't want to miss a single moment. When it flew away, I felt grateful that I had the chance to see something so special. This adventure taught me that nature is full of unexpected surprises!", "Wonderful!"]
        ]
    }}

* **입력:**
    ["비가 와서 집에 있었다.", "좋아하는 책을 읽었다."]

* **출력:**
    {{
        "title": "A Cozy Rainy Day",
        "stories": [
            ["When I woke up this morning, I heard the sound of rain tapping against my window. I looked outside and saw that the sky was gray and cloudy. The rain was falling heavily, so I decided to stay home where it was warm and cozy. Even though I couldn't go outside to play, I wasn't disappointed because I knew I could find other fun things to do inside.", "Hmm!"],
            ["I remembered my favorite book that I had been wanting to read again. I found it on my bookshelf and sat down on my comfortable bed. The story was about a brave little mouse who went on exciting adventures and never gave up, even when things got difficult. As I read each page, I felt more and more inspired by the courageous mouse. When I finally finished the book, I realized something important: rainy days can be just as wonderful as sunny days if you find the right activity. I felt proud of myself for making the best of a rainy day!", "Hooray!"]
        ]
    }}

**[주의사항]**
- 1~2음절 (50~60%), 3음절 자유, 4음절 일부 허용 (incredible, magnificent, unexpected)
- 문장 길이 9~15단어
- 모든 접속사 자유 (because, when, if, after, before, while)
- 복문 구조와 관계대명사 사용
- 감정과 이유를 상세하게 설명
"""
