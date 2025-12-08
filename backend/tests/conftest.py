"""
Pytest Configuration and Fixtures
테스트용 Fixture 정의
"""

import asyncio
import pytest
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from httpx import AsyncClient

from backend.main import app
from backend.core.database.base import Base
from backend.core.config import settings

import os

# 테스트용 데이터베이스 URL
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://moriai_user:moriai_password@localhost:5432/test_db"
)

# 테스트용 엔진 생성
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

# 테스트용 세션 팩토리
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """이벤트 루프 픽스처 (세션 단위)"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    테스트용 데이터베이스 세션 픽스처

    각 테스트마다 새로운 세션을 생성하고,
    테스트 종료 후 롤백하여 격리된 환경 제공
    """
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    테스트용 HTTP 클라이언트 픽스처
    """
    from backend.core.database.session import get_db

    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
async def setup_test_database():
    """
    테스트 데이터베이스 초기화 픽스처

    테스트 시작 전 모든 테이블 생성,
    테스트 종료 후 모든 테이블 삭제
    """
    # 테이블 생성
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # 테이블 삭제
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()
