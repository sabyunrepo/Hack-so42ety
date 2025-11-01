"""
Core Configuration Module
환경변수 및 앱 설정 중앙 관리 (TTS 서비스 패턴 적용)
"""

import os
import json
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # 서버 설정
    uvicorn_reload: bool = Field(default=False, env="UVICORN_RELOAD")

    # 데이터 디렉토리
    book_data_dir: str = Field(default="./data/book", env="BOOK_DATA_DIR")
    image_data_dir: str = Field(default="./data/image", env="IMAGE_DATA_DIR")
    video_data_dir: str = Field(default="./data/video", env="VIDEO_DATA_DIR")

    # CORS 설정 (환경변수에서 쉼표 구분 문자열로 받음)
    cors_origins_str: str = Field(default="http://localhost:5173", env="CORS_ORIGINS")

    @property
    def cors_origins(self) -> List[str]:
        """CORS origins를 쉼표로 분리하여 리스트로 반환"""
        return [origin.strip() for origin in self.cors_origins_str.split(",")]

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore",  # .env의 TTS 관련 환경변수 무시
    }


# 싱글톤 인스턴스
settings = Settings()
