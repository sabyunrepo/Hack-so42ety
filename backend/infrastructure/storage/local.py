"""
Local Storage Service
로컬 파일 시스템을 사용하는 스토리지 서비스 구현체
"""

import os
import aiofiles
from typing import Optional, BinaryIO, Union
from pathlib import Path

from .base import AbstractStorageService
from ...core.config import settings


class LocalStorageService(AbstractStorageService):
    """
    로컬 파일 시스템 스토리지 서비스
    """

    def __init__(self, base_path: Optional[str] = None, base_url: Optional[str] = None):
        """
        Args:
            base_path: 파일이 저장될 로컬 기본 경로
            base_url: 파일 접근을 위한 기본 URL
        """
        self.base_path = Path(base_path or settings.storage_base_path or "data/storage")
        self.base_url = base_url or settings.storage_base_url or "http://localhost:8000/static"
        
        # 기본 디렉토리 생성
        os.makedirs(self.base_path, exist_ok=True)

    async def save(
        self, 
        file_data: Union[bytes, BinaryIO], 
        path: str, 
        content_type: Optional[str] = None
    ) -> str:
        """파일 저장"""
        full_path = self.base_path / path
        
        # 상위 디렉토리 생성
        os.makedirs(full_path.parent, exist_ok=True)
        
        if isinstance(file_data, bytes):
            async with aiofiles.open(full_path, "wb") as f:
                await f.write(file_data)
        else:
            # file-like object
            content = file_data.read()
            if isinstance(content, str):
                content = content.encode('utf-8')
            async with aiofiles.open(full_path, "wb") as f:
                await f.write(content)
                
        return self.get_url(path)

    async def get(self, path: str) -> bytes:
        """파일 조회"""
        full_path = self.base_path / path
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
            
        async with aiofiles.open(full_path, "rb") as f:
            return await f.read()

    async def delete(self, path: str) -> bool:
        """파일 삭제"""
        full_path = self.base_path / path
        
        if full_path.exists():
            os.remove(full_path)
            return True
        return False

    async def exists(self, path: str) -> bool:
        """파일 존재 여부 확인"""
        full_path = self.base_path / path
        return full_path.exists()

    def get_url(self, path: str) -> str:
        """파일 접근 URL 반환"""
        # URL 결합 시 슬래시 처리 주의
        base = self.base_url.rstrip("/")
        clean_path = path.lstrip("/")
        return f"{base}/{clean_path}"
