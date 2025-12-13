from fastapi import APIRouter, Depends, status, File, Form, UploadFile
from typing import List
from uuid import UUID

from backend.core.auth.dependencies import get_current_user_object as get_current_user
from backend.core.dependencies import get_storage_service
from backend.infrastructure.storage.base import AbstractStorageService
from backend.features.auth.models import User
from backend.features.storybook.service import BookOrchestratorService
from backend.features.storybook.schemas import CreateBookRequest, BookResponse, BookListResponse
from backend.features.storybook.models import Book
from backend.features.storybook.dependencies import get_book_service_readonly, get_book_service_write

router = APIRouter()


def convert_book_urls_to_api_format(book: Book, storage_service: AbstractStorageService) -> Book:
    """
    Book ORM 객체의 URL을 변환 (세션에서 분리하여 안전하게 수정)
    
    ⚠️ 핵심 아이디어: session.expunge()로 ORM 객체를 세션에서 분리한 후
    URL을 변환하면 DB에 영향을 주지 않습니다.
    
    Args:
        book: Book ORM 모델
        storage_service: Storage Service (Local 또는 S3)
    
    Returns:
        Book: URL이 변환된 Book 객체 (세션에서 분리됨)
    """
    # ORM 객체를 세션에서 분리 (이후 수정해도 DB에 영향 없음)
    from sqlalchemy.orm import object_session
    from sqlalchemy import inspect
    
    session = object_session(book)
    if session:
        # Book 객체 분리
        if inspect(book).session is not None:
            session.expunge(book)
        
        # 연관된 객체들도 모두 분리
        for page in book.pages:
            if inspect(page).session is not None:
                session.expunge(page)
            for dialogue in page.dialogues:
                if inspect(dialogue).session is not None:
                    session.expunge(dialogue)
                for trans in dialogue.translations:
                    if inspect(trans).session is not None:
                        session.expunge(trans)
                for audio in dialogue.audios:
                    if inspect(audio).session is not None:
                        session.expunge(audio)
    
    # 이제 안전하게 URL 변환 가능
    if book.cover_image:
        book.cover_image = storage_service.get_url(book.cover_image)
    
    for page in book.pages:
        if page.image_url:
            page.image_url = storage_service.get_url(page.image_url)
        
        for dialogue in page.dialogues:
            for audio in dialogue.audios:
                audio.audio_url = storage_service.get_url(audio.audio_url)
    
    return book


