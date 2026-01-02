"""
Rate Limiter Service Unit Tests
속도 제한 서비스 테스트 (Sliding Window 알고리즘)
"""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from backend.core.rate_limiter import (
    RateLimiterService,
    RateLimitResult,
    get_rate_limiter,
)



class TestRateLimitResult:
    """RateLimitResult 데이터클래스 테스트"""

    def test_to_headers_allowed(self):
        """허용된 요청의 헤더 변환 테스트"""
        result = RateLimitResult(
            allowed=True,
            limit=10,
            remaining=5,
            reset_at=1609459200,
            retry_after=None,
        )

        headers = result.to_headers()

        assert headers["X-RateLimit-Limit"] == "10"
        assert headers["X-RateLimit-Remaining"] == "5"
        assert headers["X-RateLimit-Reset"] == "1609459200"

    def test_to_headers_exceeded(self):
        """제한 초과된 요청의 헤더 변환 테스트"""
        result = RateLimitResult(
            allowed=False,
            limit=10,
            remaining=0,
            reset_at=1609459260,
            retry_after=60,
        )

        headers = result.to_headers()

        assert headers["X-RateLimit-Limit"] == "10"
        assert headers["X-RateLimit-Remaining"] == "0"
        assert headers["X-RateLimit-Reset"] == "1609459260"


