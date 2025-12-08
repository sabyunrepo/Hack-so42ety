"""
Audio Domain Models
TTS 생성 오디오 메타데이터 모델
"""
import uuid
from datetime import datetime
from typing import Optional
from enum import Enum
from sqlalchemy import String, DateTime, ForeignKey, Float, JSON, Integer, Text, Enum as SQLEnum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database.base import Base


class VoiceVisibility(str, Enum):
    """Voice 공개 범위"""
    PRIVATE = "private"  # 사용자 개인 음성
    PUBLIC = "public"    # 공개 음성 (모든 사용자 조회 가능)
    DEFAULT = "default"  # 기본 음성 (ElevenLabs premade, 모든 사용자 조회 가능)


class VoiceStatus(str, Enum):
    """Voice 생성 상태"""
    PROCESSING = "processing"  # 생성 중
    COMPLETED = "completed"    # 생성 완료
    FAILED = "failed"          # 생성 실패


class Audio(Base):
    """
    오디오 메타데이터 모델
    """
    __tablename__ = "audios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    # 소유자 (RLS 적용 대상)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 파일 정보
    file_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)  # Storage 내 경로
    duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str] = mapped_column(String(50), default="audio/mpeg", nullable=False)

    # 생성 정보
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    voice_id: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # elevenlabs, etc.

    # 추가 메타데이터
    meta_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Audio(id={self.id}, user_id={self.user_id}, provider={self.provider})>"


class Voice(Base):
    """
    Voice 모델 (사용자별 음성 관리)
    
    ElevenLabs Voice Clone 생성 및 관리를 위한 모델
    """
    __tablename__ = "voices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    # 소유자
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ElevenLabs Voice ID
    elevenlabs_voice_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    # Voice 정보
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    language: Mapped[str] = mapped_column(
        String(10),
        default="en",
        nullable=False,
    )
    gender: Mapped[str] = mapped_column(
        String(20),
        default="unknown",
        nullable=False,
    )
    preview_url: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
    )
    category: Mapped[str] = mapped_column(
        String(50),
        default="cloned",  # premade, cloned, custom
        server_default="cloned",
        nullable=False,
    )

    # 공개 범위
    visibility: Mapped[VoiceVisibility] = mapped_column(
        SQLEnum(VoiceVisibility, name="voicevisibility"),
        default=VoiceVisibility.PRIVATE,
        server_default="private",
        nullable=False,
        index=True,
    )

    # 생성 상태
    status: Mapped[VoiceStatus] = mapped_column(
        SQLEnum(VoiceStatus, name="voicestatus"),
        default=VoiceStatus.PROCESSING,
        server_default="processing",
        nullable=False,
        index=True,
    )

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    # 추가 메타데이터
    meta_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # 인덱스
    __table_args__ = (
        Index('idx_voice_user_id', 'user_id'),
        Index('idx_voice_status', 'status'),
        Index('idx_voice_visibility', 'visibility'),
        Index('idx_voice_user_status', 'user_id', 'status'),
        Index('idx_voice_visibility_status', 'visibility', 'status'),
        Index('idx_voice_elevenlabs_id', 'elevenlabs_voice_id'),
    )

    def __repr__(self) -> str:
        return (
            f"<Voice(id={self.id}, name={self.name}, "
            f"visibility={self.visibility.value}, status={self.status.value})>"
        )