@router.post(
    "/test",
    summary="Runware 테스트 (이미지 또는 비디오 생성)",
    responses={
        200: {"description": "생성 성공"},
        400: {"description": "잘못된 요청"},
        500: {"description": "서버 오류"},
    },
)
async def test_endpoint(
    mode: str = Form(default="image"),
    prompt: str = Form(default="a cute cat playing with a ball"),
    image: UploadFile = File(None),
    strength: float = Form(default=0.7),
    cfg_scale: float = Form(default=7.0),
    steps: int = Form(default=30),
    video_duration: int = Form(default=5),
    video_width: int = Form(default=1920),
    video_height: int = Form(default=1080),
    service: BookOrchestratorService = Depends(get_book_service),
):
    """
    Runware 테스트 엔드포인트 (이미지 또는 비디오 생성)

    세 가지 모드를 지원합니다:

    1. Image Mode - Text-to-Image (이미지 미제공):
       curl -X POST "http://localhost:8000/api/v1/storybook/test" \
         -F "mode=image" \
         -F "prompt=a beautiful sunset"

    2. Image Mode - Image-to-Image (이미지 제공):
       curl -X POST "http://localhost:8000/api/v1/storybook/test" \
         -F "mode=image" \
         -F "image=@path/to/image.png" \
         -F "prompt=make it more vibrant" \
         -F "strength=0.8"

    3. Video Mode - Image-to-Video:
       # 이미지 제공
       curl -X POST "http://localhost:8000/api/v1/storybook/test" \
         -F "mode=video" \
         -F "image=@path/to/image.png" \
         -F "prompt=animate this scene naturally" \
         -F "video_duration=5"

       # 이미지 미제공 (자동 생성)
       curl -X POST "http://localhost:8000/api/v1/storybook/test" \
         -F "mode=video" \
         -F "prompt=a peaceful lake at sunset" \
         -F "video_duration=5"

    Args:
        mode (str): 생성 모드 ("image" 또는 "video")
        prompt (str): 생성 프롬프트
        image (UploadFile, optional): 입력 이미지 파일
        strength (float): [Image 모드] 변환 강도 0.0-1.0
        cfg_scale (float): [Image 모드] 프롬프트 가이드 강도
        steps (int): [Image 모드] 디노이징 스텝 수
        video_duration (int): [Video 모드] 비디오 길이 (초)
        video_width (int): [Video 모드] 비디오 너비
        video_height (int): [Video 모드] 비디오 높이

    Returns:
        dict: 생성 결과 정보
    """
    image_bytes = None

    # 이미지 파일 읽기 (제공된 경우)
    if image:
        image_bytes = await image.read()

    # Validate mode
    if mode not in ["image", "video"]:
        return {
            "status": "error",
            "message": "mode must be 'image' or 'video'"
        }

    # Validate parameters for image mode
    if mode == "image":
        if not (0.0 <= strength <= 1.0):
            return {
                "status": "error",
                "message": "strength must be between 0.0 and 1.0"
            }

        if steps < 1 or steps > 50:
            return {
                "status": "error",
                "message": "steps must be between 1 and 50"
            }

    # Validate parameters for video mode
    if mode == "video":
        if not (1 <= video_duration <= 10):
            return {
                "status": "error",
                "message": "video_duration must be between 1 and 10 seconds"
            }

        if video_width % 8 != 0 or video_height % 8 != 0:
            return {
                "status": "error",
                "message": f"video_width and video_height must be multiples of 8. Got: {video_width}x{video_height}"
            }

        if video_width < 256 or video_width > 1920:
            return {
                "status": "error",
                "message": f"video_width must be between 256 and 1920. Got: {video_width}"
            }

        if video_height < 256 or video_height > 1080:
            return {
                "status": "error",
                "message": f"video_height must be between 256 and 1080. Got: {video_height}"
            }

    # Call service
    result = await service.test_fun(
        mode=mode,
        image_bytes=image_bytes,
        prompt=prompt,
        strength=strength,
        cfg_scale=cfg_scale,
        steps=steps,
        video_duration=video_duration,
        video_width=video_width,
        video_height=video_height,
    )

    return result

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
    service: BookOrchestratorService = Depends(get_book_service_write),
    storage_service: AbstractStorageService = Depends(get_storage_service),
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
        storage_service: Storage Service (URL 변환용)

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
        theme=request.theme,
        is_public=request.is_public,  # 기본값 False
        visibility=request.visibility,  # 기본값 "private"
    )

    # ✅ ORM → DTO 변환 + URL 변환 (ORM 객체 직접 수정하지 않음)
    return BookResponse.from_orm_with_urls(book, storage_service)

@router.post(
    "/create-async",
    response_model=BookResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="동화책 비동기 생성 (즉시 응답)",
    responses={
        202: {"description": "비동기 생성 시작됨 (백그라운드 처리 중)"},
        401: {"description": "인증 실패"},
        400: {"description": "잘못된 요청"},
    },
)
async def create_book_async(
    stories: List[str] = Form(
        ..., description="각 페이지의 텍스트 배열 (같은 키 'stories'를 반복 전송)"
    ),
    images: List[UploadFile] = File(
        ..., description="각 페이지의 이미지 파일 배열 (같은 키 'images'를 반복 전송)"
    ),
    voice_id: Optional[str] = Form(default=None, description="TTS 음성 ID"),
    level: Optional[int] = Form(default=1, description="난이도 레벨"),
    current_user: User = Depends(get_current_user),
    service: BookOrchestratorService = Depends(get_book_service_write),
    storage_service: AbstractStorageService = Depends(get_storage_service),
):
    """
    AI 기반 동화책 비동기 생성 (즉시 응답)

    DAG-Task 패턴을 사용하여 백그라운드에서 동화책을 생성합니다.
    - API 응답 시간: <1초 (즉시 응답)
    - 전체 처리 시간: ~55초 (백그라운드 병렬 처리)

    프로세스:
    1. Book 레코드 생성 (status=CREATING)
    2. 백그라운드 Task 시작 (Story → Image/TTS → Video → Finalize)
    3. 즉시 응답 반환

    진행 상황 확인: GET /books/{book_id}/progress

    Args:
        request (CreateBookRequest): 동화책 생성 요청
            - prompt: 동화책 주제/내용
            - num_pages: 페이지 수 (1-20)
            - target_age: 대상 연령
            - theme: 테마

    Returns:
        BookResponse: 생성 시작된 동화책 정보
            - id: 동화책 고유 ID
            - status: "creating"
            - pipeline_stage: "initializing"
            - progress_percentage: 0
            - task_metadata: Task IDs

    Example:
        ```
        POST /api/v1/storybook/create-async
        {
          "prompt": "우주를 탐험하는 용감한 고양이",
          "num_pages": 5,
          "target_age": "5-7",
          "theme": "adventure"
        }

        Response (202 Accepted):
        {
          "id": "550e8400-e29b-41d4-a716-446655440000",
          "status": "creating",
          "pipeline_stage": "initializing",
          "progress_percentage": 0,
          ...
        }
        ```
    """
    _images = []
    for image in images:
        _byte = await image.read()
        _images.append(_byte)

    print("######################################################")
    print(f"[[endpoint]] create_book_async called by user_id={current_user.id} with {len(stories)} stories and {len(_images)} images")
    book = await service.create_storybook_async(
        user_id=current_user.id,
        stories=stories,
        images=_images,
        voice_id=voice_id,
        level=level,
    )

    # URL 변환
    # book = convert_book_urls_to_api_format(book, storage_service)
    return book

