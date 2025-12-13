"""
Voice 동기화 작업 큐 (Redis 기반)
Voice 생성 시 Redis에 작업 정보 저장, Scheduled Task에서 조회
"""
import logging
import uuid
from typing import Set, Optional
import redis.asyncio as aioredis
from backend.core.config import settings

logger = logging.getLogger(__name__)


class VoiceSyncQueue:
    """
    Voice 동기화 작업 큐 (Redis 기반)
    
    Redis Set을 사용하여 처리 대기 중인 Voice ID 저장
    - Key: "voice:sync:queue"
    - Value: Set of voice_id (UUID string)
    - TTL: 30분 (자동 만료)
    """
    
    def __init__(self, redis_url: str = None):
        """
        Args:
            redis_url: Redis 연결 URL (None일 경우 settings에서 가져옴)
        """
        self.redis_url = redis_url or settings.redis_url
        self.redis: Optional[aioredis.Redis] = None
        self.queue_key = "voice:sync:queue"
        self.ttl_seconds = 30 * 60  # 30분
    
    async def connect(self):
        """Redis 연결"""
        if not self.redis:
            self.redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
    
    async def enqueue(self, voice_id: uuid.UUID) -> bool:
        """
        Voice 동기화 작업 추가
        
        Args:
            voice_id: Voice UUID
        
        Returns:
            bool: 추가 성공 여부
        """
        await self.connect()
        
        try:
            voice_id_str = str(voice_id)
            
            # Set에 추가
            await self.redis.sadd(self.queue_key, voice_id_str)
            
            # TTL 설정 (큐 자체는 영구, 개별 항목은 처리 시 제거)
            await self.redis.expire(self.queue_key, self.ttl_seconds)
            
            logger.info(f"Voice {voice_id} added to sync queue")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enqueue voice {voice_id}: {e}", exc_info=True)
            return False
    
    async def dequeue(self, voice_id: uuid.UUID) -> bool:
        """
        Voice 동기화 작업 제거 (처리 완료 시)
        
        Args:
            voice_id: Voice UUID
        
        Returns:
            bool: 제거 성공 여부
        """
        await self.connect()
        
        try:
            voice_id_str = str(voice_id)
            removed = await self.redis.srem(self.queue_key, voice_id_str)
            
            if removed:
                logger.info(f"Voice {voice_id} removed from sync queue")
            
            return removed > 0
            
        except Exception as e:
            logger.error(f"Failed to dequeue voice {voice_id}: {e}", exc_info=True)
            return False
    
    async def get_all(self) -> Set[str]:
        """
        모든 대기 중인 작업 조회
        
        Returns:
            Set[str]: Voice ID 문자열 집합
        """
        await self.connect()
        
        try:
            voice_ids = await self.redis.smembers(self.queue_key)
            return voice_ids if voice_ids else set()
            
        except Exception as e:
            logger.error(f"Failed to get queue items: {e}", exc_info=True)
            return set()
    
    async def count(self) -> int:
        """
        대기 중인 작업 개수 조회
        
        Returns:
            int: 작업 개수
        """
        await self.connect()
        
        try:
            return await self.redis.scard(self.queue_key)
            
        except Exception as e:
            logger.error(f"Failed to get queue count: {e}", exc_info=True)
            return 0
    
    async def clear(self) -> int:
        """
        모든 작업 제거 (테스트용)
        
        Returns:
            int: 제거된 작업 개수
        """
        await self.connect()
        
        try:
            count = await self.count()
            await self.redis.delete(self.queue_key)
            return count
            
        except Exception as e:
            logger.error(f"Failed to clear queue: {e}", exc_info=True)
            return 0
    
    async def close(self):
        """Redis 연결 종료"""
        if self.redis:
            await self.redis.close()
            self.redis = None

    async def mark_trigger_processed(self, voice_id: uuid.UUID) -> bool:
        """
        Voice Trigger TTS 요청 성공 기록
        
        Args:
            voice_id: Voice UUID
            
        Returns:
            bool: 성공 여부
        """
        await self.connect()
        try:
            key = f"voice:trigger:success:{voice_id}"
            # 30분 TTL 설정 (전체 타임아웃과 동일)
            await self.redis.set(key, "1", ex=self.ttl_seconds)
            logger.info(f"Marked trigger processed for voice {voice_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to mark trigger processed for voice {voice_id}: {e}", exc_info=True)
            return False

    async def is_trigger_processed(self, voice_id: uuid.UUID) -> bool:
        """
        Voice Trigger TTS 요청 성공 여부 확인
        
        Args:
            voice_id: Voice UUID
            
        Returns:
            bool: 이미 성공적으로 요청했으면 True
        """
        await self.connect()
        try:
            key = f"voice:trigger:success:{voice_id}"
            exists = await self.redis.exists(key)
            return exists > 0
        except Exception as e:
            logger.error(f"Failed to check trigger status for voice {voice_id}: {e}", exc_info=True)
            return False

