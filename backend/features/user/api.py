from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.session import get_db
from backend.core.auth.dependencies import get_current_user_object as get_current_user
from backend.features.auth.models import User
from backend.features.auth.repository import UserRepository
from backend.features.auth.schemas import UserResponse
from backend.features.user.schemas import UserUpdateRequest
from passlib.context import CryptContext

router = APIRouter(prefix="/user", tags=["user"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """내 정보 조회"""
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_me(
    request: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """내 정보 수정"""
    repo = UserRepository(db)
    
    if request.password:
        current_user.password_hash = pwd_context.hash(request.password)
        
    await repo.save(current_user)
    return current_user

@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """회원 탈퇴"""
    repo = UserRepository(db)
    await repo.delete(current_user.id)
