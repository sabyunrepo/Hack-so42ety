"""
File Access API Endpoints
파일 접근 API 엔드포인트

하이브리드 캐싱 전략 적용:
- HTTP 캐싱 (ETag, Cache-Control)
- Redis 캐싱 (공개 파일만)
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Request, Response, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.session import get_db
from backend.core.auth.dependencies import get_optional_user_object
from backend.core.dependencies import (
    get_storage_service,
    get_cache_service,
)
from backend.core.services.file_access import FileAccessService
from backend.core.services.file_cache import FileCacheService
from backend.features.auth.models import User
from backend.infrastructure.storage.base import AbstractStorageService
from backend.core.cache.service import CacheService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_content_type(file_path: str) -> str:
    """
    파일 경로에서 Content-Type 추출
    
    Args:
        file_path: 파일 경로
    
    Returns:
        str: Content-Type
    """
    ext = file_path.split('.')[-1].lower()
    content_types = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'webp': 'image/webp',
        'mp3': 'audio/mpeg',
        'wav': 'audio/wav',
        'ogg': 'audio/ogg',
        'mp4': 'video/mp4',
        'webm': 'video/webm',
    }
    return content_types.get(ext, 'application/octet-stream')


def get_filename(file_path: str) -> str:
    """
    파일 경로에서 파일명 추출
    
    Args:
        file_path: 파일 경로
    
    Returns:
        str: 파일명
    """
    return file_path.split('/')[-1]


@router.get(
    "/files/{file_path:path}",
    summary="파일 접근 (접근 제어 및 캐싱)",
    responses={
        200: {"description": "파일 반환 성공"},
        304: {"description": "Not Modified (캐시 유효)"},
        401: {"description": "인증 필요"},
        403: {"description": "접근 권한 없음"},
        404: {"description": "파일을 찾을 수 없음"},
    },
)
async def get_file(
    file_path: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user_object),
    storage_service: AbstractStorageService = Depends(get_storage_service),
    cache_service: CacheService = Depends(get_cache_service),
):
    """
    파일 접근 제어 API (하이브리드 캐싱)
    
    - 공개 책: 인증 없이 접근 가능, Redis 캐싱 적용
    - 비공개 책: 인증된 소유자만 접근 가능, Redis 캐싱 안 함
    
    Args:
        file_path: 파일 경로 (예: users/{user_id}/books/{book_id}/images/page_1.png)
        request: FastAPI Request 객체 (If-None-Match 헤더 확인용)
        db: 데이터베이스 세션
        current_user: 현재 사용자 (Optional, 비인증 사용자 가능)
        storage_service: 스토리지 서비스
        cache_service: 캐시 서비스
    
    Returns:
        Response: 파일 데이터 또는 304 Not Modified
    """
    current_user_id = current_user.id if current_user else None
    
    try:
        # 1. 접근 권한 확인
        access_service = FileAccessService(db)
        await access_service.check_file_access(file_path, current_user_id)
        
        # 2. 파일 캐싱 서비스 초기화
        file_cache = FileCacheService(cache_service)
        
        # 3. Redis 캐시 확인 (공개 파일만)
        cached_file = None
        if not current_user_id:  # 공개 파일만 Redis 캐싱
            cached_file = await file_cache.get_file(file_path)
            
            if cached_file:
                # ETag 생성
                etag = file_cache.get_etag(cached_file)
                
                # 304 Not Modified 확인
                if_none_match = request.headers.get("If-None-Match")
                if if_none_match and if_none_match.strip('"') == etag:
                    return Response(
                        status_code=304,
                        headers={
                            "ETag": f'"{etag}"',
                            "Cache-Control": "public, max-age=86400, immutable",
                            "X-Cache": "HIT",
                        }
                    )
                
                # 캐시된 파일 반환
                return Response(
                    content=cached_file,
                    media_type=get_content_type(file_path),
                    headers={
                        "X-Cache": "HIT",
                        "ETag": f'"{etag}"',
                        "Cache-Control": "public, max-age=86400, immutable",
                        "Content-Disposition": f'inline; filename="{get_filename(file_path)}"',
                    }
                )
        
        # 4. 스토리지에서 파일 읽기
        try:
            file_data = await storage_service.get(file_path)
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"File not found: {file_path}"
            )
        
        # 5. Redis 캐시에 저장 (공개 파일만)
        if not current_user_id:
            await file_cache.cache_file(file_path, file_data, ttl=86400)  # 24시간
        
        # 6. ETag 생성
        etag = file_cache.get_etag(file_data)
        
        # 7. 304 Not Modified 확인
        if_none_match = request.headers.get("If-None-Match")
        if if_none_match and if_none_match.strip('"') == etag:
            return Response(
                status_code=304,
                headers={
                    "ETag": f'"{etag}"',
                    "Cache-Control": "private, max-age=3600" if current_user_id else "public, max-age=86400",
                    "X-Cache": "MISS",
                }
            )
        
        # 8. 응답 반환
        cache_control = (
            "private, max-age=3600, must-revalidate" 
            if current_user_id 
            else "public, max-age=86400, immutable"
        )
        
        return Response(
            content=file_data,
            media_type=get_content_type(file_path),
            headers={
                "X-Cache": "MISS",
                "ETag": f'"{etag}"',
                "Cache-Control": cache_control,
                "Content-Disposition": f'inline; filename="{get_filename(file_path)}"',
            }
        )
    
    except PermissionError as e:
        logger.warning(f"File access denied: {file_path}, user: {current_user_id}, error: {e}")
        raise HTTPException(
            status_code=403,
            detail=str(e)
        )
    except FileNotFoundError as e:
        logger.warning(f"File not found: {file_path}, error: {e}")
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"File access error: {file_path}, error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

