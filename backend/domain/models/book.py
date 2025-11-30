"""
Book Domain Models
동화책 관련 ORM 모델 (Book, Page, Dialogue)
"""

import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, DateTime, ForeignKey, Integer, Text, Boolean
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
    cover_image_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    
    # 메타데이터 (장르, 연령대 등)
    genre: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    target_age: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    theme: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # 상태 (draft, published)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    
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
    페이지 내 대사/지문 모델
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
    speaker: Mapped[str] = mapped_column(String(100), default="Narrator", nullable=False)
    
    # 내용 (영어/한국어)
    text_en: Mapped[str] = mapped_column(Text, nullable=False)
    text_ko: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # TTS 오디오 연결
    audio_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    page: Mapped["Page"] = relationship("Page", back_populates="dialogues")

    def __repr__(self) -> str:
        return f"<Dialogue(id={self.id}, page_id={self.page_id}, speaker={self.speaker})>"
