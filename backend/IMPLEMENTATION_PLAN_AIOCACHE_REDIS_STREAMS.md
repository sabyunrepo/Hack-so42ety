# aiocache + Redis Streams 구현 계획

## 📋 전체 개요

### 목표
- aiocache를 활용한 비동기 캐싱 시스템 구축
- Redis Streams 기반 이벤트 드리븐 캐시 무효화
- 데코레이터 패턴으로 간결한 코드
- 완벽한 테스트 및 검증

### 기술 스택
- **캐싱**: aiocache (Redis 백엔드)
- **이벤트**: Redis Streams
- **프레임워크**: FastAPI
- **인프라**: Docker Compose

---

## 🔄 Phase별 구현 루프

각 Phase는 다음 루프를 따릅니다:

```
Phase 시작
    ↓
1. 구현 (Implementation)
    ↓
2. 단위 테스트 (Unit Tests)
    ↓
3. 통합 테스트 (Integration Tests)
    ↓
4. 디버깅 (Debugging)
    ↓
5. 검증 (Verification)
    ↓
6. 문서화 (Documentation)
    ↓
Phase 완료 → 다음 Phase
```

---

## Phase 1: 인프라 구축 및 기본 설정

### 목표
- Redis 컨테이너 추가
- aiocache 라이브러리 설치
- 기본 설정 파일 구성
- 연결 테스트

### 작업 목록

#### 1.1 Docker Compose 수정
- [ ] Redis 서비스 추가
- [ ] Redis Streams 지원 확인
- [ ] Health check 설정
- [ ] 네트워크 설정 확인

#### 1.2 requirements.txt 업데이트
- [ ] aiocache 추가
- [ ] aioredis 버전 확인 (이미 있음)
- [ ] 의존성 충돌 확인

#### 1.3 설정 파일 추가
- [ ] Redis 연결 설정 추가
- [ ] aiocache 설정 추가
- [ ] 환경 변수 추가

#### 1.4 기본 연결 테스트
- [ ] Redis 연결 테스트 스크립트
- [ ] aiocache 초기화 테스트
- [ ] Streams 생성 테스트

### 구현 코드

#### 1.1 Docker Compose 수정
```yaml
# docker-compose.yml에 추가
services:
  redis:
    image: redis:7-alpine
    container_name: moriai-redis
    restart: unless-stopped
    ports:
      - "${REDIS_PORT:-6379}:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes
    networks:
      - moriai-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  redis-data:
```

#### 1.2 requirements.txt 업데이트
```txt
# 추가
aiocache==0.12.2
```

#### 1.3 설정 파일
```python
# backend/core/config.py에 추가
redis_host: str = Field(default="redis", env="REDIS_HOST")
redis_port: int = Field(default=6379, env="REDIS_PORT")
redis_url: str = Field(default="redis://redis:6379", env="REDIS_URL")

@property
def aiocache_config(self) -> dict:
    """aiocache 설정"""
    return {
        "cache": "aiocache.RedisCache",
        "endpoint": self.redis_host,
        "port": self.redis_port,
        "timeout": 1,
        "serializer": {
            "class": "aiocache.serializers.JsonSerializer"
        }
    }
```

### 테스트 계획

#### 단위 테스트
```python
# tests/integration/test_redis_connection.py
async def test_redis_connection():
    """Redis 연결 테스트"""
    redis = await aioredis.from_url("redis://redis:6379")
    await redis.ping()
    assert True

async def test_redis_streams():
    """Redis Streams 생성 테스트"""
    redis = await aioredis.from_url("redis://redis:6379")
    await redis.xadd("test:stream", {"test": "data"})
    messages = await redis.xread({"test:stream": "0"}, count=1)
    assert len(messages) > 0
```

#### 통합 테스트
```python
# tests/integration/test_aiocache_setup.py
async def test_aiocache_initialization():
    """aiocache 초기화 테스트"""
    from aiocache import Cache
    cache = Cache(Cache.REDIS, endpoint="redis", port=6379)
    await cache.set("test", "value")
    result = await cache.get("test")
    assert result == "value"
```

### 검증 기준
- [ ] Redis 컨테이너 정상 실행
- [ ] Redis 연결 성공
- [ ] Streams 생성/읽기 성공
- [ ] aiocache 초기화 성공
- [ ] 모든 테스트 통과

### 디버깅 체크리스트
- [ ] Redis 로그 확인: `docker-compose logs redis`
- [ ] Redis CLI 접속: `docker-compose exec redis redis-cli`
- [ ] Streams 확인: `XINFO STREAM events:voice`
- [ ] 네트워크 연결 확인: `docker network inspect`

### 롤백 계획
- Redis 서비스만 제거하면 기존 시스템에 영향 없음

---

## Phase 2: 이벤트 시스템 구축 (Redis Streams)

### 목표
- Redis Streams 기반 Event Bus 구현
- 이벤트 타입 정의
- Consumer Groups 설정
- 이벤트 발행/구독 테스트

### 작업 목록

#### 2.1 이벤트 타입 정의
- [ ] EventType enum 생성
- [ ] Event 모델 생성
- [ ] 이벤트 스키마 정의

#### 2.2 Event Bus 인터페이스
- [ ] EventBus 추상 클래스
- [ ] publish 메서드 정의
- [ ] subscribe 메서드 정의
- [ ] start/stop 메서드 정의

