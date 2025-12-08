# Backend API 개발 가이드

## 목차
1. [프로젝트 구조](#프로젝트-구조)
2. [새로운 API 추가 방법](#새로운-api-추가-방법)
3. [상세 단계별 가이드](#상세-단계별-가이드)
4. [Best Practices](#best-practices)

---

## 프로젝트 구조

```
backend/
├── api/
│   └── v1/
│       ├── router.py              # 메인 라우터 (모든 엔드포인트 통합)
│       └── endpoints/             # API 엔드포인트 모듈
│           ├── auth.py            # 인증 관련 API
│           ├── storybook.py       # 동화책 관련 API
│           ├── tts.py             # TTS 관련 API
│           └── user.py            # 사용자 관련 API
├── features/                      # 비즈니스 로직 (Feature별 구성)
│   ├── auth/
│   │   ├── schemas.py            # Pydantic 스키마 (Request/Response)
│   │   └── service.py            # 비즈니스 로직
│   ├── storybook/
│   │   ├── schemas.py
│   │   └── service.py
│   ├── tts/
│   │   ├── schemas.py
│   │   └── service.py
│   └── user/
│       ├── schemas.py
│       └── service.py
├── domain/                        # 도메인 레이어
│   ├── models/                   # ORM 모델
│   │   ├── user.py
│   │   └── book.py
│   └── repositories/             # 데이터 접근 레이어
│       ├── user_repository.py
│       └── book_repository.py
├── infrastructure/               # 인프라 레이어
│   ├── ai/                      # AI 제공자
│   │   └── providers/
│   └── storage/                 # 스토리지 서비스
│       ├── local.py
│       └── s3.py
└── core/                        # 핵심 설정
    ├── config.py                # 환경 설정
    ├── database/                # DB 설정
    └── auth/                    # 인증 설정
```

---

## 새로운 API 추가 방법

### 개요
새로운 API를 추가할 때는 다음 순서로 작업합니다:

1. **스키마 정의** (`features/{feature}/schemas.py`)
2. **서비스 로직 구현** (`features/{feature}/service.py`)
3. **API 엔드포인트 작성** (`api/v1/endpoints/{feature}.py`)
4. **라우터 등록** (`api/v1/router.py`)

---

## 상세 단계별 가이드

### Step 1: 스키마 정의 (Pydantic)

**파일 위치**: `backend/features/{feature_name}/schemas.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime

# Request 스키마
class CreateItemRequest(BaseModel):
    """아이템 생성 요청"""
    name: str = Field(..., min_length=1, max_length=255, description="아이템 이름")
    description: Optional[str] = Field(None, max_length=1000, description="아이템 설명")
    price: int = Field(..., ge=0, description="가격 (0 이상)")

class UpdateItemRequest(BaseModel):
    """아이템 수정 요청"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    price: Optional[int] = Field(None, ge=0)

# Response 스키마
class ItemResponse(BaseModel):
    """아이템 응답"""
    id: UUID
    name: str
    description: Optional[str]
    price: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True  # ORM 모델 → Pydantic 변환 허용

class ItemListResponse(BaseModel):
    """아이템 목록 응답"""
    items: List[ItemResponse]
    total: int
```

**주요 포인트**:
- `Request`: 클라이언트가 보내는 데이터
- `Response`: 서버가 반환하는 데이터
- `Field()`: 유효성 검증 및 문서화
- `Config.from_attributes = True`: ORM 모델을 Pydantic으로 변환

---

### Step 2: 서비스 로직 구현

**파일 위치**: `backend/features/{feature_name}/service.py`

```python
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from backend.domain.models.item import Item
from backend.domain.repositories.item_repository import ItemRepository
from backend.infrastructure.storage.base import AbstractStorageService

class ItemService:
    """아이템 비즈니스 로직"""
    
    def __init__(self, db: AsyncSession, storage_service: AbstractStorageService):
        self.db = db
        self.storage_service = storage_service
        self.item_repo = ItemRepository(db)
    
    async def create_item(
        self,
        user_id: UUID,
        name: str,
        description: Optional[str] = None,
        price: int = 0
    ) -> Item:
        """아이템 생성"""
        # 비즈니스 로직 검증
        if price < 0:
            raise ValueError("Price must be non-negative")
        
        # 아이템 생성
        item = Item(
            user_id=user_id,
            name=name,
            description=description,
            price=price
        )
        
        # 저장
        item = await self.item_repo.save(item)
        await self.db.commit()
        
        return item
    
    async def get_items(self, user_id: UUID) -> List[Item]:
        """사용자의 아이템 목록 조회"""
        return await self.item_repo.get_by_user_id(user_id)
    
    async def get_item(self, item_id: UUID) -> Optional[Item]:
        """아이템 상세 조회"""
        return await self.item_repo.get_by_id(item_id)
    
    async def update_item(
        self,
        item_id: UUID,
        user_id: UUID,
        **updates
    ) -> Optional[Item]:
        """아이템 수정"""
        item = await self.item_repo.get_by_id(item_id)
        
        if not item or item.user_id != user_id:
            return None
        
        # 업데이트
        for key, value in updates.items():
            if value is not None and hasattr(item, key):
                setattr(item, key, value)
        
        await self.db.commit()
        return item
    
    async def delete_item(self, item_id: UUID, user_id: UUID) -> bool:
        """아이템 삭제"""
        item = await self.item_repo.get_by_id(item_id)
        
        if not item or item.user_id != user_id:
            return False
        
        await self.item_repo.delete(item_id)
        await self.db.commit()
        return True
```

**주요 포인트**:
- 비즈니스 로직과 데이터 접근을 분리
- Repository 패턴 사용
- 에러 처리 (ValueError, None 반환 등)
- 트랜잭션 관리 (`await self.db.commit()`)

---

### Step 3: API 엔드포인트 작성

**파일 위치**: `backend/api/v1/endpoints/{feature_name}.py`

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from backend.core.database.session import get_db
from backend.core.auth.dependencies import get_current_user_object as get_current_user
from backend.domain.models.user import User
from backend.infrastructure.storage.local import LocalStorageService
from backend.infrastructure.storage.s3 import S3StorageService
from backend.core.config import settings
from backend.features.item.service import ItemService
from backend.features.item.schemas import (
    CreateItemRequest,
    UpdateItemRequest,
    ItemResponse,
    ItemListResponse
)

router = APIRouter()

def get_storage_service():
    """스토리지 서비스 팩토리"""
    if settings.storage_provider == "s3":
        return S3StorageService()
    return LocalStorageService()

@router.post(
    "/items",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="아이템 생성",
    description="새로운 아이템을 생성합니다."
)
async def create_item(
    request: CreateItemRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """아이템 생성 API"""
    storage_service = get_storage_service()
    service = ItemService(db, storage_service)
    
    try:
        item = await service.create_item(
            user_id=current_user.id,
            name=request.name,
            description=request.description,
            price=request.price
        )
        return item
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create item: {str(e)}"
        )

@router.get(
    "/items",
    response_model=ItemListResponse,
    summary="아이템 목록 조회",
    description="현재 사용자의 모든 아이템을 조회합니다."
)
async def list_items(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """아이템 목록 조회 API"""
    storage_service = get_storage_service()
    service = ItemService(db, storage_service)
    
    items = await service.get_items(current_user.id)
    return ItemListResponse(items=items, total=len(items))

@router.get(
    "/items/{item_id}",
    response_model=ItemResponse,
    summary="아이템 상세 조회",
    description="특정 아이템의 상세 정보를 조회합니다."
)
async def get_item(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """아이템 상세 조회 API"""
    storage_service = get_storage_service()
    service = ItemService(db, storage_service)
    
    item = await service.get_item(item_id)
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # 권한 체크
    if item.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this item"
        )
    
    return item

@router.put(
    "/items/{item_id}",
    response_model=ItemResponse,
    summary="아이템 수정",
    description="아이템 정보를 수정합니다."
)
async def update_item(
    item_id: UUID,
    request: UpdateItemRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """아이템 수정 API"""
    storage_service = get_storage_service()
    service = ItemService(db, storage_service)
    
    # None이 아닌 필드만 업데이트
    updates = {k: v for k, v in request.dict().items() if v is not None}
    
    item = await service.update_item(item_id, current_user.id, **updates)
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found or not authorized"
        )
    
    return item

@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="아이템 삭제",
    description="아이템을 삭제합니다."
)
async def delete_item(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """아이템 삭제 API"""
    storage_service = get_storage_service()
    service = ItemService(db, storage_service)
    
    success = await service.delete_item(item_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found or not authorized"
        )
```

**주요 포인트**:
- `@router.{method}`: HTTP 메서드 지정
- `response_model`: 응답 스키마 지정 (자동 검증 및 문서화)
- `status_code`: HTTP 상태 코드
- `summary`, `description`: API 문서화
- `Depends()`: 의존성 주입 (DB, 인증 등)
- 에러 처리: `HTTPException` 사용

---

### Step 4: 라우터 등록

**파일 위치**: `backend/api/v1/router.py`

```python
from fastapi import APIRouter
from backend.api.v1.endpoints import auth, storybook, tts, user, item  # 새로운 모듈 import

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(storybook.router, prefix="/storybook", tags=["Storybook"])
api_router.include_router(tts.router, prefix="/tts", tags=["TTS"])
api_router.include_router(user.router, prefix="/user", tags=["User"])
api_router.include_router(item.router, prefix="/item", tags=["Item"])  # 새로운 라우터 추가
```

**주요 포인트**:
- `prefix`: URL 경로 접두사 (예: `/api/v1/item`)
- `tags`: Swagger 문서에서 그룹화

---

## Best Practices

### 1. 에러 처리
```python
# ✅ Good: 명확한 에러 메시지
raise HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Invalid price: must be non-negative"
)

# ❌ Bad: 불명확한 에러
raise HTTPException(status_code=400, detail="Error")
```

### 2. 인증 및 권한
```python
# ✅ Good: 인증된 사용자만 접근
@router.get("/items")
async def list_items(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 현재 사용자의 아이템만 조회
    items = await service.get_items(current_user.id)
    return items

# ✅ Good: 소유권 확인
if item.user_id != current_user.id:
    raise HTTPException(status_code=403, detail="Not authorized")
```

### 3. 트랜잭션 관리
```python
# ✅ Good: 명시적 커밋
async def create_item(self, ...):
    item = await self.item_repo.save(item)
    await self.db.commit()  # 명시적 커밋
    return item

# ✅ Good: 롤백 처리
try:
    item = await self.item_repo.save(item)
    await self.db.commit()
except Exception as e:
    await self.db.rollback()
    raise
```

### 4. 유효성 검증
```python
# ✅ Good: Pydantic 스키마에서 검증
class CreateItemRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    price: int = Field(..., ge=0)  # >= 0

# ✅ Good: 서비스 레이어에서 비즈니스 로직 검증
async def create_item(self, ...):
    if price < 0:
        raise ValueError("Price must be non-negative")
```

### 5. 문서화
```python
# ✅ Good: 명확한 문서화
@router.post(
    "/items",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="아이템 생성",
    description="새로운 아이템을 생성합니다. 가격은 0 이상이어야 합니다.",
    responses={
        201: {"description": "아이템 생성 성공"},
        400: {"description": "잘못된 요청 (유효성 검증 실패)"},
        401: {"description": "인증 실패"},
    }
)
async def create_item(...):
    """
    아이템 생성 API
    
    Args:
        request: 아이템 생성 요청 데이터
        current_user: 현재 인증된 사용자
        db: 데이터베이스 세션
    
    Returns:
        ItemResponse: 생성된 아이템 정보
    
    Raises:
        HTTPException: 400 - 유효성 검증 실패
        HTTPException: 500 - 서버 에러
    """
    ...
```

### 6. 비동기 처리
```python
# ✅ Good: async/await 사용
async def get_items(self, user_id: UUID) -> List[Item]:
    return await self.item_repo.get_by_user_id(user_id)

# ✅ Good: 병렬 처리
items, total = await asyncio.gather(
    self.item_repo.get_by_user_id(user_id),
    self.item_repo.count_by_user_id(user_id)
)
```

---

## 체크리스트

새로운 API를 추가할 때 다음 사항을 확인하세요:

- [ ] **스키마 정의**: Request/Response 스키마 작성
- [ ] **서비스 로직**: 비즈니스 로직 구현
- [ ] **API 엔드포인트**: FastAPI 라우터 작성
- [ ] **라우터 등록**: `api/v1/router.py`에 등록
- [ ] **인증**: 필요한 경우 `Depends(get_current_user)` 추가
- [ ] **권한 체크**: 소유권 확인 로직 추가
- [ ] **에러 처리**: 적절한 HTTP 상태 코드 및 에러 메시지
- [ ] **문서화**: summary, description, docstring 작성
- [ ] **테스트**: 단위 테스트 및 통합 테스트 작성
- [ ] **Swagger 확인**: `http://localhost:8000/docs`에서 API 문서 확인

---

## 추가 리소스

- **FastAPI 공식 문서**: https://fastapi.tiangolo.com/
- **Pydantic 문서**: https://docs.pydantic.dev/
- **SQLAlchemy 문서**: https://docs.sqlalchemy.org/
- **프로젝트 API 명세**: `API_SPECIFICATION.md` 참조
