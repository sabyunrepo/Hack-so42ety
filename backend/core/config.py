"""
Core Configuration Module
환경변수 및 애플리케이션 설정 중앙 관리
"""

import json
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 설정 (Pydantic Settings v2)"""

    # ==================== Application ====================
    app_title: str = "MoriAI Storybook Service"
    app_description: str = "동화책 생성, 조회, 삭제 API (인증 및 AI 연동)"
    app_version: str = "2.0.0"
    app_env: str = Field(default="dev", env="APP_ENV")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # ==================== Server ====================
    backend_port: int = Field(default=8000, env="BACKEND_PORT")

    # ==================== Database (PostgreSQL) ====================
    postgres_user: str = Field(default="moriai_user", env="POSTGRES_USER")
    postgres_password: str = Field(default="moriai_password", env="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="moriai_db", env="POSTGRES_DB")
    postgres_host: str = Field(default="postgres", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")

    @property
    def database_url(self) -> str:
        """SQLAlchemy Database URL (Async)"""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        """SQLAlchemy Database URL (Sync - for Alembic)"""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ==================== JWT Authentication ====================
    jwt_secret_key: str = Field(
        default="default-secret-key-change-in-production-min-32-characters",
        env="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(
        default=15, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    jwt_refresh_token_expire_days: int = Field(
        default=7, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS"
    )

    # ==================== Google OAuth ====================
    google_oauth_client_id: Optional[str] = Field(
        default=None, env="GOOGLE_OAUTH_CLIENT_ID"
    )
    google_oauth_client_secret: Optional[str] = Field(
        default=None, env="GOOGLE_OAUTH_CLIENT_SECRET"
    )
    google_oauth_redirect_uri: str = Field(
        default="http://localhost:8000/auth/google/callback",
        env="GOOGLE_OAUTH_REDIRECT_URI",
    )

    # ==================== AI Providers ====================
    # Story Generation
    ai_story_provider: str = Field(default="google", env="AI_STORY_PROVIDER")
    google_api_key: Optional[str] = Field(default=None, env="GOOGLE_API_KEY")

    # TTS (Text-to-Speech)
    ai_tts_provider: str = Field(default="elevenlabs", env="AI_TTS_PROVIDER")
    elevenlabs_api_key: Optional[str] = Field(default=None, env="ELEVENLABS_API_KEY")
    tts_default_voice_id: str = Field(
        default="TxWD6rImY3v4izkm2VL0", env="TTS_DEFAULT_VOICE_ID"
    )
    tts_default_model_id: str = Field(default="eleven_v3", env="TTS_DEFAULT_MODEL_ID")
    tts_default_language: str = Field(default="en", env="TTS_DEFAULT_LANGUAGE")

    # Image Generation
    ai_image_provider: str = Field(default="google", env="AI_IMAGE_PROVIDER")

    # Video Generation
    ai_video_provider: str = Field(default="kling", env="AI_VIDEO_PROVIDER")
    kling_access_key: str = Field(default="[]", env="KLING_ACCESS_KEY")
    kling_secret_key: str = Field(default="[]", env="KLING_SECRET_KEY")
    kling_api_url: str = Field(
        default="https://api-singapore.klingai.com", env="KLING_API_URL"
    )
    kling_model_name: str = Field(default="kling-v2-1", env="KLING_MODEL_NAME")
    kling_video_mode: str = Field(default="std", env="KLING_VIDEO_MODE")
    kling_video_duration: str = Field(default="5", env="KLING_VIDEO_DURATION")
    kling_key_cooldown_seconds: int = Field(
        default=300, env="KLING_KEY_COOLDOWN_SECONDS"
    )
    kling_max_concurrent: int = Field(default=3, env="KLING_MAX_CONCURRENT")
    kling_polling_interval: int = Field(default=10, env="KLING_POLLING_INTERVAL")
    kling_max_polling_time: int = Field(default=600, env="KLING_MAX_POLLING_TIME")
    kling_api_key: Optional[str] = Field(default=None, env="KLING_API_KEY")

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

    # ==================== Storage ====================
    storage_provider: str = Field(default="local", env="STORAGE_PROVIDER")
    storage_base_path: str = Field(default="/app/data", env="STORAGE_BASE_PATH")
    storage_base_url: str = Field(default="http://localhost:8000/static", env="STORAGE_BASE_URL")

    # AWS S3 (if STORAGE_PROVIDER=s3)
    aws_access_key_id: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(
        default=None, env="AWS_SECRET_ACCESS_KEY"
    )
    aws_s3_bucket_name: Optional[str] = Field(default=None, env="AWS_S3_BUCKET_NAME")
    aws_s3_region: str = Field(default="ap-northeast-2", env="AWS_S3_REGION")

    # ==================== CORS ====================
    cors_origins_str: str = Field(
        default="http://localhost:5173", env="CORS_ORIGINS"
    )

    @property
    def cors_origins(self) -> List[str]:
        """CORS origins를 쉼표로 분리하여 리스트로 반환"""
        return [origin.strip() for origin in self.cors_origins_str.split(",")]

    cors_allow_credentials: bool = Field(
        default=True, env="CORS_ALLOW_CREDENTIALS"
    )
    cors_allow_methods: str = Field(
        default="GET,POST,PUT,DELETE,OPTIONS", env="CORS_ALLOW_METHODS"
    )
    cors_allow_headers: str = Field(default="*", env="CORS_ALLOW_HEADERS")

    # ==================== Feature Flags ====================
    use_template_mode: bool = Field(default=False, env="USE_TEMPLATE_MODE")

    # ==================== HTTP Client ====================
    http_timeout: float = Field(default=60.0, env="HTTP_TIMEOUT")
    http_read_timeout: float = Field(default=300.0, env="HTTP_READ_TIMEOUT")
    http_max_connections: int = Field(default=10, env="HTTP_MAX_CONNECTIONS")

    # ==================== Pydantic Config ====================
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ==================== Validators ====================
    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """JWT Secret Key 길이 검증 (최소 32자)"""
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")
        return v

    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        """APP_ENV 값 검증"""
        allowed_envs = ["dev", "prod"]
        if v not in allowed_envs:
            raise ValueError(f"APP_ENV must be one of {allowed_envs}")
        return v


# 싱글톤 인스턴스
settings = Settings()
