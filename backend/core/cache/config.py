"""
aiocache Configuration
aiocache 설정
"""

from aiocache import Cache, caches
from aiocache.serializers import JsonSerializer
from ..config import settings

def get_cache_config() -> dict:
    """
    aiocache 설정 반환
    
    Returns:
        dict: aiocache 설정 딕셔너리
    """
    return {
        "cache": Cache.REDIS,
        "endpoint": settings.redis_host,
        "port": settings.redis_port,
        "timeout": 1,
        "serializer": JsonSerializer(),
    }

def initialize_cache():
    """
    aiocache 초기화
    lifespan에서 호출
    """
    caches.set_config({
        "default": get_cache_config()
    })

