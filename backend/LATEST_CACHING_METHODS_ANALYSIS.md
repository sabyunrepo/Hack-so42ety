# 최신 캐싱 방법 분석 및 개선 제안

## 📊 조사 결과 요약

### 현재 제안한 방법 vs 최신 트렌드

| 항목 | 현재 제안 | 최신 트렌드 | 평가 |
|------|----------|------------|------|
| 이벤트 시스템 | Redis Pub/Sub | Redis Pub/Sub ✅ / Redis Streams ⭐ | Pub/Sub 적합, Streams 고려 |
| 캐싱 라이브러리 | 직접 구현 | aiocache / fastapi-cache2 ⭐ | 라이브러리 활용 권장 |
| 데코레이터 패턴 | 직접 구현 | 데코레이터 패턴 ✅ | 현재 방법 적합 |
| 의존성 주입 | 수동 DI | FastAPI Depends ⭐ | 개선 가능 |

---

## 🔍 최신 라이브러리 및 도구

### 1. aiocache ⭐⭐⭐⭐⭐ (강력 추천)

**특징**:
- 비동기 전용 캐싱 라이브러리
- Redis, Memcached, Memory 백엔드 지원
- 데코레이터 지원
- TTL 자동 관리
- FastAPI와 잘 통합

**장점**:
- 검증된 라이브러리 (GitHub 1.2k+ stars)
- 비동기 최적화
- 다양한 백엔드 지원
- 간단한 API

**사용 예시**:
```python
from aiocache import cached, Cache
from aiocache.serializers import JsonSerializer

@cached(ttl=3600, cache=Cache.REDIS, serializer=JsonSerializer())
async def get_voices():
    return await api_call()
```

**단점**:
- 이벤트 기반 무효화는 직접 구현 필요
- 커스터마이징 제한

---

### 2. fastapi-cache2 ⭐⭐⭐⭐

**특징**:
- FastAPI 전용 캐싱 라이브러리
- Redis, Memory 백엔드
- 의존성 주입 통합
- 데코레이터 지원

**장점**:
- FastAPI와 완벽 통합
- 의존성 주입 패턴
- 간단한 설정

**사용 예시**:
```python
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache

@cache(expire=3600)
async def get_voices():
    return await api_call()
```

**단점**:
- 상대적으로 새로운 라이브러리
- 이벤트 기반 무효화 직접 구현 필요

---

### 3. cachetools (현재 사용 중) ⭐⭐⭐

**특징**:
- 동기/비동기 모두 지원
- TTLCache, LRUCache 등
- 메모리 기반

**장점**:
- 가벼움
- 다양한 캐시 알고리즘
- 외부 의존성 없음

**단점**:
- 비동기 지원 제한적
- 분산 캐싱 불가
- 단일 인스턴스만

---

## 🚀 개선된 아키텍처 제안

### Option A: aiocache + Redis Streams (최신 추천) ⭐⭐⭐⭐⭐

**구성**:
- **캐싱**: aiocache (Redis 백엔드)
- **이벤트**: Redis Streams (Pub/Sub 대신)
- **데코레이터**: aiocache + 커스텀 무효화 데코레이터

**장점**:
1. **Redis Streams의 장점**:
   - 메시지 영속성 (Pub/Sub은 구독자가 없으면 손실)
   - Consumer Groups 지원 (여러 인스턴스가 안전하게 구독)
   - 메시지 순서 보장
   - 재처리 가능 (장애 복구)

2. **aiocache의 장점**:
   - 검증된 라이브러리
   - 비동기 최적화
   - 간단한 API