#### 2.3 Redis Streams 구현
- [ ] RedisStreamsEventBus 클래스
- [ ] 이벤트 발행 로직
- [ ] Consumer Groups 설정
- [ ] 이벤트 수신 루프
- [ ] ACK 처리

#### 2.4 FastAPI 통합
- [ ] lifespan에서 Event Bus 시작/중지
- [ ] 의존성 주입 설정

### 구현 코드

#### 2.1 이벤트 타입 정의
```python
# backend/core/events/types.py
from enum import Enum
from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any
import uuid

class EventType(str, Enum):
    """이벤트 타입"""
    VOICE_CREATED = "voice.created"
    VOICE_UPDATED = "voice.updated"
    VOICE_DELETED = "voice.deleted"

class Event(BaseModel):
    """이벤트 기본 구조"""
    type: EventType
    payload: Dict[str, Any]
    timestamp: datetime
    source: str
    event_id: str
    
    @classmethod
    def create(cls, event_type: EventType, payload: Dict[str, Any], source: str = "unknown"):
        return cls(
            type=event_type,
            payload=payload,
            timestamp=datetime.utcnow(),
            source=source,
            event_id=str(uuid.uuid4())
        )
```

#### 2.2 Event Bus 인터페이스
```python
# backend/core/events/bus.py
from abc import ABC, abstractmethod
from typing import Callable, Awaitable
from .types import Event, EventType

class EventBus(ABC):
    """이벤트 버스 추상 인터페이스"""
    
    @abstractmethod
    async def publish(self, event_type: EventType, payload: dict) -> None:
        """이벤트 발행"""
        pass
    
    @abstractmethod
    async def subscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], Awaitable[None]]
    ) -> None:
        """이벤트 구독"""
        pass
    
    @abstractmethod
    async def start(self, consumer_name: str = "worker-1") -> None:
        """이벤트 버스 시작"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """이벤트 버스 중지"""
        pass
```

#### 2.3 Redis Streams 구현
```python
# backend/core/events/redis_streams_bus.py
import json
import asyncio
import logging
from typing import Dict, List, Callable, Awaitable, Optional
import aioredis
from .bus import EventBus
from .types import Event, EventType
from ..config import settings

logger = logging.getLogger(__name__)

class RedisStreamsEventBus(EventBus):
    """Redis Streams 기반 이벤트 버스"""
    
    def __init__(self, redis_url: str = None, consumer_group: str = "cache-service"):
        self.redis_url = redis_url or settings.redis_url
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
        
        # Consumer Groups 생성 (이미 있으면 무시)
        for event_type in EventType:
            stream_name = f"events:{event_type.value}"
            try:
                await self.redis.xgroup_create(
                    stream_name,
                    self.consumer_group,
                    id="0",
                    mkstream=True
                )
                logger.info(f"Consumer group created: {self.consumer_group} for {stream_name}")
            except aioredis.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise
                logger.debug(f"Consumer group already exists: {self.consumer_group}")
    
    async def publish(self, event_type: EventType, payload: dict) -> None:
        """이벤트 발행 (Redis Streams)"""
        if not self.redis:
            await self.connect()
        
        event = Event.create(event_type, payload, source="tts-service")
        stream_name = f"events:{event_type.value}"
        
        try:
            await self.redis.xadd(
                stream_name,
                {
                    "event": event.model_dump_json(),
                    "type": event_type.value
                },
                maxlen=10000  # 최대 10,000개 메시지 유지
            )
            logger.info(f"Event published: {event_type.value} (id: {event.event_id})")
        except Exception as e:
            logger.error(f"Failed to publish event: {e}", exc_info=True)
            raise
    
    async def subscribe(
        self,
        event_type: EventType,
        handler: Callable[[Event], Awaitable[None]]
    ) -> None:
        """이벤트 구독"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        logger.info(f"Handler registered for {event_type.value}")
    
    async def _listen(self, consumer_name: str):
        """이벤트 수신 루프 (Consumer Group)"""
        logger.info(f"Event listener started: {consumer_name}")
        
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
                                        logger.debug(f"Handler executed for {event_type.value}")
                                    except Exception as e:
                                        logger.error(f"Handler error: {e}", exc_info=True)
                            
                            # ACK 처리
                            await self.redis.xack(
                                stream_name,
                                self.consumer_group,
                                msg_id
                            )
                            logger.debug(f"Event processed and ACKed: {msg_id}")
                            
                        except Exception as e:
                            logger.error(f"Event processing error: {e}", exc_info=True)
                            # 실패한 메시지는 나중에 재처리 가능
            
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Event listening error: {e}", exc_info=True)
                await asyncio.sleep(1)
        
        logger.info(f"Event listener stopped: {consumer_name}")
    
    async def start(self, consumer_name: str = "worker-1") -> None:
        """이벤트 버스 시작"""
        if not self.redis:
            await self.connect()
        
        self._running = True
        self._task = asyncio.create_task(self._listen(consumer_name))
        logger.info("Event bus started")
    
    async def stop(self) -> None:
        """이벤트 버스 중지"""
        logger.info("Stopping event bus...")
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        if self.redis:
            await self.redis.close()
        
        logger.info("Event bus stopped")
```

