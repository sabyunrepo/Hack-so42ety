"""
Cache Metrics
캐시 메트릭 수집 및 모니터링
"""

from typing import Dict
from collections import defaultdict
import time
import threading


class CacheMetrics:
    """캐시 메트릭 수집"""
    
    def __init__(self):
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0
        self.set_operations = 0
        self.delete_operations = 0
        self.total_get_time = 0.0
        self.total_set_time = 0.0
        self.total_delete_time = 0.0
        self.errors = 0
        self._key_stats = defaultdict(lambda: {"hits": 0, "misses": 0})
    
    def record_hit(self, key: str, duration: float):
        """캐시 히트 기록"""
        with self._lock:
            self.hits += 1
            self.total_get_time += duration
            self._key_stats[key]["hits"] += 1
    
    def record_miss(self, key: str, duration: float):
        """캐시 미스 기록"""
        with self._lock:
            self.misses += 1
            self.total_get_time += duration
            self._key_stats[key]["misses"] += 1
    
    def record_set(self, key: str, duration: float):
        """캐시 저장 기록"""
        with self._lock:
            self.set_operations += 1
            self.total_set_time += duration
    
    def record_delete(self, key: str, duration: float):
        """캐시 삭제 기록"""
        with self._lock:
            self.delete_operations += 1
            self.total_delete_time += duration
    
    def record_error(self, key: str):
        """캐시 오류 기록"""
        with self._lock:
            self.errors += 1
    
    @property
    def hit_rate(self) -> float:
        """캐시 히트율"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    @property
    def avg_get_time(self) -> float:
        """평균 조회 시간 (초)"""
        total = self.hits + self.misses
        return self.total_get_time / total if total > 0 else 0.0
    
    @property
    def avg_set_time(self) -> float:
        """평균 저장 시간 (초)"""
        return self.total_set_time / self.set_operations if self.set_operations > 0 else 0.0
    
    @property
    def avg_delete_time(self) -> float:
        """평균 삭제 시간 (초)"""
        return self.total_delete_time / self.delete_operations if self.delete_operations > 0 else 0.0
    
    def get_stats(self) -> Dict:
        """전체 통계 반환"""
        with self._lock:
            return {
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": self.hit_rate,
                "set_operations": self.set_operations,
                "delete_operations": self.delete_operations,
                "errors": self.errors,
                "avg_get_time_ms": self.avg_get_time * 1000,
                "avg_set_time_ms": self.avg_set_time * 1000,
                "avg_delete_time_ms": self.avg_delete_time * 1000,
                "total_operations": self.hits + self.misses + self.set_operations + self.delete_operations,
            }
    
    def get_key_stats(self, key: str) -> Dict:
        """특정 키의 통계 반환"""
        with self._lock:
            stats = self._key_stats.get(key, {"hits": 0, "misses": 0})
            total = stats["hits"] + stats["misses"]
            return {
                "key": key,
                "hits": stats["hits"],
                "misses": stats["misses"],
                "hit_rate": stats["hits"] / total if total > 0 else 0.0,
            }
    
    def reset(self):
        """통계 초기화"""
        with self._lock:
            self.hits = 0
            self.misses = 0
            self.set_operations = 0
            self.delete_operations = 0
            self.total_get_time = 0.0
            self.total_set_time = 0.0
            self.total_delete_time = 0.0
            self.errors = 0
            self._key_stats.clear()


# 전역 메트릭 인스턴스
cache_metrics = CacheMetrics()