**구현 예시**:
```python
from aiocache import cached, Cache
from aiocache.serializers import JsonSerializer
import aioredis

# 캐싱
@cached(
    ttl=3600,
    cache=Cache.REDIS,
    serializer=JsonSerializer(),
    key_builder=lambda f, *args, **kwargs: "tts:voices"
)
async def get_voices(self) -> List[Dict[str, Any]]:
    return await tts_provider.get_available_voices()

# 이벤트 발행 (Redis Streams)
async def create_voice_clone(self, ...):
    voice = await create_voice(...)
    
    # Redis Streams에 이벤트 발행
    redis = await aioredis.from_url("redis://localhost")
    await redis.xadd(
        "events:voice",
        {
            "type": "voice.created",
            "voice_id": voice["voice_id"],
            "timestamp": str(datetime.utcnow())
        }
    )
    
    return voice

# 이벤트 구독 (Redis Streams Consumer Group)
async def listen_events():
    redis = await aioredis.from_url("redis://localhost")
    
    while True:
        # Consumer Group으로 메시지 읽기
        messages = await redis.xreadgroup(
            "cache-service",
            "worker-1",
            {"events:voice": ">"},
            count=10,
            block=1000
        )
        
        for stream, msgs in messages:
            for msg_id, data in msgs:
                # 캐시 무효화
                await cache.delete("tts:voices")
                # ACK 처리
                await redis.xack("events:voice", "cache-service", msg_id)
```

---

### Option B: fastapi-cache2 + Redis Pub/Sub (간단한 방법) ⭐⭐⭐⭐

**구성**:
- **캐싱**: fastapi-cache2
- **이벤트**: Redis Pub/Sub (현재 제안)
- **데코레이터**: fastapi-cache2 + 커스텀 무효화

**장점**:
- FastAPI와 완벽 통합
- 구현 간단
- 의존성 주입 패턴

**구현 예시**:
```python
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache
from fastapi_cache.backends.redis import RedisBackend

# 초기화
@asynccontextmanager
async def lifespan(app: FastAPI):
    redis = await aioredis.from_url("redis://localhost")
    FastAPICache.init(RedisBackend(redis))
    yield

# 캐싱
@cache(expire=3600)
async def get_voices(self) -> List[Dict[str, Any]]:
    return await tts_provider.get_available_voices()
```

---

### Option C: 커스텀 구현 (현재 제안) ⭐⭐⭐

**구성**:
- **캐싱**: 직접 구현
- **이벤트**: Redis Pub/Sub
- **데코레이터**: 직접 구현

**장점**:
- 완전한 제어
- 커스터마이징 자유

**단점**:
- 구현 복잡도 높음
- 버그 가능성
- 유지보수 부담

---

## 🎯 최종 추천: aiocache + Redis Streams

### 이유

1. **Redis Streams의 우수성**:
   - 메시지 영속성으로 신뢰성 향상
   - Consumer Groups로 확장성 확보
   - Pub/Sub 대비 더 견고함

2. **aiocache의 검증성**:
   - 널리 사용되는 라이브러리
   - 비동기 최적화
   - 다양한 백엔드 지원

3. **균형잡힌 복잡도**:
   - 라이브러리 활용으로 구현 간소화
   - 필요한 부분만 커스터마이징

---

## 📋 개선된 구현 설계

### 1. aiocache 통합

```python
# backend/core/cache/aiocache_service.py

from aiocache import cached, Cache
from aiocache.serializers import JsonSerializer
from typing import Callable, Any
from functools import wraps

class CacheService:
    """aiocache 기반 캐시 서비스"""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
    
    def cache_result(
        self,
        key: str,
        ttl: int = 3600,
        key_builder: Optional[Callable] = None
    ):
        """캐시 결과 데코레이터"""
        def decorator(func: Callable) -> Callable:
            @cached(
                ttl=ttl,
                cache=Cache.REDIS,
                serializer=JsonSerializer(),
                key_builder=lambda f, *args, **kwargs: (
                    key_builder(*args, **kwargs) if key_builder 
                    else key.format(**kwargs) if '{' in key 
                    else key
                )
            )
            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    async def delete(self, key: str) -> None:
        """캐시 삭제"""
        from aiocache import caches
        cache = await caches.get('default')
        await cache.delete(key)
```

---

### 2. Redis Streams 이벤트 시스템

