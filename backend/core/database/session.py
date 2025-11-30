"""
Database Session Management
비동기 SQLAlchemy 세션 관리
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from ..config import settings

# 비동기 엔진 생성
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # SQL 로그 출력 (개발 모드)
    poolclass=NullPool if settings.app_env == "testing" else None,
    pool_pre_ping=True,  # 연결 유효성 검사
    pool_size=10,  # 커넥션 풀 크기
    max_overflow=20,  # 최대 오버플로우 커넥션
)

# 비동기 세션 팩토리
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI Dependency로 사용되는 DB 세션 생성기

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()

    Yields:
        AsyncSession: 비동기 데이터베이스 세션
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
