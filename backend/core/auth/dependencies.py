"""
Authentication Dependencies
FastAPI Depends용 인증 의존성
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from .jwt_manager import JWTManager

# HTTP Bearer 토큰 스킴
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    현재 인증된 사용자 정보 추출

    Args:
        credentials: HTTP Authorization Bearer 토큰
        db: 데이터베이스 세션

    Returns:
        dict: 사용자 정보 (user_id, email 등)

    Raises:
        HTTPException: 토큰이 유효하지 않거나 만료된 경우
    """
    # JWT 토큰 검증
    payload = JWTManager.verify_token(credentials.credentials, token_type="access")

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # user_id 추출
    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 사용자 정보 반환 (DB 조회는 Repository에서 수행)
    return {
        "user_id": user_id,
        "email": payload.get("email"),
    }


async def get_current_active_user(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    활성화된 사용자 정보 추출

    추후 사용자 비활성화 기능 추가 시 사용

    Args:
        current_user: 현재 사용자 정보

    Returns:
        dict: 활성화된 사용자 정보

    Raises:
        HTTPException: 사용자가 비활성화된 경우
    """
    # 추후 User 모델에 is_active 필드 추가 시 검증 로직 구현
    # if not current_user.get("is_active"):
    #     raise HTTPException(status_code=400, detail="Inactive user")

    return current_user

async def get_current_user_object(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    현재 인증된 사용자 객체(DB 모델) 반환
    """
    from ...domain.repositories.user_repository import UserRepository
    import uuid
    
    user_repo = UserRepository(db)
    try:
        user_id = uuid.UUID(current_user["user_id"])
        user = await user_repo.get(user_id)
        if user is None:
             raise HTTPException(status_code=404, detail="User not found")
        return user
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user ID format")