```python
# backend/core/events/redis_streams_bus.py

import aioredis
from typing import Dict, List, Callable, Awaitable
from .bus import EventBus
from .types import Event, EventType
import json
from datetime import datetime
import uuid

class RedisStreamsEventBus(EventBus):
    """Redis Streams 기반 이벤트 버스"""
    
    def __init__(self, redis_url: str, consumer_group: str = "cache-service"):
        self.redis_url = redis_url
        self.consumer_group = consumer_group
        self.redis: Optional[aioredis.Redis] = None
        self.handlers: Dict[EventType, List[Callable]] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def connect(self):
        """Redis 연결"""
        self.redis = await aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        
        # Consumer Group 생성 (이미 있으면 무시)
        for event_type in EventType:
            stream_name = f"events:{event_type.value}"
            try:
                await self.redis.xgroup_create(
                    stream_name,
                    self.consumer_group,
                    id="0",
                    mkstream=True
                )
            except aioredis.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise
    
    async def publish(self, event_type: EventType, payload: dict) -> None:
        """이벤트 발행 (Redis Streams)"""
        event = Event(
            type=event_type,
            payload=payload,
            timestamp=datetime.utcnow(),
            source="tts-service",
            event_id=str(uuid.uuid4())
        )
        
        stream_name = f"events:{event_type.value}"
        await self.redis.xadd(
            stream_name,
            {
                "event": event.model_dump_json(),
                "type": event_type.value
            },
            maxlen=10000  # 최대 10,000개 메시지 유지
        )
    
    async def subscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], Awaitable[None]]
    ) -> None:
        """이벤트 구독"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
    
    async def _listen(self, consumer_name: str):
        """이벤트 수신 루프 (Consumer Group)"""
        while self._running:
            try:
                # 모든 이벤트 스트림에서 읽기
                streams = {
                    f"events:{et.value}": ">" 
                    for et in self.handlers.keys()
                }
                
                if not streams:
                    await asyncio.sleep(1)
                    continue
                
                messages = await self.redis.xreadgroup(
                    self.consumer_group,
                    consumer_name,
                    streams,
                    count=10,
                    block=1000
                )
                
                for stream_name, msgs in messages:
                    for msg_id, data in msgs:
                        try:
                            event_data = json.loads(data["event"])
                            event = Event(**event_data)
                            
                            # 이벤트 타입 추출
                            event_type = EventType(data["type"])
                            
                            # 모든 핸들러 실행
                            if event_type in self.handlers:
                                for handler in self.handlers[event_type]:
                                    try:
                                        await handler(event)
                                    except Exception as e:
                                        logger.error(f"Handler error: {e}", exc_info=True)
                            
                            # ACK 처리
                            await self.redis.xack(
                                stream_name,
                                self.consumer_group,
                                msg_id
                            )
                        except Exception as e:
                            logger.error(f"Event processing error: {e}", exc_info=True)
                            # 실패한 메시지는 나중에 재처리 가능
            
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Event listening error: {e}", exc_info=True)
                await asyncio.sleep(1)
    
    async def start(self, consumer_name: str = "worker-1") -> None:
        """이벤트 버스 시작"""
        if not self.redis:
            await self.connect()
        
        self._running = True
        self._task = asyncio.create_task(self._listen(consumer_name))
    
    async def stop(self) -> None:
        """이벤트 버스 중지"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        if self.redis:
            await self.redis.close()
```

---

### 3. 통합 사용 예시

```python
# backend/features/tts/service.py

from ..core.cache.aiocache_service import CacheService
from ..core.events.redis_streams_bus import RedisStreamsEventBus
from ..core.events.types import EventType

class TTSService:
    def __init__(
        self,
        audio_repo: AudioRepository,
        storage_service: AbstractStorageService,
        ai_factory: AIProviderFactory,
        db_session: AsyncSession,
        cache_service: CacheService,
        event_bus: RedisStreamsEventBus,
    ):
        self.cache_service = cache_service
        self.event_bus = event_bus
        # ... 기타 의존성
    
    @cache_service.cache_result(key="tts:voices", ttl=3600)
    async def get_voices(self) -> List[Dict[str, Any]]:
        """캐싱이 자동으로 적용됨"""
        tts_provider = self.ai_factory.get_tts_provider()
        return await tts_provider.get_available_voices()
    
    async def create_voice_clone(self, ...):
        """이벤트 발행 (Redis Streams)"""
        voice = await tts_provider.clone_voice(...)
        
        # Redis Streams에 이벤트 발행
        await self.event_bus.publish(
            EventType.VOICE_CREATED,
            {
                "voice_id": voice["voice_id"],
                "name": voice["name"],
                "user_id": str(user_id),
            }
        )
        
        return voice
```

