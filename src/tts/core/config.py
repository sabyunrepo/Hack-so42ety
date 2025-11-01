"""
Core Configuration Module
환경변수 및 앱 설정 관리
"""

import os
from typing import List, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # API 기본 정보
    app_title: str = "MoriAI TTS Service"
    app_description: str = "ElevenLabs 기반 비동기 TTS 생성 API"
    app_version: str = "1.0.0"

    # 서버 설정
    port: int = int(os.getenv("TTS_API_PORT", "8000"))
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    uvicorn_reload: bool = os.getenv("UVICORN_RELOAD", "false").lower() == "true"

    # TTS 기본 설정
    tts_default_voice_id: str = os.getenv(
        "TTS_DEFAULT_VOICE_ID", "TxWD6rImY3v4izkm2VL0"
    )
    tts_default_model_id: str = os.getenv("TTS_DEFAULT_MODEL_ID", "eleven_v3")
    tts_default_language: str = os.getenv("TTS_DEFAULT_LANGUAGE", "en")

    # 파일 경로 설정
    output_dir: str = "/app/data/sound"
    word_dir: str = "/app/data/sound/word"

    # CORS 설정 (환경변수에서 문자열로 받아서 @property에서 List로 변환)
    cors_origins_str: str = "http://localhost:5173"

    @property
    def cors_origins(self) -> List[str]:
        """CORS origins를 쉼표로 분리하여 리스트로 반환"""
        return [origin.strip() for origin in self.cors_origins_str.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = False


# 싱글톤 인스턴스
settings = Settings()
