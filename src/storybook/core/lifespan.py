"""
Application Lifespan Management
애플리케이션 시작/종료 이벤트 관리
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI

from .config import settings as config
from .logging import get_logger
from .dependencies import get_book_repository

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    애플리케이션 생명주기 관리

    Startup: 캐시 워밍업, 공유 클라이언트 초기화
    Shutdown: 정리 작업 (HTTP 클라이언트 종료, GenAI 클라이언트 정리)
    """
    # Startup
    logger.info("=" * 60)
    logger.info("MoriAI Storybook Service Starting...")
    logger.info("=" * 60)
    logger.info(config)
    try:
        # 의존성 인스턴스 가져오기 (싱글톤 초기화)
        book_repository = get_book_repository()

        # 인메모리 캐시 워밍업 (파일 시스템 스캔)
        await book_repository.initialize_cache()

        # 캐시 통계 출력
        stats = book_repository.get_cache_stats()
        logger.info(f"Cache Stats: {stats}")

        # Kling API 키 풀 초기화 및 크레딧 확인
        logger.info("=" * 60)
        logger.info("Storybook Service Ready!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        raise

    yield  # 애플리케이션 실행 중

    # Shutdown
    logger.info("=" * 60)
    logger.info("MoriAI Storybook Service Shutting Down...")
    logger.info("=" * 60)
    logger.info("Shutdown complete")
