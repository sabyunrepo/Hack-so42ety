"""
Redis Task Store
비동기 파이프라인의 중간 결과를 Redis에 저장
"""

import json
import logging
from typing import Any, Optional, Dict
import redis.asyncio as aioredis

from backend.core.config import settings
from .schemas import TaskResult, TaskStatus

logger = logging.getLogger(__name__)


class TaskStore:
    """
    Redis 기반 Task 결과 저장소

    Key Patterns:
    - task_result:{task_id} → TaskResult JSON
    - story:{book_id} → Story data (pages, content, prompts)
    - image:{book_id}:{page_idx} → Image URL
    - tts:{book_id}:{page_idx} → Audio URL
    - video:{book_id} → Video URL

    Features:
    - TTL 기반 자동 만료 (기본 1시간)
    - JSON 직렬화/역직렬화
    - 타입 안전성 (TaskResult 객체 변환)
    """

    def __init__(self, redis_url: str = None, default_ttl: int = 3600):
        """
        Args:
            redis_url: Redis 연결 URL (None일 경우 settings에서 가져옴)
            default_ttl: 기본 TTL (초), 기본값 1시간 (3600초)
        """
        self.redis_url = redis_url or settings.redis_url
        self.default_ttl = default_ttl
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self):
        """Redis 연결"""
        if self.redis:
            return

        # from_url은 동기 함수 (await 불필요)
        self.redis = aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50  # connection pool 설정
        )

        # 연결 확인
        try:
            await self.redis.ping()
            logger.debug("TaskStore Redis connection established")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}", exc_info=True)
            self.redis = None
            raise

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Task 결과를 Redis에 저장

        Args:
            key: Redis key (예: "task_result:abc-123", "story:book-456")
            value: 저장할 값 (dict, TaskResult, str 등)
            ttl: TTL (초), None이면 default_ttl 사용

        Returns:
            bool: 저장 성공 여부
        """
        await self.connect()

        try:
            # TaskResult 객체는 dict로 변환
            if isinstance(value, TaskResult):
                value_dict = value.model_dump()
            elif isinstance(value, dict):
                value_dict = value
            else:
                # 기타 타입은 그대로 문자열로 저장
                value_dict = {"data": value}

            # JSON으로 직렬화
            serialized = json.dumps(value_dict, ensure_ascii=False)

            # Redis에 저장 (TTL 설정)
            ttl_value = ttl if ttl is not None else self.default_ttl
            await self.redis.setex(key, ttl_value, serialized)

            logger.debug(f"TaskStore set: {key} (TTL: {ttl_value}s)")
            return True

        except Exception as e:
            logger.error(f"Failed to set key '{key}': {e}", exc_info=True)
            return False

    async def get(self, key: str) -> Optional[Any]:
        """
        Redis에서 Task 결과 조회

        Args:
            key: Redis key

        Returns:
            Optional[Any]: 저장된 값 (dict), 없으면 None
        """
        await self.connect()

        try:
            value = await self.redis.get(key)

            if value is None:
                logger.debug(f"TaskStore get: {key} → Not found")
                return None

            # JSON 역직렬화
            deserialized = json.loads(value)
            logger.debug(f"TaskStore get: {key} → Found")
            return deserialized

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON for key '{key}': {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to get key '{key}': {e}", exc_info=True)
            return None

    async def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """
        Task 결과를 TaskResult 객체로 조회

        Args:
            task_id: Task UUID

        Returns:
            Optional[TaskResult]: TaskResult 객체, 없으면 None
        """
        key = f"task_result:{task_id}"
        data = await self.get(key)

        if data is None:
            return None

        try:
            return TaskResult(**data)
        except Exception as e:
            logger.error(f"Failed to parse TaskResult for '{task_id}': {e}")
            return None

    async def set_task_result(
        self,
        task_id: str,
        result: TaskResult,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Task 결과를 TaskResult 객체로 저장

        Args:
            task_id: Task UUID
            result: TaskResult 객체
            ttl: TTL (초)

        Returns:
            bool: 저장 성공 여부
        """
        key = f"task_result:{task_id}"
        return await self.set(key, result, ttl)

    async def delete(self, key: str) -> bool:
        """
        Task 결과 삭제 (정리용)

        Args:
            key: Redis key

        Returns:
            bool: 삭제 성공 여부 (키가 존재했으면 True)
        """
        await self.connect()

        try:
            deleted_count = await self.redis.delete(key)
            success = deleted_count > 0

            if success:
                logger.debug(f"TaskStore delete: {key} → Deleted")
            else:
                logger.debug(f"TaskStore delete: {key} → Not found")

            return success

        except Exception as e:
            logger.error(f"Failed to delete key '{key}': {e}", exc_info=True)
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        패턴과 일치하는 모든 키 삭제 (정리용)

        Args:
            pattern: Redis key 패턴 (예: "story:*", "task_result:book-123-*")

        Returns:
            int: 삭제된 키 개수
        """
        await self.connect()

        try:
            # 패턴과 일치하는 키 검색
            cursor = 0
            deleted_count = 0

            while True:
                cursor, keys = await self.redis.scan(
                    cursor,
                    match=pattern,
                    count=100
                )

                if keys:
                    deleted = await self.redis.delete(*keys)
                    deleted_count += deleted

                if cursor == 0:
                    break

            logger.info(f"TaskStore delete_pattern: {pattern} → {deleted_count} keys deleted")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete pattern '{pattern}': {e}", exc_info=True)
            return 0

    async def exists(self, key: str) -> bool:
        """
        키 존재 여부 확인

        Args:
            key: Redis key

        Returns:
            bool: 키 존재 여부
        """
        await self.connect()

        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Failed to check existence of key '{key}': {e}", exc_info=True)
            return False

    async def get_ttl(self, key: str) -> Optional[int]:
        """
        키의 남은 TTL 조회

        Args:
            key: Redis key

        Returns:
            Optional[int]: 남은 TTL (초), 키가 없으면 None, TTL 없으면 -1
        """
        await self.connect()

        try:
            ttl = await self.redis.ttl(key)

            if ttl == -2:
                # 키가 존재하지 않음
                return None
            elif ttl == -1:
                # TTL이 설정되지 않음 (영구)
                return -1
            else:
                return ttl

        except Exception as e:
            logger.error(f"Failed to get TTL for key '{key}': {e}", exc_info=True)
            return None

    async def cleanup_book_tasks(self, book_id: str) -> int:
        """
        Book과 관련된 모든 Task 결과 정리 (Finalize 후 호출)

        Args:
            book_id: Book UUID

        Returns:
            int: 삭제된 키 개수
        """
        patterns = [
            f"story:{book_id}",
            f"image:{book_id}:*",
            f"tts:{book_id}:*",
            f"video:{book_id}",
            f"task_result:*{book_id}*"
        ]

        total_deleted = 0
        for pattern in patterns:
            deleted = await self.delete_pattern(pattern)
            total_deleted += deleted

        logger.info(f"Cleaned up {total_deleted} keys for book {book_id}")
        return total_deleted

    async def close(self):
        """Redis 연결 종료"""
        if self.redis:
            await self.redis.close()
            self.redis = None
            logger.debug("TaskStore Redis connection closed")
