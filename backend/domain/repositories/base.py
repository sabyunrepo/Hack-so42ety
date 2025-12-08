"""
Base Repository Interface
Repository 패턴을 위한 추상 베이스 클래스
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Type, Optional, List, Any
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class AbstractRepository(ABC, Generic[ModelType]):
    """
    Abstract Repository Interface
    
    기본적인 CRUD 작업을 정의하는 추상 클래스
    """

    def __init__(self, session: AsyncSession, model: Type[ModelType]):
        self.session = session
        self.model = model

    async def get(self, id: UUID) -> Optional[ModelType]:
        """ID로 단일 엔티티 조회"""
        query = select(self.model).where(self.model.id == id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """모든 엔티티 조회 (Paging)"""
        query = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, **kwargs) -> ModelType:
        """엔티티 생성"""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, id: UUID, **kwargs) -> Optional[ModelType]:
        """엔티티 수정"""
        instance = await self.get(id)
        if instance:
            for key, value in kwargs.items():
                setattr(instance, key, value)
            await self.session.flush()
            await self.session.refresh(instance)
        return instance

    async def delete(self, id: UUID) -> bool:
        """엔티티 삭제"""
        instance = await self.get(id)
        if instance:
            await self.session.delete(instance)
            await self.session.flush()
            return True
        return False
