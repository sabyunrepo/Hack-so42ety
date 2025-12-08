"""
Application Lifespan Management
애플리케이션 시작/종료 이벤트 관리
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI

from .config import settings as config
from .logging import get_logger
from .dependencies import get_book_repository, get_http_client, get_key_pool_manager
from .jwt_auth import check_kling_credits

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
        http_client = get_http_client()

        # 인메모리 캐시 워밍업 (파일 시스템 스캔)
        await book_repository.initialize_cache()

        # 캐시 통계 출력
        stats = book_repository.get_cache_stats()
        logger.info(f"Cache Stats: {stats}")

        logger.info(f"key_pool: {config.kling_access_key}")
        logger.info(f"secret_pool: {config.kling_secret_key}")

        # Kling API 키 풀 초기화 및 크레딧 확인
        try:
            key_pool_manager = get_key_pool_manager()
            all_keys = key_pool_manager.get_all_key_pairs()
            logger.info(f"🔑 Kling API Key Pool initialized with {len(all_keys)} keys")

            # 각 키별로 크레딧 확인
            for idx, (ak, sk) in enumerate(all_keys):
                logger.info(f"📊 Checking credits for Kling API key #{idx + 1}...")
                try:
                    await check_kling_credits(
                        access_key=ak, secret_key=sk, api_url=config.kling_api_url
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Failed to check credits for key #{idx + 1}: {e}")
                    logger.warning("This is not critical. Service will continue.")

        except ValueError as e:
            logger.error(f"❌ Kling API key pool configuration error: {e}")
            logger.error(
                "Please set KLING_ACCESS_KEYS_JSON and KLING_SECRET_KEYS_JSON environment variables."
            )
            raise
        except Exception as e:
            logger.error(f"❌ Failed to initialize Kling API key pool: {e}")
            raise

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

    try:
        # 공유 HTTP 클라이언트 정리
        await http_client.aclose()
        logger.info("HTTP client closed successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

    logger.info("Shutdown complete")
