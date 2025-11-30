"""
Custom Model Provider
자체 학습 모델을 위한 Placeholder Provider
"""

from typing import Optional, Dict, Any, List
from ..base import StoryGenerationProvider


class CustomModelProvider(StoryGenerationProvider):
    """
    Custom Model Provider
    
    추후 자체 학습된 LLM을 서빙할 때 사용할 Provider
    현재는 단순한 Placeholder로 동작
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path

    async def generate_story(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        max_length: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        스토리 생성 (Placeholder)
        """
        return f"""
        [Custom Model Placeholder]
        This is a generated story based on prompt: {prompt}
        
        Once the custom model is trained and deployed, this method will call the model inference API.
        """

    async def generate_story_with_images(
        self,
        prompt: str,
        num_images: int = 3,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        스토리 + 이미지 프롬프트 생성 (Placeholder)
        """
        return {
            "story": await self.generate_story(prompt, context),
            "image_prompts": [f"Custom model image prompt for {prompt} - {i+1}" for i in range(num_images)],
            "metadata": {
                "provider": "custom",
                "model_path": self.model_path
            }
        }
