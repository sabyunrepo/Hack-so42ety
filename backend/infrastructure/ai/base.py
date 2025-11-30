"""
AI Provider Abstract Base Classes
모든 AI 제공자가 구현해야 하는 인터페이스 정의
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from enum import Enum


class AIProviderType(str, Enum):
    """AI 제공자 타입"""

    GOOGLE = "google"
    OPENAI = "openai"
    CUSTOM = "custom"


class TTSProviderType(str, Enum):
    """TTS 제공자 타입"""

    ELEVENLABS = "elevenlabs"
    CUSTOM = "custom"


class VideoProviderType(str, Enum):
    """비디오 제공자 타입"""

    KLING = "kling"
    CUSTOM = "custom"


# ==================== Story Generation Provider ====================


class StoryGenerationProvider(ABC):
    """
    스토리 생성 Provider 인터페이스

    AI 모델을 사용하여 스토리를 생성하는 Provider
    """

    @abstractmethod
    async def generate_story(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        max_length: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        스토리 생성

        Args:
            prompt: 스토리 생성 프롬프트
            context: 추가 컨텍스트 (사용자 정보, 이전 스토리 등)
            max_length: 최대 토큰 길이
            temperature: 생성 온도 (0.0~1.0)

        Returns:
            str: 생성된 스토리 텍스트
        """
        pass

    @abstractmethod
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
            Dict[str, Any]: {
                "story": str,
                "image_prompts": List[str],
                "metadata": Dict[str, Any]
            }
        """
        pass


# ==================== Image Generation Provider ====================


class ImageGenerationProvider(ABC):
    """
    이미지 생성 Provider 인터페이스

    텍스트 프롬프트로부터 이미지를 생성하는 Provider
    """

    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        quality: str = "standard",
        style: Optional[str] = None,
    ) -> bytes:
        """
        이미지 생성

        Args:
            prompt: 이미지 생성 프롬프트
            width: 이미지 너비
            height: 이미지 높이
            quality: 품질 (standard, hd)
            style: 스타일 (vivid, natural 등)

        Returns:
            bytes: 생성된 이미지 바이너리 데이터
        """
        pass

    @abstractmethod
    async def generate_images_batch(
        self,
        prompts: List[str],
        width: int = 1024,
        height: int = 1024,
    ) -> List[bytes]:
        """
        여러 이미지 배치 생성

        Args:
            prompts: 이미지 프롬프트 리스트
            width: 이미지 너비
            height: 이미지 높이

        Returns:
            List[bytes]: 생성된 이미지 바이너리 데이터 리스트
        """
        pass

    @abstractmethod
    async def generate_image_from_image(
        self,
        image_data: bytes,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        style: Optional[str] = None,
    ) -> bytes:
        """
        이미지-to-이미지 생성

        Args:
            image_data: 입력 이미지 바이너리
            prompt: 이미지 생성 프롬프트
            width: 너비
            height: 높이
            style: 스타일

        Returns:
            bytes: 생성된 이미지 바이너리 데이터
        """
        pass


# ==================== TTS Provider ====================


class TTSProvider(ABC):
    """
    TTS (Text-to-Speech) Provider 인터페이스

    텍스트를 음성으로 변환하는 Provider
    """

    @abstractmethod
    async def text_to_speech(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None,
        language: str = "en",
        speed: float = 1.0,
    ) -> bytes:
        """
        텍스트를 음성으로 변환

        Args:
            text: 변환할 텍스트
            voice_id: 음성 ID (provider별 다름)
            model_id: 모델 ID
            language: 언어 코드 (en, ko 등)
            speed: 재생 속도 (0.5~2.0)

        Returns:
            bytes: 오디오 바이너리 데이터 (mp3, wav 등)
        """
        pass

    @abstractmethod
    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        사용 가능한 음성 목록 조회

        Returns:
            List[Dict[str, Any]]: [
                {
                    "voice_id": str,
                    "name": str,
                    "language": str,
                    "gender": str,
                    "preview_url": Optional[str]
                }
            ]
        """
        pass


# ==================== Video Generation Provider ====================


class VideoGenerationProvider(ABC):
    """
    비디오 생성 Provider 인터페이스

    이미지로부터 비디오를 생성하는 Provider
    """

    @abstractmethod
    async def generate_video(
        self,
        image_data: bytes,
        prompt: Optional[str] = None,
        duration: int = 5,
        mode: str = "std",
    ) -> str:
        """
        비디오 생성 작업 시작

        Args:
            image_data: 입력 이미지 바이너리 데이터
            prompt: 비디오 생성 프롬프트 (옵션)
            duration: 비디오 길이 (초)
            mode: 생성 모드 (std, pro 등)

        Returns:
            str: 작업 ID (비동기 작업)
        """
        pass

    @abstractmethod
    async def check_video_status(self, task_id: str) -> Dict[str, Any]:
        """
        비디오 생성 상태 확인

        Args:
            task_id: 작업 ID

        Returns:
            Dict[str, Any]: {
                "status": str,  # pending, processing, completed, failed
                "progress": int,  # 0~100
                "video_url": Optional[str],
                "error": Optional[str]
            }
        """
        pass

    @abstractmethod
    async def download_video(self, video_url: str) -> bytes:
        """
        생성된 비디오 다운로드

        Args:
            video_url: 비디오 URL

        Returns:
            bytes: 비디오 바이너리 데이터
        """
        pass
