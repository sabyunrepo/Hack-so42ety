from dataclasses import dataclass
from typing import Dict, Any, List

from .difficulty_settings import (
    get_level_prompt_template,
    get_difficulty_settings,
    get_universal_level_prompt,
)


# 다국어 설정 (레벨별 예시 포함)
LANGUAGE_CONFIG: Dict[str, Dict[str, Any]] = {
    "en": {
        "name": "English",
        "native_name": "English",
        "first_person": "I",
        "level_examples": {
            1: {
                "title": "A Happy Day",
                "stories": [
                    ["I see my dog.", "Woof!", "My dog is big.", "We run.", "So fun!"],
                ],
            },
            2: {
                "title": "Fun at the Park",
                "stories": [
                    ["Today I went to the park with my friend.", "We played on the swings.", "The sun was warm and bright.", "It was so much fun!", "Hooray!"],
                ],
            },
            3: {
                "title": "An Amazing Adventure",
                "stories": [
                    ["This morning, I decided to explore the forest behind my house.", "The trees were tall and the birds sang beautiful songs.", "I felt curious and excited as I walked deeper into the woods.", "This adventure showed me that nature is full of surprises!", "Amazing!"],
                ],
            },
        },
    },
    "ko": {
        "name": "Korean",
        "native_name": "한국어",
        "first_person": "나/저",
        "level_examples": {
            1: {
                "title": "즐거운 하루",
                "stories": [
                    ["나는 강아지를 봤어요.", "멍멍!", "강아지가 커요.", "우리는 뛰었어요.", "재미있어요!"],
                ],
            },
            2: {
                "title": "공원에서 놀았어요",
                "stories": [
                    ["오늘 친구와 공원에 갔어요.", "그네를 탔어요.", "햇살이 따뜻했어요.", "정말 재미있었어요!", "신나요!"],
                ],
            },
            3: {
                "title": "신나는 모험",
                "stories": [
                    ["오늘 아침, 집 뒤 숲을 탐험하기로 했어요.", "나무는 크고 새들이 아름다운 노래를 불렀어요.", "숲 속으로 걸어갈수록 더 신기하고 설레었어요.", "이 모험으로 자연에는 놀라운 것들이 가득하다는 걸 알았어요!", "대단해요!"],
                ],
            },
        },
    },
    "zh": {
        "name": "Chinese",
        "native_name": "中文",
        "first_person": "我",
        "level_examples": {
            1: {
                "title": "快乐的一天",
                "stories": [
                    ["我看到小狗。", "汪汪!", "小狗很大。", "我们跑。", "真开心!"],
                ],
            },
            2: {
                "title": "公园里玩耍",
                "stories": [
                    ["今天我和朋友去公园了。", "我们荡秋千。", "阳光很温暖。", "玩得真开心!", "太棒了!"],
                ],
            },
            3: {
                "title": "神奇的冒险",
                "stories": [
                    ["早上醒来的时候，我决定去探索房子后面的森林。", "树木高大，鸟儿唱着美妙的歌。", "我越走越深，心里越来越好奇和激动。", "这次冒险让我明白了大自然充满了奇妙的惊喜!", "太神奇了!"],
                ],
            },
        },
    },
    "vi": {
        "name": "Vietnamese",
        "native_name": "Tiếng Việt",
        "first_person": "Tôi/Con",
        "level_examples": {
            1: {
                "title": "Một ngày vui vẻ",
                "stories": [
                    ["Tôi thấy con chó.", "Gâu gâu!", "Con chó to lắm.", "Chúng tôi chạy.", "Vui quá!"],
                ],
            },
            2: {
                "title": "Vui chơi ở công viên",
                "stories": [
                    ["Hôm nay tôi đi công viên với bạn.", "Chúng tôi chơi xích đu.", "Nắng ấm áp lắm.", "Thật là vui!", "Tuyệt vời!"],
                ],
            },
            3: {
                "title": "Cuộc phiêu lưu kỳ thú",
                "stories": [
                    ["Sáng nay, tôi quyết định khám phá khu rừng sau nhà.", "Cây cối cao lớn và chim hót những bài ca hay.", "Tôi đi sâu vào rừng, cảm thấy tò mò và hào hứng.", "Cuộc phiêu lưu dạy tôi rằng thiên nhiên thật kỳ diệu!", "Thật tuyệt vời!"],
                ],
            },
        },
    },
    "ru": {
        "name": "Russian",
        "native_name": "Русский",
        "first_person": "Я",
        "level_examples": {
            1: {
                "title": "Счастливый день",
                "stories": [
                    ["Я вижу собаку.", "Гав-гав!", "Собака большая.", "Мы бежим.", "Весело!"],
                ],
            },
            2: {
                "title": "Веселье в парке",
                "stories": [
                    ["Сегодня я пошёл в парк с другом.", "Мы качались на качелях.", "Солнце было тёплым.", "Было очень весело!", "Ура!"],
                ],
            },
            3: {
                "title": "Удивительное приключение",
                "stories": [
                    ["Утром я решил исследовать лес за домом.", "Деревья были высокими, и птицы пели красиво.", "Чем глубже я заходил в лес, тем интереснее было.", "Это приключение показало мне, что природа полна чудес!", "Удивительно!"],
                ],
            },
        },
    },
    "th": {
        "name": "Thai",
        "native_name": "ไทย",
        "first_person": "ฉัน/ผม",
        "level_examples": {
            1: {
                "title": "วันที่มีความสุข",
                "stories": [
                    ["ฉันเห็นสุนัข", "โฮ่งโฮ่ง!", "สุนัขตัวใหญ่", "เราวิ่ง", "สนุกมาก!"],
                ],
            },
            2: {
                "title": "สนุกที่สวนสาธารณะ",
                "stories": [
                    ["วันนี้ฉันไปสวนสาธารณะกับเพื่อน", "เราเล่นชิงช้า", "แดดอุ่นสบาย", "สนุกมากเลย!", "เยี่ยมเลย!"],
                ],
            },
            3: {
                "title": "การผจญภัยมหัศจรรย์",
                "stories": [
                    ["เช้านี้ ฉันตัดสินใจไปสำรวจป่าหลังบ้าน", "ต้นไม้สูงใหญ่และนกร้องเพลงไพเราะ", "ฉันเดินลึกเข้าไปในป่า รู้สึกตื่นเต้นมาก", "การผจญภัยนี้สอนฉันว่าธรรมชาติเต็มไปด้วยสิ่งมหัศจรรย์!", "น่าทึ่งมาก!"],
                ],
            },
        },
    },
}