---

## 📊 비교 분석

### Redis Pub/Sub vs Redis Streams

| 항목 | Pub/Sub | Streams | 추천 |
|------|---------|---------|------|
| 메시지 영속성 | ❌ | ✅ | Streams |
| Consumer Groups | ❌ | ✅ | Streams |
| 재처리 가능 | ❌ | ✅ | Streams |
| 구현 복잡도 | 낮음 | 중간 | Pub/Sub (간단) |
| 성능 | 높음 | 높음 | 동일 |
| 확장성 | 제한적 | 우수 | Streams |

**결론**: 프로덕션 환경에서는 **Redis Streams** 권장

---

### 라이브러리 비교

| 라이브러리 | 비동기 | Redis | 데코레이터 | FastAPI 통합 | 추천도 |
|-----------|--------|-------|-----------|-------------|--------|
| aiocache | ✅ | ✅ | ✅ | ⚠️ | ⭐⭐⭐⭐⭐ |
| fastapi-cache2 | ✅ | ✅ | ✅ | ✅ | ⭐⭐⭐⭐ |
| cachetools | ⚠️ | ❌ | ✅ | ❌ | ⭐⭐⭐ |
| 직접 구현 | ✅ | ✅ | ✅ | ✅ | ⭐⭐⭐ |

**결론**: **aiocache** 또는 **fastapi-cache2** 권장

---

## 🎯 최종 추천 조합

### 조합 1: aiocache + Redis Streams (프로덕션 권장) ⭐⭐⭐⭐⭐

**구성**:
- 캐싱: aiocache
- 이벤트: Redis Streams
- 데코레이터: aiocache + 커스텀

**장점**:
- 검증된 라이브러리
- 메시지 영속성
- 확장성 우수
- 신뢰성 높음

**단점**:
- 구현 복잡도 중간
- Redis Streams 학습 필요

---

### 조합 2: fastapi-cache2 + Redis Pub/Sub (빠른 구현) ⭐⭐⭐⭐

**구성**:
- 캐싱: fastapi-cache2
- 이벤트: Redis Pub/Sub
- 데코레이터: fastapi-cache2 + 커스텀

**장점**:
- FastAPI 완벽 통합
- 구현 간단
- 빠른 개발

**단점**:
- 메시지 영속성 없음
- 확장성 제한

---

### 조합 3: 현재 제안 (커스텀 구현) ⭐⭐⭐

**구성**:
- 캐싱: 직접 구현
- 이벤트: Redis Pub/Sub
- 데코레이터: 직접 구현

**장점**:
- 완전한 제어
- 커스터마이징 자유

**단점**:
- 구현 복잡도 높음
- 유지보수 부담

---

## 💡 마이그레이션 전략

### Step 1: aiocache 도입 (캐싱만)

1. `aiocache` 설치
2. 기존 캐시 로직을 aiocache로 교체
3. 데코레이터 적용

### Step 2: Redis Streams 도입 (이벤트)

1. Redis Streams 이벤트 버스 구현
2. Pub/Sub에서 Streams로 마이그레이션
3. Consumer Groups 설정

### Step 3: 통합 및 최적화

1. 전체 시스템 통합
2. 모니터링 추가
3. 성능 최적화

---

## 📦 필요한 패키지

```txt
# requirements.txt 추가
aiocache==0.12.2  # 비동기 캐싱
aioredis==2.0.1   # Redis async client (이미 있음)
```

또는

```txt
fastapi-cache2==0.2.1  # FastAPI 전용 캐싱
aioredis==2.0.1
```

---

## ✅ 결론

### 최종 추천: **aiocache + Redis Streams**

**이유**:
1. 검증된 라이브러리 (aiocache)
2. 메시지 영속성 (Redis Streams)
3. 확장성 및 신뢰성
4. 적절한 복잡도

**대안**: 빠른 구현이 필요하면 **fastapi-cache2 + Redis Pub/Sub**

**현재 제안**: 커스텀 구현도 가능하지만, 라이브러리 활용 권장

