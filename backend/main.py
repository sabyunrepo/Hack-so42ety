"""
MoriAI Storybook Backend - Main Application
FastAPI 통합 백엔드 서비스
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from asgi_correlation_id import CorrelationIdMiddleware
import sentry_sdk

from .core.config import settings
from .core.database import engine, Base
from .core.middleware import setup_cors
from .core.middleware.auth import UserContextMiddleware
from .core.events.redis_streams_bus import RedisStreamsEventBus

from .core.dependencies import set_event_bus
from .core.cache.config import initialize_cache
from .core.redis import get_redis_manager
from .core.tasks.voice_sync import sync_voice_status_periodically
from .core.logging import configure_logging, get_logger
from backend.features.tts.producer import TTSProducer
from backend.features.storybook.dependencies import set_tts_producer

# Sentry 초기화
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
    )

# 로깅 설정 초기화
configure_logging()
logger = get_logger(__name__)




# 전역 Event Bus 인스턴스
event_bus: RedisStreamsEventBus = None

# 전역 Voice Sync Task 인스턴스
voice_sync_task: asyncio.Task = None

# 전역 TTS Worker 인스턴스
from backend.features.tts.worker import TTSWorker
tts_worker: TTSWorker = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 생명주기 관리

    Startup:
        - 데이터베이스 연결 확인
        - Event Bus 시작
        - 로깅 초기화

    Shutdown:
        - Event Bus 중지
        - 데이터베이스 연결 종료
    """
    global event_bus
    
    # Startup
    logger.info("Application Starting", 
        version=settings.app_version, 
        env=settings.app_env, 
        debug=settings.debug
    )
    print("=" * 60)

    # 데이터베이스 연결 확인
    try:
        async with engine.begin() as conn:
            # 연결 테스트만 수행 (테이블 생성은 entrypoint.sh에서 처리)
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))
            print("✓ Database connection verified")
    except Exception as e:
        print(f"⚠ Database connection failed: {e}")

    # aiocache 초기화
    try:
        initialize_cache()
        print("✓ Cache initialized")
    except Exception as e:
        print(f"⚠ Cache initialization failed: {e}")

    # Event Bus 시작
    global voice_sync_task
    try:
        # 1. Redis 연결 초기화
        redis_manager = get_redis_manager()
        await redis_manager.connect()
        print("✓ Redis Manager connected")

        # 2. Event Bus 시작 (공유된 Redis 클라이언트 사용)
        event_bus = RedisStreamsEventBus(
            redis_client=redis_manager.client,  # 클라이언트 주입
            consumer_group="cache-service"
        )
        await event_bus.start()
        set_event_bus(event_bus)  # 의존성 주입을 위해 설정
        print("✓ Event Bus started")
    except Exception as e:
        print(f"⚠ Event Bus failed to start: {e}")

    # TTS Producer 초기화 (싱글톤)
    try:
        tts_producer = TTSProducer(event_bus=event_bus)
        set_tts_producer(tts_producer)
        print("✓ TTS Producer initialized")
    except Exception as e:
        print(f"⚠ TTS Producer initialization failed: {e}")

    # Voice 동기화 작업 시작
    try:
        voice_sync_task = asyncio.create_task(
            sync_voice_status_periodically(
                event_bus=event_bus,
                interval=60,  # 1분마다 실행
            )
        )
        print("✓ Voice sync task started")
    except Exception as e:
        print(f"⚠ Voice sync task failed to start: {e}")

    # TTS Worker 시작 (이벤트 컨슈머)
    global tts_worker
    try:
        tts_worker = TTSWorker()
        asyncio.create_task(tts_worker.start())
        print("✓ TTS Worker started")
    except Exception as e:
        print(f"⚠ TTS Worker failed to start: {e}")

    print(f"✓ {settings.app_title} Started Successfully")
    print("=" * 60)

    yield

    # Shutdown
    print("=" * 60)
    print(f"{settings.app_title} Shutting Down...")
    
    # Voice 동기화 작업 중지
    if voice_sync_task:
        try:
            voice_sync_task.cancel()
            try:
                await voice_sync_task
            except asyncio.CancelledError:
                pass
            print("✓ Voice sync task stopped")
        except Exception as e:
            print(f"⚠ Voice sync task stop error: {e}")
    
    # Event Bus 중지
    if event_bus:
        try:
            await event_bus.stop()
            print("✓ Event Bus stopped")
        except Exception as e:
            print(f"⚠ Event Bus stop error: {e}")

    # Redis 연결 종료
    try:
        redis_manager = get_redis_manager()
        await redis_manager.disconnect()
        print("✓ Redis Manager disconnected")
    except Exception as e:
        print(f"⚠ Redis Manager disconnect error: {e}")

    # TTS Worker 중지
    if tts_worker:
        try:
            await tts_worker.shutdown()
            print("✓ TTS Worker stopped")
        except Exception as e:
            print(f"⚠ TTS Worker stop error: {e}")
    
    await engine.dispose()
    print("✓ Database connections closed")
    print("=" * 60)


