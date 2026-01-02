"""
Redis Core Module
Redis 연결 관리 및 공통 유틸리티
"""

import logging
from typing import Optional
import redis.asyncio as aioredis
from .config import settings

logger = logging.getLogger(__name__)


class RedisManager:
    """
    Redis 연결 관리자 (Singleton 패턴 권장)
    
    애플리케이션 생명주기(lifespan) 동안 하나의 연결 풀을 유지하고 관리합니다.
    """

    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.redis_url
        self._redis: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        """Redis 연결 초기화"""
        if self._redis:
            return

        try:
            # decode_responses=True를 사용하여 자동으로 bytes -> str 변환
            self._redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # 연결 테스트
            await self._redis.ping()
            logger.info("RedisManager connected", extra={"redis_url": self.redis_url})
        except Exception as e:
            logger.error(
                f"Failed to connect to Redis: {e}",
                extra={"redis_url": self.redis_url, "error": str(e)},
                exc_info=True
            )
            raise

    async def disconnect(self) -> None:
        """Redis 연결 종료"""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("RedisManager disconnected")

    @property
    def client(self) -> aioredis.Redis:
        """
        Redis 클라이언트 반환
        
        연결이 없으면 런타임 에러 발생 (connect() 호출 필수)
        """
        if not self._redis:
            raise RuntimeError("Redis client is not initialized. Call connect() first.")
        return self._redis


# 전역 Redis Manager 인스턴스 (lazy initialization in main.py)
_redis_manager: Optional[RedisManager] = None


def get_redis_manager() -> RedisManager:
    """전역 Redis Manager 반환"""
    global _redis_manager
    if not _redis_manager:
        _redis_manager = RedisManager()
    return _redis_manager


def get_redis_client() -> aioredis.Redis:
    """
    Redis 클라이언트 의존성 주입용 함수
    """
    manager = get_redis_manager()
    return manager.client
