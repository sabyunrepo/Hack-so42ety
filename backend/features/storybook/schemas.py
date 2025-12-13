from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, TYPE_CHECKING
from uuid import UUID
from datetime import datetime
from backend.core.config import settings

if TYPE_CHECKING:
    from backend.features.storybook.models import Book, Page, Dialogue, DialogueTranslation, DialogueAudio
    from backend.infrastructure.storage.base import AbstractStorageService

class CreateBookRequest(BaseModel):
    prompt: str = Field(
        ...,
        description="동화책 주제/내용",
        min_length=10,
        max_length=500,
        example="우주를 탐험하는 용감한 고양이 이야기"
    )
    num_pages: int = Field(
        default=5,
        ge=1,
        description="생성할 페이지 수",
        example=5
    )

    @field_validator("num_pages")
    @classmethod
    def validate_num_pages(cls, v: int) -> int:
        """페이지 수 검증"""
        if v > settings.max_pages_per_book:
            raise ValueError(f"페이지 수는 {settings.max_pages_per_book} 이하여야 합니다")
        return v
    target_age: str = Field(
        default="5-7",
        description="대상 연령대",
        example="5-7"
    )
    theme: str = Field(
        default="adventure",
        description="동화 테마 (adventure, education, fantasy, friendship 등)",
        example="adventure"
    )
    is_public: bool = Field(
        default=False,
        description="공개 여부 (기본값: False)",
        example=False
    )
    visibility: str = Field(
        default="private",
        description="공개 범위 (private, public) (기본값: private)",
        example="private"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "우주를 탐험하는 용감한 고양이 이야기",
                "num_pages": 5,
                "target_age": "5-7",
                "theme": "adventure"
            }
        }

# ==================== Multi-Language Support Schemas ====================

class DialogueTranslationResponse(BaseModel):
    """대화문 번역 응답"""
    language_code: str = Field(..., description="언어 코드 (ISO 639-1)", example="en")
    text: str = Field(..., description="번역된 텍스트", example="I'm ready for space adventure!")
    is_primary: bool = Field(..., description="원본 언어 여부", example=True)

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "language_code": "en",
                "text": "I'm ready for space adventure!",
                "is_primary": True
            }
        }

    @classmethod
    def from_orm_model(cls, translation: "DialogueTranslation") -> "DialogueTranslationResponse":
        """ORM 모델 → DTO 변환 (URL 변환 불필요)"""
        return cls(
            language_code=translation.language_code,
            text=translation.text,
            is_primary=translation.is_primary
        )

class DialogueAudioResponse(BaseModel):
    """대화문 오디오 응답"""
    language_code: str = Field(..., description="언어 코드 (ISO 639-1)", example="en")
    voice_id: str = Field(..., description="음성 ID", example="21m00Tcm4TlvDq8ikWAM")
    audio_url: str = Field(..., description="오디오 파일 URL", example="https://storage.example.com/audio/dialogue1.mp3")
    duration: Optional[float] = Field(None, description="재생 시간 (초)", example=3.5)

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "language_code": "en",
                "voice_id": "21m00Tcm4TlvDq8ikWAM",
                "audio_url": "https://storage.example.com/audio/dialogue1.mp3",
                "duration": 3.5
            }
        }

    @classmethod
    def from_orm_with_url(cls, audio: "DialogueAudio", storage_service: "AbstractStorageService") -> "DialogueAudioResponse":
        """ORM 모델 → DTO 변환 + URL 변환"""
        return cls(
            language_code=audio.language_code,
            voice_id=audio.voice_id,
            audio_url=storage_service.get_url(audio.audio_url) if audio.audio_url else "",
            duration=audio.duration
        )

class DialogueResponse(BaseModel):
    """대화문 응답 (다국어 지원)"""
    id: UUID = Field(..., description="대화문 고유 ID")
    sequence: int = Field(..., description="페이지 내 순서", example=1)
    speaker: str = Field(..., description="화자", example="Cat")
    translations: List[DialogueTranslationResponse] = Field(
        default_factory=list,
        description="다국어 번역 목록"
    )
    audios: List[DialogueAudioResponse] = Field(
        default_factory=list,
        description="다국어 오디오 목록"
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "323e4567-e89b-12d3-a456-426614174002",
                "sequence": 1,
                "speaker": "Cat",
                "translations": [
                    {
                        "language_code": "en",
                        "text": "I'm ready for space adventure!",
                        "is_primary": True
                    },
                    {
                        "language_code": "ko",
                        "text": "우주 모험을 떠날 준비가 됐어!",
                        "is_primary": False
                    }
                ],
                "audios": [
                    {
                        "language_code": "en",
                        "voice_id": "21m00Tcm4TlvDq8ikWAM",
                        "audio_url": "https://storage.example.com/audio/dialogue1.mp3",
                        "duration": 3.5
                    }
                ]
            }
        }

    @classmethod
    def from_orm_with_urls(cls, dialogue: "Dialogue", storage_service: "AbstractStorageService") -> "DialogueResponse":
        """ORM 모델 → DTO 변환 + URL 변환"""
        return cls(
            id=dialogue.id,
            sequence=dialogue.sequence,
            speaker=dialogue.speaker,
            translations=[
                DialogueTranslationResponse.from_orm_model(t)
                for t in dialogue.translations
            ],
            audios=[
                DialogueAudioResponse.from_orm_with_url(a, storage_service)
                for a in dialogue.audios
            ]
        )