# 태그 메타데이터 정의
tags_metadata = [
    {
        "name": "Authentication",
        "description": """
사용자 인증 및 권한 관리 API

**주요 기능:**
- 이메일/비밀번호 기반 회원가입 및 로그인
- Google OAuth 2.0 소셜 로그인
- JWT 토큰 기반 인증
- Access Token 자동 갱신 (Refresh Token)

**인증 방식:**
- Bearer Token (JWT)
- 헤더: `Authorization: Bearer <access_token>`
        """,
        "externalDocs": {
            "description": "JWT 인증 표준 문서",
            "url": "https://jwt.io/introduction",
        },
    },
    {
        "name": "Storybook",
        "description": """
AI 기반 동화책 생성, 조회, 관리 API

**주요 기능:**
- 프롬프트 기반 AI 동화책 자동 생성 (Google Gemini)
- 고품질 이미지 자동 생성 (Kling AI)
- 다국어 대화문 생성 (영어/한국어)
- 이미지 업로드 기반 커스텀 동화책 생성
- 동화책 목록 조회 및 상세 정보 확인

**생성 프로세스:**
1. 프롬프트 입력
2. AI 스토리 생성
3. 이미지 프롬프트 생성
4. 이미지 생성 (Kling AI)
5. TTS 음성 생성 (ElevenLabs)
        """,
    },
    {
        "name": "TTS",
        "description": """
텍스트 음성 변환 API (ElevenLabs 연동)

**주요 기능:**
- 다국어 TTS 지원 (한국어, 영어, 일본어, 중국어 등)
- 다양한 음성 선택 가능
- 자연스러운 음성 합성
- 음성 미리듣기 지원

**지원 언어:**
- 한국어 (ko)
- 영어 (en-US, en-GB)
- 일본어 (ja)
- 중국어 (zh-CN)

**성능:**
- 최대 텍스트 길이: 5000자
- 평균 생성 시간: 2-5초
        """,
    },
    {
        "name": "User",
        "description": "사용자 프로필 관리 API",
    },
    {
        "name": "Health",
        "description": """
서비스 상태 확인 API

**용도:**
- 서버 헬스 체크
- 로드 밸런서 모니터링
- CI/CD 파이프라인 검증
        """,
    },
    {
        "name": "Root",
        "description": "API 루트 정보 및 메타데이터",
    },
]

# FastAPI 앱 생성
app = FastAPI(
    title=settings.app_title,
    description="""
## 🎨 MoriAI Storybook Service

AI 기반 맞춤형 동화책 생성 플랫폼 백엔드 API

### ✨ 주요 기능

**🎨 AI 동화책 생성**
- **Google Gemini**: 연령대별 맞춤 스토리 자동 생성
- **Kling AI**: 고품질 이미지 자동 생성
- **자동 대화문 생성**: 영어/한국어 이중 언어 지원

**🔊 TTS 음성 생성**
- **ElevenLabs API**: 자연스러운 음성 합성
- **다국어 지원**: 한국어, 영어, 일본어, 중국어 등
- **다양한 음성**: 남성/여성/중성 음성 선택 가능

**🔐 인증 시스템**
- **JWT 기반**: 안전한 토큰 인증
- **Google OAuth 2.0**: 간편한 소셜 로그인
- **자동 토큰 갱신**: Refresh Token을 통한 seamless 인증

### 🛠️ 기술 스택

- **Framework**: FastAPI 0.104+
- **Database**: PostgreSQL 16 + SQLAlchemy 2.0
- **AI Services**:
  - Google Gemini (스토리 생성)
  - Kling AI (이미지 생성)
  - ElevenLabs (음성 합성)
- **Storage**: Local/S3 지원
- **Auth**: JWT + OAuth 2.0

### 📚 API 버전

현재 버전: **v1** (2.0.0)

### 🔗 참고 문서

- API 문서는 `/docs`에서 확인 (개발 모드)
- ReDoc 문서는 `/redoc`에서 확인 (개발 모드)
    """,
    version=settings.app_version,
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    contact={
        "name": "MoriAI Team",
        "email": "support@moriai.com",
    },
    license_info={
        "name": "Private",
    },
)



# 미들웨어 설정
app.add_middleware(CorrelationIdMiddleware) # Request ID 추적
app.add_middleware(UserContextMiddleware)
setup_cors(app)


# ==================== OpenAPI 커스터마이징 ====================


def custom_openapi():
    """
    OpenAPI 스키마 커스터마이징
    JWT 인증 스키마 추가
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=settings.app_title,
        version=settings.app_version,
        description=settings.app_description,
        routes=app.routes,
    )

    # JWT 보안 스키마 추가
    openapi_schema["components"]["securitySchemes"] = {
        "HTTPBearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT Access Token을 입력하세요 (Authorization: Bearer <token>)"
        }
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# ==================== Health Check ====================
# 라우터 등록
from backend.api.v1.router import api_router as api_v1_router
app.include_router(api_v1_router, prefix="/api/v1")

@app.get("/health", tags=["Health"])
async def health_check():
    """
    헬스 체크 엔드포인트

    Returns:
        dict: 서비스 상태 정보
    """
    return {
        "status": "ok",
        "service": settings.app_title,
        "version": settings.app_version,
        "environment": settings.app_env,
    }


@app.head("/health", tags=["Health"])
async def health_check_head():
    """헬스 체크 HEAD 메서드"""
    return JSONResponse(content={"status": "ok"})


@app.get("/", tags=["Root"])
async def root():
    """
    루트 엔드포인트

    Returns:
        dict: API 정보
    """
    return {
        "service": settings.app_title,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs" if settings.debug else None,
    }




# ==================== Global Exception Handlers ====================

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from backend.core.exceptions import AppException, RateLimitExceededException
from backend.core.exceptions.handlers import (
    app_exception_handler,
    rate_limit_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    generic_exception_handler,
)

# 속도 제한 예외 (AppException의 서브클래스이므로 먼저 등록)
app.add_exception_handler(RateLimitExceededException, rate_limit_exception_handler)

# 커스텀 애플리케이션 예외
app.add_exception_handler(AppException, app_exception_handler)

# Pydantic 검증 에러
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# FastAPI/Starlette HTTP 예외
app.add_exception_handler(StarletteHTTPException, http_exception_handler)

# 일반 예외 (catch-all)
app.add_exception_handler(Exception, generic_exception_handler)
