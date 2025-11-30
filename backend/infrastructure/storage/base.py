"""
Storage Service Interface
파일 저장소 추상화 계층
"""

from abc import ABC, abstractmethod
from typing import Optional, BinaryIO, Union


class AbstractStorageService(ABC):
    """
    스토리지 서비스 추상 클래스
    
    로컬 파일 시스템, S3, GCS 등 다양한 스토리지 백엔드를 지원하기 위한 인터페이스
    """

    @abstractmethod
    async def save(
        self, 
        file_data: Union[bytes, BinaryIO], 
        path: str, 
        content_type: Optional[str] = None
    ) -> str:
        """
        파일 저장

        Args:
            file_data: 저장할 파일 데이터 (bytes 또는 file-like object)
            path: 저장 경로 (파일명 포함)
            content_type: MIME 타입 (옵션)

        Returns:
            str: 저장된 파일의 접근 URL 또는 경로
        """
        pass

    @abstractmethod
    async def get(self, path: str) -> bytes:
        """
        파일 조회

        Args:
            path: 파일 경로

        Returns:
            bytes: 파일 데이터
        """
        pass

    @abstractmethod
    async def delete(self, path: str) -> bool:
        """
        파일 삭제

        Args:
            path: 파일 경로

        Returns:
            bool: 삭제 성공 여부
        """
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """
        파일 존재 여부 확인

        Args:
            path: 파일 경로

        Returns:
            bool: 존재 여부
        """
        pass

    @abstractmethod
    def get_url(self, path: str) -> str:
        """
        파일 접근 URL 반환

        Args:
            path: 파일 경로

        Returns:
            str: 접근 URL
        """
        pass