class PageResponse(BaseModel):
    id: UUID = Field(..., description="페이지 고유 ID")
    sequence: int = Field(..., description="페이지 순서", example=1)
    image_url: Optional[str] = Field(None, description="이미지 URL", example="https://storage.example.com/pages/page1.jpg")
    image_prompt: Optional[str] = Field(None, description="이미지 생성 프롬프트", example="A brave cat in a spacesuit")
    dialogues: List[DialogueResponse] = Field(default_factory=list, description="페이지 내 대화문 목록")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "223e4567-e89b-12d3-a456-426614174001",
                "sequence": 1,
                "image_url": "https://storage.example.com/pages/page1.jpg",
                "image_prompt": "A brave cat in a spacesuit",
                "dialogues": [
                    {
                        "id": "323e4567-e89b-12d3-a456-426614174002",
                        "sequence": 1,
                        "speaker": "Cat",
                        "text_en": "I'm ready for space adventure!",
                        "text_ko": "우주 모험을 떠날 준비가 됐어!",
                        "audio_url": "https://storage.example.com/audio/dialogue1.mp3"
                    }
                ]
            }
        }

    @classmethod
    def from_orm_with_urls(cls, page: "Page", storage_service: "AbstractStorageService") -> "PageResponse":
        """ORM 모델 → DTO 변환 + URL 변환"""
        return cls(
            id=page.id,
            sequence=page.sequence,
            image_url=storage_service.get_url(page.image_url) if page.image_url else None,
            image_prompt=page.image_prompt,
            dialogues=[
                DialogueResponse.from_orm_with_urls(d, storage_service)
                for d in page.dialogues
            ]
        )

class BookResponse(BaseModel):
    id: UUID = Field(..., description="동화책 고유 ID")
    title: str = Field(..., description="동화책 제목", example="우주를 탐험하는 용감한 고양이")
    cover_image: Optional[str] = Field(None, description="표지 이미지 URL", example="https://storage.example.com/covers/cat-space.jpg")
    status: str = Field(..., description="생성 상태", example="completed")
    created_at: datetime = Field(..., description="생성 시간")
    pages: List[PageResponse] = Field(default_factory=list, description="페이지 목록")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "우주를 탐험하는 용감한 고양이",
                "cover_image": "https://storage.example.com/covers/cat-space.jpg",
                "status": "completed",
                "created_at": "2024-11-30T12:00:00Z",
                "pages": [
                    {
                        "id": "223e4567-e89b-12d3-a456-426614174001",
                        "sequence": 1,
                        "image_url": "https://storage.example.com/pages/page1.jpg",
                        "image_prompt": "A brave cat in a spacesuit",
                        "dialogues": [
                            {
                                "id": "323e4567-e89b-12d3-a456-426614174002",
                                "sequence": 1,
                                "speaker": "Cat",
                                "text_en": "I'm ready for space adventure!",
                                "text_ko": "우주 모험을 떠날 준비가 됐어!",
                                "audio_url": "https://storage.example.com/audio/dialogue1.mp3"
                            }
                        ]
                    }
                ]
            }
        }

    @classmethod
    def from_orm_with_urls(cls, book: "Book", storage_service: "AbstractStorageService") -> "BookResponse":
        """
        ORM 모델 → DTO 변환 + URL 변환

        ✅ ORM 객체를 직접 수정하지 않고 DTO로 변환
        ✅ URL 변환 로직을 Schema 레이어에 위임

        Args:
            book: Book ORM 모델
            storage_service: Storage Service (URL 변환용)

        Returns:
            BookResponse: URL이 변환된 DTO 객체
        """
        return cls(
            id=book.id,
            title=book.title,
            cover_image=storage_service.get_url(book.cover_image) if book.cover_image else None,
            status=book.status,
            created_at=book.created_at,
            pages=[
                PageResponse.from_orm_with_urls(page, storage_service)
                for page in book.pages
            ]
        )

class BookListResponse(BaseModel):
    books: List[BookResponse]