#### 2.4 FastAPI 통합
```python
# backend/main.py 수정
from backend.core.events.redis_streams_bus import RedisStreamsEventBus
from backend.core.config import settings

event_bus: Optional[RedisStreamsEventBus] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global event_bus
    
    # Startup
    # ... 기존 코드 ...
    
    # Event Bus 시작
    event_bus = RedisStreamsEventBus(
        redis_url=settings.redis_url,
        consumer_group="cache-service"
    )
    await event_bus.start(consumer_name=f"worker-{os.getpid()}")
    logger.info("Event bus started")
    
    yield
    
    # Shutdown
    if event_bus:
        await event_bus.stop()
    # ... 기존 코드 ...
```

### 테스트 계획

#### 단위 테스트
```python
# tests/unit/events/test_redis_streams_bus.py
import pytest
from backend.core.events.redis_streams_bus import RedisStreamsEventBus
from backend.core.events.types import EventType

@pytest.mark.asyncio
async def test_event_publish():
    """이벤트 발행 테스트"""
    bus = RedisStreamsEventBus(redis_url="redis://redis:6379")
    await bus.connect()
    
    await bus.publish(EventType.VOICE_CREATED, {"voice_id": "test-123"})
    
    # Streams에서 확인
    messages = await bus.redis.xread({"events:voice.created": "0"}, count=1)
    assert len(messages) > 0

@pytest.mark.asyncio
async def test_event_subscribe():
    """이벤트 구독 테스트"""
    bus = RedisStreamsEventBus(redis_url="redis://redis:6379")
    await bus.connect()
    
    received_events = []
    
    async def handler(event):
        received_events.append(event)
    
    await bus.subscribe(EventType.VOICE_CREATED, handler)
    await bus.start(consumer_name="test-worker")
    
    # 이벤트 발행
    await bus.publish(EventType.VOICE_CREATED, {"voice_id": "test-123"})
    
    # 잠시 대기
    await asyncio.sleep(2)
    
    assert len(received_events) > 0
    assert received_events[0].type == EventType.VOICE_CREATED
    
    await bus.stop()
```

#### 통합 테스트
```python
# tests/integration/test_event_flow.py
@pytest.mark.asyncio
async def test_complete_event_flow():
    """전체 이벤트 플로우 테스트"""
    # 1. Event Bus 시작
    bus = RedisStreamsEventBus()
    await bus.start()
    
    # 2. 핸들러 등록
    events_received = []
    
    async def handler(event):
        events_received.append(event)
    
    await bus.subscribe(EventType.VOICE_CREATED, handler)
    
    # 3. 이벤트 발행
    await bus.publish(EventType.VOICE_CREATED, {"voice_id": "test-123"})
    
    # 4. 이벤트 수신 확인
    await asyncio.sleep(2)
    assert len(events_received) == 1
    
    await bus.stop()
```

### 검증 기준
- [ ] 이벤트 발행 성공
- [ ] 이벤트 구독 성공
- [ ] Consumer Groups 정상 동작
- [ ] ACK 처리 정상
- [ ] 여러 핸들러 동시 실행
- [ ] 에러 핸들링 정상
- [ ] 모든 테스트 통과

### 디버깅 체크리스트
- [ ] Redis Streams 확인: `XINFO STREAM events:voice.created`
- [ ] Consumer Groups 확인: `XINFO GROUPS events:voice.created`
- [ ] Pending 메시지 확인: `XPENDING events:voice.created cache-service`
- [ ] 이벤트 로그 확인: `docker-compose logs backend | grep Event`

### 롤백 계획
- Event Bus 코드만 제거하면 기존 시스템에 영향 없음

---

## Phase 3: Cache Service 구현 (aiocache 통합)

### 목표
- aiocache 기반 Cache Service 구현
- 데코레이터 패턴 구현
- 이벤트 핸들러 등록
- 캐시 무효화 로직

### 작업 목록

#### 3.1 aiocache 설정
- [ ] aiocache 초기화
- [ ] Redis 백엔드 설정
- [ ] Serializer 설정 (JSON)

#### 3.2 Cache Service 구현
- [ ] CacheService 클래스
- [ ] get/set/delete 메서드
- [ ] 이벤트 핸들러 등록
- [ ] 캐시 무효화 로직

#### 3.3 데코레이터 구현
- [ ] `@cache_result` 데코레이터
- [ ] `@invalidate_cache` 데코레이터
- [ ] 동적 키 빌더 지원

#### 3.4 의존성 주입 설정
- [ ] CacheService 의존성 함수
- [ ] EventBus 의존성 함수

### 구현 코드

#### 3.1 aiocache 설정
```python
# backend/core/cache/config.py
from aiocache import Cache
from aiocache.serializers import JsonSerializer
from ..config import settings

def get_cache_config():
    """aiocache 설정"""
    return {
        "cache": Cache.REDIS,
        "endpoint": settings.redis_host,
        "port": settings.redis_port,
        "timeout": 1,
        "serializer": JsonSerializer(),
    }

# aiocache 초기화
from aiocache import caches

caches.set_config({
    "default": get_cache_config()
})
```

