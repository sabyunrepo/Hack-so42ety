"""
File Access API Endpoints
파일 접근 API 엔드포인트

하이브리드 캐싱 전략 적용:
- HTTP 캐싱 (ETag, Cache-Control)
- Redis 캐싱 (공개 파일만)
"""
import logging
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.exceptions import (
    NotFoundException, 
    AuthorizationException, 
    InternalServerException, 
    ErrorCode
)

from backend.core.database.session import get_db_readonly
from backend.core.auth.dependencies import get_optional_user_object
from backend.core.dependencies import (
    get_storage_service,
    get_cache_service,
    get_tts_service,
)
from backend.core.services.file_access import FileAccessService
from backend.core.services.file_cache import FileCacheService
from backend.features.auth.models import User
from backend.infrastructure.storage.base import AbstractStorageService
from backend.core.cache.service import CacheService
from backend.features.tts.service import TTSService

logger = logging.getLogger(__name__)

router = APIRouter()


def is_word_audio_path(path: str) -> bool:
    """
    단어 오디오 경로인지 확인

    Args:
        path: 파일 경로

    Returns:
        bool: 단어 오디오 경로 여부
    """
    return "/words/" in path and path.endswith(".mp3")


def extract_word_from_path(path: str) -> str:
    """
    경로에서 단어 추출

    Args:
        path: 파일 경로 (예: shared/books/32e543c7-a845-4cfb-a93d-a0153dc9e063/words/a.mp3)

    Returns:
        str: 추출된 단어 (예: "a")
    """
    # /words/ 뒤의 파일명 추출
    if "/words/" in path:
        filename = path.split("/words/")[-1]
        return filename.replace(".mp3", "")
    return ""


async def extract_voice_id_from_path(path: str, db: AsyncSession) -> Optional[str]:
    """
    경로에서 book_id를 추출하고 해당 book의 voice_id 조회

    Args:
        path: 파일 경로 (예: shared/books/32e543c7-a845-4cfb-a93d-a0153dc9e063/words/a.mp3)
        db: 데이터베이스 세션 (읽기 전용)

    Returns:
        Optional[str]: Voice ID, 없으면 None
    """
    try:
        # shared/books/{book_id}/words/... 패턴 파싱
        if "/shared/books/" in path or "/users/" in path and "/books/" in path:
            # book_id 추출
            parts = path.split("/books/")
            if len(parts) >= 2:
                book_id_part = parts[1].split("/")[0]
                try:
                    book_uuid = uuid.UUID(book_id_part)
                except ValueError:
                    logger.warning(f"Invalid book_id in path: {book_id_part}")
                    return None

                # DB에서 book 조회
                from backend.features.storybook.repository import BookRepository
                book_repo = BookRepository(db)
                book = await book_repo.get(book_uuid)

                if book and book.voice_id:
                    return book.voice_id
                else:
                    logger.warning(f"Book {book_uuid} not found or has no voice_id")
                    return None
    except Exception as e:
        logger.error(f"Failed to extract voice_id from path: {path}, error: {e}")
        return None

    return None


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


@router.head(
    "/files/{file_path:path}",
    summary="파일 메타데이터 확인 (HEAD 요청)",
    responses={
        200: {"description": "파일 존재 확인 성공"},
        401: {"description": "인증 필요"},
        403: {"description": "접근 권한 없음"},
        404: {"description": "파일을 찾을 수 없음"},
    },
)
async def head_file(
    file_path: str,
    db: AsyncSession = Depends(get_db_readonly),
    current_user: Optional[User] = Depends(get_optional_user_object),
    storage_service: AbstractStorageService = Depends(get_storage_service),
):
    """
    파일 메타데이터 확인 (HEAD 요청)
    
    브라우저가 오디오/비디오 파일 재생 전에 파일 크기 확인을 위해 사용합니다.
    
    Args:
        file_path: 파일 경로
        db: 데이터베이스 세션
        current_user: 현재 사용자 (Optional)
        storage_service: 스토리지 서비스
    
    Returns:
        Response: 파일 메타데이터 (헤더만, 본문 없음)
    """
    # 보안: 운영 환경(R2/S3)에서는 로컬 파일 엔드포인트 접근 차단
    if settings.storage_provider != "local":
        raise NotFoundException(
            error_code=ErrorCode.BIZ_RESOURCE_NOT_FOUND,
            message=f"File not found: {file_path}"
        )

    current_user_id = current_user.id if current_user else None
    
    try:
        # 1. 접근 권한 확인
        access_service = FileAccessService(db)
        await access_service.check_file_access(file_path, current_user_id)
        
        # 2. 파일 존재 여부 확인
        file_exists = await storage_service.exists(file_path)
        if not file_exists:
            raise HTTPException(
                status_code=404,
                detail=f"File not found: {file_path}"
            )
        
        # 3. 파일 메타데이터 반환 (본문 없음)
        return Response(
            status_code=200,
            headers={
                "Content-Type": get_content_type(file_path),
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=86400, immutable",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Expose-Headers": "Content-Length, Content-Type, Accept-Ranges",
            }
        )
    
    except NotFoundException:
        raise
    except Exception as e:
        logger.error(f"HEAD request error: {e}")
        raise InternalServerException(
            error_code=ErrorCode.SYS_INTERNAL_ERROR,
            message="Internal server error"
        )


