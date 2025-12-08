from fastapi import APIRouter, Depends, status, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from backend.core.database.session import get_db
from backend.core.auth.dependencies import get_current_user_object as get_current_user
from backend.core.dependencies import get_storage_service, get_ai_factory
from backend.features.auth.models import User
from backend.features.storybook.service import BookOrchestratorService
from backend.features.storybook.repository import BookRepository
from backend.features.storybook.schemas import CreateBookRequest, BookResponse, BookListResponse

router = APIRouter()

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

@router.post(
    "/create",
    response_model=BookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="동화책 생성",
    responses={
        201: {"description": "동화책 생성 성공"},
        401: {"description": "인증 실패"},
        500: {"description": "서버 오류"},
    },
)
async def create_book(
    request: CreateBookRequest,
    current_user: User = Depends(get_current_user),
    service: BookOrchestratorService = Depends(get_book_service),
):
    """
    AI 기반 동화책 생성

    프롬프트를 입력하면 AI가 자동으로:
    - 연령대에 맞는 스토리 생성 (Google Gemini)
    - 각 페이지별 이미지 프롬프트 생성
    - 대화문 생성 (영어/한국어)
    - 이미지 생성 (Kling AI)

    Args:
        request (CreateBookRequest): 동화책 생성 요청
            - prompt: 동화책 주제/내용 (예: "우주를 여행하는 토끼 이야기")
            - num_pages: 페이지 수 (기본값: 5, 범위: 1-20)
            - target_age: 대상 연령 (예: "5-7", "8-10")
            - theme: 테마 (예: "adventure", "education", "fantasy")
        current_user: 인증된 사용자 정보 (JWT에서 추출)
        service: BookOrchestratorService (의존성 주입)

    Returns:
        BookResponse: 생성된 동화책 정보
            - id: 동화책 고유 ID (UUID)
            - title: AI가 생성한 제목
            - status: 생성 상태 (processing/completed/failed)
            - pages: 페이지 목록 (이미지, 대화문 포함)
            - created_at: 생성 시간

    Raises:
        HTTPException 401: 인증 토큰이 없거나 유효하지 않음
        HTTPException 500: AI 생성 실패 또는 서버 오류

    Example:
        ```
        POST /api/v1/storybook/create
        {
          "prompt": "우주를 탐험하는 용감한 고양이",
          "num_pages": 5,
          "target_age": "5-7",
          "theme": "adventure"
        }
        ```
    """
    book = await service.create_storybook(
        user_id=current_user.id,
        prompt=request.prompt,
        num_pages=request.num_pages,
        target_age=request.target_age,
        theme=request.theme
    )
    return book