#### 3.2 Cache Service 구현
```python
# backend/core/cache/service.py
import logging
from typing import Optional, Any, Callable, Awaitable
from functools import wraps
from aiocache import caches
from aiocache.serializers import JsonSerializer
from ..events.bus import EventBus
from ..events.types import Event, EventType

logger = logging.getLogger(__name__)

class CacheService:
    """aiocache 기반 캐시 서비스 (이벤트 기반 무효화)"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._cache = None
        self._setup_event_handlers()
    
    async def _get_cache(self):
        """캐시 인스턴스 가져오기 (lazy initialization)"""
        if not self._cache:
            self._cache = await caches.get("default")
        return self._cache
    
    def _setup_event_handlers(self):
        """이벤트 핸들러 등록"""
        self.event_bus.subscribe(EventType.VOICE_CREATED, self._handle_voice_created)
        self.event_bus.subscribe(EventType.VOICE_UPDATED, self._handle_voice_updated)
        self.event_bus.subscribe(EventType.VOICE_DELETED, self._handle_voice_deleted)
    
    async def get(self, key: str) -> Optional[Any]:
        """캐시 조회"""
        try:
            cache = await self._get_cache()
            return await cache.get(key)
        except Exception as e:
            logger.error(f"Cache get error: {e}", exc_info=True)
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """캐시 저장"""
        try:
            cache = await self._get_cache()
            await cache.set(key, value, ttl=ttl)
            logger.debug(f"Cache set: {key} (ttl: {ttl}s)")
        except Exception as e:
            logger.error(f"Cache set error: {e}", exc_info=True)
    
    async def delete(self, key: str) -> None:
        """캐시 삭제"""
        try:
            cache = await self._get_cache()
            await cache.delete(key)
            logger.info(f"Cache deleted: {key}")
        except Exception as e:
            logger.error(f"Cache delete error: {e}", exc_info=True)
    
    # 이벤트 핸들러들
    async def _handle_voice_created(self, event: Event) -> None:
        """Voice 생성 이벤트 처리"""
        await self.delete("tts:voices")
        logger.info(f"Cache invalidated: tts:voices (event: {event.event_id})")
    
    async def _handle_voice_updated(self, event: Event) -> None:
        """Voice 수정 이벤트 처리"""
        await self.delete("tts:voices")
        logger.info(f"Cache invalidated: tts:voices (event: {event.event_id})")
    
    async def _handle_voice_deleted(self, event: Event) -> None:
        """Voice 삭제 이벤트 처리"""
        await self.delete("tts:voices")
        logger.info(f"Cache invalidated: tts:voices (event: {event.event_id})")


def cache_result(
    key: str,
    ttl: int = 3600,
    key_builder: Optional[Callable] = None
):
    """
    캐시 결과 데코레이터
    
    사용법:
        @cache_result(key="tts:voices", ttl=3600)
        async def get_voices(self) -> List[Dict[str, Any]]:
            return await api_call()
    
    Args:
        key: 캐시 키 (또는 키 템플릿)
        ttl: 캐시 TTL (초)
        key_builder: 동적 키 생성 함수 (선택)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # CacheService 인스턴스 가져오기
            cache_service = getattr(self, 'cache_service', None)
            if not cache_service:
                # 의존성 주입으로 받지 않은 경우 직접 호출
                logger.warning(f"CacheService not found for {func.__name__}, skipping cache")
                return await func(self, *args, **kwargs)
            
            # 캐시 키 생성
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            elif '{' in key:
                # 키 템플릿 사용 (예: "user:{user_id}")
                try:
                    cache_key = key.format(**kwargs)
                except KeyError:
                    # kwargs에 없으면 args에서 찾기 (함수 시그니처 기반)
                    import inspect
                    sig = inspect.signature(func)
                    bound = sig.bind(self, *args, **kwargs)
                    bound.apply_defaults()
                    cache_key = key.format(**bound.arguments)
            else:
                cache_key = key
            
            # 캐시 조회
            cached = await cache_service.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached
            
            # 캐시 미스 - 원본 함수 실행
            logger.debug(f"Cache miss: {cache_key}")
            result = await func(self, *args, **kwargs)
            
            # 캐시 저장
            await cache_service.set(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator


def invalidate_cache(*keys: str):
    """
    캐시 무효화 데코레이터
    
    사용법:
        @invalidate_cache("tts:voices")
        async def create_voice_clone(self, ...):
            voice = await create_voice(...)
            return voice
    
    Args:
        keys: 무효화할 캐시 키들
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # 원본 함수 실행
            result = await func(self, *args, **kwargs)
            
            # CacheService 인스턴스 가져오기
            cache_service = getattr(self, 'cache_service', None)
            if cache_service:
                # 모든 키 무효화
                for key in keys:
                    if '{' in key:
                        # 키 템플릿 사용
                        try:
                            formatted_key = key.format(**kwargs)
                        except KeyError:
                            import inspect
                            sig = inspect.signature(func)
                            bound = sig.bind(self, *args, **kwargs)
                            bound.apply_defaults()
                            formatted_key = key.format(**bound.arguments)
                        await cache_service.delete(formatted_key)
                    else:
                        await cache_service.delete(key)
            
            return result
        
        return wrapper
    return decorator
```

#### 3.3 의존성 주입 설정
```python
# backend/core/dependencies.py에 추가
from backend.core.cache.service import CacheService
from backend.core.events.redis_streams_bus import RedisStreamsEventBus
from backend.core.config import settings

# 전역 Event Bus (lifespan에서 초기화)
_event_bus: Optional[RedisStreamsEventBus] = None

def set_event_bus(event_bus: RedisStreamsEventBus):
    """Event Bus 설정 (lifespan에서 호출)"""
    global _event_bus
    _event_bus = event_bus

def get_event_bus() -> RedisStreamsEventBus:
    """Event Bus 의존성"""
    if not _event_bus:
        raise RuntimeError("Event bus not initialized. Call set_event_bus() first.")
    return _event_bus

def get_cache_service(
    event_bus: RedisStreamsEventBus = Depends(get_event_bus)
) -> CacheService:
    """CacheService 의존성 주입"""
    return CacheService(event_bus=event_bus)
```

