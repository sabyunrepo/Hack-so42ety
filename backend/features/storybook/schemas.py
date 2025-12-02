from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from uuid import UUID
from datetime import datetime

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
        le=20,
        description="생성할 페이지 수",
        example=5
    )
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

class BookListResponse(BaseModel):
    books: List[BookResponse]
