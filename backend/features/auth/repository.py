"""
User Repository
사용자 데이터 접근 계층
"""

import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.models.user import User
from backend.domain.repositories.base import AbstractRepository


class UserRepository(AbstractRepository[User]):
    """
    사용자 Repository

    AbstractRepository를 상속받아 기본 CRUD 제공 및
    사용자 특화 검색 기능 추가
    """

    def __init__(self, db: AsyncSession):
        super().__init__(db, User)
        self.db = db  # Alias for compatibility if needed, though base uses self.session

    async def get_by_email(self, email: str) -> Optional[User]:
        """이메일로 사용자 조회"""
        query = select(User).where(User.email == email)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_oauth(self, oauth_provider: str, oauth_id: str) -> Optional[User]:
        """OAuth 정보로 사용자 조회"""
        query = select(User).where(
            User.oauth_provider == oauth_provider,
            User.oauth_id == oauth_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def exists_by_email(self, email: str) -> bool:
        """이메일 존재 여부 확인"""
        query = select(User.id).where(User.email == email)
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    # Override create to accept User object if needed, or keep base create(**kwargs)
    # The existing service might pass a User object. Let's check usage or support both.
    # Existing create(self, user: User) -> User

    async def save(self, user: User) -> User:
        """
        User 객체 저장 (Create/Update)
        기존 코드와의 호환성을 위해 유지하거나, Service Layer를 수정해야 함.
        여기서는 기존 create 메서드와 유사하게 동작하도록 구현.
        """
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user