@router.get(
    "/books/{book_id}/progress",
    summary="동화책 생성 진행 상황 조회",
    responses={
        200: {"description": "진행 상황 조회 성공"},
        401: {"description": "인증 실패"},
        404: {"description": "동화책을 찾을 수 없음"},
    },
)
async def get_book_progress(
    book_id: UUID,
    current_user: User = Depends(get_current_user),
    service: BookOrchestratorService = Depends(get_book_service),
):
    """
    동화책 생성 진행 상황 실시간 조회

    비동기로 생성 중인 동화책의 진행 상황을 확인합니다.
    프론트엔드에서 5초마다 polling하여 진행률을 표시할 수 있습니다.

    Args:
        book_id (UUID): 조회할 동화책 ID
        current_user: 인증된 사용자 정보

    Returns:
        dict: 진행 상황 정보
            {
                "status": "creating|completed|failed",
                "pipeline_stage": "story|images|tts|video|completed",
                "progress_percentage": 0-100,
                "task_metadata": {
                    "execution_id": "...",
                    "story_task": "...",
                    "image_tasks": [...],
                    ...
                },
                "error_message": str | null,
                "title": str,
                "created_at": datetime,
                "updated_at": datetime
            }

    Pipeline Stages:
        - initializing: 초기화 중
        - story: 스토리 생성 중 (10-20%)
        - images: 이미지 생성 중 (20-60%)
        - tts: 음성 생성 중 (60-80%)
        - video: 비디오 생성 중 (80-90%)
        - finalizing: 완료 처리 중 (90-100%)
        - completed: 완료됨 (100%)
        - failed: 실패

    Raises:
        HTTPException 404: 동화책을 찾을 수 없음
        HTTPException 401: 인증 실패

    Example:
        ```
        GET /api/v1/storybook/books/550e8400-e29b-41d4-a716-446655440000/progress

        Response:
        {
          "status": "creating",
          "pipeline_stage": "images",
          "progress_percentage": 45,
          "task_metadata": {...},
          "error_message": null,
          "title": "우주를 탐험하는 용감한 고양이",
          "created_at": "2024-01-01T00:00:00Z",
          "updated_at": "2024-01-01T00:01:00Z"
        }
        ```

    Note:
        - 완료된 책(status="completed")에 대해서는 progress_percentage=100
        - 실패한 책(status="failed")에 대해서는 error_message에 에러 내용 포함
        - 본인이 생성한 책만 조회 가능
    """
    from fastapi import HTTPException

    progress = await service.book_repo.get_progress(book_id)

    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book {book_id} not found"
        )

    # 권한 확인 (본인 책인지 확인은 service 레이어에서도 가능하지만, 여기서 간단히 처리)
    # TODO: service.get_book으로 권한 확인하는 것이 더 안전
    book = await service.get_book(book_id, user_id=current_user.id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book {book_id} not found or access denied"
        )

    return progress

# NOTE: This endpoint is temporarily commented out during image-to-image implementation.
# Use /test endpoint to test image-to-image functionality.
# Will be re-enabled after image-to-image testing is complete.