### 테스트 계획

#### 단위 테스트
```python
# tests/unit/cache/test_cache_service.py
@pytest.mark.asyncio
async def test_cache_get_set():
    """캐시 조회/저장 테스트"""
    event_bus = MockEventBus()
    cache_service = CacheService(event_bus=event_bus)
    
    await cache_service.set("test:key", {"data": "value"}, ttl=60)
    result = await cache_service.get("test:key")
    
    assert result == {"data": "value"}

@pytest.mark.asyncio
async def test_cache_delete():
    """캐시 삭제 테스트"""
    event_bus = MockEventBus()
    cache_service = CacheService(event_bus=event_bus)
    
    await cache_service.set("test:key", "value")
    await cache_service.delete("test:key")
    result = await cache_service.get("test:key")
    
    assert result is None

@pytest.mark.asyncio
async def test_cache_decorator():
    """캐시 데코레이터 테스트"""
    event_bus = MockEventBus()
    cache_service = CacheService(event_bus=event_bus)
    
    class TestService:
        def __init__(self):
            self.cache_service = cache_service
            self.call_count = 0
        
        @cache_result(key="test:key", ttl=60)
        async def get_data(self):
            self.call_count += 1
            return {"data": "value"}
    
    service = TestService()
    
    # 첫 호출 - 캐시 미스
    result1 = await service.get_data()
    assert result1 == {"data": "value"}
    assert service.call_count == 1
    
    # 두 번째 호출 - 캐시 히트
    result2 = await service.get_data()
    assert result2 == {"data": "value"}
    assert service.call_count == 1  # 호출 안 됨
```

#### 통합 테스트
```python
# tests/integration/test_cache_with_events.py
@pytest.mark.asyncio
async def test_cache_invalidation_on_event():
    """이벤트 기반 캐시 무효화 테스트"""
    # 1. Event Bus 시작
    event_bus = RedisStreamsEventBus()
    await event_bus.start()
    
    # 2. Cache Service 생성
    cache_service = CacheService(event_bus=event_bus)
    
    # 3. 캐시 저장
    await cache_service.set("tts:voices", [{"id": "1"}])
    
    # 4. 이벤트 발행
    await event_bus.publish(EventType.VOICE_CREATED, {"voice_id": "new-voice"})
    
    # 5. 이벤트 처리 대기
    await asyncio.sleep(2)
    
    # 6. 캐시 무효화 확인
    result = await cache_service.get("tts:voices")
    assert result is None
    
    await event_bus.stop()
```

### 검증 기준
- [ ] 캐시 조회/저장 성공
- [ ] 캐시 삭제 성공
- [ ] 데코레이터 정상 동작
- [ ] 이벤트 기반 무효화 정상
- [ ] TTL 정상 동작
- [ ] 동적 키 빌더 정상
- [ ] 모든 테스트 통과

### 디버깅 체크리스트
- [ ] Redis 키 확인: `KEYS tts:*`
- [ ] 캐시 TTL 확인: `TTL tts:voices`
- [ ] 이벤트 로그 확인: `docker-compose logs backend | grep Cache`
- [ ] aiocache 로그 확인

### 롤백 계획
- CacheService 코드만 제거하면 기존 시스템에 영향 없음

---

## Phase 4: Service Layer 통합

### 목표
- TTSService에 캐싱 적용
- 이벤트 발행 추가
- 의존성 주입 업데이트
- API 엔드포인트 수정

### 작업 목록

#### 4.1 TTSService 수정
- [ ] CacheService, EventBus 의존성 추가
- [ ] `get_voices()`에 `@cache_result` 데코레이터 적용
- [ ] `create_voice_clone()`에 이벤트 발행 추가 (추후 구현 시)

#### 4.2 의존성 주입 업데이트
- [ ] `get_tts_service()` 함수 수정
- [ ] CacheService, EventBus 주입

#### 4.3 API 엔드포인트 확인
- [ ] 기존 엔드포인트 정상 동작 확인
- [ ] 캐시 동작 확인

### 구현 코드

#### 4.1 TTSService 수정
```python
# backend/features/tts/service.py
from ..core.cache.service import cache_result
from ..core.events.bus import EventBus
from ..core.events.types import EventType

class TTSService:
    def __init__(
        self,
        audio_repo: AudioRepository,
        storage_service: AbstractStorageService,
        ai_factory: AIProviderFactory,
        db_session: AsyncSession,
        cache_service: CacheService,  # 추가
        event_bus: EventBus,  # 추가
    ):
        self.audio_repo = audio_repo
        self.storage_service = storage_service
        self.ai_factory = ai_factory
        self.db_session = db_session
        self.cache_service = cache_service  # 데코레이터에서 사용
        self.event_bus = event_bus
    
    @cache_result(key="tts:voices", ttl=3600)
    async def get_voices(self) -> List[Dict[str, Any]]:
        """
        사용 가능한 음성 목록 조회 (캐싱 자동 적용)
        
        데코레이터가 자동으로:
        1. 캐시 조회
        2. 캐시 미스 시 API 호출
        3. 결과 캐시 저장
        """
        try:
            tts_provider = self.ai_factory.get_tts_provider()
        except TTSAPIKeyNotConfiguredException:
            raise
        except Exception as e:
            raise TTSGenerationFailedException(reason=f"TTS Provider 초기화 실패: {str(e)}")
        
        try:
            voices = await tts_provider.get_available_voices()
            return voices
        except (TTSAPIKeyNotConfiguredException, TTSAPIAuthenticationFailedException):
            raise
        except Exception as e:
            raise TTSGenerationFailedException(reason=f"음성 목록 조회 실패: {str(e)}")
    
    # 추후 Voice Clone 생성 시
    async def create_voice_clone(
        self,
        user_id: uuid.UUID,
        name: str,
        audio_file: bytes,
    ) -> Dict[str, Any]:
        """Voice Clone 생성 (이벤트 발행으로 캐시 무효화)"""
        tts_provider = self.ai_factory.get_tts_provider()
        voice = await tts_provider.clone_voice(name=name, audio_file=audio_file)
        
        # 이벤트 발행 (Redis Streams)
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

#### 4.2 의존성 주입 업데이트
```python
# backend/api/v1/endpoints/tts.py
from backend.core.dependencies import get_cache_service, get_event_bus

