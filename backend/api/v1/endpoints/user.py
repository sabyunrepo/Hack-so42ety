from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.session import get_db_write
from backend.core.auth.dependencies import get_current_user_object as get_current_user
from backend.core.auth.providers.credentials import CredentialsAuthProvider
from backend.features.auth.models import User
from backend.features.auth.repository import UserRepository
from backend.features.auth.schemas import UserResponse
from backend.features.user.schemas import UserUpdateRequest
from backend.features.user.service import UserService

router = APIRouter()


def get_user_service(
    db: AsyncSession = Depends(get_db_write),
) -> UserService:
    """UserService 의존성 주입"""
    user_repo = UserRepository(db)
    credentials_provider = CredentialsAuthProvider()
    return UserService(
        user_repo=user_repo,
        credentials_provider=credentials_provider,
        db_session=db,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """내 정보 조회"""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_me(
    request: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    """
    내 정보 수정

    Args:
        request: 수정 요청 (비밀번호 등)
        current_user: 현재 사용자 정보
        service: UserService (의존성 주입)

    Returns:
        UserResponse: 수정된 사용자 정보
    """
    user = await service.update_user(
        user_id=current_user.id,
        password=request.password,
    )
    return user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    """
    회원 탈퇴

    Args:
        current_user: 현재 사용자 정보
        service: UserService (의존성 주입)

    Returns:
        None (HTTP 204 No Content)
    """
    await service.delete_user(current_user.id)
