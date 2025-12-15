"""
Resource Limiters - Global Semaphores for Rate Limiting
서버 전체 리소스 사용량 제어 (동시성 제한)
"""

import asyncio
from typing import Optional
from .config import settings


class ResourceLimiters:
    """
    글로벌 리소스 제한자 (싱글톤 패턴)

    서버 전체에서 공유되는 세마포어를 관리하여 외부 API 호출량 제어

    Attributes:
        video_generation: 비디오 생성 API 동시 호출 제한
        (향후 확장: image_generation, tts_generation 등)
    """

    _instance: Optional['ResourceLimiters'] = None

    def __new__(cls):
        """싱글톤 패턴 구현"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """세마포어 초기화 (최초 1회만)"""
        if self._initialized:
            return

        # Video Generation Semaphore
        self.video_generation = asyncio.Semaphore(
            settings.video_generation_limit
        )

        self._initialized = True

    def reset(self):
        """테스트용: 세마포어 재초기화"""
        self.video_generation = asyncio.Semaphore(
            settings.video_generation_limit
        )


# 글로벌 싱글톤 인스턴스
_limiters = ResourceLimiters()


def get_limiters() -> ResourceLimiters:
    """
    글로벌 리소스 제한자 반환

    Returns:
        ResourceLimiters: 서버 전체 세마포어 관리 객체

    Example:
        limiters = get_limiters()
        async with limiters.video_generation:
            result = await video_provider.generate_video(...)
    """
    return _limiters
