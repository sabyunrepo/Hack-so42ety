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

    # API 기본 정보
    app_title: str = "MoriAI Storybook Service"
    app_description: str = "동화책 생성, 조회, 삭제 API (TTS 연동)"
    app_version: str = "1.0.0"

    # 서버 설정
    storybook_api_port: int = Field(default=8001, env="STORYBOOK_API_PORT")
    tts_api_port: int = Field(default=8000, env="TTS_API_PORT")
    debug: bool = Field(default=False, env="DEBUG")
    uvicorn_reload: bool = Field(default=False, env="UVICORN_RELOAD")

    # 데이터 디렉토리
    book_data_dir: str = Field(default="./data/book", env="BOOK_DATA_DIR")
    image_data_dir: str = Field(default="./data/image", env="IMAGE_DATA_DIR")
    video_data_dir: str = Field(default="./data/video", env="VIDEO_DATA_DIR")

    # 외부 API (TTS API URL은 동적 생성 - tts_api_url_dynamic property 사용 권장)
    google_api_key: str = Field(
        default="", env="GOOGLE_API_KEY"
    )  # 빈 문자열 허용 (테스트용)

    # Kling API 설정 (키 풀 방식)
    kling_access_key: str = Field(default="[]", env="KLING_ACCESS_KEY")
    kling_secret_key: str = Field(default="[]", env="KLING_SECRET_KEY")
    kling_key_cooldown_seconds: int = Field(
        default=300, env="KLING_KEY_COOLDOWN_SECONDS"
    )  # 5분
    kling_api_url: str = Field(
        default="https://api-singapore.klingai.com", env="KLING_API_URL"
    )
    kling_model_name: str = Field(default="kling-v2-1", env="KLING_MODEL_NAME")
    kling_video_mode: str = Field(default="std", env="KLING_VIDEO_MODE")  # std or pro
    kling_video_duration: str = Field(
        default="5", env="KLING_VIDEO_DURATION"
    )  # 5 or 10
    kling_polling_interval: int = Field(
        default=10, env="KLING_POLLING_INTERVAL"
    )  # seconds
    kling_max_concurrent: int = Field(
        default=3, env="KLING_MAX_CONCURRENT"
    )  # Global concurrency limit
    kling_max_polling_time: int = Field(
        default=600, env="KLING_MAX_POLLING_TIME"
    )  # 10 minutes timeout

    # TTS 설정
    tts_default_voice_id: str = Field(
        default="TxWD6rImY3v4izkm2VL0", env="TTS_DEFAULT_VOICE_ID"
    )

    # CORS 설정 (환경변수에서 쉼표 구분 문자열로 받음)
    cors_origins_str: str = Field(default="http://localhost:5173", env="CORS_ORIGINS")

    @property
    def cors_origins(self) -> List[str]:
        """CORS origins를 쉼표로 분리하여 리스트로 반환"""
        return [origin.strip() for origin in self.cors_origins_str.split(",")]

    @property
    def tts_api_url(self) -> str:
        """
        TTS API URL 동적 생성

        환경변수 TTS_API_URL이 있으면 사용, 없으면 tts_api_port로 동적 생성
        """
        return os.getenv("TTS_API_URL", f"http://tts-api:{self.tts_api_port}")

    @property
    def kling_access_keys(self) -> List[str]:
        """Kling Access Keys를 JSON 파싱하여 리스트로 반환"""
        try:
            return json.loads(self.kling_access_key)
        except json.JSONDecodeError:
            return []

    @property
    def kling_secret_keys(self) -> List[str]:
        """Kling Secret Keys를 JSON 파싱하여 리스트로 반환"""
        try:
            return json.loads(self.kling_secret_key)
        except json.JSONDecodeError:
            return []

    # 템플릿 파일 설정 (테스트용)
    use_template_mode: bool = Field(default=True, env="USE_TEMPLATE_MODE")
    template_book_id: str = "2bec5881-f268-4fd1-8b89-0c74e145203d"
    template_image: str = "0_page_1.png"
    template_video: str = "page_1.mp4"

    # HTTP 클라이언트 설정
    http_timeout: float = 60.0
    http_read_timeout: float = 300.0
    http_max_connections: int = 10

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore",  # .env의 TTS 관련 환경변수 무시
    }


# 싱글톤 인스턴스
settings = Settings()
