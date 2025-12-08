"""
Alembic Migration Environment
데이터베이스 마이그레이션 환경 설정
"""

from logging.config import fileConfig
from sqlalchemy import pool, engine_from_config
from sqlalchemy.engine import Connection
from alembic import context

# Backend 모듈 임포트
import sys
from pathlib import Path

# 백엔드 루트 디렉토리를 Python 경로에 추가
backend_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_path))

from core.config import settings
from core.database.base import Base

# 모든 모델 임포트 (Alembic이 테이블을 인식하도록)
from backend.features.auth.models import User
from backend.features.storybook.models import Book, Page, Dialogue
from backend.features.tts.models import Audio, Voice

# Alembic Config object
config = context.config

# Logging 설정
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# MetaData for autogenerate support
target_metadata = Base.metadata

# Database URL 설정 (환경변수에서 가져옴)
config.set_main_option("sqlalchemy.url", settings.database_url_sync)


def run_migrations_offline() -> None:
    """
    오프라인 모드로 마이그레이션 실행

    데이터베이스 연결 없이 SQL 스크립트만 생성
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    온라인 모드로 마이그레이션 실행

    실제 데이터베이스에 연결하여 마이그레이션 적용
    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.database_url_sync

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