class TestRateLimiterService:
    """RateLimiterService 단위 테스트"""

    @pytest.mark.asyncio
    async def test_make_key(self):
        """Redis 키 생성 테스트"""
        rate_limiter = RateLimiterService(redis_client=AsyncMock())

        key = rate_limiter._make_key("auth:login:192.168.1.1")

        assert key == "rate_limit:auth:login:192.168.1.1"

    @pytest.mark.asyncio
    async def test_make_key_with_different_identifiers(self):
        """다양한 식별자로 키 생성 테스트"""
        rate_limiter = RateLimiterService(redis_client=AsyncMock())

        # IP 기반 키
        ip_key = rate_limiter._make_key("auth:login:192.168.1.1")
        assert ip_key == "rate_limit:auth:login:192.168.1.1"

        # 사용자 기반 키
        user_key = rate_limiter._make_key("auth:refresh:user123")
        assert user_key == "rate_limit:auth:refresh:user123"

        # 엔드포인트 기반 키
        endpoint_key = rate_limiter._make_key("auth:register:10.0.0.1")
        assert endpoint_key == "rate_limit:auth:register:10.0.0.1"


    @pytest.mark.asyncio
    async def test_check_rate_limit_first_request(self):
        """첫 번째 요청 - 속도 제한 확인 테스트"""
        mock_redis = AsyncMock()
        # Pipeline mock
        mock_pipeline = AsyncMock()
        mock_pipeline.zremrangebyscore = MagicMock()
        mock_pipeline.zcard = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=[0, 0])  # removed=0, count=0
        mock_redis.pipeline = MagicMock(return_value=mock_pipeline)
        mock_redis.zadd = AsyncMock()
        mock_redis.expire = AsyncMock()

        rate_limiter = RateLimiterService(redis_client=mock_redis)

        result = await rate_limiter.check_rate_limit(
            key="auth:login:192.168.1.1",
            limit=5,
            window_seconds=60
        )

        assert result.allowed is True
        assert result.limit == 5
        assert result.remaining == 4  # 5 - 0 - 1
        assert result.retry_after is None
        mock_redis.zadd.assert_called_once()
        mock_redis.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_rate_limit_within_limit(self):
        """제한 내 요청 - 속도 제한 확인 테스트"""
        mock_redis = AsyncMock()
        
        # Pipeline mock - 이미 3개의 요청이 있는 상태
        mock_pipeline = AsyncMock()
        mock_pipeline.zremrangebyscore = MagicMock()
        mock_pipeline.zcard = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=[0, 3])  # removed=0, count=3
        mock_redis.pipeline = MagicMock(return_value=mock_pipeline)
        
        rate_limiter = RateLimiterService(redis_client=mock_redis)

        result = await rate_limiter.check_rate_limit(
            key="auth:login:192.168.1.1",
            limit=5,
            window_seconds=60
        )

        assert result.allowed is True
        assert result.limit == 5
        assert result.remaining == 1  # 5 - 3 - 1
        assert result.retry_after is None

    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self):
        """제한 초과 - 속도 제한 확인 테스트"""
        mock_redis = AsyncMock()

        # Pipeline mock - 이미 5개의 요청이 있는 상태 (제한 도달)
        mock_pipeline = AsyncMock()
        mock_pipeline.zremrangebyscore = MagicMock()
        mock_pipeline.zcard = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=[0, 5])  # removed=0, count=5
        mock_redis.pipeline = MagicMock(return_value=mock_pipeline)

        # 가장 오래된 요청 타임스탬프
        now = time.time()
        oldest_timestamp = now - 50  # 50초 전
        mock_redis.zrange = AsyncMock(return_value=[("req1", oldest_timestamp)])

        rate_limiter = RateLimiterService(redis_client=mock_redis)

        result = await rate_limiter.check_rate_limit(
            key="auth:login:192.168.1.1",
            limit=5,
            window_seconds=60
        )

        assert result.allowed is False
        assert result.limit == 5
        assert result.remaining == 0
        assert result.retry_after is not None
        assert result.retry_after > 0

    @pytest.mark.asyncio
    async def test_check_rate_limit_sliding_window(self):
        """Sliding Window 알고리즘 정확성 테스트"""
        mock_redis = AsyncMock()

        # Pipeline mock - 오래된 요청 2개 제거됨
        mock_pipeline = AsyncMock()
        mock_pipeline.zremrangebyscore = MagicMock()
        mock_pipeline.zcard = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=[2, 3])  # removed=2, count=3
        mock_redis.pipeline = MagicMock(return_value=mock_pipeline)

        mock_redis.zadd = AsyncMock()
        mock_redis.expire = AsyncMock()

        rate_limiter = RateLimiterService(redis_client=mock_redis)

        result = await rate_limiter.check_rate_limit(
            key="auth:login:192.168.1.1",
            limit=5,
            window_seconds=60
        )

        # zremrangebyscore가 호출되어 오래된 요청 제거
        mock_pipeline.zremrangebyscore.assert_called_once()
        # 남은 요청 수 확인 (3개)
        assert result.allowed is True
        assert result.remaining == 1  # 5 - 3 - 1

    @pytest.mark.asyncio
    async def test_check_rate_limit_redis_error_fail_open(self):
        """Redis 에러 시 Fail-Open 전략 테스트"""
        mock_redis = AsyncMock()

        # Pipeline에서 에러 발생
        mock_pipeline = AsyncMock()
        mock_pipeline.execute = AsyncMock(side_effect=Exception("Redis error"))
        mock_redis.pipeline = MagicMock(return_value=mock_pipeline)

        rate_limiter = RateLimiterService(redis_client=mock_redis)

        result = await rate_limiter.check_rate_limit(
            key="auth:login:192.168.1.1",
            limit=5,
            window_seconds=60
        )

        # Redis 에러 시 기본적으로 허용 (Fail-Open)
        assert result.allowed is True
        assert result.limit == 5
        assert result.remaining == 4
        assert result.retry_after is None

    @pytest.mark.asyncio
    async def test_reset_limit_success(self):
        """속도 제한 초기화 성공 테스트"""
        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock(return_value=1)

        rate_limiter = RateLimiterService(redis_client=mock_redis)

        await rate_limiter.reset_limit("auth:login:192.168.1.1")

        mock_redis.delete.assert_called_once_with("rate_limit:auth:login:192.168.1.1")

    @pytest.mark.asyncio
    async def test_reset_limit_redis_error(self):
        """속도 제한 초기화 중 Redis 에러 테스트"""
        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock(side_effect=Exception("Redis error"))

        rate_limiter = RateLimiterService(redis_client=mock_redis)

        # 에러가 발생해도 예외를 던지지 않고 로깅만 함
        await rate_limiter.reset_limit("auth:login:192.168.1.1")

        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_current_usage_success(self):
        """현재 사용량 조회 성공 테스트"""
        mock_redis = AsyncMock()
        mock_redis.zremrangebyscore = AsyncMock()
        mock_redis.zcard = AsyncMock(return_value=3)

        rate_limiter = RateLimiterService(redis_client=mock_redis)

        usage = await rate_limiter.get_current_usage(
            key="auth:login:192.168.1.1",
            window_seconds=60
        )

        assert usage == 3
        mock_redis.zremrangebyscore.assert_called_once()
        mock_redis.zcard.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_current_usage_redis_error(self):
        """현재 사용량 조회 중 Redis 에러 테스트"""
        mock_redis = AsyncMock()
        mock_redis.zremrangebyscore = AsyncMock(side_effect=Exception("Redis error"))

        rate_limiter = RateLimiterService(redis_client=mock_redis)

        usage = await rate_limiter.get_current_usage(
            key="auth:login:192.168.1.1",
            window_seconds=60
        )

        # 에러 시 0 반환
        assert usage == 0

    @pytest.mark.asyncio
    async def test_auto_connect_if_not_connected(self):
        """연결되지 않은 상태에서 자동 연결 테스트"""
        # 이 테스트는 의존성 주입이 없어서 내부적으로 get_redis_client를 호출할 때를 시뮬레이션
        # 하지만 get_redis_client는 RedisManager에서 가져오므로 RedisManager를 모킹해야 함
        
        mock_redis = AsyncMock()
        # Pipeline mock
        mock_pipeline = AsyncMock()
        mock_pipeline.zremrangebyscore = MagicMock()
        mock_pipeline.zcard = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=[0, 0])
        mock_redis.pipeline = MagicMock(return_value=mock_pipeline)
        
        mock_redis.zadd = AsyncMock()
        mock_redis.expire = AsyncMock()

        # get_redis_client가 mock_redis를 반환하도록 patch
        with patch("backend.core.redis.get_redis_client", return_value=mock_redis):
            # redis_client 없이 생성 -> 내부적으로 _redis 프로퍼티 접근 시 get_redis_client 호출
            rate_limiter = RateLimiterService()
            
            result = await rate_limiter.check_rate_limit(
                key="auth:login:192.168.1.1",
                limit=5,
                window_seconds=60
            )

            assert result.allowed is True


    def test_get_rate_limiter_singleton(self):
        """싱글톤 패턴 테스트"""
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()

        # 동일한 인스턴스여야 함
        assert limiter1 is limiter2

    @pytest.mark.asyncio
    async def test_check_rate_limit_reset_time_calculation(self):
        """Reset 시간 계산 정확성 테스트"""
        mock_redis = AsyncMock()
        
        # Pipeline mock
        mock_pipeline = AsyncMock()
        mock_pipeline.zremrangebyscore = MagicMock()
        mock_pipeline.zcard = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=[0, 0])
        mock_redis.pipeline = MagicMock(return_value=mock_pipeline)

        mock_redis.zadd = AsyncMock()
        mock_redis.expire = AsyncMock()

        with patch("backend.core.rate_limiter.time.time", return_value=1000.0):
            rate_limiter = RateLimiterService(redis_client=mock_redis)

            result = await rate_limiter.check_rate_limit(
                key="auth:login:192.168.1.1",
                limit=5,
                window_seconds=60
            )

            # reset_at은 현재 시간 + window_seconds
            assert result.reset_at == 1060  # 1000 + 60


    @pytest.mark.asyncio
    async def test_check_rate_limit_retry_after_calculation(self):
        """Retry-After 시간 계산 정확성 테스트"""
        mock_redis = AsyncMock()

        # 제한 초과 상태
        mock_pipeline = AsyncMock()
        mock_pipeline.zremrangebyscore = MagicMock()
        mock_pipeline.zcard = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=[0, 5])
        mock_redis.pipeline = MagicMock(return_value=mock_pipeline)

        # 가장 오래된 요청 타임스탬프
        oldest_timestamp = 950.0  # 1000 - 50
        mock_redis.zrange = AsyncMock(return_value=[("req1", oldest_timestamp)])

        with patch("backend.core.rate_limiter.time.time", return_value=1000.0):
            rate_limiter = RateLimiterService(redis_client=mock_redis)

            result = await rate_limiter.check_rate_limit(
                key="auth:login:192.168.1.1",
                limit=5,
                window_seconds=60
            )

            assert result.allowed is False
            # reset_at = oldest_timestamp + window_seconds = 950 + 60 = 1010
            assert result.reset_at == 1010
            # retry_after = reset_at - now = 1010 - 1000 = 10
            assert result.retry_after == 10

    @pytest.mark.asyncio
    async def test_check_rate_limit_expire_ttl(self):
        """Redis 키 TTL 설정 테스트"""
        mock_redis = AsyncMock()

        mock_pipeline = AsyncMock()
        mock_pipeline.zremrangebyscore = MagicMock()
        mock_pipeline.zcard = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=[0, 0])
        mock_redis.pipeline = MagicMock(return_value=mock_pipeline)

        mock_redis.zadd = AsyncMock()
        mock_redis.expire = AsyncMock()

        rate_limiter = RateLimiterService(redis_client=mock_redis)

        await rate_limiter.check_rate_limit(
            key="auth:login:192.168.1.1",
            limit=5,
            window_seconds=60
        )

        # TTL은 window_seconds + 10 (여유 시간)
        mock_redis.expire.assert_called_once()
        call_args = mock_redis.expire.call_args
        assert call_args[0][1] == 70  # 60 + 10
