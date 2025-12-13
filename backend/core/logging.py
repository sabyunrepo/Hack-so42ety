"""
Core Logging Configuration
structlog 기반의 구조화된 로깅 설정
"""

import logging
import sys
from typing import Any, Dict

import structlog
from asgi_correlation_id import correlation_id

from backend.core.config import settings


def configure_logging() -> None:
    """
    structlog 및 표준 로깅 설정
    """
    
    # 공통 프로세서 (structlog & standard logging)
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.stdlib.ExtraAdder(), # extra 인자 표시
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
        structlog.processors.StackInfoRenderer(),
    ]

    # 렌더러 선택
    if settings.log_json_format:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(
            colors=True, 
            pad_event=20,     # 메시지 패딩 (정렬)
        )

    # 1. structlog 자체 설정
    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter, # 로거 래퍼
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # 2. 표준 logging 포맷터 설정 (structlog를 통해 렌더링)
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,  # 표준 로그에 적용할 프로세서
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    # 3. 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.handlers = [] # 기존 핸들러 제거
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level.upper())

    # 4. Uvicorn 및 라이브러리 로거 조정
    # uvicorn.access 로그 등도 structlog 포맷으로 통일
    for _log in ["uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine"]:
        logger = logging.getLogger(_log)
        logger.handlers = [] # 핸들러 제거 (루트로 전파)
        logger.propagate = True


def get_logger(name: str = None) -> Any:
    """
    구조화된 로거 반환
    """
    return structlog.get_logger(name)
