"""
User Repository
사용자 데이터 접근 계층
"""

import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import User


class UserRepository:
    """
    사용자 Repository

    CRUD 및 사용자 검색 기능 제공
    """

    def __init__(self, db: AsyncSession):
        """
        Args:
            db: 비동기 데이터베이스 세션
        """
        self.db = db

    async def create(self, user: User) -> User:
        """
        사용자 생성

        Args:
            user: User 모델 인스턴스

        Returns:
            User: 생성된 사용자
        """
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """
        ID로 사용자 조회

        Args:
            user_id: 사용자 UUID

        Returns:
            Optional[User]: 사용자 또는 None
        """
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        이메일로 사용자 조회

        Args:
            email: 사용자 이메일

        Returns:
            Optional[User]: 사용자 또는 None
        """
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_oauth(
        self, oauth_provider: str, oauth_id: str
    ) -> Optional[User]:
        """
        OAuth 정보로 사용자 조회

        Args:
            oauth_provider: OAuth 제공자 (google)
            oauth_id: OAuth 사용자 ID

        Returns:
            Optional[User]: 사용자 또는 None
        """
        result = await self.db.execute(
            select(User).where(
                User.oauth_provider == oauth_provider,
                User.oauth_id == oauth_id,
            )
        )
        return result.scalar_one_or_none()

    async def update(self, user: User) -> User:
        """
        사용자 정보 업데이트

        Args:
            user: 업데이트할 User 모델 인스턴스

        Returns:
            User: 업데이트된 사용자
        """
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        """
        사용자 삭제

        Args:
            user: 삭제할 User 모델 인스턴스
        """
        await self.db.delete(user)
        await self.db.flush()

    async def exists_by_email(self, email: str) -> bool:
        """
        이메일 존재 여부 확인

        Args:
            email: 확인할 이메일

        Returns:
            bool: 존재 여부
        """
        result = await self.db.execute(
            select(User.id).where(User.email == email)
        )
        return result.scalar_one_or_none() is not None