@router.post(
    "/create/with-images",
    response_model=BookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="이미지 기반 동화책 생성",
    responses={
        201: {"description": "동화책 생성 성공"},
        400: {"description": "잘못된 요청 (이미지/스토리 개수 불일치)"},
        401: {"description": "인증 실패"},
        500: {"description": "서버 오류"},
    },
)
async def create_book_with_images(
    stories: List[str] = Form(...),
    images: List[UploadFile] = File(...),
    voice_id: str = Form(None),
    current_user: User = Depends(get_current_user),
    service: BookOrchestratorService = Depends(get_book_service),
):
    """
    이미지 기반 동화책 생성 (Multipart/Form-Data)

    사용자가 업로드한 이미지와 스토리 텍스트로 동화책을 생성합니다.
    프론트엔드 Creator.tsx와 호환됩니다.

    Args:
        stories (List[str]): 각 페이지의 스토리 텍스트 배열
        images (List[UploadFile]): 각 페이지의 이미지 파일 배열
        voice_id (str, optional): TTS 음성 ID (기본값: 시스템 기본 음성)
        current_user: 인증된 사용자 정보
        service: BookOrchestratorService (의존성 주입)

    Returns:
        BookResponse: 생성된 동화책 정보
            - id: 동화책 고유 ID
            - title: 생성된 제목
            - pages: 업로드된 이미지와 스토리가 포함된 페이지 목록

    Raises:
        HTTPException 400: 스토리와 이미지 개수가 일치하지 않음
        HTTPException 401: 인증 실패
        HTTPException 500: 파일 업로드 또는 처리 실패

    Note:
        - Content-Type: multipart/form-data
        - 이미지와 스토리 배열의 길이가 동일해야 함
        - 지원 이미지 형식: JPG, PNG, WEBP
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

@router.get(
    "/books",
    response_model=List[BookResponse],
    summary="내 동화책 목록 조회",
    responses={
        200: {"description": "조회 성공"},
        401: {"description": "인증 실패"},
    },
)
async def list_books(
    current_user: User = Depends(get_current_user),
    service: BookOrchestratorService = Depends(get_book_service),
):
    """
    내 동화책 목록 조회

    현재 로그인한 사용자가 생성한 모든 동화책을 조회합니다.

    Args:
        current_user: 인증된 사용자 정보 (JWT에서 추출)
        service: BookOrchestratorService (의존성 주입)

    Returns:
        List[BookResponse]: 동화책 목록
            - 생성 시간 역순으로 정렬
            - 각 동화책의 기본 정보 포함 (id, title, status, created_at)
            - 페이지 정보는 상세 조회 API에서 확인 가능

    Raises:
        HTTPException 401: 인증 실패
    """
    books = await service.get_books(current_user.id)
    return books

@router.get(
    "/books/{book_id}",
    response_model=BookResponse,
    summary="동화책 상세 조회",
    responses={
        200: {"description": "조회 성공"},
        401: {"description": "인증 실패"},
        403: {"description": "권한 없음"},
        404: {"description": "동화책을 찾을 수 없음"},
    },
)
async def get_book(
    book_id: UUID,
    current_user: User = Depends(get_current_user),
    service: BookOrchestratorService = Depends(get_book_service),
):
    """
    동화책 상세 조회

    특정 동화책의 전체 정보를 조회합니다 (페이지, 대화문, 이미지 포함).

    Args:
        book_id (UUID): 조회할 동화책의 고유 ID
        current_user: 인증된 사용자 정보
        service: BookOrchestratorService (의존성 주입)

    Returns:
        BookResponse: 동화책 상세 정보
            - pages: 모든 페이지 정보 (순서대로 정렬)
            - dialogues: 각 페이지의 대화문 (영어/한국어, 음성 URL)
            - images: 각 페이지의 이미지 URL

    Raises:
        HTTPException 401: 인증 실패
        HTTPException 403: 다른 사용자의 동화책 접근 시도
        HTTPException 404: 동화책을 찾을 수 없음

    Note:
        - 본인이 생성한 동화책만 조회 가능
        - is_default=true인 샘플 동화책은 모두 조회 가능
    """
    book = await service.get_book(book_id)

    # RLS가 있지만, 서비스 레벨에서도 한 번 더 체크하는 것이 안전 (또는 RLS가 처리)
    # Service에서 StorybookUnauthorizedException을 발생시키도록 변경 필요
    from backend.features.storybook.exceptions import StorybookUnauthorizedException
    if book.user_id != current_user.id and not book.is_default:
        raise StorybookUnauthorizedException(
            storybook_id=str(book_id),
            user_id=str(current_user.id)
        )

    return book

@router.delete(
    "/books/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="동화책 삭제",
    responses={
        204: {"description": "삭제 성공"},
        401: {"description": "인증 실패"},
        404: {"description": "동화책을 찾을 수 없거나 권한 없음"},
    },
)
async def delete_book(
    book_id: UUID,
    current_user: User = Depends(get_current_user),
    service: BookOrchestratorService = Depends(get_book_service),
):
    """
    동화책 삭제

    지정된 동화책과 관련된 모든 데이터를 삭제합니다.

    Args:
        book_id (UUID): 삭제할 동화책의 고유 ID
        current_user: 인증된 사용자 정보
        service: BookOrchestratorService (의존성 주입)

    Returns:
        None (HTTP 204 No Content)

    Raises:
        HTTPException 401: 인증 실패
        HTTPException 404: 동화책을 찾을 수 없거나 권한 없음

    Note:
        - 본인이 생성한 동화책만 삭제 가능
        - 삭제 시 관련된 페이지, 대화문, 이미지 파일도 함께 삭제됨
        - 삭제된 데이터는 복구할 수 없음
    """
    await service.delete_book(book_id, current_user.id)
