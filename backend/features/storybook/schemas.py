from pydantic import BaseModel, Field
from typing import List, Optional
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

class DialogueResponse(BaseModel):
    id: UUID = Field(..., description="대화문 고유 ID")
    sequence: int = Field(..., description="페이지 내 순서", example=1)
    speaker: str = Field(..., description="화자", example="Cat")
    text_en: str = Field(..., description="영어 대화문", example="I'm ready for space adventure!")
    text_ko: Optional[str] = Field(None, description="한국어 대화문", example="우주 모험을 떠날 준비가 됐어!")
    audio_url: Optional[str] = Field(None, description="음성 파일 URL", example="https://storage.example.com/audio/dialogue1.mp3")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "323e4567-e89b-12d3-a456-426614174002",
                "sequence": 1,
                "speaker": "Cat",
                "text_en": "I'm ready for space adventure!",
                "text_ko": "우주 모험을 떠날 준비가 됐어!",
                "audio_url": "https://storage.example.com/audio/dialogue1.mp3"
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
