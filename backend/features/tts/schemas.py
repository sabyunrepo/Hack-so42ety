from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

class GenerateSpeechRequest(BaseModel):
    text: str
    voice_id: Optional[str] = None
    model_id: Optional[str] = None

class AudioResponse(BaseModel):
    id: UUID
    file_url: str
    text_content: str
    voice_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class VoiceResponse(BaseModel):
    voice_id: str
    name: str
    language: str = "en"
    gender: str = "unknown"
    preview_url: Optional[str] = None