def get_tts_service(
    db: AsyncSession = Depends(get_db),
    storage_service = Depends(get_storage_service),
    ai_factory = Depends(get_ai_factory),
    cache_service: CacheService = Depends(get_cache_service),  # 추가
    event_bus: EventBus = Depends(get_event_bus),  # 추가
) -> TTSService:
    """TTSService 의존성 주입"""
    audio_repo = AudioRepository(db)
    return TTSService(
        audio_repo=audio_repo,
        storage_service=storage_service,
        ai_factory=ai_factory,
        db_session=db,
        cache_service=cache_service,
        event_bus=event_bus,
    )
```

### 테스트 계획

#### 단위 테스트
```python
# tests/unit/tts/test_tts_service_caching.py
@pytest.mark.asyncio
async def test_get_voices_caching():
    """get_voices 캐싱 테스트"""
    # Mock 설정
    mock_cache_service = MockCacheService()
    mock_event_bus = MockEventBus()
    mock_tts_provider = MockTTSProvider()
    
    service = TTSService(
        audio_repo=MockAudioRepository(),
        storage_service=MockStorageService(),
        ai_factory=MockAIFactory(mock_tts_provider),
        db_session=MockSession(),
        cache_service=mock_cache_service,
        event_bus=mock_event_bus,
    )
    
    # 첫 호출 - 캐시 미스
    result1 = await service.get_voices()
    assert mock_tts_provider.get_available_voices_call_count == 1
    
    # 두 번째 호출 - 캐시 히트
    result2 = await service.get_voices()
    assert mock_tts_provider.get_available_voices_call_count == 1  # 호출 안 됨
    assert result1 == result2
```

#### 통합 테스트
```python
# tests/integration/test_tts_api_caching.py
@pytest.mark.asyncio
async def test_voices_api_caching():
    """Voices API 캐싱 통합 테스트"""
    # 1. 첫 요청 - 캐시 미스
    response1 = await client.get("/api/v1/tts/voices")
    assert response1.status_code == 200
    
    # 2. 두 번째 요청 - 캐시 히트 (응답 시간 확인)
    import time
    start = time.time()
    response2 = await client.get("/api/v1/tts/voices")
    elapsed = time.time() - start
    
    assert response2.status_code == 200
    assert elapsed < 0.1  # 캐시 히트는 매우 빠름
    assert response1.json() == response2.json()
```

#### E2E 테스트
```python
# tests/e2e/test_cache_invalidation_flow.py
@pytest.mark.asyncio
async def test_complete_cache_invalidation_flow():
    """전체 캐시 무효화 플로우 테스트"""
    # 1. Voices 조회 (캐시 저장)
    response1 = await client.get("/api/v1/tts/voices")
    voices1 = response1.json()
    
    # 2. Voice 생성 (이벤트 발행)
    # Note: Voice Clone 엔드포인트가 구현되면 실제로 테스트
    # 현재는 이벤트 직접 발행
    event_bus = get_event_bus()
    await event_bus.publish(
        EventType.VOICE_CREATED,
        {"voice_id": "new-voice-123", "name": "New Voice"}
    )
    
    # 3. 이벤트 처리 대기
    await asyncio.sleep(2)
    
    # 4. Voices 재조회 (캐시 무효화되어 새로 조회)
    response2 = await client.get("/api/v1/tts/voices")
    voices2 = response2.json()
    
    # 5. 새 음성이 포함되었는지 확인 (실제 API 응답에 따라)
    # assert len(voices2) > len(voices1)  # 새 음성 추가 확인
```

### 검증 기준
- [ ] `get_voices()` 데코레이터 정상 동작
- [ ] 캐시 히트/미스 정상
- [ ] API 응답 시간 개선 확인
- [ ] 이벤트 발행 정상 (Voice 생성 시)
- [ ] 캐시 무효화 정상
- [ ] 모든 테스트 통과

### 디버깅 체크리스트
- [ ] API 로그 확인: `docker-compose logs backend | grep tts`
- [ ] 캐시 키 확인: `docker-compose exec redis redis-cli KEYS tts:*`
- [ ] 이벤트 스트림 확인: `XINFO STREAM events:voice.created`
- [ ] 응답 시간 확인: API 호출 시 `time` 측정

### 롤백 계획
- 데코레이터만 제거하면 기존 로직으로 복귀

---

## Phase 5: 모니터링 및 최적화

### 목표
- 캐시 히트율 모니터링
- 이벤트 처리 모니터링
- 성능 최적화
- 로깅 개선

### 작업 목록

#### 5.1 모니터링 메트릭
- [ ] 캐시 히트율 추적
- [ ] 이벤트 처리 시간 추적
- [ ] API 응답 시간 추적
- [ ] Redis 메모리 사용량 모니터링

#### 5.2 로깅 개선
- [ ] 구조화된 로깅
- [ ] 캐시 동작 로그
- [ ] 이벤트 발행/처리 로그

#### 5.3 성능 최적화
- [ ] TTL 최적화
- [ ] 캐시 키 최적화
- [ ] 이벤트 처리 최적화

### 구현 코드

#### 5.1 모니터링 메트릭
```python
# backend/core/cache/metrics.py
from typing import Dict
from collections import defaultdict
import time

