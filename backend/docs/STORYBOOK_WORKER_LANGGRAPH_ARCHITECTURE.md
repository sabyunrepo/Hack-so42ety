# Storybook Worker + LangGraph 아키텍처

이 문서는 Storybook 생성 파이프라인을 **Worker 패턴**과 **LangGraph**를 결합하여 확장 가능하고 복구 가능한 시스템으로 구축하는 방법을 설명합니다.

---

## 목차

1. [현재 구조 분석](#1-현재-구조-분석)
2. [확장 필요성](#2-확장-필요성)
3. [아키텍처 개요](#3-아키텍처-개요)
4. [LangGraph 소개](#4-langgraph-소개)
5. [구현 코드](#5-구현-코드)
6. [실행 흐름](#6-실행-흐름)
7. [장애 복구](#7-장애-복구)
8. [배포 구성](#8-배포-구성)
9. [비교 분석](#9-비교-분석)

---

## 1. 현재 구조 분석

### 현재 Storybook DAG Runner

```
┌──────────────────────────────────────────────────────┐
│              FastAPI 프로세스 (단일)                   │
│                                                       │
│  ┌─────────────────────────────────────────────┐     │
│  │           asyncio Event Loop                │     │
│  │                                             │     │
│  │  ┌─────────┐  ┌─────────────────────────┐  │     │
│  │  │ API     │  │  asyncio.create_task()  │  │     │
│  │  │ Handler │  │                         │  │     │
│  │  └─────────┘  │  ┌─────────────────────┐│  │     │
│  │               │  │   Storybook DAG     ││  │     │
│  │               │  │   (runner.py)       ││  │     │
│  │               │  └─────────────────────┘│  │     │
│  │               └─────────────────────────┘  │     │
│  └─────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────┘
```

### 현재 구조의 특징

| 항목 | 설명 |
|------|------|
| 프로세스 | 1개 (FastAPI + DAG 실행) |
| 스레드 | 1개 |
| 실행 방식 | `asyncio.create_task()` |
| 상태 관리 | 메모리 + Redis |
| 장애 격리 | ❌ API와 함께 죽음 |
| 재시작 복구 | ❌ 없음 |

### 현재 DAG 구조 (runner.py)

```
        [Story]
           │
    ┌──────┴──────┐
    ▼             ▼
[Image]        [TTS]     (병렬)
    │             │
    ▼             │
[Video]          │
    │             │
    └──────┬──────┘
           ▼
      [Finalize]
```

---

## 2. 확장 필요성

### 현재 구조의 한계

```
문제 1: 장애 격리 없음
─────────────────────
API 서버 죽음 → 진행 중인 모든 Storybook 작업 손실

문제 2: 수평 확장 어려움
─────────────────────
서버 추가 시 동시성 제어 어려움 (전역 Semaphore 공유 불가)

문제 3: 재시작 복구 없음
─────────────────────
서버 재시작 시 PROCESSING 상태의 책들은 영원히 미완료
```

### 확장 요구사항

| 요구사항 | 설명 |
|----------|------|
| 프로세스 분리 | API와 Worker 독립 실행 |
| 수평 확장 | Worker 인스턴스 추가로 처리량 증가 |
| 장애 복구 | Worker 재시작 시 중단점에서 이어서 실행 |
| 상태 추적 | 각 단계의 진행 상황 영구 저장 |

---

## 3. 아키텍처 개요

### 목표 아키텍처

```
┌─────────────┐     ┌───────────────┐     ┌──────────────────────┐
│ API Server  │────▶│ Redis Streams │────▶│  Storybook Worker    │
│             │     │               │     │                      │
│ Producer:   │     │ book_id만     │     │ LangGraph App 실행   │
│ book_id 발행│     │ 저장          │     │ + PostgreSQL 체크포인터│
└─────────────┘     └───────────────┘     └──────────────────────┘
```

### 확장된 구조

```
                    ┌─── API Server 1 ───┐
사용자 ──▶ LB ──▶   ├─── API Server 2 ───┼──▶ Redis Streams
                    └─── API Server 3 ───┘
                                              │
                    ┌─── Storybook Worker 1 ──┤
                    ├─── Storybook Worker 2 ──┤  (수평 확장)
                    └─── Storybook Worker 3 ──┘
                                │
                                ▼
                    ┌─────────────────────┐
                    │ PostgreSQL          │
                    │ (LangGraph 체크포인터)│
                    └─────────────────────┘
```

---

## 4. LangGraph 소개

### LangGraph란?

LangChain 팀에서 개발한 **상태 기반 워크플로우 엔진**입니다.

### 핵심 기능

| 기능 | 설명 |
|------|------|
| 상태 관리 | TypedDict 기반 상태 정의 |
| 체크포인트 | 각 노드 완료 시 자동 저장 |
| 재시도 | 내장 RetryPolicy |
| 조건부 분기 | `add_conditional_edges()` |
| 병렬 실행 | 여러 엣지로 자동 병렬화 |

### 현재 구조 vs LangGraph

| 기능 | 현재 (runner.py) | LangGraph |
|------|-----------------|-----------|
| DAG 정의 | 수동 (`depends_on`) | 선언적 (`add_edge`) |
| 상태 관리 | Redis + 메모리 | 내장 State + Checkpointer |
| 체크포인트 | ❌ 직접 구현 필요 | ✅ 내장 |
| 재시도 | 직접 구현 (`retry.py`) | ✅ 내장 |
| 중단점 복구 | ❌ 없음 | ✅ 자동 |
| 조건부 분기 | 수동 | ✅ `add_conditional_edges` |
| 시각화 | ❌ 없음 | ✅ 그래프 시각화 |

---

## 5. 구현 코드

### 5.1 LangGraph Workflow 정의

```python
# backend/features/storybook/graph/workflow.py

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from typing import TypedDict, Optional, Annotated
import operator

class BookState(TypedDict):
    """Storybook 생성 워크플로우 상태"""

    # 입력 데이터
    book_id: str
    user_id: str
    stories: list[str]
    images: list[bytes]
    level: int
    voice_id: str
    target_language: str

    # 결과 데이터 (Reducer로 누적)
    generated_story: Annotated[Optional[dict], operator.or_]
    generated_images: Annotated[list, operator.add]
    generated_tts: Annotated[list, operator.add]
    generated_videos: Annotated[list, operator.add]
    error: Optional[str]


async def story_node(state: BookState) -> dict:
    """Story 생성 노드"""
    from backend.features.storybook.tasks.core import generate_story_task

    result = await generate_story_task(
        book_id=state["book_id"],
        stories=state["stories"],
        level=state["level"],
        target_language=state["target_language"],
        # ...
    )
    return {"generated_story": result.result}


async def images_node(state: BookState) -> dict:
    """Image 생성 노드"""
    from backend.features.storybook.tasks.core import generate_image_task

    result = await generate_image_task(
        book_id=state["book_id"],
        images=state["images"],
        # ...
    )
    return {"generated_images": result.result.get("storage_paths", [])}


async def tts_node(state: BookState) -> dict:
    """TTS 생성 노드"""
    from backend.features.storybook.tasks.core import generate_tts_task

    result = await generate_tts_task(
        book_id=state["book_id"],
        # ...
    )
    return {"generated_tts": result.result}


async def video_node(state: BookState) -> dict:
    """Video 생성 노드"""
    from backend.features.storybook.tasks.core import generate_video_task

    result = await generate_video_task(
        book_id=state["book_id"],
        # ...
    )
    return {"generated_videos": result.result}


async def finalize_node(state: BookState) -> dict:
    """완료 처리 노드"""
    from backend.features.storybook.tasks.core import finalize_book_task

    await finalize_book_task(
        book_id=state["book_id"],
        # ...
    )
    return {}


def build_workflow() -> StateGraph:
    """Storybook 생성 워크플로우 그래프 빌드"""

    workflow = StateGraph(BookState)

    # 노드 추가
    workflow.add_node("story", story_node)
    workflow.add_node("images", images_node)
    workflow.add_node("tts", tts_node)
    workflow.add_node("video", video_node)
    workflow.add_node("finalize", finalize_node)

    # 엣지 정의 (의존성)
    workflow.set_entry_point("story")

    # story 완료 후 images, tts 병렬 실행
    workflow.add_edge("story", "images")
    workflow.add_edge("story", "tts")

    # images 완료 후 video 실행
    workflow.add_edge("images", "video")

    # video, tts 모두 완료 후 finalize
    workflow.add_edge(["video", "tts"], "finalize")

    # finalize 완료 후 종료
    workflow.add_edge("finalize", END)

    return workflow


# 싱글톤 워크플로우
_workflow = build_workflow()


async def get_compiled_app(checkpointer):
    """체크포인터와 함께 컴파일된 앱 반환"""
    return _workflow.compile(checkpointer=checkpointer)
```

### 5.2 Producer (API에서 사용)

```python
# backend/features/storybook/producer.py

import uuid
import logging
from backend.core.events.bus import EventBus
from backend.core.events.types import EventType

logger = logging.getLogger(__name__)


class StorybookProducer:
    """
    Storybook 생성 요청을 Redis Streams에 발행

    API 서버에서 사용하며, 실제 처리는 Worker가 담당
    """

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    async def enqueue_book_creation(
        self,
        book_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """
        Storybook 생성 작업을 큐에 등록

        Args:
            book_id: Book UUID (데이터는 DB에 이미 저장됨)
            user_id: User UUID

        Note:
            이미지, 스토리 등 큰 데이터는 DB에 저장되어 있으므로
            book_id만 전달하고 Worker에서 조회
        """
        payload = {
            "book_id": str(book_id),
            "user_id": str(user_id),
        }

        try:
            await self.event_bus.publish(
                EventType.STORYBOOK_CREATION,
                payload
            )
            logger.info(f"Storybook creation enqueued: book_id={book_id}")
        except Exception as e:
            logger.error(f"Failed to enqueue storybook creation: {e}")
            raise
```

### 5.3 Worker (별도 프로세스)

```python
# backend/features/storybook/worker.py

import asyncio
import json
import logging
import uuid
from typing import Optional, Set

import redis.asyncio as aioredis
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from backend.core.config import settings
from backend.core.events.types import EventType
from backend.core.database.session import AsyncSessionLocal
from backend.features.storybook.repository import BookRepository
from backend.features.storybook.models import BookStatus
from backend.features.storybook.graph.workflow import get_compiled_app, BookState

logger = logging.getLogger(__name__)


class StorybookWorker:
    """
    Storybook 생성 Worker

    Redis Streams에서 book_id를 받아 LangGraph 워크플로우를 실행합니다.
    PostgreSQL 체크포인터를 통해 중간 상태를 저장하며,
    Worker 재시작 시 마지막 체크포인트에서 자동으로 재개합니다.

    Features:
        - Redis Streams Consumer Group 패턴
        - LangGraph 체크포인트 자동 저장
        - Semaphore 기반 동시성 제어
        - 장애 복구 지원
    """

    def __init__(self):
        self.redis_url = settings.redis_url
        self.stream_name = f"events:{EventType.STORYBOOK_CREATION.value}"
        self.group_name = "storybook_workers"
        self.consumer_name = f"worker-{uuid.uuid4().hex[:8]}"

        # 동시 실행 제한 (리소스 보호)
        self.semaphore = asyncio.Semaphore(3)
        self.active_tasks: Set[asyncio.Task] = set()
        self.running = False

        # 연결 객체
        self.redis: Optional[aioredis.Redis] = None
        self.checkpointer: Optional[AsyncPostgresSaver] = None
        self.app = None

    async def start(self):
        """Worker 시작"""
        logger.info(
            f"Starting Storybook Worker: {self.consumer_name} "
            f"(Redis: {self.redis_url})"
        )

        # Redis 연결
        self.redis = await aioredis.from_url(
            self.redis_url,
            decode_responses=True
        )

        # LangGraph 체크포인터 초기화 (PostgreSQL)
        self.checkpointer = AsyncPostgresSaver.from_conn_string(
            settings.database_url
        )
        await self.checkpointer.setup()  # 체크포인트 테이블 생성

        # LangGraph App 컴파일
        self.app = await get_compiled_app(self.checkpointer)

        # Consumer Group 생성 (없으면)
        try:
            await self.redis.xgroup_create(
                self.stream_name,
                self.group_name,
                id="0",
                mkstream=True
            )
            logger.info(f"Consumer group created: {self.group_name}")
        except aioredis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise
            logger.info(f"Consumer group already exists: {self.group_name}")

        # 미완료 작업 복구
        await self.recover_incomplete_books()

        self.running = True

        try:
            while self.running:
                await self.semaphore.acquire()

                try:
                    messages = await self.redis.xreadgroup(
                        self.group_name,
                        self.consumer_name,
                        {self.stream_name: ">"},
                        count=1,
                        block=1000
                    )

                    if not messages:
                        self.semaphore.release()
                        continue

                    for stream, msgs in messages:
                        for msg_id, data in msgs:
                            task = asyncio.create_task(
                                self.process_message_wrapper(msg_id, data)
                            )
                            self.active_tasks.add(task)
                            task.add_done_callback(self.active_tasks.discard)

                except Exception as e:
                    logger.error(f"Error in main loop: {e}", exc_info=True)
                    self.semaphore.release()
                    await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("Worker cancelled")
        finally:
            await self.shutdown()

    async def process_message_wrapper(self, msg_id: str, data: dict):
        """메시지 처리 래퍼 (Semaphore 반환 보장)"""
        try:
            await self.process_message(msg_id, data)
        finally:
            self.semaphore.release()

    async def process_message(self, msg_id: str, data: dict):
        """메시지 처리 - LangGraph 워크플로우 실행"""
        try:
            # 이벤트 파싱
            event_json = data.get("event")
            if not event_json:
                logger.error(f"Invalid message format: {data}")
                await self.redis.xack(self.stream_name, self.group_name, msg_id)
                return

            event_dict = json.loads(event_json)
            payload = event_dict.get("payload", {})

            book_id = payload.get("book_id")
            user_id = payload.get("user_id")

            if not book_id:
                logger.error(f"Missing book_id in payload: {payload}")
                await self.redis.xack(self.stream_name, self.group_name, msg_id)
                return

            logger.info(f"Processing book: {book_id}")

            # DB에서 Book 데이터 조회
            async with AsyncSessionLocal() as session:
                repo = BookRepository(session)
                book = await repo.get_with_pages(uuid.UUID(book_id))

                if not book:
                    logger.error(f"Book not found: {book_id}")
                    await self.redis.xack(self.stream_name, self.group_name, msg_id)
                    return

                # 상태를 PROCESSING으로 업데이트
                await repo.update(
                    uuid.UUID(book_id),
                    status=BookStatus.PROCESSING
                )
                await session.commit()

                # 초기 상태 구성
                initial_state: BookState = {
                    "book_id": book_id,
                    "user_id": user_id,
                    "stories": [p.story for p in book.pages if p.story],
                    "images": [],  # 별도 로드 필요
                    "level": book.level or 1,
                    "voice_id": book.voice_id or "",
                    "target_language": book.target_language or "en",
                    "generated_story": None,
                    "generated_images": [],
                    "generated_tts": [],
                    "generated_videos": [],
                    "error": None,
                }

            # LangGraph 실행 (thread_id = book_id로 체크포인트 관리)
            config = {"configurable": {"thread_id": book_id}}

            result = await self.app.ainvoke(initial_state, config=config)

            if result.get("error"):
                logger.error(f"Book {book_id} failed: {result['error']}")
            else:
                logger.info(f"Book {book_id} completed successfully")

            # ACK (성공적으로 처리됨)
            await self.redis.xack(self.stream_name, self.group_name, msg_id)

        except Exception as e:
            logger.error(
                f"Failed to process message {msg_id}: {e}",
                exc_info=True
            )
            # ACK하지 않음 → 재시도 가능 (XCLAIM으로 다른 Worker가 가져갈 수 있음)

    async def recover_incomplete_books(self):
        """
        미완료 작업 복구

        서버 재시작 시 PROCESSING 상태인 책들을 찾아
        LangGraph 체크포인트에서 이어서 실행
        """
        logger.info("Checking for incomplete books to recover...")

        async with AsyncSessionLocal() as session:
            repo = BookRepository(session)

            # PROCESSING 상태이고 5분 이상 경과한 책들
            from datetime import datetime, timedelta

            incomplete_books = await repo.find_by_status_and_age(
                status=BookStatus.PROCESSING,
                older_than=timedelta(minutes=5)
            )

            for book in incomplete_books:
                try:
                    book_id = str(book.id)
                    config = {"configurable": {"thread_id": book_id}}

                    # LangGraph에서 이전 상태 조회
                    state = await self.app.aget_state(config)

                    if state and state.values:
                        logger.info(
                            f"Resuming book {book_id} from checkpoint "
                            f"(last node: {state.next})"
                        )

                        # 체크포인트에서 이어서 실행
                        # None을 전달하면 마지막 상태에서 재개
                        asyncio.create_task(
                            self.resume_book(book_id, config)
                        )
                    else:
                        logger.warning(
                            f"No checkpoint found for book {book_id}, "
                            "marking as failed"
                        )
                        await repo.update(
                            book.id,
                            status=BookStatus.FAILED,
                            error_message="No checkpoint found for recovery"
                        )
                        await session.commit()

                except Exception as e:
                    logger.error(
                        f"Failed to recover book {book.id}: {e}",
                        exc_info=True
                    )

    async def resume_book(self, book_id: str, config: dict):
        """체크포인트에서 책 생성 재개"""
        try:
            async with self.semaphore:
                # None 전달 = 마지막 체크포인트에서 이어서 실행
                result = await self.app.ainvoke(None, config=config)

                if result.get("error"):
                    logger.error(f"Resumed book {book_id} failed: {result['error']}")
                else:
                    logger.info(f"Resumed book {book_id} completed successfully")

        except Exception as e:
            logger.error(f"Failed to resume book {book_id}: {e}", exc_info=True)

    async def shutdown(self):
        """Worker 종료"""
        logger.info("Shutting down Storybook Worker...")
        self.running = False

        # 진행 중인 태스크 취소
        if self.active_tasks:
            for task in self.active_tasks:
                task.cancel()
            await asyncio.gather(*self.active_tasks, return_exceptions=True)

        # Redis 연결 종료
        if self.redis:
            await self.redis.close()

        logger.info("Storybook Worker shutdown complete")


# 독립 실행용 엔트리포인트
if __name__ == "__main__":
    from backend.core.logging import configure_logging

    configure_logging()

    worker = StorybookWorker()

    try:
        asyncio.run(worker.start())
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received")
```

### 5.4 이벤트 타입 추가

```python
# backend/core/events/types.py

class EventType(str, Enum):
    """이벤트 타입"""
    VOICE_CREATED = "voice.created"
    VOICE_UPDATED = "voice.updated"
    VOICE_DELETED = "voice.deleted"
    TTS_CREATION = "tts.creation"
    STORYBOOK_CREATION = "storybook.creation"  # 추가
```

---

## 6. 실행 흐름

### 정상 흐름

```
1. API 요청 수신
   │
   ▼
2. StorybookProducer.enqueue_book_creation(book_id)
   │
   ▼
3. Redis Streams에 이벤트 발행
   │  {"book_id": "abc-123", "user_id": "user-456"}
   │
   ▼
4. StorybookWorker가 메시지 수신
   │
   ▼
5. DB에서 Book 데이터 조회
   │
   ▼
6. LangGraph app.ainvoke(initial_state, thread_id=book_id)
   │
   ├──▶ [story_node] ──▶ 체크포인트 저장 ✓
   │         │
   │    ┌────┴────┐
   │    ▼         ▼
   ├──▶ [images]  [tts] ──▶ 체크포인트 저장 ✓ (병렬)
   │    │         │
   │    ▼         │
   ├──▶ [video] ──┘ ──▶ 체크포인트 저장 ✓
   │         │
   │         ▼
   └──▶ [finalize] ──▶ 완료!

7. Redis ACK (메시지 처리 완료)
```

### 체크포인트 저장 시점

```
각 노드 완료 시 PostgreSQL에 자동 저장:

┌─────────────────────────────────────────────────────────────┐
│  langgraph_checkpoints 테이블                                │
├─────────────────────────────────────────────────────────────┤
│  thread_id  │  checkpoint_id  │  parent_id  │  checkpoint   │
├─────────────────────────────────────────────────────────────┤
│  abc-123    │  cp-001         │  NULL       │  {story완료}   │
│  abc-123    │  cp-002         │  cp-001     │  {images완료}  │
│  abc-123    │  cp-003         │  cp-001     │  {tts완료}     │
│  abc-123    │  cp-004         │  cp-002,003 │  {video완료}   │
│  abc-123    │  cp-005         │  cp-004     │  {finalize}    │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. 장애 복구

### Worker 중단 시나리오

```
상황: Worker가 images_node 실행 중 죽음

┌─────────────────────────────────────────────────────────────┐
│  Worker 1 (죽음)                                             │
│                                                              │
│  [story] ✓ ──▶ [images] 💀                                  │
│                    │                                         │
│         체크포인트: story 완료 상태 저장됨                     │
└─────────────────────────────────────────────────────────────┘

                         ▼ Worker 재시작

┌─────────────────────────────────────────────────────────────┐
│  Worker 2 (복구)                                             │
│                                                              │
│  recover_incomplete_books() 실행                             │
│       │                                                      │
│       ▼                                                      │
│  app.aget_state(thread_id="abc-123")                         │
│       │                                                      │
│       ▼                                                      │
│  마지막 체크포인트: story 완료                                │
│       │                                                      │
│       ▼                                                      │
│  app.ainvoke(None, config) ──▶ images부터 재개!              │
│                                                              │
│  [images] ✓ ──▶ [tts] ✓ ──▶ [video] ✓ ──▶ [finalize] ✓      │
└─────────────────────────────────────────────────────────────┘
```

### 복구 코드

```python
async def recover_incomplete_books(self):
    """미완료 작업 복구"""

    # PROCESSING 상태인 책들 조회
    incomplete_books = await repo.find_by_status(BookStatus.PROCESSING)

    for book in incomplete_books:
        book_id = str(book.id)
        config = {"configurable": {"thread_id": book_id}}

        # 체크포인트 조회
        state = await self.app.aget_state(config)

        if state and state.values:
            # 체크포인트에서 이어서 실행
            # None을 전달하면 마지막 상태에서 자동 재개
            await self.app.ainvoke(None, config=config)
        else:
            # 체크포인트 없음 → 실패 처리
            await repo.update(book.id, status=BookStatus.FAILED)
```

### LangGraph 복구의 핵심

```python
# 체크포인트에서 재개하는 마법 ✨

# 1. 마지막 상태 조회
state = await app.aget_state(config)
# → state.values: 마지막 저장된 상태
# → state.next: 다음에 실행할 노드들

# 2. 재개 실행
result = await app.ainvoke(None, config=config)
#                          ^^^^
#                          None = "마지막 체크포인트에서 이어서"

# 3. 처음부터 실행하려면
result = await app.ainvoke(initial_state, config=config)
#                          ^^^^^^^^^^^^^
#                          새 상태 전달 = 처음부터 시작
```

---

## 8. 배포 구성

### Docker Compose

```yaml
# docker-compose.prod.yml

version: '3.8'

services:
  # API 서버 (가벼움)
  api:
    build: .
    command: uvicorn backend.main:app --host 0.0.0.0 --port 8000
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://redis:6379
    deploy:
      replicas: 3
    depends_on:
      - db
      - redis

  # Storybook Worker (무거운 작업)
  storybook-worker:
    build: .
    command: python -m backend.features.storybook.worker
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://redis:6379
    deploy:
      replicas: 5  # 수평 확장!
    depends_on:
      - db
      - redis

  # TTS Worker (기존)
  tts-worker:
    build: .
    command: python -m backend.features.tts.worker
    deploy:
      replicas: 3
    depends_on:
      - redis

  # 인프라
  db:
    image: postgres:16

  redis:
    image: redis:7-alpine
```

### Kubernetes Deployment

```yaml
# k8s/storybook-worker.yaml

apiVersion: apps/v1
kind: Deployment
metadata:
  name: storybook-worker
spec:
  replicas: 5
  selector:
    matchLabels:
      app: storybook-worker
  template:
    metadata:
      labels:
        app: storybook-worker
    spec:
      containers:
      - name: worker
        image: moriai/backend:latest
        command: ["python", "-m", "backend.features.storybook.worker"]
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        - name: REDIS_URL
          valueFrom:
            configMapKeyRef:
              name: redis-config
              key: url
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: storybook-worker-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: storybook-worker
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

---

## 9. 비교 분석

### 아키텍처 비교

| 항목 | 현재 구조 | Worker + LangGraph |
|------|----------|---------------------|
| 프로세스 분리 | ❌ | ✅ |
| 수평 확장 | ❌ | ✅ |
| 장애 격리 | ❌ | ✅ |
| 체크포인트 | ❌ | ✅ (자동) |
| 재시작 복구 | ❌ | ✅ (자동) |
| 코드 복잡도 | 낮음 | 중간 |
| 외부 의존성 | 없음 | langgraph |

### 성능 비교

| 시나리오 | 현재 구조 | Worker + LangGraph |
|----------|----------|---------------------|
| 단일 서버, 10권 요청 | 동시 처리 (Semaphore 제한) | 동일 |
| 다중 서버, 100권 요청 | 동기화 어려움 | Worker 수만큼 분산 처리 |
| 서버 재시작 | 진행 중 작업 손실 | 체크포인트에서 재개 |
| 부분 실패 | 수동 처리 필요 | 자동 재시도 가능 |

### 도입 권장 상황

```
✅ Worker + LangGraph 도입 권장:
   - 서비스 확장이 예상될 때
   - 장애 복구가 중요할 때
   - 복잡한 워크플로우가 추가될 예정일 때
   - 팀이 LangChain 생태계에 익숙할 때

⚠️ 현재 구조 유지 권장:
   - 단일 서버로 충분할 때
   - 추가 의존성을 피하고 싶을 때
   - 워크플로우가 단순하고 고정적일 때
```

---

## 의존성

```
# requirements.txt 추가

langgraph>=0.2.0
langgraph-checkpoint-postgres>=1.0.0
```

---

## 참고 자료

- [LangGraph 공식 문서](https://langchain-ai.github.io/langgraph/)
- [LangGraph Checkpointing](https://langchain-ai.github.io/langgraph/concepts/persistence/)
- [Redis Streams 가이드](https://redis.io/docs/data-types/streams/)
