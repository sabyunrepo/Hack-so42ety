"""
aiocache Setup Tests
aiocache 초기화 테스트
"""

import pytest
from aiocache import caches, Cache
from aiocache.serializers import JsonSerializer
from backend.core.cache.config import get_cache_config
from backend.core.config import settings


@pytest.mark.asyncio
async def test_aiocache_config():
    """aiocache 설정 테스트"""
    from backend.core.cache.config import get_cache_config_for_test
    config = get_cache_config_for_test()
    
    assert config["cache"] == Cache.REDIS
    assert config["endpoint"] == settings.redis_host
    assert config["port"] == settings.redis_port
    assert isinstance(config["serializer"], JsonSerializer)


@pytest.mark.asyncio
async def test_aiocache_initialization():
    """aiocache 초기화 테스트"""
    from backend.core.cache.config import get_cache_config
    # 설정 적용
    caches.set_config({
        "default": get_cache_config()
    })
    
    # 캐시 인스턴스 가져오기
    cache = caches.get("default")
    
    # 테스트 데이터 저장
    await cache.set("test:key", {"data": "value"}, ttl=60)
    
    # 데이터 조회
    result = await cache.get("test:key")
    assert result == {"data": "value"}
    
    # 데이터 삭제
    await cache.delete("test:key")
    
    # 삭제 확인
    result = await cache.get("test:key")
    assert result is None
    
    await cache.close()

