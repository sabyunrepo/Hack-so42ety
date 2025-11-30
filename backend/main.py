"""
MoriAI Storybook Backend - Main Application
FastAPI 통합 백엔드 서비스
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .core.config import settings
from .core.database import engine, Base
from .core.middleware import setup_cors
from .core.middleware.auth import UserContextMiddleware

# Feature 라우터 imports
from .features.auth.api import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 생명주기 관리

    Startup:
        - 데이터베이스 연결 확인
        - 로깅 초기화

    Shutdown:
        - 데이터베이스 연결 종료
    """
    # Startup
    print("=" * 60)
    print(f"{settings.app_title} Starting...")
    print(f"Version: {settings.app_version}")
    print(f"Environment: {settings.app_env}")
    print(f"Debug Mode: {settings.debug}")
    print("=" * 60)

    # 데이터베이스 연결 확인
    try:
        async with engine.begin() as conn:
            # 테이블 생성 (개발 모드에서만)
            # 프로덕션에서는 Alembic 사용
            if settings.app_env == "development" and settings.debug:
                await conn.run_sync(Base.metadata.create_all)
                print("✓ Database tables created (development mode)")
    except Exception as e:
        print(f"⚠ Database connection failed: {e}")

    print(f"✓ {settings.app_title} Started Successfully")
    print("=" * 60)

    yield

    # Shutdown
    print("=" * 60)
    print(f"{settings.app_title} Shutting Down...")
    await engine.dispose()
    print("✓ Database connections closed")
    print("=" * 60)


# FastAPI 앱 생성
app = FastAPI(
    title=settings.app_title,
    description=settings.app_description,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
)

# 미들웨어 설정
setup_cors(app)
app.add_middleware(UserContextMiddleware)

# 라우터 등록
app.include_router(auth_router)


# ==================== Health Check ====================


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


# ==================== Error Handlers ====================


@app.exception_handler(404)
async def not_found_handler(request, exc):
    """404 Not Found 핸들러"""
    return JSONResponse(
        status_code=404,
        content={"detail": "Resource not found"},
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """500 Internal Server Error 핸들러"""
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
