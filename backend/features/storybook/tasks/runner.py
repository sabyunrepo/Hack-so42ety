"""
Task Runner - DAG Execution Engine
의존성 기반 Task 실행 오케스트레이터
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Callable, Awaitable, Optional, Any
from dataclasses import dataclass
from backend.features.tts.producer import TTSProducer

from .schemas import TaskResult, TaskContext, TaskStatus
from .store import TaskStore
from .core import (
    generate_story_task,
    generate_image_task,
    generate_tts_task,
    generate_video_task,
    finalize_book_task,
)

logger = logging.getLogger(__name__)

# Global Semaphore for Production Safety
# 동시 실행 제어 (리소스 폭주 방지)
GLOBAL_TASK_LIMIT = asyncio.Semaphore(10)  # 동시 AI 호출 10개 제한


@dataclass
class TaskNode:
    """
    DAG의 Task 노드

    Attributes:
        task_id: Task 고유 ID
        name: Task 이름 (로깅용)
        func: 실행할 비동기 함수
        args: 함수 인자
        kwargs: 함수 키워드 인자
        depends_on: 의존하는 Task ID 리스트
    """
    task_id: str
    name: str
    func: Callable[..., Awaitable[TaskResult]]
    args: tuple
    kwargs: dict
    depends_on: List[str]


class TaskRunner:
    """
    Asyncio 기반 DAG 실행 엔진

    Features:
    - 의존성 기반 Task 실행 순서 결정
    - 병렬 실행 지원 (의존성 없는 Task는 동시 실행)
    - Task 결과를 Redis TaskStore에 저장
    - 에러 전파 (의존성 Task 실패 시 후속 Task 취소)

    Example:
        runner = TaskRunner()
        t1 = await runner.submit_task("task1", my_task_func, args=(arg1,))
        t2 = await runner.submit_task("task2", my_task_func, depends_on=[t1])
        await runner.execute_dag([t1, t2])
    """

    def __init__(self):
        self.tasks: Dict[str, TaskNode] = {}
        self.futures: Dict[str, asyncio.Task] = {}
        self.results: Dict[str, TaskResult] = {}
        self.task_store = TaskStore()

    async def submit_task(
        self,
        name: str,
        func: Callable[..., Awaitable[TaskResult]],
        args: tuple = (),
        kwargs: Optional[dict] = None,
        depends_on: Optional[List[str]] = None,
    ) -> str:
        """
        Task를 DAG에 추가 (실행은 execute_dag에서)

        Args:
            name: Task 이름 (로깅용, 예: "generate_story", "generate_image_0")
            func: 실행할 비동기 함수 (TaskResult 반환)
            args: 함수 인자
            kwargs: 함수 키워드 인자
            depends_on: 의존하는 Task ID 리스트

        Returns:
            str: Task ID (UUID)
        """
        task_id = str(uuid.uuid4())
        task_node = TaskNode(
            task_id=task_id,
            name=name,
            func=func,
            args=args,
            kwargs=kwargs or {},
            depends_on=depends_on or [],
        )

        self.tasks[task_id] = task_node
        print(f"[TaskRunner] Submitted task: {name} (id={task_id[:8]}...)")

        return task_id

    async def _wait_for_dependencies(self, task_id: str) -> List[TaskResult]:
        """
        Task의 의존성이 완료될 때까지 대기

        Args:
            task_id: Task ID

        Returns:
            List[TaskResult]: 의존하는 Task들의 결과

        Raises:
            ValueError: 의존성 Task가 실패한 경우
        """
        task = self.tasks[task_id]

        if not task.depends_on:
            return []

        print(
            f"[TaskRunner] Task {task.name} waiting for {len(task.depends_on)} dependencies"
        )

        # Wait for all dependency tasks to complete
        dep_futures = [self.futures[dep_id] for dep_id in task.depends_on]
        dep_results = await asyncio.gather(*dep_futures, return_exceptions=True)

        # Check for failures
        results = []
        for dep_id, dep_result in zip(task.depends_on, dep_results):
            dep_name = self.tasks[dep_id].name

            # Handle exceptions
            if isinstance(dep_result, Exception):
                raise ValueError(
                    f"Dependency task '{dep_name}' raised exception: {dep_result}"
                )

            # Check TaskResult status
            if dep_result.status == TaskStatus.FAILED:
                raise ValueError(
                    f"Dependency task '{dep_name}' failed: {dep_result.error}"
                )

            results.append(dep_result)

        print(f"[TaskRunner] Task {task.name} dependencies satisfied")
        return results

    async def _execute_task(self, task_id: str) -> TaskResult:
        """
        개별 Task 실행

        Args:
            task_id: Task ID

        Returns:
            TaskResult: Task 실행 결과
        """
        task = self.tasks[task_id]

        try:
            print(f"[TaskRunner] Executing task: {task.name} (id={task_id[:8]}...)")

            # 1. Wait for dependencies
            dependency_results = await self._wait_for_dependencies(task_id)

            # 2. Execute task function with semaphore (prevent resource explosion)
            # Option B: 의존성은 실행 순서만 보장, 데이터는 Redis 공유
            async with GLOBAL_TASK_LIMIT:
                result = await task.func(*task.args, **task.kwargs)

            # 3. Store result in Redis
            await self.task_store.set_task_result(task_id, result, ttl=3600)

            # 4. Store in memory
            self.results[task_id] = result

            if result.status == TaskStatus.COMPLETED:
                print(
                    f"[TaskRunner] Task completed: {task.name} (id={task_id[:8]}...)"
                )
            elif result.status == TaskStatus.FAILED:
                logger.error(
                    f"[TaskRunner] Task failed: {task.name} (id={task_id[:8]}...), "
                    f"error={result.error}"
                )

            return result

        except asyncio.CancelledError:
            logger.warning(
                f"[TaskRunner] Task cancelled (shutdown): {task.name} (id={task_id[:8]}...)"
            )
            # Create cancelled result
            result = TaskResult(status=TaskStatus.FAILED, error="Task cancelled by shutdown")
            await self.task_store.set_task_result(task_id, result, ttl=3600)
            self.results[task_id] = result
            raise  # Re-raise to propagate cancellation

        except Exception as e:
            logger.error(
                f"[TaskRunner] Task exception: {task.name} (id={task_id[:8]}...), "
                f"error={e}",
                exc_info=True,
            )

            # Create failed result
            result = TaskResult(status=TaskStatus.FAILED, error=str(e))

            # Store failed result
            await self.task_store.set_task_result(task_id, result, ttl=3600)
            self.results[task_id] = result

            return result

    async def execute_dag(self, task_ids: List[str]) -> Dict[str, TaskResult]:
        """
        DAG 실행 (비동기, 병렬 처리)

        ⚠️ 중요: 모든 task를 한꺼번에 asyncio.create_task로 시작하지만,
        각 task는 자신의 depends_on을 먼저 await하므로 실행 순서가 보장됩니다.

        실행 흐름:
        1. 모든 task를 코루틴으로 시작 (await 없이)
        2. 각 task는 _execute_task 내부에서 _wait_for_dependencies 호출
        3. 의존성이 있는 task는 해당 futures를 await하며 대기
        4. 의존성이 완료되면 그제야 실제 함수 실행

        예시:
        - Story task: 의존성 없음 → 즉시 실행
        - Image task: depends_on=[story] → story 완료 대기 → 실행
        - Video task: depends_on=[all images] → 모든 image 완료 대기 → 실행

        Args:
            task_ids: 실행할 Task ID 리스트

        Returns:
            Dict[str, TaskResult]: Task ID → TaskResult 매핑
        """
        print(f"[TaskRunner] Starting DAG execution with {len(task_ids)} tasks")

        # Create asyncio tasks for all nodes
        # ⭐ 여기서는 모든 task를 "시작"만 함 (실제 실행은 의존성 대기 후)
        for task_id in task_ids:
            task = self.tasks[task_id]
            self.futures[task_id] = asyncio.create_task(
                self._execute_task(task_id),
                name=task.name,
            )

        # Wait for all tasks to complete
        # 각 task는 자신의 의존성을 내부에서 await하므로 순서가 보장됨
        await asyncio.gather(*self.futures.values(), return_exceptions=True)

        print(f"[TaskRunner] DAG execution completed")

        return self.results

    def get_result(self, task_id: str) -> Optional[TaskResult]:
        """
        Task 결과 조회 (메모리)

        Args:
            task_id: Task ID

        Returns:
            Optional[TaskResult]: Task 결과, 없으면 None
        """
        return self.results.get(task_id)

    async def get_result_from_store(self, task_id: str) -> Optional[TaskResult]:
        """
        Task 결과 조회 (Redis)

        Args:
            task_id: Task ID

        Returns:
            Optional[TaskResult]: Task 결과, 없으면 None
        """
        return await self.task_store.get_task_result(task_id)


async def create_storybook_dag(
    user_id: uuid.UUID,
    book_id: uuid.UUID,
    stories: List[str],
    images: List[bytes],
    tts_producer: TTSProducer,
    voice_id: str,
    level: int,
    target_language: str = "en",
) -> Dict[str, Any]:
    """
    동화책 생성 DAG 생성 및 실행

    DAG 구조:
        [Story]
           ↓
        ┌──┴──┬──────┐
        ↓     ↓      ↓
     [Img0] [Img1] [Img2] ... (병렬)
        ↓     ↓      ↓
     [TTS0] [TTS1] [TTS2] ... (병렬, Image와도 병렬)
        └──┬──┴──────┘
           ↓
        [Video]
           ↓
       [Finalize]

    Args:
        book_id: Book UUID
        prompt: 사용자 입력 프롬프트
        num_pages: 페이지 수
        target_age: 대상 연령대
        theme: 테마
        user_id: 사용자 UUID

    Returns:
        Dict[str, Any]: Task IDs 매핑
            {
                "story_task": str,
                "image_tasks": List[str],
                "tts_tasks": List[str],
                "video_task": str,
                "finalize_task": str,
            }
    """
    print("#######################################################################")
    print("[create_storybook_dag] Creating DAG for book_id:", book_id, "\n시작한다잉~~~")
    runner = TaskRunner()

    # Task Context
    execution_id = str(uuid.uuid4())
    context = TaskContext(
        book_id=str(book_id),
        user_id=str(user_id),
        execution_id=execution_id,
        retry_count=0,
    )

    # Task 1: Story 생성
    t_story = await runner.submit_task(
        name="generate_story",
        func=generate_story_task,
        args=(
            str(book_id),
            stories,
            level,
            len(stories),
            context,
            target_language,
        ),
    )

    # Task 2: Image 생성 (배치, 모든 페이지 처리)
    t_image = await runner.submit_task(
        name="generate_image_batch",
        func=generate_image_task,
        args=(str(book_id), images, context),
        depends_on=[t_story],  # 실행 순서만 보장, dialogues는 Redis 조회
    )

    # Task 3: TTS 생성 (배치, 모든 페이지 처리, Image와 병렬)
    t_tts = await runner.submit_task(
        name="generate_tts_batch",
        func=generate_tts_task,
        args=(str(book_id), tts_producer, context),
        depends_on=[t_story],  # 실행 순서만 보장, dialogues는 Redis 조회
    )

    # Task 4: Video 생성 (Image 완료 후)
    t_video = await runner.submit_task(
        name="generate_video",
        func=generate_video_task,
        args=(str(book_id), context),
        depends_on=[t_image],  # Image Task 완료 후 실행, Redis에서 image_urls 조회
    )

    # Task 5: Finalize (모든 Task 완료 후)
    t_finalize = await runner.submit_task(
        name="finalize_book",
        func=finalize_book_task,
        args=(str(book_id), context),
        depends_on=[t_story, t_image, t_tts, t_video],
    )

    # DAG 실행 (백그라운드)
    all_task_ids = [t_story, t_image, t_tts, t_video, t_finalize]

    print(
        f"[create_storybook_dag] Submitting {len(all_task_ids)} tasks to background"
    )

    # 백그라운드 실행
    asyncio.create_task(
        runner.execute_dag(all_task_ids),
        name=f"storybook_dag_{book_id}"
    )

    # Task IDs 반환
    return {
        "execution_id": execution_id,
        "story_task": t_story,
        "image_task": t_image,       # 단일 태스크 (기존: image_tasks 리스트)
        "tts_task": t_tts,            # 단일 태스크 (기존: tts_tasks 리스트)
        "video_task": t_video,
        "finalize_task": t_finalize,
        "all_tasks": all_task_ids,
    }
