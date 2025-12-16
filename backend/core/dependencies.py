"""
Core Dependencies
공통 의존성 주입 함수
"""

from typing import Optional
from fastapi import Depends
from backend.core.config import settings
from backend.infrastructure.storage.local import LocalStorageService
from backend.infrastructure.storage.s3 import S3StorageService
from backend.infrastructure.ai.factory import AIProviderFactory
from backend.core.events.redis_streams_bus import RedisStreamsEventBus
from backend.core.cache.service import CacheService

# 전역 Event Bus 참조 (main.py의 lifespan에서 설정)
_event_bus: Optional[RedisStreamsEventBus] = None


def set_event_bus(event_bus_instance: RedisStreamsEventBus):
    """Event Bus 설정 (lifespan에서 호출)"""
    global _event_bus
    _event_bus = event_bus_instance


def get_event_bus() -> RedisStreamsEventBus:
    """Event Bus 의존성 주입"""
    if not _event_bus:
        raise RuntimeError("Event bus not initialized. Check if lifespan started correctly.")
    return _event_bus


# 전역 CacheService 참조
_cache_service: Optional[CacheService] = None


def get_cache_service(
    event_bus: RedisStreamsEventBus = Depends(get_event_bus)
) -> CacheService:
    """CacheService 의존성 주입 (Singleton)"""
    global _cache_service
    if not _cache_service:
        _cache_service = CacheService(event_bus=event_bus)
    return _cache_service


def get_storage_service():
    """
    스토리지 서비스 의존성

    설정에 따라 LocalStorageService 또는 S3StorageService 반환

    Returns:
        AbstractStorageService: 스토리지 서비스 인스턴스
    """
    if settings.storage_provider == "s3":
        return S3StorageService()
    return LocalStorageService()


def get_ai_factory() -> AIProviderFactory:
    """
    AI Factory 의존성

    Returns:
        AIProviderFactory: AI Provider Factory 인스턴스
    """
    return AIProviderFactory()

