"""
Video Prompt Generator
비디오 생성을 위한 프롬프트 클래스
"""
from dataclasses import dataclass
from typing import List


@dataclass
class GenerateVideoPrompt:
    """
    비디오 생성 프롬프트 클래스

    Attributes:
        dialogues: 페이지 대사 리스트 (Scene Description에 포함)
    """

    dialogues: List[str]

    def render(self) -> str:
        """프롬프트 렌더링"""
        scene_description = " ".join(self.dialogues)

        return f"""Use the provided image as the single and exact reference. Preserve the character's identity, proportions, silhouette, and drawing style. Do not introduce new characters, objects, or background elements.
Scene Description: "{scene_description}"
The camera is static with no zoom or pan."""
