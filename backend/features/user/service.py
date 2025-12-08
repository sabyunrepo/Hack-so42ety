"""
User Service
사용자 비즈니스 로직
"""

import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.auth.models import User
from backend.features.auth.repository import UserRepository
from backend.core.auth.providers.credentials import CredentialsAuthProvider
from .exceptions import (
    UserNotFoundException,
    UserUpdateFailedException,
    InvalidPasswordException,
)


class UserService:
    """
    사용자 서비스

    사용자 정보 조회, 수정, 삭제 처리

    DI Pattern: 모든 의존성을 생성자를 통해 주입받습니다.
    """

    def __init__(
        self,
        user_repo: UserRepository,
        credentials_provider: CredentialsAuthProvider,
        db_session: AsyncSession,
    ):
        """
        Args:
            user_repo: 사용자 레포지토리
            credentials_provider: 비밀번호 인증 제공자
            db_session: 비동기 데이터베이스 세션
        """
        self.user_repo = user_repo
        self.credentials_provider = credentials_provider
        self.db_session = db_session

    async def get_user(self, user_id: uuid.UUID) -> User:
        """
        사용자 조회

        Args:
            user_id: 사용자 UUID

        Returns:
            User: 사용자 정보

        Raises:
            UserNotFoundException: 사용자를 찾을 수 없음
        """
        user = await self.user_repo.get(user_id)
        if user is None:
            raise UserNotFoundException(user_id=str(user_id))
        return user

    async def update_user(
        self,
        user_id: uuid.UUID,
        password: Optional[str] = None,
    ) -> User:
        """
        사용자 정보 수정

        Args:
            user_id: 사용자 UUID
            password: 새 비밀번호 (선택)

        Returns:
            User: 수정된 사용자 정보

        Raises:
            UserNotFoundException: 사용자를 찾을 수 없음
            InvalidPasswordException: 유효하지 않은 비밀번호
            UserUpdateFailedException: 수정 실패
        """
        # 사용자 조회
        user = await self.user_repo.get(user_id)
        if user is None:
            raise UserNotFoundException(user_id=str(user_id))

        # 비밀번호 변경
        if password is not None:
            # 비밀번호 유효성 검증은 Pydantic 스키마에서 처리
            # 여기서는 해싱만 수행
            user.password_hash = self.credentials_provider.hash_password(password)

        # 저장
        try:
            user = await self.user_repo.save(user)
            await self.db_session.commit()
        except Exception as e:
            await self.db_session.rollback()
            raise UserUpdateFailedException(reason=str(e))

        return user

    async def delete_user(self, user_id: uuid.UUID) -> bool:
        """
        사용자 삭제 (회원 탈퇴)

        Args:
            user_id: 사용자 UUID

        Returns:
            bool: 삭제 성공 여부

        Raises:
            UserNotFoundException: 사용자를 찾을 수 없음
        """
        # 사용자 존재 확인
        user = await self.user_repo.get(user_id)
        if user is None:
            raise UserNotFoundException(user_id=str(user_id))

        # 삭제
        result = await self.user_repo.delete(user_id)
        if result:
            await self.db_session.commit()
        else:
            await self.db_session.rollback()

        return result

