"""
Event Bus Interface
이벤트 버스 추상 인터페이스
"""

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

