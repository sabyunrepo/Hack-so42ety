"""
Database Session Management
비동기 SQLAlchemy 세션 관리
"""

from typing import AsyncGenerator
from sqlalchemy import text
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

# 비동기 세션 팩토리 (Write용)
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 비동기 세션 팩토리 (ReadOnly용)
AsyncSessionLocalReadOnly = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db_readonly() -> AsyncGenerator[AsyncSession, None]:
    """
    ReadOnly 전용 DB 세션 생성기

    ✅ PostgreSQL READ ONLY 트랜잭션으로 데이터 수정 방지
    ✅ GET 요청 등 조회 전용 엔드포인트에 사용

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db_readonly)):
            result = await db.execute(select(Item))
            return result.scalars().all()

    Yields:
        AsyncSession: ReadOnly 비동기 데이터베이스 세션
    """
    async with AsyncSessionLocalReadOnly() as session:
        try:
            # PostgreSQL READ ONLY 트랜잭션 시작
            await session.execute(text("SET TRANSACTION READ ONLY"))
            yield session
            # ReadOnly 세션은 commit 불필요하지만 명시적으로 호출
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_write() -> AsyncGenerator[AsyncSession, None]:
    """
    Write 전용 DB 세션 생성기

    ✅ 데이터 수정 작업용 세션 (POST, PUT, DELETE)
    ✅ 기존 get_db() 로직과 동일

    Usage:
        @app.post("/items")
        async def create_item(db: AsyncSession = Depends(get_db_write)):
            db.add(new_item)
            await db.commit()

    Yields:
        AsyncSession: Write 가능 비동기 데이터베이스 세션
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


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI Dependency로 사용되는 DB 세션 생성기

    ⚠️ Deprecated: 새로운 코드에서는 get_db_readonly() 또는 get_db_write() 사용 권장
    ⚠️ 기존 코드 호환성을 위해 유지 (get_db_write()와 동일한 동작)

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
