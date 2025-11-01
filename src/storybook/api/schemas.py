"""
Storybook API Request/Response Schemas
FastAPI 엔드포인트에서 사용할 요청/응답 스키마 정의
"""

from typing import List, Literal, Annotated, Type
from datetime import datetime
from pydantic import BaseModel, Field, create_model
from ..domain.models import Page


# ============================================================
# Request Schemas
# ============================================================


class CreateBookRequest(BaseModel):
    """
    동화책 생성 요청 스키마 (multipart/form-data)

    Note: FastAPI에서는 Form 파라미터로 받아서 처리
    이 스키마는 문서화 및 검증용

    Attributes:
        title: 동화책 제목 (선택 사항)
        stories: 각 페이지의 텍스트 배열
        images: 각 페이지의 이미지 파일 배열 (File 타입)
        voice_id: TTS 음성 ID (필수)
    """

    title: str = Field(default="새로운 동화책", description="동화책 제목")
    stories: List[str] = Field(..., min_length=1, description="각 페이지의 텍스트 배열")
    voice_id: str = Field(..., description="TTS 음성 ID")
    # images는 UploadFile 타입으로 FastAPI에서 직접 처리


# ============================================================
# Response Schemas
# ============================================================


class BookSummary(BaseModel):
    """
    동화책 요약 정보 (목록 조회용)

    Attributes:
        id: 동화책 ID
        title: 동화책 제목
        cover_image: 커버 이미지 URL
        status: 동화책 상태
    """

    id: str = Field(..., description="동화책 ID")
    title: str = Field(..., description="동화책 제목")
    cover_image: str = Field(..., description="커버 이미지 URL")
    status: Literal["process", "success", "error"] = Field(
        ..., description="동화책 상태"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "uuid-book-1234",
                "title": "우리집 동화책",
                "cover_image": "/data/image/uuid-book-1234/cover.png",
                "status": "success",
            }
        }


class BooksListResponse(BaseModel):
    """
    전체 동화책 목록 응답

    Attributes:
        books: 동화책 요약 정보 리스트
    """

    books: List[BookSummary] = Field(default_factory=list, description="동화책 목록")

    class Config:
        json_schema_extra = {
            "example": {
                "books": [
                    {
                        "id": "uuid-book-1234",
                        "title": "우리집 동화책",
                        "cover_image": "/data/image/uuid-book-1234/cover.png",
                        "status": "success",
                    },
                    {
                        "id": "uuid-book-5678",
                        "title": "모험 이야기",
                        "cover_image": "/data/image/uuid-book-5678/cover.png",
                        "status": "process",
                    },
                ]
            }
        }


class BookDetailResponse(BaseModel):
    """
    동화책 상세 정보 응답 (Book 모델과 동일)

    Attributes:
        id: 동화책 ID
        title: 동화책 제목
        cover_image: 커버 이미지 URL
        status: 동화책 상태
        pages: 동화책 페이지 리스트
        created_at: 생성 시간
    """

    id: str = Field(..., description="동화책 ID")
    title: str = Field(..., description="동화책 제목")
    cover_image: str = Field(..., description="커버 이미지 URL")
    status: Literal["process", "success", "error"] = Field(
        ..., description="동화책 상태"
    )
    pages: List[Page] = Field(default_factory=list, description="동화책 페이지 리스트")
    created_at: datetime = Field(..., description="생성 시간")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "uuid-book-1234",
                "title": "우리집 동화책",
                "cover_image": "/data/image/uuid-book-1234/cover.png",
                "status": "success",
                "pages": [
                    {
                        "id": "uuid-page-1",
                        "index": 1,
                        "background_image": "/data/image/uuid-book-1234/uuid-page-1.png",
                        "dialogues": [
                            {
                                "id": "uuid-dialogue-1",
                                "index": 1,
                                "text": "아침을 먹었다.",
                                "part_audio_url": "/data/sound/batch-uuid/uuid-dialogue-1.mp3",
                            }
                        ],
                    }
                ],
                "created_at": "2025-10-21T12:00:00",
            }
        }


class DeleteBookResponse(BaseModel):
    """
    동화책 삭제 응답

    Attributes:
        success: 성공 여부
        message: 응답 메시지
        book_id: 삭제된 동화책 ID
    """

    success: bool = Field(..., description="성공 여부")
    message: str = Field(..., description="응답 메시지")
    book_id: str = Field(..., description="삭제된 동화책 ID")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Book deleted successfully",
                "book_id": "uuid-book-1234",
            }
        }


class ErrorResponse(BaseModel):
    """
    에러 응답 스키마

    Attributes:
        detail: 에러 상세 메시지
    """

    detail: str = Field(..., description="에러 상세 메시지")

    class Config:
        json_schema_extra = {"example": {"detail": "Book not found"}}