class CacheMetrics:
    """캐시 메트릭 수집"""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.set_operations = 0
        self.delete_operations = 0
        self.total_get_time = 0.0
        self.total_set_time = 0.0
    
    def record_hit(self, duration: float):
        self.hits += 1
        self.total_get_time += duration
    
    def record_miss(self, duration: float):
        self.misses += 1
        self.total_get_time += duration
    
    def record_set(self, duration: float):
        self.set_operations += 1
        self.total_set_time += duration
    
    def record_delete(self):
        self.delete_operations += 1
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    @property
    def avg_get_time(self) -> float:
        total = self.hits + self.misses
        return self.total_get_time / total if total > 0 else 0.0
    
    def get_stats(self) -> Dict:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hit_rate,
            "set_operations": self.set_operations,
            "delete_operations": self.delete_operations,
            "avg_get_time_ms": self.avg_get_time * 1000,
        }

# 전역 메트릭
cache_metrics = CacheMetrics()
```

#### 5.2 로깅 개선
```python
# backend/core/cache/service.py에 추가
import structlog

logger = structlog.get_logger(__name__)

class CacheService:
    async def get(self, key: str) -> Optional[Any]:
        start = time.time()
        try:
            cache = await self._get_cache()
            result = await cache.get(key)
            duration = time.time() - start
            
            if result is not None:
                cache_metrics.record_hit(duration)
                logger.info(
                    "cache_hit",
                    key=key,
                    duration_ms=duration * 1000
                )
            else:
                cache_metrics.record_miss(duration)
                logger.info(
                    "cache_miss",
                    key=key,
                    duration_ms=duration * 1000
                )
            
            return result
        except Exception as e:
            logger.error("cache_get_error", key=key, error=str(e))
            return None
```

### 테스트 계획

#### 성능 테스트
```python
# tests/performance/test_cache_performance.py
@pytest.mark.asyncio
async def test_cache_performance():
    """캐시 성능 테스트"""
    service = get_tts_service()
    
    # 첫 호출 (캐시 미스)
    start = time.time()
    await service.get_voices()
    miss_time = time.time() - start
    
    # 두 번째 호출 (캐시 히트)
    start = time.time()
    await service.get_voices()
    hit_time = time.time() - start
    
    # 캐시 히트가 10배 이상 빠른지 확인
    assert hit_time < miss_time / 10
    assert hit_time < 0.1  # 100ms 이하
```

### 검증 기준
- [ ] 캐시 히트율 90% 이상
- [ ] API 응답 시간 5배 이상 개선
- [ ] 이벤트 처리 지연 1초 이하
- [ ] 메모리 사용량 정상 범위
- [ ] 모든 테스트 통과

---

## 전체 마이그레이션 체크리스트

### Phase 1: 인프라
- [ ] Redis 컨테이너 추가
- [ ] aiocache 설치
- [ ] 설정 파일 추가
- [ ] 연결 테스트 통과
- [ ] 문서화 완료

### Phase 2: 이벤트 시스템
- [ ] 이벤트 타입 정의
- [ ] Event Bus 구현
- [ ] Redis Streams 통합
- [ ] FastAPI lifespan 통합
- [ ] 단위 테스트 통과
- [ ] 통합 테스트 통과
- [ ] 문서화 완료

### Phase 3: Cache Service
- [ ] aiocache 통합
- [ ] CacheService 구현
- [ ] 데코레이터 구현
- [ ] 이벤트 핸들러 등록
- [ ] 단위 테스트 통과
- [ ] 통합 테스트 통과
- [ ] 문서화 완료

### Phase 4: Service 통합
- [ ] TTSService 수정
- [ ] 의존성 주입 업데이트
- [ ] API 엔드포인트 확인
- [ ] 단위 테스트 통과
- [ ] 통합 테스트 통과
- [ ] E2E 테스트 통과
- [ ] 문서화 완료

### Phase 5: 모니터링
- [ ] 메트릭 수집
- [ ] 로깅 개선
- [ ] 성능 최적화
- [ ] 성능 테스트 통과
- [ ] 문서화 완료

---

## 각 Phase별 테스트-구현-디버깅 루프

### 루프 프로세스

```
┌─────────────────┐
│  Phase 시작     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  1. 구현        │
│  - 코드 작성    │
│  - 기본 동작    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  2. 단위 테스트 │
│  - 함수별 테스트│
│  - Mock 사용    │
└────────┬────────┘
         │
    ┌────┴────┐
    │ 통과?   │
    └────┬────┘
    NO   │   YES
    │    │    │
    ▼    │    ▼
