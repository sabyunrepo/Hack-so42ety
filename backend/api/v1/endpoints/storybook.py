from fastapi import APIRouter, Depends, HTTPException, status, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from backend.core.database.session import get_db
from backend.core.auth.dependencies import get_current_user_object as get_current_user
from backend.domain.models.user import User
from backend.infrastructure.storage.local import LocalStorageService
from backend.infrastructure.storage.s3 import S3StorageService
from backend.core.config import settings
from backend.features.storybook.service import BookOrchestratorService
from backend.features.storybook.schemas import CreateBookRequest, BookResponse, BookListResponse

router = APIRouter()

def get_storage_service():
    # 환경 설정에 따라 스토리지 서비스 반환
    # 여기서는 간단히 LocalStorageService 사용 (또는 config에 따라 분기)
    # 실제로는 DI 컨테이너나 Factory를 사용하는 것이 좋음
    if settings.storage_provider == "s3":
        return S3StorageService()
    return LocalStorageService()

@router.post("/create", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(
    request: CreateBookRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """동화책 생성 요청"""
    storage_service = get_storage_service()
    service = BookOrchestratorService(db, storage_service)
    
    try:
        book = await service.create_storybook(
            user_id=current_user.id,
            prompt=request.prompt,
            num_pages=request.num_pages,
            target_age=request.target_age,
            theme=request.theme
        )
        return book
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create book: {str(e)}"
        )

@router.post("/create/with-images", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book_with_images(
    stories: List[str] = Form(...),
    images: List[UploadFile] = File(...),
    voice_id: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    이미지 기반 동화책 생성 (Multipart/Form-Data)
    프론트엔드 Creator.tsx와 호환됨.
    """
    if len(stories) != len(images):
        raise HTTPException(status_code=400, detail="Stories and images count mismatch")

    storage_service = get_storage_service()
    service = BookOrchestratorService(db, storage_service)
    
    try:
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
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create book with images: {str(e)}"
        )

@router.get("/books", response_model=List[BookResponse])
async def list_books(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """내 동화책 목록 조회"""
    storage_service = get_storage_service()
    service = BookOrchestratorService(db, storage_service)
    
    books = await service.get_books(current_user.id)
    return books

@router.get("/books/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """동화책 상세 조회"""
    storage_service = get_storage_service()
    service = BookOrchestratorService(db, storage_service)
    
    book = await service.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # RLS가 있지만, 서비스 레벨에서도 한 번 더 체크하는 것이 안전 (또는 RLS가 처리)
    if book.user_id != current_user.id and not book.is_default:
        raise HTTPException(status_code=403, detail="Not authorized to view this book")
        
    return book

@router.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(
    book_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """동화책 삭제"""
    storage_service = get_storage_service()
    service = BookOrchestratorService(db, storage_service)
    
    success = await service.delete_book(book_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Book not found or not authorized")
