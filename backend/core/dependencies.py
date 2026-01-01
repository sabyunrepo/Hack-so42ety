"""
Core Dependencies
공통 의존성 주입 함수
"""

from typing import Optional, Callable
from fastapi import Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.config import settings
from backend.infrastructure.storage.local import LocalStorageService
from backend.infrastructure.storage.s3 import S3StorageService
from backend.infrastructure.ai.factory import AIProviderFactory
from backend.core.events.redis_streams_bus import RedisStreamsEventBus
from backend.core.cache.service import CacheService
from backend.core.database.session import get_db
from backend.core.rate_limiter import get_rate_limiter, RateLimiterService
from backend.core.exceptions import RateLimitExceededException, ErrorCode

# 전역 Event Bus 참조 (main.py의 lifespan에서 설정)
_event_bus: Optional[RedisStreamsEventBus] = None


def set_event_bus(event_bus_instance: RedisStreamsEventBus):
    """Event Bus 설정 (lifespan에서 호출)"""
    global _event_bus
    _event_bus = event_bus_instance


def get_event_bus() -> RedisStreamsEventBus:
    """Event Bus 의존성 주입"""
    if not _event_bus:
        raise RuntimeError("Event bus not initialized. Check if lifespan started correctly.")
    return _event_bus


# 전역 CacheService 참조
_cache_service: Optional[CacheService] = None


def get_cache_service(
    event_bus: RedisStreamsEventBus = Depends(get_event_bus)
) -> CacheService:
    """CacheService 의존성 주입 (Singleton)"""
    global _cache_service
    if not _cache_service:
        _cache_service = CacheService(event_bus=event_bus)
    return _cache_service


def get_storage_service():
    """
    스토리지 서비스 의존성

    설정에 따라 LocalStorageService 또는 S3StorageService 반환

    Returns:
        AbstractStorageService: 스토리지 서비스 인스턴스
    """
    if settings.storage_provider == "s3":
        return S3StorageService()
    return LocalStorageService()


def get_ai_factory() -> AIProviderFactory:
    """
    AI Factory 의존성

    Returns:
        AIProviderFactory: AI Provider Factory 인스턴스
    """
    return AIProviderFactory()


async def get_tts_service(
    db: AsyncSession = Depends(get_db),
    storage_service = Depends(get_storage_service),
    cache_service: CacheService = Depends(get_cache_service),
    ai_factory: AIProviderFactory = Depends(get_ai_factory),
    event_bus: RedisStreamsEventBus = Depends(get_event_bus),
):
    """
    TTS Service 의존성 주입

    Args:
        db: 데이터베이스 세션
        storage_service: 스토리지 서비스
        cache_service: 캐시 서비스
        ai_factory: AI Factory
        event_bus: Event Bus

    Returns:
        TTSService: TTS Service 인스턴스
    """
    from backend.features.tts.service import TTSService
    from backend.features.tts.repository import AudioRepository, VoiceRepository

    audio_repo = AudioRepository(db)
    voice_repo = VoiceRepository(db)

    return TTSService(
        audio_repo=audio_repo,
        voice_repo=voice_repo,
        storage_service=storage_service,
        ai_factory=ai_factory,
        db_session=db,
        cache_service=cache_service,
        event_bus=event_bus,
    )


def get_client_ip(request: Request) -> str:
    """
    클라이언트 IP 주소 추출

    프록시 환경을 지원하기 위해 X-Forwarded-For 헤더를 우선적으로 확인합니다.

    Args:
        request: FastAPI Request 객체

    Returns:
        str: 클라이언트 IP 주소
    """
    # X-Forwarded-For 헤더 확인 (프록시, 로드 밸런서 환경)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For는 "client, proxy1, proxy2" 형식
        # 첫 번째 IP가 실제 클라이언트 IP
        return forwarded_for.split(",")[0].strip()

    # X-Real-IP 헤더 확인 (Nginx 등에서 사용)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # 헤더가 없으면 직접 연결된 클라이언트 IP 사용
    if request.client:
        return request.client.host

    # 모두 없으면 기본값
    return "unknown"


def create_rate_limit_dependency(
    endpoint: str,
    limit: int,
    window_seconds: int,
) -> Callable:
    """
    속도 제한 의존성 팩토리 함수

    특정 엔드포인트에 대한 속도 제한 의존성 함수를 생성합니다.

    Args:
        endpoint: 엔드포인트 식별자 (예: "auth:login")
        limit: 최대 요청 수
        window_seconds: 시간 윈도우 (초)

    Returns:
        Callable: FastAPI 의존성 함수

    Example:
        ```python
        rate_limit_login = create_rate_limit_dependency(
            endpoint="auth:login",
            limit=5,
            window_seconds=60
        )

        @router.post("/login", dependencies=[Depends(rate_limit_login)])
        async def login(...):
            ...
        ```
    """
    async def rate_limit_dependency(
        request: Request,
        response: Response,
    ) -> None:
        """
        속도 제한 검사 의존성

        Args:
            request: FastAPI Request 객체
            response: FastAPI Response 객체

        Raises:
            RateLimitExceededException: 속도 제한 초과 시
        """
        # 속도 제한 비활성화 시 스킵
        if not settings.rate_limit_enabled:
            return

        # 클라이언트 IP 추출
        client_ip = get_client_ip(request)

        # Rate limiter 인스턴스 가져오기
        rate_limiter = get_rate_limiter()

        # Redis 연결 확인
        if not rate_limiter._connected:
            await rate_limiter.connect()

        # 속도 제한 키 생성 (endpoint:ip)
        rate_limit_key = f"{endpoint}:{client_ip}"

        # 속도 제한 검사
        result = await rate_limiter.check_rate_limit(
            key=rate_limit_key,
            limit=limit,
            window_seconds=window_seconds,
        )

        # 응답에 Rate Limit 헤더 추가
        for header_name, header_value in result.to_headers().items():
            response.headers[header_name] = header_value

        # 제한 초과 시 예외 발생
        if not result.allowed:
            # Retry-After 헤더 추가
            if result.retry_after:
                response.headers["Retry-After"] = str(result.retry_after)

            raise RateLimitExceededException(
                error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
                message=f"요청 속도 제한을 초과했습니다. {result.retry_after}초 후에 다시 시도해주세요.",
                details={
                    "limit": result.limit,
                    "window_seconds": window_seconds,
                    "retry_after": result.retry_after,
                    "reset_at": result.reset_at,
                }
            )

    return rate_limit_dependency

