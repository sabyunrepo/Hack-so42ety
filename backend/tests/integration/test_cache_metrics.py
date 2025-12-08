"""
Cache Metrics Integration Tests
캐시 메트릭 통합 테스트
"""

import pytest
from backend.core.cache.metrics import cache_metrics, CacheMetrics


@pytest.mark.asyncio
async def test_cache_metrics_recording():
    """캐시 메트릭 기록 테스트"""
    # 메트릭 초기화
    cache_metrics.reset()
    
    # 히트 기록
    cache_metrics.record_hit("test:key1", 0.001)
    cache_metrics.record_hit("test:key1", 0.002)
    
    # 미스 기록
    cache_metrics.record_miss("test:key2", 0.005)
    
    # 저장 기록
    cache_metrics.record_set("test:key1", 0.003)
    
    # 삭제 기록
    cache_metrics.record_delete("test:key1", 0.001)
    
    # 통계 확인
    stats = cache_metrics.get_stats()
    
    assert stats["hits"] == 2
    assert stats["misses"] == 1
    assert stats["hit_rate"] == pytest.approx(2/3, rel=0.01)
    assert stats["set_operations"] == 1
    assert stats["delete_operations"] == 1
    assert stats["avg_get_time_ms"] > 0
    assert stats["avg_set_time_ms"] > 0
    assert stats["avg_delete_time_ms"] > 0


@pytest.mark.asyncio
async def test_cache_metrics_key_stats():
    """키별 캐시 메트릭 테스트"""
    # 메트릭 초기화
    cache_metrics.reset()
    
    # 특정 키에 대한 히트/미스 기록
    cache_metrics.record_hit("tts:voices", 0.001)
    cache_metrics.record_hit("tts:voices", 0.002)
    cache_metrics.record_miss("tts:voices", 0.005)
    
    # 키별 통계 확인
    key_stats = cache_metrics.get_key_stats("tts:voices")
    
    assert key_stats["key"] == "tts:voices"
    assert key_stats["hits"] == 2
    assert key_stats["misses"] == 1
    assert key_stats["hit_rate"] == pytest.approx(2/3, rel=0.01)


@pytest.mark.asyncio
async def test_cache_metrics_reset():
    """캐시 메트릭 초기화 테스트"""
    # 메트릭 기록
    cache_metrics.record_hit("test:key", 0.001)
    cache_metrics.record_miss("test:key", 0.002)
    
    # 초기화
    cache_metrics.reset()
    
    # 통계 확인
    stats = cache_metrics.get_stats()
    
    assert stats["hits"] == 0
    assert stats["misses"] == 0
    assert stats["hit_rate"] == 0.0
    assert stats["total_operations"] == 0

