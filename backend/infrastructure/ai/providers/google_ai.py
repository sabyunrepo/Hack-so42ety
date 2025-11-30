"""
Google AI Provider
Google Gemini를 사용한 스토리 및 이미지 생성
"""

import json
from typing import Optional, Dict, Any, List
import httpx

from ..base import StoryGenerationProvider, ImageGenerationProvider
from ....core.config import settings


class GoogleAIProvider(StoryGenerationProvider, ImageGenerationProvider):
    """
    Google AI (Gemini) Provider

    - Story Generation: Gemini API
    - Image Generation: Imagen API (또는 Gemini Vision)
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: Google API Key (None일 경우 settings에서 가져옴)
        """
        self.api_key = api_key or settings.google_api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.timeout = httpx.Timeout(settings.http_timeout, read=settings.http_read_timeout)

    async def generate_story(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        max_length: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Gemini로 스토리 생성

        Args:
            prompt: 스토리 생성 프롬프트
            context: 추가 컨텍스트
            max_length: 최대 토큰 수
            temperature: 생성 온도

        Returns:
            str: 생성된 스토리
        """
        # 컨텍스트를 프롬프트에 통합
        full_prompt = self._build_story_prompt(prompt, context)

        # Gemini API 호출
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/models/gemini-pro:generateContent",
                params={"key": self.api_key},
                json={
                    "contents": [{"parts": [{"text": full_prompt}]}],
                    "generationConfig": {
                        "temperature": temperature or 0.7,
                        "maxOutputTokens": max_length or 2048,
                    },
                },
            )
            response.raise_for_status()

        result = response.json()
        story = result["candidates"][0]["content"]["parts"][0]["text"]
        return story.strip()

    async def generate_story_with_images(
        self,
        prompt: str,
        num_images: int = 3,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        스토리 + 이미지 프롬프트 생성

        Args:
            prompt: 스토리 생성 프롬프트
            num_images: 생성할 이미지 수
            context: 추가 컨텍스트

        Returns:
            Dict: {
                "story": str,
                "image_prompts": List[str],
                "metadata": Dict[str, Any]
            }
        """
        # 스토리와 이미지 프롬프트를 함께 생성하도록 요청
        full_prompt = f"""
Generate a children's storybook with the following requirements:

Story Prompt: {prompt}

Please provide:
1. A complete story (approximately 200-300 words)
2. {num_images} image prompts for key scenes in the story

Format your response as JSON:
{{
    "story": "the complete story text",
    "image_prompts": ["prompt 1", "prompt 2", "prompt 3"],
    "scene_descriptions": ["scene 1 description", "scene 2 description", "scene 3 description"]
}}
"""

        if context:
            full_prompt += f"\n\nAdditional Context: {json.dumps(context)}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/models/gemini-pro:generateContent",
                params={"key": self.api_key},
                json={
                    "contents": [{"parts": [{"text": full_prompt}]}],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 3072,
                    },
                },
            )
            response.raise_for_status()

        result = response.json()
        generated_text = result["candidates"][0]["content"]["parts"][0]["text"]

        # JSON 파싱 시도
        try:
            # Markdown 코드 블록 제거
            if "```json" in generated_text:
                generated_text = generated_text.split("```json")[1].split("```")[0]
            elif "```" in generated_text:
                generated_text = generated_text.split("```")[1].split("```")[0]

            data = json.loads(generated_text.strip())
            return {
                "story": data["story"],
                "image_prompts": data["image_prompts"],
                "metadata": {
                    "scene_descriptions": data.get("scene_descriptions", []),
                    "num_images": num_images,
                    "provider": "google_ai",
                },
            }
        except (json.JSONDecodeError, KeyError) as e:
            # JSON 파싱 실패 시 폴백
            return {
                "story": generated_text,
                "image_prompts": [f"{prompt} - scene {i+1}" for i in range(num_images)],
                "metadata": {
                    "error": f"JSON parsing failed: {str(e)}",
                    "provider": "google_ai",
                },
            }

    async def generate_image(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        quality: str = "standard",
        style: Optional[str] = None,
    ) -> bytes:
        """
        이미지 생성 (현재는 placeholder)

        Note: Google Imagen API는 별도의 접근 권한이 필요합니다.
              실제 구현 시 Imagen API 또는 다른 이미지 생성 서비스 사용

        Args:
            prompt: 이미지 프롬프트
            width: 너비
            height: 높이
            quality: 품질
            style: 스타일

        Returns:
            bytes: 이미지 바이너리 데이터
        """
        # TODO: Imagen API 또는 다른 이미지 생성 서비스 통합
        raise NotImplementedError(
            "Google Imagen API integration is not yet implemented. "
            "Please use a different image generation provider."
        )

    async def generate_images_batch(
        self,
        prompts: List[str],
        width: int = 1024,
        height: int = 1024,
    ) -> List[bytes]:
        """
        배치 이미지 생성 (현재는 placeholder)

        Args:
            prompts: 이미지 프롬프트 리스트
            width: 너비
            height: 높이

        Returns:
            List[bytes]: 이미지 바이너리 데이터 리스트
        """
        # TODO: 배치 이미지 생성 구현
        raise NotImplementedError(
            "Batch image generation is not yet implemented. "
            "Please generate images individually."
        )

    def _build_story_prompt(self, prompt: str, context: Optional[Dict[str, Any]]) -> str:
        """
        스토리 생성을 위한 전체 프롬프트 구성

        Args:
            prompt: 기본 프롬프트
            context: 컨텍스트

        Returns:
            str: 전체 프롬프트
        """
        base_prompt = f"""
You are a creative children's storybook writer. Generate an engaging, age-appropriate story.

Story Request: {prompt}
"""

        if context:
            if "target_age" in context:
                base_prompt += f"\nTarget Age: {context['target_age']} years old"
            if "genre" in context:
                base_prompt += f"\nGenre: {context['genre']}"
            if "themes" in context:
                base_prompt += f"\nThemes: {', '.join(context['themes'])}"
            if "previous_stories" in context:
                base_prompt += f"\n\nPrevious Stories Context: {context['previous_stories']}"

        base_prompt += "\n\nPlease write a complete, engaging story (200-300 words)."

        return base_prompt
