from fastapi import APIRouter, Depends, status, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from backend.core.database.session import get_db
from backend.core.auth.dependencies import get_current_user_object as get_current_user
from backend.features.auth.models import User
from backend.infrastructure.storage.local import LocalStorageService
from backend.infrastructure.storage.s3 import S3StorageService
from backend.core.config import settings
from backend.features.storybook.service import BookOrchestratorService
from backend.features.storybook.repository import BookRepository
from backend.features.storybook.schemas import CreateBookRequest, BookResponse, BookListResponse
from backend.infrastructure.ai.factory import AIProviderFactory

router = APIRouter(prefix="/storybook", tags=["storybook"])

def get_storage_service():
    """스토리지 서비스 의존성"""
    if settings.storage_provider == "s3":
        return S3StorageService()
    return LocalStorageService()

def get_ai_factory():
    """AI Factory 의존성"""
    return AIProviderFactory()

def get_book_service(
    db: AsyncSession = Depends(get_db),
    storage_service = Depends(get_storage_service),
    ai_factory = Depends(get_ai_factory),
) -> BookOrchestratorService:
    """BookOrchestratorService 의존성 주입"""
    book_repo = BookRepository(db)
    return BookOrchestratorService(
        book_repo=book_repo,
        storage_service=storage_service,
        ai_factory=ai_factory,
        db_session=db,
    )

@router.post("/create", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(
    request: CreateBookRequest,
    current_user: User = Depends(get_current_user),
    service: BookOrchestratorService = Depends(get_book_service),
):
    """동화책 생성 요청"""
    book = await service.create_storybook(
        user_id=current_user.id,
        prompt=request.prompt,
        num_pages=request.num_pages,
        target_age=request.target_age,
        theme=request.theme
    )
    return book

@router.post("/create/with-images", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book_with_images(
    stories: List[str] = Form(...),
    images: List[UploadFile] = File(...),
    voice_id: str = Form(None),
    current_user: User = Depends(get_current_user),
    service: BookOrchestratorService = Depends(get_book_service),
):
    """
    이미지 기반 동화책 생성 (Multipart/Form-Data)
    프론트엔드 Creator.tsx와 호환됨.
    """
    # 이미지 파일 읽기
    image_data_list = []
    content_types = []
    for image in images:
        content = await image.read()
        image_data_list.append(content)
        content_types.append(image.content_type)

    book = await service.create_storybook_with_images(
        user_id=current_user.id,
        stories=stories,
        images=image_data_list,
        image_content_types=content_types,
        voice_id=voice_id
    )
    return book

@router.get("/books", response_model=List[BookResponse])
async def list_books(
    current_user: User = Depends(get_current_user),
    service: BookOrchestratorService = Depends(get_book_service),
):
    """내 동화책 목록 조회"""
    books = await service.get_books(current_user.id)
    return books

@router.get("/books/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: UUID,
    current_user: User = Depends(get_current_user),
    service: BookOrchestratorService = Depends(get_book_service),
):
    """동화책 상세 조회"""
    book = await service.get_book(book_id, user_id=current_user.id)
    return book

@router.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(
    book_id: UUID,
    current_user: User = Depends(get_current_user),
    service: BookOrchestratorService = Depends(get_book_service),
):
    """동화책 삭제"""
    await service.delete_book(book_id, current_user.id)
