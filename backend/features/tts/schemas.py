from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

class GenerateSpeechRequest(BaseModel):
    """TTS 음성 생성 요청 스키마"""
    model_config = ConfigDict(
        protected_namespaces=(),  # Suppress 'model_' namespace warning
        json_schema_extra={
            "example": {
                "text": "안녕하세요. 오늘 날씨가 참 좋네요.",
                "voice_id": "21m00Tcm4TlvDq8ikWAM",
                "model_id": "eleven_multilingual_v2"
            }
        }
    )
    
    text: str = Field(
        ...,
        description="변환할 텍스트",
        min_length=1,
        max_length=5000,
        example="안녕하세요. 오늘 날씨가 참 좋네요."
    )
    voice_id: Optional[str] = Field(
        None,
        description="음성 ID (기본값: Rachel)",
        example="21m00Tcm4TlvDq8ikWAM"
    )
    model_id: Optional[str] = Field(
        None,
        description="모델 ID (기본값: eleven_multilingual_v2)",
        example="eleven_multilingual_v2"
    )

class AudioResponse(BaseModel):
    id: UUID = Field(..., description="오디오 고유 ID")
    file_url: str = Field(..., description="오디오 파일 URL", example="https://storage.example.com/audio/speech.mp3")
    text_content: str = Field(..., description="변환된 텍스트", example="안녕하세요. 오늘 날씨가 참 좋네요.")
    voice_id: str = Field(..., description="사용된 음성 ID", example="21m00Tcm4TlvDq8ikWAM")
    created_at: datetime = Field(..., description="생성 시간")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "file_url": "https://storage.example.com/audio/speech.mp3",
                "text_content": "안녕하세요. 오늘 날씨가 참 좋네요.",
                "voice_id": "21m00Tcm4TlvDq8ikWAM",
                "created_at": "2024-11-30T12:00:00Z"
            }
        }

class CreateVoiceCloneRequest(BaseModel):
    name: str = Field(
        ...,
        description="Voice 이름",
        min_length=1,
        max_length=200,
        example="My Custom Voice"
    )
    description: Optional[str] = Field(
        None,
        description="Voice 설명",
        max_length=500,
        example="나만의 커스텀 음성"
    )
    visibility: Optional[str] = Field(
        "private",
        description="공개 범위 (private/public/default)",
        example="private"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "My Custom Voice",
                "description": "나만의 커스텀 음성",
                "visibility": "private"
            }
        }


class VoiceResponse(BaseModel):
    voice_id: str = Field(..., description="음성 고유 ID", example="21m00Tcm4TlvDq8ikWAM")
    name: str = Field(..., description="음성 이름", example="Rachel")
    language: str = Field(default="en", description="지원 언어", example="en-US")
    gender: str = Field(default="unknown", description="성별", example="female")
    preview_url: Optional[str] = Field(None, description="미리듣기 URL", example="https://storage.elevenlabs.io/voices/preview.mp3")
    category: Optional[str] = Field(None, description="카테고리 (premade/cloned/custom)", example="cloned")
    visibility: Optional[str] = Field(None, description="공개 범위 (private/public/default)", example="private")
    status: Optional[str] = Field(None, description="생성 상태 (processing/completed/failed)", example="completed")
    is_custom: Optional[bool] = Field(None, description="커스텀 Voice 여부", example=True)

    class Config:
        json_schema_extra = {
            "example": {
                "voice_id": "21m00Tcm4TlvDq8ikWAM",
                "name": "Rachel",
                "language": "en-US",
                "gender": "female",
                "preview_url": "https://storage.elevenlabs.io/voices/rachel-preview.mp3",
                "category": "cloned",
                "visibility": "private",
                "status": "completed",
                "is_custom": True
            }
        }


class WordTTSResponse(BaseModel):
    """단어 TTS 생성 응답 스키마"""
    success: bool = Field(..., description="성공 여부", example=True)
    word: str = Field(..., description="변환된 단어", example="hello")
    file_path: str = Field(..., description="파일 시스템 경로", example="/data/shared/books/{book_id}/words/hello.mp3")
    audio_url: str = Field(..., description="API 접근 URL", example="/api/v1/files/shared/books/{book_id}/words/hello.mp3")
    cached: bool = Field(..., description="캐시 사용 여부", example=False)
    duration_ms: Optional[int] = Field(None, description="생성 소요 시간 (밀리초)", example=245)
    voice_id: str = Field(..., description="사용된 음성 ID", example="uzyfnLLlKo55AbgBU5uH")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "word": "hello",
                "file_path": "/data/shared/books/32e543c7-a845-4cfb-a93d-a0153dc9e063/words/hello.mp3",
                "audio_url": "/api/v1/files/shared/books/32e543c7-a845-4cfb-a93d-a0153dc9e063/words/hello.mp3",
                "cached": False,
                "duration_ms": 245,
                "voice_id": "uzyfnLLlKo55AbgBU5uH"
            }
        }
