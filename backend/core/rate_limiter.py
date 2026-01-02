"""
Rate Limiter Service
Redis 기반 속도 제한 서비스 (Sliding Window 알고리즘)
"""

import time
import logging
from typing import Optional, Dict
from dataclasses import dataclass
import redis.asyncio as aioredis
from .config import settings

logger = logging.getLogger(__name__)


@dataclass
class RateLimitResult:
    """
    속도 제한 검사 결과

    Attributes:
        allowed: 요청 허용 여부
        limit: 최대 요청 수
        remaining: 남은 요청 수
        reset_at: 제한 초기화 시간 (Unix timestamp)
        retry_after: 재시도까지 남은 시간 (초) - 제한 초과 시에만 설정됨
    """
    allowed: bool
    limit: int
    remaining: int
    reset_at: int
    retry_after: Optional[int] = None

    def to_headers(self) -> Dict[str, str]:
        """
        HTTP 응답 헤더 딕셔너리로 변환

        Returns:
            Dict[str, str]: X-RateLimit-* 헤더 딕셔너리
        """
        return {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(self.remaining),
            "X-RateLimit-Reset": str(self.reset_at),
        }


class RateLimiterService:
    """
    Redis 기반 속도 제한 서비스

    Sliding Window 알고리즘을 사용하여 분산 환경에서 속도 제한을 구현합니다.
    공유된 Redis 클라이언트를 사용합니다.
    """

    def __init__(self, redis_client: Optional[aioredis.Redis] = None):
        """
        Args:
            redis_client: 공유 Redis 클라이언트 (injectable)
        """
        self.redis = redis_client

    @property
    def _redis(self) -> aioredis.Redis:
        """Redis 클라이언트 Lazy Loading (singleton fallback)"""
        if self.redis:
            return self.redis
        
        # 의존성 주입이 안 된 경우 전역 매니저에서 가져옴
        from .redis import get_redis_client
        try:
            return get_redis_client()
        except RuntimeError:
            # 테스트 환경 등에서 연결이 없는 경우
            logger.warning("Redis client not explicitly initialized. Connecting now...")
            # 여기서는 임시로 연결하지 않고 에러를 내거나, 
            # 테스트를 위해 on-demand connect를 할 수도 있지만 
            # 원칙상 main.py에서 연결된 것을 써야 함.
            raise

    def _make_key(self, identifier: str) -> str:
        """
        Redis 키 생성

        Args:
            identifier: 식별자 (예: "auth:login:192.168.1.1")

        Returns:
            str: Redis 키 (예: "rate_limit:auth:login:192.168.1.1")
        """
        return f"rate_limit:{identifier}"

    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int
    ) -> RateLimitResult:
        """
        속도 제한 검사 (Sliding Window 알고리즘)

        Args:
            key: 식별자 키 (예: "auth:login:192.168.1.1")
            limit: 최대 요청 수
            window_seconds: 윈도우 크기 (초)

        Returns:
            RateLimitResult: 속도 제한 검사 결과
        """
        try:
            redis_client = self._redis
        except Exception:
             # Redis 연결 실패 시 Fail-open
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit - 1,
                reset_at=int(time.time() + window_seconds),
                retry_after=None,
            )

        redis_key = self._make_key(key)
        now = time.time()
        window_start = now - window_seconds

        try:
            # Pipeline으로 원자적 실행
            pipe = redis_client.pipeline()

            # 1. 윈도우 밖의 오래된 요청 제거
            pipe.zremrangebyscore(redis_key, 0, window_start)

            # 2. 현재 윈도우 내 요청 개수 확인
            pipe.zcard(redis_key)

            # 파이프라인 실행
            results = await pipe.execute()
            current_count = results[1]

            # 3. 속도 제한 확인
            if current_count < limit:
                # 제한 미만 - 새 요청 추가
                allowed = True
                remaining = limit - current_count - 1

                # 새 요청을 Sorted Set에 추가 (score = timestamp)
                await redis_client.zadd(redis_key, {str(now): now})

                # TTL 설정 (윈도우 크기 + 여유시간)
                await redis_client.expire(redis_key, window_seconds + 10)

                # 다음 리셋 시간 계산 (현재 윈도우 종료 시간)
                reset_at = int(now + window_seconds)
                retry_after = None

                logger.debug(
                    f"Rate limit check passed: {key}",
                    extra={
                        "key": key,
                        "current": current_count + 1,
                        "limit": limit,
                        "remaining": remaining,
                    }
                )
            else:
                # 제한 초과
                allowed = False
                remaining = 0

                # 가장 오래된 요청의 타임스탬프 조회
                oldest_requests = await redis_client.zrange(
                    redis_key, 0, 0, withscores=True
                )

                if oldest_requests:
                    oldest_timestamp = oldest_requests[0][1]
                    # 가장 오래된 요청이 윈도우에서 벗어나는 시간
                    reset_at = int(oldest_timestamp + window_seconds)
                    retry_after = max(1, reset_at - int(now))
                else:
                    # Sorted Set이 비어있으면 현재 시간 + 윈도우
                    reset_at = int(now + window_seconds)
                    retry_after = window_seconds

                logger.warning(
                    f"Rate limit exceeded: {key}",
                    extra={
                        "key": key,
                        "current": current_count,
                        "limit": limit,
                        "retry_after": retry_after,
                    }
                )

            return RateLimitResult(
                allowed=allowed,
                limit=limit,
                remaining=remaining,
                reset_at=reset_at,
                retry_after=retry_after,
            )

        except Exception as e:
            logger.error(
                f"Rate limit check failed: {key}",
                extra={
                    "key": key,
                    "error": str(e),
                },
                exc_info=True
            )
            # Redis 오류 시 기본적으로 허용 (Fail-open)
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit - 1,
                reset_at=int(now + window_seconds),
                retry_after=None,
            )

    async def reset_limit(self, key: str) -> None:
        """
        특정 키의 속도 제한 초기화
        """
        try:
            redis_client = self._redis
            redis_key = self._make_key(key)
            await redis_client.delete(redis_key)
            logger.info(f"Rate limit reset: {key}", extra={"key": key})
        except Exception as e:
             logger.error(
                f"Failed to reset rate limit: {key}",
                extra={"key": key, "error": str(e)},
                exc_info=True
            )

    async def get_current_usage(
        self,
        key: str,
        window_seconds: int
    ) -> int:
        """
        현재 윈도우 내 요청 수 조회
        """
        try:
            redis_client = self._redis
            redis_key = self._make_key(key)
            now = time.time()
            window_start = now - window_seconds
            
            # 오래된 요청 제거 후 개수 확인
            await redis_client.zremrangebyscore(redis_key, 0, window_start)
            count = await redis_client.zcard(redis_key)
            return count
        except Exception as e:
            logger.error(
                f"Failed to get current usage: {key}",
                extra={"key": key, "error": str(e)},
                exc_info=True
            )
            return 0


# 전역 Rate Limiter 인스턴스 (싱글톤 패턴)
_rate_limiter: Optional[RateLimiterService] = None


def get_rate_limiter() -> RateLimiterService:
    """
    Rate Limiter 싱글톤 인스턴스 가져오기

    Returns:
        RateLimiterService: Rate Limiter 인스턴스
    """
    global _rate_limiter
    if not _rate_limiter:
        _rate_limiter = RateLimiterService()
    return _rate_limiter
