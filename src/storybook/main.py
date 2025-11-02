"""
Storybook FastAPI Application

동화책 생성, 조회, 삭제 API
Repository 패턴 + 인메모리 캐싱 + 파일 백업 전략 사용
"""

from typing import List, Optional
from fastapi import (
    FastAPI,
    HTTPException,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
    Depends,
)

from .core.config import settings
from .core.logging import setup_logging, get_logger
from .core.middleware import setup_middleware
from .core.lifespan import lifespan
from .core.dependencies import (
    get_storage_service,
    get_book_repository,
    get_book_service,
)
from .api.schemas import (
    BooksListResponse,
    BookDetailResponse,
    BookSummary,
    DeleteBookResponse,
    ErrorResponse,
)
from .repositories import InMemoryBookRepository
from .services import BookOrchestratorService
from .domain.models import Book

# 로깅 설정
setup_logging()
logger = get_logger(__name__)

# ================================================================
# FastAPI Application Setup
# ================================================================

# FastAPI 앱 생성 (lifespan 적용)
app = FastAPI(
    title=settings.app_title,
    description=settings.app_description,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/storybook-docs",
    redoc_url="/storybook-redoc",
    openapi_url="/storybook-docs/openapi.json",
)

# 미들웨어 설정 (CORS 등)
setup_middleware(app)

# ================================================================
# Health Check
# ================================================================


