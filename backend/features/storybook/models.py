"""
Book Domain Models
동화책 관련 ORM 모델 (Book, Page, Dialogue)
"""

import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, DateTime, ForeignKey, Integer, Text, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database.base import Base


class BookStatus:
    CREATING = "creating"
    COMPLETED = "completed"
    FAILED = "failed"
    DRAFT = "draft"

class Book(Base):
    """
    동화책 모델
    """
    __tablename__ = "books"

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

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    cover_image: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    # 메타데이터 (장르, 연령대 등)
    genre: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    target_age: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    theme: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # 상태 (draft, published)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    
    # TTS 음성 ID (ElevenLabs voice ID for word TTS)
    voice_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # 기본 제공 책 여부 (공통 라이브러리)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 공개/비공개 설정
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        index=True,
    )
    visibility: Mapped[str] = mapped_column(
        String(20),
        default="private",
        server_default="private",
        nullable=False,
        index=True,
    )

    # Soft delete support for quota tracking
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        index=True,  # For fast quota queries: WHERE user_id = ? AND is_deleted = false
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    pages: Mapped[List["Page"]] = relationship(
        "Page", back_populates="book", cascade="all, delete-orphan", order_by="Page.sequence"
    )

    @property
    def base_path(self) -> str:
        """
        Book의 기본 저장 경로 반환
        
        - 공통 책 (is_default=true): shared/books/{book_id}
        - 사용자 책 (is_default=false): users/{user_id}/books/{book_id}
        
        Returns:
            str: 파일 저장 기본 경로
        """
        if self.is_default:
            return f"shared/books/{self.id}"
        else:
            return f"users/{self.user_id}/books/{self.id}"

    def __repr__(self) -> str:
        return f"<Book(id={self.id}, title={self.title}, user_id={self.user_id})>"


class Page(Base):
    """
    동화책 페이지 모델
    """
    __tablename__ = "pages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    book_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 페이지 순서 (1부터 시작)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    image_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    image_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    book: Mapped["Book"] = relationship("Book", back_populates="pages")
    dialogues: Mapped[List["Dialogue"]] = relationship(
        "Dialogue", back_populates="page", cascade="all, delete-orphan", order_by="Dialogue.sequence"
    )

    def __repr__(self) -> str:
        return f"<Page(id={self.id}, book_id={self.book_id}, sequence={self.sequence})>"


class Dialogue(Base):
    """
    페이지 내 대사/지문 모델 (멀티언어 지원)

    다국어 텍스트는 DialogueTranslation 테이블로 관리
    TTS 오디오는 DialogueAudio 테이블로 관리
    """
    __tablename__ = "dialogues"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    page_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 대사 순서
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    # 화자 (Narrator, Character Name)
    # 멀티언어 지원: speaker_code 기반 (코드는 번역되지 않음)
    speaker: Mapped[str] = mapped_column(String(100), default="Narrator", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    page: Mapped["Page"] = relationship("Page", back_populates="dialogues")
    translations: Mapped[List["DialogueTranslation"]] = relationship(
        "DialogueTranslation", back_populates="dialogue", cascade="all, delete-orphan"
    )
    audios: Mapped[List["DialogueAudio"]] = relationship(
        "DialogueAudio", back_populates="dialogue", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Dialogue(id={self.id}, page_id={self.page_id}, speaker={self.speaker})>"


class DialogueTranslation(Base):
    """
    대사 번역 모델 (멀티언어 지원)

    각 Dialogue는 여러 언어로 번역 가능
    is_primary=True는 원본 언어를 나타냄
    """
    __tablename__ = "dialogue_translations"

    __table_args__ = (
        # 복합 유니크 제약: 하나의 대사는 언어당 하나의 번역만 가능
        Index('idx_dialogue_language', 'dialogue_id', 'language_code', unique=True),
        # 성능 최적화 인덱스: 언어별 검색
        Index('idx_language_primary', 'language_code', 'is_primary'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    dialogue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dialogues.id", ondelete="CASCADE"),
        nullable=False,
    )

    # 언어 코드 (ISO 639-1: en, ko, ja, zh, es, fr, de, etc.)
    language_code: Mapped[str] = mapped_column(String(10), nullable=False)

    # 번역된 텍스트
    text: Mapped[str] = mapped_column(Text, nullable=False)

    # 원본 언어 여부
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    dialogue: Mapped["Dialogue"] = relationship("Dialogue", back_populates="translations")

    def __repr__(self) -> str:
        return f"<DialogueTranslation(id={self.id}, dialogue_id={self.dialogue_id}, language={self.language_code})>"


class DialogueAudio(Base):
    """
    대사 TTS 오디오 모델 (멀티언어 + 멀티보이스 지원)

    각 Dialogue는 언어별, 음성별로 여러 오디오 파일 보유 가능
    예: 영어(남성), 영어(여성), 한국어(남성), 한국어(여성) 등
    """
    __tablename__ = "dialogue_audios"

    __table_args__ = (
        # 복합 유니크 제약: 하나의 대사는 언어+음성 조합당 하나의 오디오만 가능
        Index('idx_dialogue_language_voice', 'dialogue_id', 'language_code', 'voice_id', unique=True),
        # 성능 최적화 인덱스: 언어별 오디오 검색
        Index('idx_audio_language', 'language_code'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    dialogue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dialogues.id", ondelete="CASCADE"),
        nullable=False,
    )

    # 언어 코드 (ISO 639-1: en, ko, ja, zh, es, fr, de, etc.)
    language_code: Mapped[str] = mapped_column(String(10), nullable=False)

    # ElevenLabs 음성 ID (다양한 음성 지원)
    voice_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # 상태 (PENDING, PROCESSING, COMPLETED, FAILED)
    status: Mapped[str] = mapped_column(
        String(20),
        default="PENDING",
        server_default="PENDING",
        nullable=False
    )

    # 오디오 파일 URL
    audio_url: Mapped[str] = mapped_column(String(1024), nullable=False)

    # 오디오 재생 시간 (초)
    duration: Mapped[Optional[float]] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    dialogue: Mapped["Dialogue"] = relationship("Dialogue", back_populates="audios")

    def __repr__(self) -> str:
        return f"<DialogueAudio(id={self.id}, dialogue_id={self.dialogue_id}, language={self.language_code}, voice={self.voice_id})>"
