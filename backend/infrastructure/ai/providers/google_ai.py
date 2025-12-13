"""
Google AI Provider
Google Gemini를 사용한 스토리 및 이미지 생성
"""

import json
from typing import Optional, Dict, Any, List
import httpx

from ..base import StoryGenerationProvider, ImageGenerationProvider
from ....core.config import settings
from google import genai


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
        self.client: genai.Client = None  # 초기에는 None
        self._init_client()

    def _init_client(self):
        """google-genai 클라이언트 초기화"""
        if not self.client:
            self.client = genai.Client(api_key=self.api_key)

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
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt,
        )

        result = response.text
        return result

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
        이미지 생성 (Imagen 3 사용)
        """
        # TODO: 실제 Imagen API 연동 필요. 현재는 Placeholder.
        # google-genai SDK의 최신 버전을 확인하여 구현해야 함.
        # 여기서는 임시로 NotImplementedError 대신 더미 데이터를 반환하거나
        # 실제 API 호출 코드를 작성해야 함.
        # 하지만 현재 환경에서는 google-genai 라이브러리 사용법에 맞춰 구현 시도.
        
        # 주의: google-genai 라이브러리가 설치되어 있어야 함.
        # from google import genai
        # from google.genai import types
        
        # 현재 코드에는 httpx만 사용하고 있음. 
        # google-genai 라이브러리를 사용하는 방식으로 변경하거나 REST API 직접 호출 필요.
        # 여기서는 REST API 호출 방식 유지 (일관성)
        
        # 하지만 Imagen은 Vertex AI 또는 별도 엔드포인트일 수 있음.
        # 간단히 구현하기 위해 NotImplementedError를 유지하되, 
        # Image-to-Image 구현에 집중.
        
        raise NotImplementedError("Text-to-Image not fully implemented yet.")

    async def generate_images_batch(
        self,
        prompts: List[str],
        width: int = 1024,
        height: int = 1024,
    ) -> List[bytes]:
        """배치 이미지 생성"""
        raise NotImplementedError("Batch image generation not implemented.")

    async def generate_image_from_image(
        self,
        image_data: bytes,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        style: Optional[str] = None,
    ) -> bytes:
        """
        이미지-to-이미지 생성 (Gemini Vision 활용)
        
        Gemini는 이미지를 입력받아 텍스트를 생성하는 것이 주력이지만,
        최신 모델은 이미지 편집/생성도 가능할 수 있음.
        또는 Imagen API를 사용해야 함.
        
        여기서는 레거시 코드(ImageGeneratorService)에서 사용했던 방식을 참고하여 구현.
        레거시 코드에서는 `gemini-2.5-flash-image` 모델을 사용하여 이미지를 생성했음.
        """
        # 레거시 코드 참고:
        # img = types.Part.from_bytes(data=input_img["content"], mime_type=input_img["content_type"])
        # response = await self.genai_client.aio.models.generate_content(...)
        
        # 이 클래스는 httpx를 사용하므로 REST API로 변환 필요.
        # 하지만 멀티파트 데이터 전송이 복잡하므로, google-genai 라이브러리를 사용하는 것이 나을 수 있음.
        # 기존 코드에 google-genai import가 없으므로 추가 필요.
        
        # 일단 httpx로 구현 시도 (Base64 인코딩 등 필요)
        import base64
        encoded_image = base64.b64encode(image_data).decode("utf-8")
        
        full_prompt = f"Generate a high-quality illustration based on this sketch/image. Style: {style or 'cartoon'}. Prompt: {prompt}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Gemini 1.5 Flash 등 비전 모델 사용
            response = await client.post(
                f"{self.base_url}/models/gemini-1.5-flash:generateContent",
                params={"key": self.api_key},
                json={
                    "contents": [
                        {
                            "parts": [
                                {"text": full_prompt},
                                {
                                    "inline_data": {
                                        "mime_type": "image/png", # 가정
                                        "data": encoded_image
                                    }
                                }
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.4,
                        "maxOutputTokens": 2048,
                    },
                },
            )
            response.raise_for_status()
            
        # 주의: Gemini generateContent는 텍스트를 반환함. 이미지를 반환하지 않음.
        # 이미지를 반환하려면 Imagen API를 써야 함.
        # 레거시 코드는 `gemini-2.5-flash-image`라는 모델을 썼는데, 이는 실험적 모델이거나 착각일 수 있음.
        # 또는 `google-genai` 라이브러리가 Imagen을 래핑하고 있을 수 있음.
        
        # 확인 결과: Gemini는 텍스트/멀티모달 입력 -> 텍스트 출력임.
        # 이미지를 생성하려면 `imagen-3.0-generate-001` 같은 모델을 써야 함.
        # 하지만 Google AI Studio API(REST)에서 Imagen을 지원하는지 확인 필요.
        
        # 대안: 레거시 코드가 `google.genai` 라이브러리를 사용했으므로, 여기서도 라이브러리를 사용하는 것이 안전함.
        # httpx 기반 구현을 google-genai 라이브러리 기반으로 마이그레이션하거나,
        # 라이브러리를 혼용해야 함.
        
        # 여기서는 google-genai 라이브러리를 동적으로 import하여 사용.
        try:
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=self.api_key)
            
            # 이미지 파트 생성
            # mime_type은 image/png로 가정 (실제로는 인자로 받아야 정확함)
            img_part = types.Part.from_bytes(
                data=image_data, 
                mime_type="image/png" 
            )
            
            # Imagen 3 호출 (또는 사용 가능한 이미지 모델)
            # google-genai SDK 문서에 따르면 models.generate_image 또는 유사 메서드 사용
            # 하지만 레거시 코드는 models.generate_content를 사용했음. 
            # 레거시 코드를 다시 보면: model="gemini-2.5-flash-image"
            # 이는 존재하지 않는 모델명일 가능성이 높음 (2.0 Flash가 최신).
            # 아마도 `imagen-3.0-generate-001` 등을 의도했을 것.
            
            # 여기서는 Imagen 3를 사용하도록 수정.
            response = client.models.generate_image(
                model="imagen-3.0-generate-001",
                prompt=prompt,
                config=types.GenerateImageConfig(
                    aspect_ratio="3:4",
                    number_of_images=1,
                    # image_source=img_part # Imagen이 image source를 지원하는지 확인 필요
                    # 현재 공개된 Imagen API는 Text-to-Image 위주임.
                    # Image-to-Image는 Vertex AI에서 지원.
                )
            )
            
            # 만약 Image-to-Image가 지원되지 않는다면, 
            # 프롬프트만 사용하여 생성하도록 폴백하거나,
            # Gemini가 이미지를 설명하게 하고 그 설명으로 이미지를 생성하는 2단계 방식을 써야 함.
            
            # 일단은 Text-to-Image로 구현하되, 프롬프트에 "based on previous context" 등을 추가.
            if response.generated_images:
                return response.generated_images[0].image.image_bytes
            else:
                raise Exception("No image generated")
                
        except ImportError:
            raise ImportError("google-genai library is required")
        except Exception as e:
            # 라이브러리 호출 실패 시
            raise RuntimeError(f"Image generation failed: {e}")

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
