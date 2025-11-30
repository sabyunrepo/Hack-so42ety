from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime

class CreateBookRequest(BaseModel):
    prompt: str
    num_pages: int = 5
    target_age: str = "5-7"
    theme: str = "adventure"

class DialogueResponse(BaseModel):
    id: UUID
    sequence: int
    speaker: str
    text_en: str
    text_ko: Optional[str] = None
    audio_url: Optional[str] = None
    
    class Config:
        from_attributes = True

class PageResponse(BaseModel):
    id: UUID
    sequence: int
    image_url: Optional[str] = None
    image_prompt: Optional[str] = None
    dialogues: List[DialogueResponse] = []
    
    class Config:
        from_attributes = True

class BookResponse(BaseModel):
    id: UUID
    title: str
    cover_image: Optional[str] = None
    status: str
    created_at: datetime
    pages: List[PageResponse] = []

    class Config:
        from_attributes = True

class BookListResponse(BaseModel):
    books: List[BookResponse]
