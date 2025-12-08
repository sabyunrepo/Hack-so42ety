"""
Redis Streams Event Bus
Redis Streams 기반 이벤트 버스 구현
"""

import json
import asyncio
import logging
import os
from typing import Dict, List, Callable, Awaitable, Optional
import redis.asyncio as aioredis
import redis
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
            except redis.exceptions.ResponseError as e:
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
    
    async def start(self, consumer_name: str = None) -> None:
        """이벤트 버스 시작"""
        if not self.redis:
            await self.connect()
        
        # Consumer name이 없으면 PID 기반으로 생성
        if consumer_name is None:
            consumer_name = f"worker-{os.getpid()}"
        
        self._running = True
        self._task = asyncio.create_task(self._listen(consumer_name))
        logger.info(f"Event bus started (consumer: {consumer_name})")
    
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

