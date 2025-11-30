from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserUpdateRequest(BaseModel):
    """사용자 정보 수정 요청"""
    password: Optional[str] = Field(None, min_length=8, description="새 비밀번호")
    # 이메일 변경은 별도 인증 절차가 필요하므로 여기서는 제외하거나 추후 구현
    # email: Optional[EmailStr] = None 
