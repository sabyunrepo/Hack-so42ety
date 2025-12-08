"""
Redis Connection Tests
Redis 연결 테스트
"""

import pytest
import redis.asyncio as aioredis
from backend.core.config import settings


@pytest.mark.asyncio
async def test_redis_connection():
    """Redis 연결 테스트"""
    redis = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True
    )
    
    result = await redis.ping()
    assert result is True
    
    await redis.aclose()


@pytest.mark.asyncio
async def test_redis_streams():
    """Redis Streams 생성 테스트"""
    redis = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True
    )
    
    # Streams에 메시지 추가
    msg_id = await redis.xadd(
        "test:stream",
        {"test": "data", "value": "123"}
    )
    assert msg_id is not None
    
    # Streams에서 메시지 읽기
    messages = await redis.xread({"test:stream": "0"}, count=1)
    assert len(messages) > 0
    assert len(messages[0][1]) > 0  # (stream_name, [(msg_id, data), ...])
    
    # 테스트 데이터 정리
    await redis.delete("test:stream")
    
    await redis.aclose()


@pytest.mark.asyncio
async def test_redis_consumer_group():
    """Redis Consumer Groups 테스트"""
    redis = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True
    )
    
    stream_name = "test:consumer:stream"
    
    # Consumer Group 생성
    try:
        await redis.xgroup_create(
            stream_name,
            "test-group",
            id="0",
            mkstream=True
        )
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise
    
    # 메시지 추가
    await redis.xadd(stream_name, {"test": "data"})
    
    # Consumer Group으로 읽기
    messages = await redis.xreadgroup(
        "test-group",
        "consumer-1",
        {stream_name: ">"},
        count=1
    )
    
    assert len(messages) > 0
    
    # ACK 처리
    if messages:
        stream, msgs = messages[0]
        for msg_id, data in msgs:
            await redis.xack(stream_name, "test-group", msg_id)
    
    # 테스트 데이터 정리
    await redis.delete(stream_name)
    
    await redis.aclose()

