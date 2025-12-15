"""
Storybook Feature Dependencies
의존성 주입 함수 정의 (ReadOnly / Write 세션 분리)
"""

from typing import Optional
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.session import get_db_readonly, get_db_write
from backend.core.dependencies import get_storage_service, get_ai_factory
from backend.infrastructure.storage.base import AbstractStorageService
from backend.features.tts.producer import TTSProducer
from backend.features.storybook.service import BookOrchestratorService
from backend.features.storybook.repository import BookRepository

# 전역 TTS Producer 참조 (main.py lifespan에서 초기화)
_tts_producer: Optional[TTSProducer] = None


def set_tts_producer(producer_instance: TTSProducer):
    """TTS Producer 설정 (lifespan에서 호출)"""
    global _tts_producer
    _tts_producer = producer_instance


def get_tts_producer() -> TTSProducer:
    """TTS Producer 의존성 주입 (싱글톤)"""
    if not _tts_producer:
        raise RuntimeError("TTS Producer not initialized. Check if lifespan started correctly.")
    return _tts_producer


def get_book_service_readonly(
    db: AsyncSession = Depends(get_db_readonly),
    storage_service: AbstractStorageService = Depends(get_storage_service),
    ai_factory = Depends(get_ai_factory),
    tts_producer = Depends(get_tts_producer),
) -> BookOrchestratorService:
    """
    ReadOnly BookOrchestratorService 의존성 주입

    ✅ GET 요청 전용 (조회만 수행)
    ✅ PostgreSQL READ ONLY 트랜잭션 사용
    """
    book_repo = BookRepository(db)
    return BookOrchestratorService(
        book_repo=book_repo,
        storage_service=storage_service,
        ai_factory=ai_factory,
        db_session=db,
        tts_producer=tts_producer,
    )


def get_book_service_write(
    db: AsyncSession = Depends(get_db_write),
    storage_service: AbstractStorageService = Depends(get_storage_service),
    ai_factory = Depends(get_ai_factory),
    tts_producer = Depends(get_tts_producer),
) -> BookOrchestratorService:
    """
    Write BookOrchestratorService 의존성 주입

    ✅ POST, PUT, DELETE 요청 전용 (데이터 수정)
    ✅ Write 가능한 세션 사용
    """
    book_repo = BookRepository(db)
    return BookOrchestratorService(
        book_repo=book_repo,
        storage_service=storage_service,
        ai_factory=ai_factory,
        db_session=db,
        tts_producer=tts_producer,
    )
