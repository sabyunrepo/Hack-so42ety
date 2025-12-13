"""
Task Execution Schemas
Task 실행 시 사용되는 스키마 정의
"""

from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel


class TaskStatus(str, Enum):
    """Task 실행 상태"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class TaskResult(BaseModel):
    """
    Task 실행 결과

    Attributes:
        status: Task 실행 상태
        result: 성공 시 결과 데이터 (dict)
        error: 실패 시 에러 메시지
    """
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    class Config:
        use_enum_values = True


class TaskContext(BaseModel):
    """
    Task 실행 컨텍스트
    모든 Task에 공통으로 전달되는 정보

    Attributes:
        book_id: Book UUID (string)
        user_id: User UUID (string)
        execution_id: DAG 실행 고유 ID
        retry_count: 재시도 횟수
    """
    book_id: str
    user_id: str
    execution_id: str
    retry_count: int = 0
