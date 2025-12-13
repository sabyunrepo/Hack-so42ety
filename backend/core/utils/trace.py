"""
Tracing & Logging Utilities
프로세스 추적 및 디버깅을 위한 유틸리티
"""

import time
import functools
import inspect
from typing import Optional, Any
from backend.core.logging import get_logger

logger = get_logger()

import contextvars

# 호출 깊이 추적을 위한 ContextVar
_call_depth = contextvars.ContextVar("call_depth", default=0)

def log_process(
    step: str,
    desc: Optional[str] = None,
    level: str = "info"
):
    """
    프로세스 실행 단계 및 소요 시간, 깊이 로깅 데코레이터
    
    Usage:
        @log_process(step="Generate Image", desc="Kling AI 이미지 생성")
        async def generate_image(...): ...
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 현재 깊이 가져오기 및 증가
            depth = _call_depth.get()
            token = _call_depth.set(depth + 1)
            
            # 트리 스타일 깊이 시각화
            # depth 0: (No indent)
            # depth 1: ├── 
            # depth 2: │   ├── 
            if depth == 0:
                prefix = ""
                # 루트일 경우 🚀 같은 이모지로 시작 표시
                icon_start = "🚀"
                icon_end = "✅"
            else:
                prefix = "│   " * (depth - 1) + "├── "
                icon_start = "▶"
                icon_end = "✓"
            
            # 함수 이름과 모듈 경로 파악
            func_name = func.__name__
            module_name = func.__module__
            
            # Context 바인딩
            log = logger.bind(
                process_step=step,
                func_name=func_name,
                module=module_name,
                depth=depth
            )
            
            start_time = time.time()
            
            try:
                # 시작 로깅
                log.info(
                    f"{prefix}{icon_start} Start: {desc or step}",
                )
                
                # 비동기 함수 실행
                if inspect.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                duration = time.time() - start_time
                
                # 종료 로깅
                log.info(
                    f"{prefix}{icon_end} Completed: {desc or step}",
                    duration_s=round(duration, 3),
                    status="success"
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                # 에러 로깅
                log.error(
                    f"{prefix}✕ Failed: {desc or step}",
                    duration_s=round(duration, 3),
                    error=str(e),
                    error_type=type(e).__name__,
                    status="failed"
                )
                raise e # 에러를 다시 던져서 상위 핸들러가 처리하게 함
            
            finally:
                # ContextVar 리셋 (깊이 복구)
                _call_depth.reset(token)

        return wrapper
    return decorator
