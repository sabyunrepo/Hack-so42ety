"""
Metrics API Endpoints
메트릭 조회 API
"""

from fastapi import APIRouter
from backend.core.cache.metrics import cache_metrics

router = APIRouter()


@router.get("/cache")
async def get_cache_metrics():
    """
    캐시 메트릭 조회
    
    Returns:
        dict: 캐시 통계 정보
            - hits: 캐시 히트 횟수
            - misses: 캐시 미스 횟수
            - hit_rate: 캐시 히트율 (0.0 ~ 1.0)
            - set_operations: 저장 횟수
            - delete_operations: 삭제 횟수
            - errors: 오류 횟수
            - avg_get_time_ms: 평균 조회 시간 (밀리초)
            - avg_set_time_ms: 평균 저장 시간 (밀리초)
            - avg_delete_time_ms: 평균 삭제 시간 (밀리초)
            - total_operations: 전체 작업 횟수
    """
    return cache_metrics.get_stats()


@router.get("/cache/{key}")
async def get_cache_key_metrics(key: str):
    """
    특정 캐시 키의 메트릭 조회
    
    Args:
        key: 캐시 키
        
    Returns:
        dict: 키별 통계 정보
            - key: 캐시 키
            - hits: 히트 횟수
            - misses: 미스 횟수
            - hit_rate: 히트율 (0.0 ~ 1.0)
    """
    return cache_metrics.get_key_stats(key)