@router.get(
    "/files/{file_path:path}",
    summary="파일 접근 (접근 제어 및 캐싱)",
    responses={
        200: {"description": "파일 반환 성공"},
        206: {"description": "Partial Content (Range 요청)"},
        304: {"description": "Not Modified (캐시 유효)"},
        401: {"description": "인증 필요"},
        403: {"description": "접근 권한 없음"},
        404: {"description": "파일을 찾을 수 없음"},
    },
)
async def get_file(
    file_path: str,
    request: Request,
    db: AsyncSession = Depends(get_db_readonly),
    current_user: Optional[User] = Depends(get_optional_user_object),
    storage_service: AbstractStorageService = Depends(get_storage_service),
    cache_service: CacheService = Depends(get_cache_service),
    tts_service: TTSService = Depends(get_tts_service),
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
    # 보안: 운영 환경(R2/S3)에서는 로컬 파일 엔드포인트 접근 차단
    # Exception: Word Audio (On-demand generation 때문에 허용)
    if settings.storage_provider != "local" and not is_word_audio_path(file_path):
        raise NotFoundException(
            error_code=ErrorCode.BIZ_RESOURCE_NOT_FOUND,
            message=f"File not found: {file_path}"
        )

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
                        "Accept-Ranges": "bytes",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Expose-Headers": "Content-Length, Content-Type, Accept-Ranges, ETag",
                    }
                )
        
        # 4. 스토리지에서 파일 읽기
        try:
            # Smart Redirect: R2 사용 시 파일이 존재하면 바로 CDN으로 리다이렉트 (Zero Egress)
            if settings.storage_provider != "local" and await storage_service.exists(file_path):
                 cdn_url = storage_service.get_url(file_path, bypass_cdn=False)
                 return RedirectResponse(url=cdn_url, status_code=307)

            file_data = await storage_service.get(file_path)
        except FileNotFoundError:
            # 단어 오디오 파일이면 자동 생성 시도
            if is_word_audio_path(file_path):
                logger.info(f"Word audio not found, generating on-demand: {file_path}")

                try:
                    # 경로에서 단어 및 voice_id 추출
                    word = extract_word_from_path(file_path)
                    voice_id = await extract_voice_id_from_path(file_path, db)

                    if not word:
                        logger.error(f"Failed to extract word from path: {file_path}")
                        raise NotFoundException(
                            error_code=ErrorCode.BIZ_RESOURCE_NOT_FOUND,
                            message=f"Invalid word audio path: {file_path}"
                        )

                    if not voice_id:
                        logger.warning(f"No voice_id found for path: {file_path}, using default")
                        # voice_id가 없으면 기본값 사용
                        voice_id = None

                    # TTS 생성 및 저장 (Redis lock으로 중복 방지)
                    file_data = await tts_service.generate_and_save_word_audio(
                        word=word,
                        file_path=file_path,
                        voice_id=voice_id
                    )

                    # 캐시 무효화 후 재설정 (공개 파일만)
                    if not current_user_id:
                        cache_key = f"file:{file_path}"
                        await cache_service.delete(cache_key)
                        # FileCacheService를 사용하여 새로 캐싱
                        file_cache = FileCacheService(cache_service)
                        await file_cache.cache_file(file_path, file_data, ttl=86400)

                    logger.info(f"Successfully generated word audio on-demand: {file_path}, word={word}")

                    # Smart Redirect: 생성된 파일을 CDN에서 다운로드하도록 리다이렉트 (Zero Egress)
                    if settings.storage_provider != "local":
                        # CDN URL 생성 (bypass_cdn=False)
                        cdn_url = storage_service.get_url(file_path, bypass_cdn=False)
                        return RedirectResponse(url=cdn_url, status_code=307)
                    
                    # Local 환경이면 파일 반환
                    etag = FileCacheService(cache_service).get_etag(file_data)
                    cache_control = (
                        "private, max-age=3600, must-revalidate"
                        if current_user_id
                        else "public, max-age=86400, immutable"
                    )

                    return Response(
                        content=file_data,
                        media_type=get_content_type(file_path),
                        headers={
                            "X-Cache": "GENERATED",
                            "ETag": f'"{etag}"',
                            "Cache-Control": cache_control,
                            "Content-Disposition": f'inline; filename="{get_filename(file_path)}"',
                            "Accept-Ranges": "bytes",
                            "Access-Control-Allow-Origin": "*",
                            "Access-Control-Expose-Headers": "Content-Length, Content-Type, Accept-Ranges, ETag",
                        }
                    )

                except Exception as e:
                    logger.error(f"Failed to generate word audio on-demand: {file_path}, error: {e}", exc_info=True)
                    # TTS 생성 실패 시에도 404가 아닌 500 에러 반환
                    raise InternalServerException(
                        error_code=ErrorCode.BIZ_TTS_GENERATION_FAILED,
                        message=f"Failed to generate audio: {str(e)}"
                    )

            # 단어 오디오가 아니면 404 반환
            raise NotFoundException(
                error_code=ErrorCode.BIZ_RESOURCE_NOT_FOUND,
                message=f"File not found: {file_path}"
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
                "Accept-Ranges": "bytes",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Expose-Headers": "Content-Length, Content-Type, Accept-Ranges, ETag",
            }
        )
    
    except PermissionError as e:
        logger.warning(f"File access denied: {file_path}, user: {current_user_id}, error: {e}")
        raise AuthorizationException(
            error_code=ErrorCode.authz_forbidden,
            message=str(e)
        )
    except FileNotFoundError as e:
        logger.warning(f"File not found: {file_path}, error: {e}")
        raise NotFoundException(
            error_code=ErrorCode.BIZ_RESOURCE_NOT_FOUND,
            message=str(e)
        )
    except Exception as e:
        logger.error(f"File access error: {file_path}, error: {e}", exc_info=True)
        raise InternalServerException(
            error_code=ErrorCode.SYS_INTERNAL_ERROR,
            message="Internal server error"
        )

