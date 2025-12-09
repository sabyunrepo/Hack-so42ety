"""
Cache Service
aiocache 기반 캐시 서비스 (이벤트 기반 무효화)
"""

import logging
import time
from typing import Optional, Any, Callable
from functools import wraps
from aiocache import caches
from ..events.bus import EventBus
from ..events.types import Event, EventType
from .metrics import cache_metrics

logger = logging.getLogger(__name__)


class CacheService:
    """aiocache 기반 캐시 서비스 (이벤트 기반 무효화)"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._cache = None
        self._handlers_registered = False
    
    def _get_cache(self):
        """캐시 인스턴스 가져오기 (lazy initialization)"""
        if not self._cache:
            self._cache = caches.get("default")
        return self._cache
    
    async def _setup_event_handlers(self):
        """이벤트 핸들러 등록 (비동기)"""
        if self._handlers_registered:
            return
        
        try:
            await self.event_bus.subscribe(EventType.VOICE_CREATED, self._handle_voice_created)
            await self.event_bus.subscribe(EventType.VOICE_UPDATED, self._handle_voice_updated)
            await self.event_bus.subscribe(EventType.VOICE_DELETED, self._handle_voice_deleted)
            self._handlers_registered = True
            logger.info("Event handlers registered successfully")
        except Exception as e:
            logger.error(f"Failed to register event handlers: {e}", exc_info=True)
    
    async def get(self, key: str) -> Optional[Any]:
        """캐시 조회"""
        # 이벤트 핸들러 등록 (최초 1회)
        await self._setup_event_handlers()
        
        start = time.time()
        try:
            cache = self._get_cache()
            result = await cache.get(key)
            duration = time.time() - start
            
            # aiocache의 JsonSerializer가 문자열로 반환하는 경우 처리
            if isinstance(result, str):
                try:
                    import json
                    result = json.loads(result)
                except (json.JSONDecodeError, TypeError):
                    pass  # JSON이 아니면 그대로 반환
            
            # 메트릭 기록
            if result is not None:
                cache_metrics.record_hit(key, duration)
                logger.info(
                    f"Cache hit: {key}",
                    extra={
                        "cache_key": key,
                        "duration_ms": duration * 1000,
                        "hit": True,
                    }
                )
            else:
                cache_metrics.record_miss(key, duration)
                logger.info(
                    f"Cache miss: {key}",
                    extra={
                        "cache_key": key,
                        "duration_ms": duration * 1000,
                        "hit": False,
                    }
                )
            
            return result
        except Exception as e:
            cache_metrics.record_error(key)
            logger.error(
                f"Cache get error: {key}",
                extra={
                    "cache_key": key,
                    "error": str(e),
                },
                exc_info=True
            )
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """캐시 저장"""
        # 이벤트 핸들러 등록 (최초 1회)
        await self._setup_event_handlers()
        
        start = time.time()
        try:
            cache = self._get_cache()
            await cache.set(key, value, ttl=ttl)
            duration = time.time() - start
            cache_metrics.record_set(key, duration)
            logger.info(
                f"Cache set: {key}",
                extra={
                    "cache_key": key,
                    "ttl": ttl,
                    "duration_ms": duration * 1000,
                }
            )
        except Exception as e:
            cache_metrics.record_error(key)
            logger.error(
                f"Cache set error: {key}",
                extra={
                    "cache_key": key,
                    "error": str(e),
                },
                exc_info=True
            )
    
    async def delete(self, key: str) -> None:
        """캐시 삭제"""
        start = time.time()
        try:
            cache = self._get_cache()
            await cache.delete(key)
            duration = time.time() - start
            cache_metrics.record_delete(key, duration)
            logger.info(
                f"Cache deleted: {key}",
                extra={
                    "cache_key": key,
                    "duration_ms": duration * 1000,
                }
            )
        except Exception as e:
            cache_metrics.record_error(key)
            logger.error(
                f"Cache delete error: {key}",
                extra={
                    "cache_key": key,
                    "error": str(e),
                },
                exc_info=True
            )
    
    # 이벤트 핸들러들
    async def _handle_voice_created(self, event: Event) -> None:
        """Voice 생성 이벤트 처리"""
        logger.info(
            f"Voice created event received: {event.event_id}",
            extra={
                "event_id": event.event_id,
                "event_type": event.type.value,
                "cache_key": "tts:voices",
            }
        )
        await self.delete("tts:voices")
        logger.info(
            f"Cache invalidated: tts:voices",
            extra={
                "event_id": event.event_id,
                "event_type": event.type.value,
                "cache_key": "tts:voices",
            }
        )
    
    async def _handle_voice_updated(self, event: Event) -> None:
        """Voice 수정 이벤트 처리"""
        logger.info(
            f"Voice updated event received: {event.event_id}",
            extra={
                "event_id": event.event_id,
                "event_type": event.type.value,
                "cache_key": "tts:voices",
            }
        )
        await self.delete("tts:voices")
        logger.info(
            f"Cache invalidated: tts:voices",
            extra={
                "event_id": event.event_id,
                "event_type": event.type.value,
                "cache_key": "tts:voices",
            }
        )
    
    async def _handle_voice_deleted(self, event: Event) -> None:
        """Voice 삭제 이벤트 처리"""
        logger.info(
            f"Voice deleted event received: {event.event_id}",
            extra={
                "event_id": event.event_id,
                "event_type": event.type.value,
                "cache_key": "tts:voices",
            }
        )
        await self.delete("tts:voices")
        logger.info(
            f"Cache invalidated: tts:voices",
            extra={
                "event_id": event.event_id,
                "event_type": event.type.value,
                "cache_key": "tts:voices",
            }
        )


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