┌────────┴────────┐
│  3. 디버깅      │
│  - 로그 확인    │
│  - 문제 수정    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  4. 통합 테스트 │
│  - 전체 플로우  │
│  - 실제 환경    │
└────────┬────────┘
         │
    ┌────┴────┐
    │ 통과?   │
    └────┬────┘
    NO   │   YES
    │    │    │
    ▼    │    ▼
┌────────┴────────┐
│  5. 검증        │
│  - 성능 확인    │
│  - 메트릭 확인  │
└────────┬────────┘
         │
    ┌────┴────┐
    │ 통과?   │
    └────┬────┘
    NO   │   YES
    │    │    │
    ▼    │    ▼
┌────────┴────────┐
│  6. 문서화      │
│  - 코드 주석    │
│  - README 업데이트│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Phase 완료     │
│  → 다음 Phase   │
└─────────────────┘
```

---

## 디버깅 가이드

### 일반적인 문제 및 해결

#### 1. Redis 연결 실패
**증상**: `ConnectionError` 또는 `TimeoutError`

**해결**:
```bash
# Redis 컨테이너 상태 확인
docker-compose ps redis

# Redis 로그 확인
docker-compose logs redis

# 네트워크 확인
docker network inspect moriai-network

# Redis 직접 연결 테스트
docker-compose exec redis redis-cli ping
```

#### 2. 캐시가 동작하지 않음
**증상**: 항상 캐시 미스

**해결**:
- CacheService 인스턴스 확인: `self.cache_service` 존재 여부
- 데코레이터 적용 확인: `@cache_result` 데코레이터 확인
- Redis 키 확인: `KEYS tts:*`
- 로그 확인: 캐시 동작 로그

#### 3. 이벤트가 처리되지 않음
**증상**: 이벤트 발행 후 캐시 무효화 안 됨

**해결**:
- Event Bus 시작 확인: lifespan에서 `start()` 호출 확인
- Consumer Groups 확인: `XINFO GROUPS events:voice.created`
- Pending 메시지 확인: `XPENDING events:voice.created cache-service`
- 핸들러 등록 확인: `subscribe()` 호출 확인

#### 4. 메모리 사용량 증가
**증상**: Redis 메모리 계속 증가

**해결**:
- Streams 길이 확인: `XLEN events:voice.created`
- MaxLen 설정 확인: `XADD` 시 `maxlen` 옵션
- TTL 확인: 캐시 TTL 설정 확인
- 메모리 정리: `MEMORY DOCTOR` 실행

---

## 성능 벤치마크

### 목표 지표

| 메트릭 | 목표 | 측정 방법 |
|--------|------|----------|
| 캐시 히트율 | > 90% | `hits / (hits + misses)` |
| API 응답 시간 (캐시 히트) | < 100ms | API 호출 시간 측정 |
| API 응답 시간 (캐시 미스) | < 2s | API 호출 시간 측정 |
| 이벤트 처리 지연 | < 1s | 이벤트 발행 → 처리 시간 |
| Redis 메모리 사용 | < 100MB | `INFO memory` |

### 벤치마크 테스트
```python
# tests/performance/benchmark_cache.py
@pytest.mark.asyncio
async def benchmark_cache_performance():
    """캐시 성능 벤치마크"""
    service = get_tts_service()
    
    # 100회 호출
    times = []
    for _ in range(100):
        start = time.time()
        await service.get_voices()
        times.append(time.time() - start)
    
    avg_time = sum(times) / len(times)
    p95_time = sorted(times)[95]
    
    print(f"Average: {avg_time*1000:.2f}ms")
    print(f"P95: {p95_time*1000:.2f}ms")
    
    assert avg_time < 0.1  # 100ms 이하
```

---

## 롤백 계획

### Phase별 롤백

#### Phase 1 롤백
```bash
# Redis 서비스만 제거
docker-compose down redis
# docker-compose.yml에서 redis 서비스 제거
```

#### Phase 2 롤백
```python
# Event Bus 코드만 제거
# lifespan에서 event_bus.start() 제거
```

#### Phase 3 롤백
```python
# CacheService 코드만 제거
# 데코레이터 제거
```

#### Phase 4 롤백
```python
# TTSService에서 데코레이터만 제거
# 기존 로직으로 복귀
```

---

## 최종 검증 체크리스트

### 기능 검증
- [ ] 캐시 조회/저장 정상
- [ ] 캐시 무효화 정상
- [ ] 이벤트 발행/구독 정상
- [ ] 데코레이터 정상 동작
- [ ] TTL 정상 동작

### 성능 검증
- [ ] 캐시 히트율 90% 이상
- [ ] API 응답 시간 5배 이상 개선
- [ ] 이벤트 처리 지연 1초 이하
- [ ] 메모리 사용량 정상

### 안정성 검증
- [ ] Redis 장애 시 graceful degradation
- [ ] 이벤트 처리 실패 시 재처리
- [ ] 동시성 테스트 통과
- [ ] 부하 테스트 통과

---

## 예상 일정

- **Phase 1**: 1-2시간
- **Phase 2**: 2-3시간
- **Phase 3**: 2-3시간
- **Phase 4**: 2-3시간
- **Phase 5**: 1-2시간

**총 예상 시간**: 8-13시간 (1-2일)

---

## 다음 단계

1. **Phase 1부터 시작**: 인프라 구축
2. **각 Phase 완료 후 검증**: 테스트 통과 확인
3. **문제 발생 시 디버깅**: 루프 반복
4. **문서화**: 각 Phase 완료 시 문서 업데이트

