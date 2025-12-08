"""
Core Dependencies
공통 의존성 주입 함수
"""

from backend.core.config import settings
from backend.infrastructure.storage.local import LocalStorageService
from backend.infrastructure.storage.s3 import S3StorageService
from backend.infrastructure.ai.factory import AIProviderFactory


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