@app.get("/health")
@app.head("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "ok", "service": "MoriAI Storybook Service"}


@app.get("/")
async def read_root():
    """루트 엔드포인트"""
    return {
        "service": "MoriAI Storybook Service",
        "version": "1.0.0",
        "status": "running",
    }


# ================================================================
# Background Tasks
# ================================================================


async def background_create_full_book(
    book_id: str,
    stories: List[str],
    images_data: List[dict],
    voice_id: str,
    book_service: BookOrchestratorService,
    book_repository: InMemoryBookRepository,
):
    """
    BackgroundTasks에서 실행될 전체 Book 생성 프로세스

    - 이미지 업로드 (AI 생성 포함 가능)
    - TTS 생성
    - 기타 후처리 작업들

    Args:
        book_id: 기존 Book ID
        stories: 각 페이지 텍스트
        images_data: [{'filename': str, 'content': bytes, 'content_type': str}]
        voice_id: TTS 음성 ID
        book_service: BookOrchestratorService 인스턴스 (DI)
        book_repository: InMemoryBookRepository 인스턴스 (DI)
    """
    try:
        logger.info(f"[Background] Starting full book creation: {book_id}")

        # 기존 create_book_with_tts 활용 (이미지 생성 + TTS 생성 + 기타 작업)
        book = await book_service.create_book_with_tts(
            stories=stories, images=images_data, voice_id=voice_id, book_id=book_id
        )

        # Repository 업데이트 (status="success" 또는 "error")
        await book_repository.update(book_id, book)

        logger.info(f"[Background] Book creation completed: {book_id}")

    except Exception as e:
        logger.error(f"[Background] Failed to create book {book_id}: {e}")

        # 에러 발생 시 status="error"로 변경
        try:
            book = await book_repository.get(book_id)
            if book:
                book.status = "error"
                await book_repository.update(book_id, book)
        except Exception as update_error:
            logger.error(f"[Background] Failed to update status: {update_error}")


# ================================================================
# Storybook API Endpoints
# ================================================================


@app.post(
    "/storybook/create",
    response_model=BookDetailResponse,
    status_code=201,
    responses={
        201: {"description": "동화책 생성 성공"},
        400: {"model": ErrorResponse, "description": "잘못된 요청"},
        500: {"model": ErrorResponse, "description": "서버 내부 오류"},
    },
)
async def create_book(
    background_tasks: BackgroundTasks,
    stories: List[str] = Form(
        ..., description="각 페이지의 텍스트 배열 (같은 키 'stories'를 반복 전송)"
    ),
    images: List[UploadFile] = File(
        ..., description="각 페이지의 이미지 파일 배열 (같은 키 'images'를 반복 전송)"
    ),
    voice_id: Optional[str] = Form(default=None, description="TTS 음성 ID"),
    book_repository: InMemoryBookRepository = Depends(get_book_repository),
    book_service: BookOrchestratorService = Depends(get_book_service),
):
    """
    새로운 동화책 생성 (비동기)

    1. 빈 Book 생성 (status="process")
    2. UploadFile을 bytes로 변환 (메모리에 미리 읽기)
    3. BackgroundTasks에 전체 작업 등록
    4. 즉시 응답 반환

    - 이미지 생성, TTS 생성 등 오래 걸리는 작업은 백그라운드에서 처리
    - 클라이언트는 즉시 응답을 받고, GET으로 상태 조회 (status: process/success/error)

    Args:
        background_tasks: FastAPI BackgroundTasks
        stories: 각 페이지의 텍스트 배열
        images: 각 페이지의 이미지 파일 배열
        voice_id: TTS 음성 ID
        title: 동화책 제목 (선택 사항)

    Returns:
        BookDetailResponse: 생성된 동화책 정보 (status="process", pages=[])
    """
    try:
        # 입력 검증
        if len(stories) != len(images):
            raise HTTPException(
                status_code=400,
                detail=f"Stories와 images의 개수가 일치하지 않습니다: {len(stories)} vs {len(images)}",
            )

        if len(stories) == 0:
            raise HTTPException(
                status_code=400, detail="최소 1개 이상의 페이지가 필요합니다"
            )

        logger.info(f"Creating book: {len(stories)} pages")

        # voice_id가 제공되지 않은 경우 기본값 사용
        voice_id = voice_id or settings.tts_default_voice_id
        logger.info(f"Using voice_id: {voice_id}")

        # 1. 빈 Book 객체 생성 (status="process")

        # 3. UploadFile을 bytes로 변환 (메모리에 미리 읽기)
        images_data = []
        total_image_size = 0
        for image in images:
            content = await image.read()
            image_size = len(content)
            total_image_size += image_size
            logger.info("*" * 20)
            logger.info(f"Read Image: {image.filename}, type={image.content_type}")
            images_data.append(
                {
                    "filename": image.filename,
                    "content": content,  # bytes
                    "content_type": image.content_type,
                }
            )
            logger.info(
                f"Image received: {image.filename} - {image_size / 1024 / 1024:.2f} MB"
            )

        logger.info(
            f"Total images size: {total_image_size / 1024 / 1024:.2f} MB ({len(images)} images)"
        )

        book = Book(
            title="",  # 기본 제목
            cover_image="",  # 나중에 설정
            voice_id=voice_id,  # TTS 음성 ID (기본값 적용됨)
            status="process",
            pages=[],  # 빈 페이지
        )

        # 2. Repository에 저장 (빈 Book)
        saved_book = await book_repository.create(book)

        # 4. 백그라운드 작업 등록 (전체 생성 프로세스)
        background_tasks.add_task(
            background_create_full_book,
            book_id=saved_book.id,
            stories=stories,
            images_data=images_data,  # bytes 전달
            voice_id=voice_id,  # TTS 음성 ID 전달
            book_service=book_service,  # DI
            book_repository=book_repository,  # DI
        )

        logger.info(f"Book created (processing in background): {saved_book.id}")

        # 5. 즉시 응답 반환 (빈 Book)
        return BookDetailResponse(
            id=saved_book.id,
            title=saved_book.title,
            cover_image=saved_book.cover_image,
            status="process",  # 진행 중
            pages=[],  # 빈 페이지
            created_at=saved_book.created_at,
        )

    except HTTPException:
        raise  # HTTPException은 그대로 전달
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create book: {e}")
        raise HTTPException(
            status_code=500, detail=f"동화책 생성 중 오류가 발생했습니다: {str(e)}"
        )


@app.get(
    "/storybook/books",
    response_model=BooksListResponse,
    responses={200: {"description": "동화책 목록 조회 성공"}},
)
async def get_all_books(
    book_repository: InMemoryBookRepository = Depends(get_book_repository),
):
    """
    모든 동화책 목록 조회 (간략 정보)

    Returns:
        BooksListResponse: 동화책 요약 정보 리스트
    """
    try:
        # Repository에서 모든 책 조회 (캐시에서)
        books = await book_repository.get_all()

        # BookSummary로 변환
        summaries = [
            BookSummary(
                id=book.id,
                title=book.title,
                cover_image=book.cover_image,
                status=book.status,
                is_default=book.is_default,
            )
            for book in books
        ]

        logger.info(f"Retrieved {len(summaries)} books")

        return BooksListResponse(books=summaries)

    except Exception as e:
        logger.error(f"Failed to get books: {e}")
        raise HTTPException(
            status_code=500, detail=f"동화책 목록 조회 중 오류가 발생했습니다: {str(e)}"
        )


@app.get(
    "/storybook/books/{book_id}",
    response_model=BookDetailResponse,
    responses={
        200: {"description": "동화책 상세 조회 성공"},
        404: {"model": ErrorResponse, "description": "동화책을 찾을 수 없음"},
    },
)
async def get_book(
    book_id: str,
    book_repository: InMemoryBookRepository = Depends(get_book_repository),
):
    """
    특정 동화책 상세 조회

    Args:
        book_id: 동화책 ID

    Returns:
        BookDetailResponse: 동화책 전체 정보 (페이지, 대사 포함)
    """
    try:
        # Repository에서 조회 (캐시 우선)
        book = await book_repository.get(book_id)

        if not book:
            raise HTTPException(status_code=404, detail=f"Book not found: {book_id}")

        logger.info(f"Retrieved book: {book_id}")

        return BookDetailResponse(
            id=book.id,
            title=book.title,
            cover_image=book.cover_image,
            status=book.status,
            is_default=book.is_default,
            pages=book.pages,
            created_at=book.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get book: {e}")
        raise HTTPException(
            status_code=500, detail=f"동화책 조회 중 오류가 발생했습니다: {str(e)}"
        )


@app.delete(
    "/storybook/books/{book_id}",
    response_model=DeleteBookResponse,
    responses={
        200: {"description": "동화책 삭제 성공"},
        404: {"model": ErrorResponse, "description": "동화책을 찾을 수 없음"},
    },
)
async def delete_book(
    book_id: str,
    book_repository: InMemoryBookRepository = Depends(get_book_repository),
    book_service: BookOrchestratorService = Depends(get_book_service),
):
    """
    동화책 삭제 (메타데이터 + 이미지 파일)

    3계층 아키텍처:
    1. Book 조회 (Repository)
    2. 파일 리소스 삭제 (StorageService via BookService)
    3. 메타데이터 삭제 (Repository)

    Args:
        book_id: 삭제할 동화책 ID

    Returns:
        DeleteBookResponse: 삭제 결과
    """
    try:
        # 1. 존재 여부 확인 및 Book 조회
        book = await book_repository.get(book_id)
        if not book:
            raise HTTPException(status_code=404, detail=f"Book not found: {book_id}")

        # 2. 파일 리소스 삭제 (이미지 등) - StorageService
        await book_service.delete_book_assets(book)

        # 3. 메타데이터 삭제 (metadata.json) - Repository
        await book_repository.delete(book_id)

        logger.info(f"Book deleted: {book_id}")

        return DeleteBookResponse(
            success=True, message="Book deleted successfully", book_id=book_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete book: {e}")
        raise HTTPException(
            status_code=500, detail=f"동화책 삭제 중 오류가 발생했습니다: {str(e)}"
        )
