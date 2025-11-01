"""
Story Generator Service Module
AI 기반 스토리 생성 및 페이지 조립 전담 서비스
"""

from typing import List, Optional
from google import genai
from google.genai import types

from ..core.config import settings
from ..core.logging import get_logger
from ..prompts.generate_story_prompt import GenerateStoryPrompt
from ..api.schemas import create_stories_response_schema
from ..prompts.generate_tts_expression_prompt import EnhanceAudioPrompt
from ..api.schemas import create_stories_response_schema, TTSExpressionResponse

logger = get_logger(__name__)


class StoryGeneratorService:
    """AI 기반 스토리 생성 및 페이지 조립 서비스"""

    def __init__(self, genai_client: Optional[genai.Client] = None):
        """
        StoryGeneratorService 초기화

        Args:
            genai_client: Google GenAI 클라이언트 (선택적)
        """
        self.genai_client = genai_client
        if genai_client:
            logger.info("StoryGeneratorService initialized with GenAI client")
        else:
            logger.warning(
                "StoryGeneratorService initialized without GenAI client - AI features disabled"
            )

    async def generate_story_with_ai(self, input_texts: List[str]) -> dict:
        """
        GenAI API를 호출하여 동화책 시나리오 생성

        입력 텍스트 개수에 따라 자동으로 페이지 수와 대사 수 제한을 설정합니다.

        Args:
            input_texts: 시나리오 생성을 위한 입력 텍스트 리스트

        Returns:
            dict: {"stories": List[List[str]], "title": str} 형태의 결과
        """
        if not self.genai_client:
            logger.error("GenAI client is not initialized")
            return {"stories": [[] for _ in input_texts], "title": "Untitled Story"}

        try:
            # 입력 텍스트 개수를 기반으로 자동으로 max_pages 설정
            max_pages = len(input_texts)

            # 페이지당 최대 대사 수 설정 (고정값 또는 동적 계산 가능)
            max_dialogues_per_page = 2  # 필요에 따라 조정 가능

            # 동적 스키마 생성 (title 필드 포함)
            response_schema = create_stories_response_schema(
                max_pages=max_pages,
                max_dialogues_per_page=max_dialogues_per_page,
                max_title_length=20,
            )

            prompt = GenerateStoryPrompt(diary_entries=input_texts).render()
            logger.info(
                f"[StoryGeneratorService] Calling GenAI API for story generation "
                f"(max_pages={max_pages}, max_dialogues_per_page={max_dialogues_per_page}, max_title_length=20)"
            )
            logger.debug(f"[StoryGeneratorService] Prompt: {prompt}")

            response = await self.genai_client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=0
                    ),  # Disables thinking
                    temperature=0.1,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                ),
            )
            logger.info(f"[StoryGeneratorService] GenAI API call completed: {response}")
            parsed = response.parsed
            story_result = {"stories": parsed.stories, "title": parsed.title}

            # TTS Expression 가공 단계 (자동 실행)
            logger.info("[StoryGeneratorService] Starting TTS expression generation")

            enhanced_result = await self._generate_expression_with_story(story_result)

            # 감정 태그가 추가된 스토리 반환
            return enhanced_result
        except Exception as e:
            logger.error(
                f"[StoryGeneratorService] GenAI story generation failed: {e}",
                exc_info=True,
            )
            return {"stories": [[] for _ in input_texts], "title": "Untitled Story"}

    async def _generate_expression_with_story(self, story: dict) -> dict:
        """
        생성된 스토리에 TTS용 감정/표현 태그를 추가

        Args:
            story: {"stories": List[List[str]], "title": str} 형태의 스토리 데이터

        Returns:
            dict: {"stories": List[List[str]], "title": str} 감정 태그가 추가된 스토리
        """
        if not self.genai_client:
            logger.error("GenAI client is not initialized")
            return story

        try:
            stories = story["stories"]
            title = story["title"]

            # 프롬프트 생성
            prompt = EnhanceAudioPrompt(stories=stories, title=title).render()
            logger.info(
                "[StoryGeneratorService] Calling GenAI API for TTS expression generation"
            )
            logger.debug(f"[StoryGeneratorService] TTS Expression Prompt: {prompt}")

            # GenAI API 호출 (정적 스키마 사용)
            response = await self.genai_client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=0
                    ),  # Disables thinking
                    temperature=0.1,
                    response_mime_type="application/json",
                    response_schema=TTSExpressionResponse,
                ),
            )
            logger.info(
                f"[StoryGeneratorService] TTS Expression API call completed: {response}"
            )

            # 파싱된 응답 반환
            parsed = response.parsed
            return {"stories": parsed.stories, "title": parsed.title}

        except Exception as e:
            logger.error(
                f"[StoryGeneratorService] TTS expression generation failed: {e}",
                exc_info=True,
            )
            # 실패 시 원본 스토리 반환
            return story
