"""
Kling Video Provider
Kling AI API를 사용한 비디오 생성
"""

import asyncio
import json
from typing import Optional, Dict, Any
import httpx

from ..base import VideoGenerationProvider
from ....core.config import settings


class KlingVideoProvider(VideoGenerationProvider):
    """
    Kling Video Provider
    
    Kling AI API를 사용하여 이미지로부터 비디오를 생성
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: Kling API Key (None일 경우 settings에서 가져옴)
        """
        self.api_key = api_key or settings.kling_api_key
        self.base_url = "https://api.klingai.com/v1"  # 가상의 URL, 실제 API 문서 확인 필요
        self.timeout = httpx.Timeout(settings.http_timeout, read=settings.http_read_timeout)

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
            str: 작업 ID
        """
        # 이미지 데이터를 Base64로 인코딩하거나 멀티파트 폼 데이터로 전송
        # 여기서는 멀티파트 폼 데이터 가정
        
        files = {"image": ("input.jpg", image_data, "image/jpeg")}
        data = {
            "duration": str(duration),
            "mode": mode,
        }
        if prompt:
            data["prompt"] = prompt

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # 1. 이미지 업로드 및 생성 요청
            response = await client.post(
                f"{self.base_url}/videos/image2video",
                headers={"Authorization": f"Bearer {self.api_key}"},
                data=data,
                files=files,
            )
            response.raise_for_status()
            
        result = response.json()
        return result.get("task_id")

    async def check_video_status(self, task_id: str) -> Dict[str, Any]:
        """
        비디오 생성 상태 확인

        Args:
            task_id: 작업 ID

        Returns:
            Dict[str, Any]: {
                "status": str,
                "progress": int,
                "video_url": Optional[str],
                "error": Optional[str]
            }
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/videos/{task_id}",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()

        result = response.json()
        
        # Kling API 응답을 표준 형식으로 변환
        status_map = {
            "succeeded": "completed",
            "processing": "processing",
            "pending": "pending",
            "failed": "failed"
        }
        
        api_status = result.get("status", "pending")
        standard_status = status_map.get(api_status, "pending")
        
        return {
            "status": standard_status,
            "progress": result.get("progress", 0),
            "video_url": result.get("output", {}).get("url"),
            "error": result.get("error_msg")
        }

    async def download_video(self, video_url: str) -> bytes:
        """
        생성된 비디오 다운로드

        Args:
            video_url: 비디오 URL

        Returns:
            bytes: 비디오 바이너리 데이터
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(video_url)
            response.raise_for_status()
            return response.content
