# Event-Driven Cache Invalidation 설계 및 구현 가이드

## 📋 목차
1. [개요](#개요)
2. [아키텍처 설계](#아키텍처-설계)
3. [이벤트 시스템 선택](#이벤트-시스템-선택)
4. [상세 설계](#상세-설계)
5. [구현 단계](#구현-단계)
6. [마이그레이션 전략](#마이그레이션-전략)
7. [모니터링 및 테스트](#모니터링-및-테스트)

---

## 개요

### Event-Driven Invalidation이란?

**전통적 방식 (Write-Invalidate)**:
```python
async def create_voice_clone(...):
    voice = await create_voice(...)
    await cache.delete("tts:voices")  # 직접 무효화
    return voice
```

**Event-Driven 방식**:
```python
async def create_voice_clone(...):
    voice = await create_voice(...)
    await event_bus.publish("voice.created", {"voice_id": voice.id})  # 이벤트 발행
    return voice

# 별도 서비스에서 이벤트 구독
async def handle_voice_created(event):
    await cache.delete("tts:voices")  # 이벤트 기반 무효화
```

### 장점 ✅
- **느슨한 결합**: 서비스 간 직접 의존성 제거
- **확장성**: 여러 서비스가 동일 이벤트 구독 가능
- **유연성**: 새로운 무효화 로직 추가 용이
- **테스트 용이**: 이벤트 모킹으로 단위 테스트 쉬움
- **감사 로그**: 모든 캐시 무효화 이벤트 추적 가능

### 단점 ❌
- **구현 복잡도**: 이벤트 시스템 구축 필요
- **비동기 처리**: 이벤트 처리 지연 가능성
- **디버깅 어려움**: 이벤트 흐름 추적 필요

---

## 아키텍처 설계

### 전체 구조

```
┌─────────────────┐
│  API Endpoint   │
│  (FastAPI)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Service Layer  │
│  (TTSService)   │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌──────────────┐
│  API   │ │ Event Bus    │
│  Call   │ │ (Redis Pub/Sub)│
└────────┘ └──────┬───────┘
                  │
                  ▼
         ┌─────────────────┐
         │ Cache Service    │
         │ (Event Listener) │
         └─────────────────┘
                  │
                  ▼
         ┌─────────────────┐
         │  Redis Cache    │
         └─────────────────┘
```

### 컴포넌트 구성

1. **Event Bus** (`backend/core/events/`)
   - 이벤트 발행/구독 인터페이스
   - Redis Pub/Sub 구현

2. **Event Types** (`backend/core/events/types.py`)
   - 이벤트 타입 정의
   - 이벤트 스키마

3. **Cache Service** (`backend/core/cache/`)
   - 캐시 조회/저장
   - 이벤트 구독 및 무효화

4. **Event Handlers** (`backend/core/cache/handlers.py`)
   - 이벤트별 캐시 무효화 로직

---

## 이벤트 시스템 선택

### 옵션 비교

#### 1. Redis Pub/Sub ⭐⭐⭐⭐⭐ (추천)

**장점**:
- Redis를 이미 캐시로 사용 → 추가 인프라 불필요
- 구현 간단
- 충분한 성능
- FastAPI와 잘 통합

**단점**:
- 메시지 영속성 없음 (구독자가 없으면 손실)
- 단순한 패턴만 지원

**사용 사례**: 현재 프로젝트에 최적

---

#### 2. RabbitMQ

**장점**:
- 메시지 영속성
- 복잡한 라우팅 패턴
- 메시지 큐잉

**단점**:
- 추가 인프라 필요
- 설정 복잡
- 오버엔지니어링 가능

**사용 사례**: 대규모 시스템, 복잡한 워크플로우

---

#### 3. Python Event Library (in-memory)

**장점**:
- 외부 의존성 없음
- 매우 빠름

**단점**:
- 단일 인스턴스만
- 서버 재시작 시 이벤트 손실

**사용 사례**: 개발/테스트 환경

---

### 최종 선택: Redis Pub/Sub

**이유**:
1. Redis를 이미 캐시로 사용할 예정
2. 추가 인프라 불필요
3. 구현 복잡도 적절
4. 프로덕션 환경에 충분

---

## 상세 설계

### 1. 이벤트 타입 정의

```python
# backend/core/events/types.py

from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

class EventType(str, Enum):
    """이벤트 타입"""
    VOICE_CREATED = "voice.created"
    VOICE_UPDATED = "voice.updated"
    VOICE_DELETED = "voice.deleted"
    # 추후 확장 가능
    STORY_GENERATED = "story.generated"
    IMAGE_GENERATED = "image.generated"

class Event(BaseModel):
    """이벤트 기본 구조"""
    type: EventType
    payload: Dict[str, Any]
    timestamp: datetime
    source: str  # 이벤트 발생 서비스
    event_id: str  # 고유 ID

class VoiceCreatedEvent(BaseModel):
    """Voice 생성 이벤트"""
    voice_id: str
    name: str
    user_id: Optional[str] = None
```

---

### 2. Event Bus 인터페이스

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
    async def start(self) -> None:
        """이벤트 버스 시작"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """이벤트 버스 중지"""
        pass
```

---

### 3. Redis Pub/Sub 구현

```python
# backend/core/events/redis_bus.py

import json
import asyncio
from typing import Dict, List, Callable, Awaitable
import aioredis
from .bus import EventBus
from .types import Event, EventType
from ..config import settings

class RedisEventBus(EventBus):
    """Redis Pub/Sub 기반 이벤트 버스"""
    
    def __init__(self):
        self.redis_pub: Optional[aioredis.Redis] = None
        self.redis_sub: Optional[aioredis.Redis] = None
        self.pubsub = None
        self.handlers: Dict[EventType, List[Callable]] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def connect(self):
        """Redis 연결"""
        self.redis_pub = await aioredis.from_url(
            f"redis://{settings.redis_host}:{settings.redis_port}",
            encoding="utf-8",
            decode_responses=True
        )
        self.redis_sub = await aioredis.from_url(
            f"redis://{settings.redis_host}:{settings.redis_port}",
            encoding="utf-8",
            decode_responses=True
        )
        self.pubsub = self.redis_sub.pubsub()
    
    async def publish(self, event_type: EventType, payload: dict) -> None:
        """이벤트 발행"""
        event = Event(
            type=event_type,
            payload=payload,
            timestamp=datetime.utcnow(),
            source="tts-service",
            event_id=str(uuid.uuid4())
        )
        
        channel = f"events:{event_type.value}"
        await self.redis_pub.publish(channel, event.model_dump_json())
    
    async def subscribe(
        self, 
        event_type: EventType, 
        handler: Callable[[Event], Awaitable[None]]
    ) -> None:
        """이벤트 구독"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
            channel = f"events:{event_type.value}"
            await self.pubsub.subscribe(channel)
        
        self.handlers[event_type].append(handler)
    
    async def _listen(self):
        """이벤트 수신 루프"""
        while self._running:
            try:
                message = await self.pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0
                )
                
                if message:
                    channel = message["channel"]
                    data = json.loads(message["data"])
                    event = Event(**data)
                    
                    # 채널에서 이벤트 타입 추출
                    event_type_str = channel.replace("events:", "")
                    event_type = EventType(event_type_str)
                    
                    # 모든 핸들러 실행
                    if event_type in self.handlers:
                        for handler in self.handlers[event_type]:
                            try:
                                await handler(event)
                            except Exception as e:
                                logger.error(f"Handler error: {e}", exc_info=True)
            
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Event listening error: {e}", exc_info=True)
                await asyncio.sleep(1)
    
    async def start(self) -> None:
        """이벤트 버스 시작"""
        if not self.redis_sub:
            await self.connect()
        
        self._running = True
        self._task = asyncio.create_task(self._listen())
    
    async def stop(self) -> None:
        """이벤트 버스 중지"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        if self.pubsub:
            await self.pubsub.unsubscribe()
        
        if self.redis_sub:
            await self.redis_sub.close()
        if self.redis_pub:
            await self.redis_pub.close()
```

---

### 4. Cache Service with Event Handling

```python
# backend/core/cache/service.py

import aioredis
from typing import Optional, Any, Callable, Awaitable
from functools import wraps
from json import dumps, loads
from ..events.bus import EventBus
from ..events.types import Event, EventType
from ..config import settings
import hashlib
import inspect

class CacheService:
    """캐시 서비스 (이벤트 기반 무효화)"""
    
    def __init__(self, event_bus: EventBus):
        self.redis: Optional[aioredis.Redis] = None
        self.event_bus = event_bus
        self._setup_event_handlers()
    
    async def connect(self):
        """Redis 연결"""
        self.redis = await aioredis.from_url(
            f"redis://{settings.redis_host}:{settings.redis_port}",
            encoding="utf-8",
            decode_responses=True
        )
    
    def _setup_event_handlers(self):
        """이벤트 핸들러 등록"""
        self.event_bus.subscribe(EventType.VOICE_CREATED, self._handle_voice_created)
        self.event_bus.subscribe(EventType.VOICE_UPDATED, self._handle_voice_updated)
        self.event_bus.subscribe(EventType.VOICE_DELETED, self._handle_voice_deleted)
    
    async def get(self, key: str) -> Optional[Any]:
        """캐시 조회"""
        if not self.redis:
            await self.connect()
        
        cached = await self.redis.get(key)
        if cached:
            return loads(cached)
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """캐시 저장"""
        if not self.redis:
            await self.connect()
        
        await self.redis.setex(key, ttl, dumps(value))
    
    async def delete(self, key: str) -> None:
        """캐시 삭제"""
        if not self.redis:
            await self.connect()
        
        await self.redis.delete(key)
    
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
    
    Returns:
        데코레이터 함수
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # CacheService 인스턴스 가져오기
            cache_service = getattr(self, 'cache_service', None)
            if not cache_service:
                # 의존성 주입으로 받지 않은 경우 직접 호출
                return await func(self, *args, **kwargs)
            
            # 캐시 키 생성
            if key_builder:
                cache_key = key_builder(self, *args, **kwargs)
            elif '{' in key:
                # 키 템플릿 사용 (예: "user:{user_id}")
                cache_key = key.format(**kwargs)
            else:
                cache_key = key
            
            # 캐시 조회
            cached = await cache_service.get(cache_key)
            if cached is not None:
                return cached
            
            # 캐시 미스 - 원본 함수 실행
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
    
    Returns:
        데코레이터 함수
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
                        formatted_key = key.format(**kwargs)
                        await cache_service.delete(formatted_key)
                    else:
                        await cache_service.delete(key)
            
            return result
        
        return wrapper
    return decorator
```

---

### 5. Service Layer 통합 (데코레이터 사용)

```python
# backend/features/tts/service.py

from ..core.cache.service import CacheService, cache_result, invalidate_cache
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
            voices = await tts_provider.get_available_voices()
            return voices
        except Exception as e:
            raise TTSGenerationFailedException(reason=str(e))
    
    async def create_voice_clone(
        self,
        user_id: uuid.UUID,
        name: str,
        audio_file: bytes,
    ) -> Dict[str, Any]:
        """
        Voice Clone 생성 (이벤트 발행으로 캐시 무효화)
        
        이벤트 핸들러가 자동으로 캐시 무효화 처리
        """
        # Voice 생성
        tts_provider = self.ai_factory.get_tts_provider()
        voice = await tts_provider.clone_voice(name=name, audio_file=audio_file)
        
        # 이벤트 발행 (캐시 무효화 트리거)
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

### 데코레이터 사용 예시

#### 기본 사용법
```python
@cache_result(key="tts:voices", ttl=3600)
async def get_voices(self) -> List[Dict[str, Any]]:
    return await api_call()
```

#### 동적 키 사용
```python
@cache_result(key="user:{user_id}:books", ttl=1800)
async def get_user_books(self, user_id: uuid.UUID) -> List[Book]:
    return await self.book_repo.get_user_books(user_id)
```

#### 커스텀 키 빌더
```python
def build_voice_key(self, voice_id: str, language: str) -> str:
    return f"tts:voice:{voice_id}:{language}"

@cache_result(key="", key_builder=build_voice_key, ttl=3600)
async def get_voice_settings(self, voice_id: str, language: str) -> Dict:
    return await api_call(voice_id, language)
```

#### 캐시 무효화 데코레이터
```python
@invalidate_cache("tts:voices")
async def create_voice_clone(self, ...):
    voice = await create_voice(...)
    return voice
```

#### 여러 키 무효화
```python
@invalidate_cache("tts:voices", "tts:voice:{voice_id}")
async def update_voice(self, voice_id: str, ...):
    voice = await update_voice(...)
    return voice
```

---

## 데코레이터 기반 캐싱의 장점

### 1. 코드 간결성
**Before (수동 캐싱)**:
```python
async def get_voices(self) -> List[Dict[str, Any]]:
    cached = await self.cache_service.get("tts:voices")
    if cached:
        return cached
    
    voices = await tts_provider.get_available_voices()
    await self.cache_service.set("tts:voices", voices, ttl=3600)
    return voices
```

**After (데코레이터)**:
```python
@cache_result(key="tts:voices", ttl=3600)
async def get_voices(self) -> List[Dict[str, Any]]:
    return await tts_provider.get_available_voices()
```

### 2. 관심사 분리
- 비즈니스 로직에 집중
- 캐싱 로직은 데코레이터가 처리

### 3. 재사용성
- 동일한 데코레이터를 여러 메서드에 적용
- 일관된 캐싱 전략

### 4. 테스트 용이성
- 데코레이터를 모킹하여 캐싱 없이 테스트 가능
- 비즈니스 로직만 단위 테스트

---

## 구현 단계

### Phase 1: 인프라 구축 (1-2시간)

#### 1.1 Docker Compose에 Redis 추가

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    container_name: moriai-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
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

#### 1.2 requirements.txt에 라이브러리 추가

```txt
aioredis==2.0.1  # Redis async client
```

#### 1.3 설정 추가

```python
# backend/core/config.py
redis_host: str = Field(default="redis", env="REDIS_HOST")
redis_port: int = Field(default=6379, env="REDIS_PORT")
```

---

### Phase 2: 이벤트 시스템 구축 (2-3시간)

#### 2.1 디렉토리 구조 생성

```
backend/core/
├── events/
│   ├── __init__.py
│   ├── bus.py          # EventBus 인터페이스
│   ├── redis_bus.py    # Redis 구현
│   └── types.py        # 이벤트 타입 정의
└── cache/
    ├── __init__.py
    ├── service.py      # CacheService
    └── handlers.py     # 이벤트 핸들러
```

#### 2.2 이벤트 타입 정의 구현
- `backend/core/events/types.py` 생성
- EventType enum 정의
- Event 모델 정의

#### 2.3 Event Bus 구현
- `backend/core/events/bus.py` - 인터페이스
- `backend/core/events/redis_bus.py` - Redis 구현

---

### Phase 3: Cache Service 구현 (2-3시간)

#### 3.1 Cache Service 구현
- `backend/core/cache/service.py` 생성
- Redis 캐시 조회/저장 메서드
- 이벤트 핸들러 등록

#### 3.2 캐싱 데코레이터 구현
- `cache_result` 데코레이터 구현
- `invalidate_cache` 데코레이터 구현
- 동적 키 빌더 지원

#### 3.3 의존성 주입 설정
- `backend/core/dependencies.py`에 추가
- FastAPI lifespan에서 이벤트 버스 시작/중지

---

### Phase 4: Service Layer 통합 (2-3시간)

#### 4.1 TTSService 수정
- CacheService, EventBus 의존성 추가
- `get_voices()`에 `@cache_result` 데코레이터 적용
- `create_voice_clone()`에 이벤트 발행 추가
- 코드 간결성 확인

#### 4.2 API 엔드포인트 수정
- 의존성 주입 업데이트
- 데코레이터 동작 확인

---

### Phase 5: 테스트 및 검증 (1-2시간)

#### 5.1 단위 테스트
- 이벤트 발행/구독 테스트
- 캐시 무효화 테스트

#### 5.2 통합 테스트
- 전체 플로우 테스트
- 동시성 테스트

---

## 마이그레이션 전략

### 전략: 점진적 마이그레이션 (Zero Downtime)

### Step 1: 인프라 준비 (비침투적)

**작업**:
1. Redis 컨테이너 추가
2. 이벤트 시스템 코드 추가 (아직 사용 안 함)
3. 기존 코드는 그대로 유지

**검증**:
- Redis 연결 테스트
- 기존 기능 정상 동작 확인

**롤백 계획**:
- Redis 컨테이너만 제거하면 됨

---

### Step 2: 이벤트 시스템 활성화 (읽기 전용)

**작업**:
1. Event Bus 시작 (lifespan)
2. Cache Service 이벤트 구독 시작
3. **캐시는 아직 사용 안 함** (읽기만)

**검증**:
- 이벤트 발행/구독 로그 확인
- 기존 API 응답 시간 변화 없음 확인

**롤백 계획**:
- Event Bus 중지만 하면 됨

---

### Step 3: 캐시 읽기 활성화 (쓰기 안 함)

**작업**:
1. `get_voices()`에 캐시 읽기 추가
2. 캐시 미스 시 API 호출
3. **캐시 저장은 아직 안 함** (읽기만)

**검증**:
- 캐시 히트율 0% 확인 (정상)
- API 호출 정상 동작 확인

**롤백 계획**:
- 캐시 읽기 코드만 제거

---

### Step 4: 캐시 쓰기 활성화

**작업**:
1. `get_voices()`에 캐시 저장 추가
2. TTL 설정 (1시간)

**검증**:
- 캐시 히트율 증가 확인
- API 호출 감소 확인
- 응답 시간 개선 확인

**롤백 계획**:
- 캐시 저장 코드만 제거

---

### Step 5: 이벤트 기반 무효화 활성화

**작업**:
1. `create_voice_clone()`에 이벤트 발행 추가
2. 이벤트 핸들러로 캐시 무효화

**검증**:
- Voice 생성 후 캐시 무효화 확인
- 다음 조회 시 새 음성 포함 확인

**롤백 계획**:
- 이벤트 발행 코드만 제거 (캐시는 유지)

---

### 마이그레이션 체크리스트

#### Phase 1: 준비
- [ ] Redis 인프라 추가
- [ ] 이벤트 시스템 코드 추가 (비활성)
- [ ] 기존 기능 테스트

#### Phase 2: 이벤트 시스템
- [ ] Event Bus 시작
- [ ] 이벤트 구독 활성화
- [ ] 로그 모니터링

#### Phase 3: 캐시 읽기
- [ ] 캐시 읽기 코드 추가
- [ ] 캐시 미스 시 API 호출 확인
- [ ] 성능 모니터링

#### Phase 4: 캐시 쓰기
- [ ] 캐시 저장 코드 추가
- [ ] 캐시 히트율 확인
- [ ] API 호출 감소 확인

#### Phase 5: 이벤트 무효화
- [ ] 이벤트 발행 코드 추가
- [ ] 캐시 무효화 확인
- [ ] 전체 플로우 테스트

---

## 모니터링 및 테스트

### 모니터링 지표

#### 1. 캐시 메트릭
- 캐시 히트율
- 캐시 미스율
- 캐시 크기
- TTL 만료 횟수

#### 2. 이벤트 메트릭
- 이벤트 발행 횟수
- 이벤트 처리 시간
- 이벤트 처리 실패 횟수
- 이벤트 지연 시간

#### 3. 성능 메트릭
- API 응답 시간 (캐시 히트/미스)
- 외부 API 호출 횟수
- 서버 부하

### 로깅

```python
# 이벤트 발행 로그
logger.info(f"Event published: {event_type.value}", extra={
    "event_id": event.event_id,
    "event_type": event_type.value,
    "payload": event.payload
})

# 캐시 무효화 로그
logger.info(f"Cache invalidated: {cache_key}", extra={
    "event_id": event.event_id,
    "cache_key": cache_key,
    "reason": "voice_created"
})
```

### 테스트 시나리오

#### 시나리오 1: 정상 캐싱
1. `/voices` 호출 → 캐시 저장
2. `/voices` 재호출 → 캐시 히트
3. **검증**: API 호출 1회만 발생

#### 시나리오 2: 이벤트 기반 무효화
1. `/voices` 호출 → 캐시 저장
2. Voice Clone 생성 → 이벤트 발행
3. 이벤트 핸들러 → 캐시 무효화
4. `/voices` 재호출 → 캐시 미스 → API 호출
5. **검증**: 새 음성이 목록에 포함됨

#### 시나리오 3: TTL 만료
1. `/voices` 호출 → 캐시 저장 (TTL 1시간)
2. 1시간 대기
3. `/voices` 재호출 → 캐시 미스 (TTL 만료)
4. **검증**: 자동 갱신

#### 시나리오 4: 동시성
1. 여러 인스턴스에서 동시에 `/voices` 호출
2. **검증**: 첫 번째만 API 호출, 나머지는 캐시 히트

---

## 장점 요약

### 1. 확장성
- 새로운 무효화 로직 추가 시 이벤트 핸들러만 추가
- 여러 서비스가 동일 이벤트 구독 가능

### 2. 유지보수성
- 서비스 간 직접 의존성 제거
- 이벤트 기반으로 느슨한 결합

### 3. 테스트 용이성
- 이벤트 모킹으로 단위 테스트 쉬움
- 각 컴포넌트 독립 테스트 가능

### 4. 감사 및 디버깅
- 모든 캐시 무효화 이벤트 추적 가능
- 이벤트 로그로 문제 진단 용이

---

## 예상 구현 시간

- **Phase 1**: 1-2시간 (인프라)
- **Phase 2**: 2-3시간 (이벤트 시스템)
- **Phase 3**: 2-3시간 (Cache Service)
- **Phase 4**: 2-3시간 (Service 통합)
- **Phase 5**: 1-2시간 (테스트)

**총 예상 시간**: 8-13시간 (1-2일)

---

## 다음 단계

1. **즉시 시작**: Phase 1 (Redis 인프라 추가)
2. **점진적 구현**: 각 Phase별 검증 후 다음 단계 진행
3. **모니터링**: 각 Phase에서 메트릭 수집
4. **문서화**: 구현 과정 문서화