# @router.post(
#     "/create/with-images",
#     response_model=BookResponse,
#     status_code=status.HTTP_201_CREATED,
#     summary="이미지 기반 동화책 생성",
#     responses={
#         201: {"description": "동화책 생성 성공"},
#         400: {"description": "잘못된 요청 (이미지/스토리 개수 불일치)"},
#         401: {"description": "인증 실패"},
#         500: {"description": "서버 오류"},
#     },
# )
# async def create_book_with_images(
#     stories: List[str] = Form(...),
#     images: List[UploadFile] = File(...),
#     voice_id: str = Form(None),
#     current_user: User = Depends(get_current_user),
#     service: BookOrchestratorService = Depends(get_book_service),
#     storage_service: AbstractStorageService = Depends(get_storage_service),
# ):
#     """
#     이미지 기반 동화책 생성 (Multipart/Form-Data)
#
#     사용자가 업로드한 이미지와 스토리 텍스트로 동화책을 생성합니다.
#     프론트엔드 Creator.tsx와 호환됩니다.
#
#     Args:
#         stories (List[str]): 각 페이지의 스토리 텍스트 배열
#         images (List[UploadFile]): 각 페이지의 이미지 파일 배열
#         voice_id (str, optional): TTS 음성 ID (기본값: 시스템 기본 음성)
#         current_user: 인증된 사용자 정보
#         service: BookOrchestratorService (의존성 주입)
#         storage_service: Storage Service (URL 변환용)
#
#     Returns:
#         BookResponse: 생성된 동화책 정보
#             - id: 동화책 고유 ID
#             - title: 생성된 제목
#             - pages: 업로드된 이미지와 스토리가 포함된 페이지 목록
#
#     Raises:
#         HTTPException 400: 스토리와 이미지 개수가 일치하지 않음
#         HTTPException 401: 인증 실패
#         HTTPException 500: 파일 업로드 또는 처리 실패
#
#     Note:
#         - Content-Type: multipart/form-data
#         - 이미지와 스토리 배열의 길이가 동일해야 함
#         - 지원 이미지 형식: JPG, PNG, WEBP
#     """
#     # 이미지 파일 읽기
#     image_data_list = []
#     content_types = []
#     for image in images:
#         content = await image.read()
#         image_data_list.append(content)
#         content_types.append(image.content_type)
#
#     book = await service.create_storybook_with_images(
#         user_id=current_user.id,
#         stories=stories,
#         images=image_data_list,
#         image_content_types=content_types,
#         voice_id=voice_id
#     )
#
#     # ✅ URL 변환
#     book = convert_book_urls_to_api_format(book, storage_service)
#
#     return book

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
    service: BookOrchestratorService = Depends(get_book_service_readonly),
    storage_service: AbstractStorageService = Depends(get_storage_service),
):
    """
    내 동화책 목록 조회

    현재 로그인한 사용자가 생성한 모든 동화책을 조회합니다.

    Args:
        current_user: 인증된 사용자 정보 (JWT에서 추출)
        service: BookOrchestratorService (의존성 주입)
        storage_service: Storage Service (URL 변환용)

    Returns:
        List[BookResponse]: 동화책 목록
            - 생성 시간 역순으로 정렬
            - 각 동화책의 기본 정보 포함 (id, title, status, created_at)
            - 페이지 정보는 상세 조회 API에서 확인 가능

    Raises:
        HTTPException 401: 인증 실패
    """
    books = await service.get_books(current_user.id)

    # ✅ ORM → DTO 변환 + URL 변환 (ORM 객체 직접 수정하지 않음)
    return [BookResponse.from_orm_with_urls(book, storage_service) for book in books]

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
    service: BookOrchestratorService = Depends(get_book_service_readonly),
    storage_service: AbstractStorageService = Depends(get_storage_service),
):
    """
    동화책 상세 조회

    특정 동화책의 전체 정보를 조회합니다 (페이지, 대화문, 이미지 포함).

    Args:
        book_id (UUID): 조회할 동화책의 고유 ID
        current_user: 인증된 사용자 정보
        service: BookOrchestratorService (의존성 주입)
        storage_service: Storage Service (URL 변환용)

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

    # ✅ ORM → DTO 변환 + URL 변환 (ORM 객체 직접 수정하지 않음)
    return BookResponse.from_orm_with_urls(book, storage_service)

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
    service: BookOrchestratorService = Depends(get_book_service_write),
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
