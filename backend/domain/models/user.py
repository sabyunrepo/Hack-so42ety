"""
User Model
사용자 ORM 모델
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database.base import Base


class User(Base):
    """
    사용자 모델

    Attributes:
        id: 사용자 UUID (Primary Key)
        email: 이메일 (Unique)
        password_hash: 비밀번호 해시 (Nullable - OAuth 전용 사용자)
        oauth_provider: OAuth 제공자 (google, None)
        oauth_id: OAuth 사용자 ID
        is_active: 활성화 여부
        created_at: 생성 시간
        updated_at: 수정 시간
    """

    __tablename__ = "users"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    # 이메일 (Unique)
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    # 비밀번호 해시 (Nullable - OAuth 전용 사용자)
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # OAuth 정보
    oauth_provider: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    oauth_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # 활성화 여부
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, provider={self.oauth_provider})>"