def get_language_config(language_code: str) -> Dict[str, Any]:
    """언어 코드에 해당하는 설정 반환"""
    if language_code not in LANGUAGE_CONFIG:
        # 지원하지 않는 언어는 영어로 fallback
        return LANGUAGE_CONFIG["en"]
    return LANGUAGE_CONFIG[language_code]


@dataclass
class GenerateStoryPrompt:
    diary_entries: list[str]
    level: int = 1  # 기본값 레벨 1 (4-5세)
    target_language: str = "en"  # 목표 언어 코드

    def render(self) -> str:
        diary_text = "\n".join(f"* {entry}" for entry in self.diary_entries)
        settings = get_difficulty_settings(self.level)
        lang = get_language_config(self.target_language)

        # 영어는 상세 템플릿, 다른 언어는 범용 템플릿 사용
        if self.target_language == "en":
            level_prompt = get_level_prompt_template(self.level)
        else:
            level_prompt = get_universal_level_prompt(self.level)

        # 언어별 레벨별 예시
        example_section = self._format_level_example(lang)

        return f"""
**[역할]**
당신은 아이들({settings.target_age}세)을 위한 **{lang['native_name']}** 동화를 작성하는 전문 작가입니다.

{level_prompt}

**[목표]**
아래 [오늘의 일기]에 나열된 사건들을 바탕으로, 1인칭 주인공 시점('{lang['first_person']}')의 즐거운 **{lang['native_name']}** 동화를 만들고, 동화에 어울리는 짧은 **{lang['native_name']}** 제목(최대 20자)을 생성해야 합니다.

**[필수 규칙]**
1. **제목:** 동화 내용을 요약하는 간단한 **{lang['native_name']}** 제목 (최대 20자)
2. **형식:** 모든 문장은 마침표로 끝나야 함
3. **언어:** 반드시 **{lang['native_name']}**로만 작성 (다른 언어 사용 금지)
4. **입력 언어:** 입력은 어떤 언어든 가능 (AI가 {lang['native_name']}로 변환)
5. **출력 형식:** 아래 JSON 형식 준수

{example_section}

---

**[오늘의 일기]**
{diary_text}
"""

    def _format_level_example(self, lang: Dict[str, Any]) -> str:
        """언어별 레벨별 예시 포맷팅"""
        level_examples = lang.get("level_examples", {})
        example = level_examples.get(self.level, {})

        if not example:
            # 예시가 없으면 기본 영어 예시 사용
            en_lang = LANGUAGE_CONFIG["en"]
            example = en_lang["level_examples"].get(self.level, {})

        title = example.get("title", "Example Title")
        stories = example.get("stories", [[]])

        # stories를 JSON 형식으로 포맷팅
        stories_json = []
        for page in stories:
            page_json = ", ".join(f'"{s}"' for s in page)
            stories_json.append(f"[{page_json}]")

        return f"""**[{lang['native_name']} 예시 - 레벨 {self.level}]**

```json
{{
    "title": "{title}",
    "stories": [
        {', '.join(stories_json)}
    ]
}}
```"""
