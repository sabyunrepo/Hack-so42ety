"""
File Cache Service
파일 캐싱 서비스

공개 파일을 Redis에 캐싱하여 성능을 최적화합니다.
"""
import hashlib
import logging
from typing import Optional
from backend.core.cache.service import CacheService

logger = logging.getLogger(__name__)


class FileCacheService:
    """
    파일 캐싱 서비스
    
    공개 파일만 Redis에 캐싱합니다 (보안 고려).
    """
    
    def __init__(self, cache_service: CacheService):
        self.cache_service = cache_service
    
    def _get_cache_key(self, file_path: str) -> str:
        """
        캐시 키 생성
        
        Args:
            file_path: 파일 경로
        
        Returns:
            str: 캐시 키
        """
        return f"file:{file_path}"
    
    async def get_file(self, file_path: str) -> Optional[bytes]:
        """
        캐시에서 파일 조회
        
        Args:
            file_path: 파일 경로
        
        Returns:
            Optional[bytes]: 캐시된 파일 데이터 또는 None
        """
        cache_key = self._get_cache_key(file_path)
        cached_data = await self.cache_service.get(cache_key)
        
        if cached_data:
            # bytes로 변환 (aiocache가 문자열로 반환할 수 있음)
            if isinstance(cached_data, str):
                try:
                    import base64
                    cached_data = base64.b64decode(cached_data)
                except Exception:
                    logger.warning(f"Failed to decode cached file: {file_path}")
                    return None
            elif isinstance(cached_data, bytes):
                return cached_data
            else:
                logger.warning(f"Unexpected cache data type: {type(cached_data)}")
                return None
        
        return None
    
    async def cache_file(
        self,
        file_path: str,
        file_data: bytes,
        ttl: int = 86400,  # 24시간
    ) -> None:
        """
        파일 캐싱
        
        Args:
            file_path: 파일 경로
            file_data: 파일 데이터
            ttl: 캐시 유지 시간 (초)
        """
        cache_key = self._get_cache_key(file_path)
        
        # bytes를 base64로 인코딩하여 저장 (aiocache 호환성)
        try:
            import base64
            encoded_data = base64.b64encode(file_data).decode('utf-8')
            await self.cache_service.set(cache_key, encoded_data, ttl=ttl)
            logger.debug(f"File cached: {file_path} (TTL: {ttl}s)")
        except Exception as e:
            logger.error(f"Failed to cache file {file_path}: {e}", exc_info=True)
    
    async def invalidate_file(self, file_path: str) -> None:
        """
        파일 캐시 무효화
        
        Args:
            file_path: 파일 경로
        """
        cache_key = self._get_cache_key(file_path)
        await self.cache_service.delete(cache_key)
        logger.debug(f"File cache invalidated: {file_path}")
    
    def get_etag(self, file_data: bytes) -> str:
        """
        파일 데이터의 ETag 생성
        
        Args:
            file_data: 파일 데이터
        
        Returns:
            str: ETag (MD5 해시)
        """
        return hashlib.md5(file_data).hexdigest()

