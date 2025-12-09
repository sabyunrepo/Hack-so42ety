# 🎓 Hack-so42ety Backend Onboarding Guide

> **신입 개발자를 위한 백엔드 온보딩 가이드**
>
> MoriAI Storybook Service의 백엔드 아키텍처, 핵심 개념, 개발 가이드를 다룹니다.

---

## 📚 목차

1. [프로젝트 개요](#-프로젝트-개요)
2. [아키텍처 개요](#-아키텍처-개요)
3. [디렉토리 구조](#-디렉토리-구조)
4. [핵심 개념](#-핵심-개념)
5. [주요 모듈 설명](#-주요-모듈-설명)
6. [개발 환경 설정](#-개발-환경-설정)
7. [API 개발 가이드](#-api-개발-가이드)
8. [테스트 작성 가이드](#-테스트-작성-가이드)
9. [자주 사용하는 패턴](#-자주-사용하는-패턴)
10. [트러블슈팅](#-트러블슈팅)
11. [다음 단계](#-다음-단계)

---

## 🎯 프로젝트 개요

### 서비스 소개

**MoriAI Storybook Service**는 AI 기반 맞춤형 동화책 생성 플랫폼입니다.

#### 주요 기능
- **AI 동화책 생성**: Google Gemini 기반 스토리 자동 생성
- **이미지 생성**: Kling AI를 활용한 고품질 이미지 생성
- **TTS 음성 합성**: ElevenLabs 다국어 음성 생성
- **인증 시스템**: JWT + Google OAuth 2.0
- **사용자별 데이터 격리**: Row Level Security (RLS)

### 기술 스택

| 분류 | 기술 |
|------|------|
| **Framework** | FastAPI 0.104+ |
| **Database** | PostgreSQL 16 + SQLAlchemy 2.0 (Async) |
| **ORM** | SQLAlchemy (with Alembic migrations) |
| **Authentication** | JWT (python-jose) + bcrypt |
| **AI Services** | Google Gemini, Kling AI, ElevenLabs |
| **Cache & Events** | Redis (aiocache, Redis Streams) |
| **Storage** | Local/S3 (추상화 레이어) |
| **Testing** | pytest, pytest-asyncio |
| **Code Quality** | ruff, black, isort, mypy |

### 프로젝트 현황

현재 프로젝트는 **Phase 6 완료** 상태입니다 (REBUILDING_PLAN.md 참조):

- ✅ Phase 1: 인증 시스템 구축
- ✅ Phase 2: AI Provider 추상화
- ✅ Phase 3: 데이터베이스 설계 및 Repository
- ✅ Phase 4: Feature 모듈 구현
- ✅ Phase 5: 프론트엔드 통합
- ✅ Phase 6: API Versioning & 데이터 마이그레이션
- 🔄 Phase 7: 배포 준비 (진행 중)

---

## 🏗️ 아키텍처 개요

### Feature-First 아키텍처

이 프로젝트는 **Feature-First 아키텍처**를 채택하고 있습니다. 기능별로 모듈을 분리하여 응집도를 높이고 결합도를 낮췄습니다.

```
┌─────────────────────────────────────────────────┐
│                  API Layer (v1)                 │
│  /auth, /storybook, /tts, /user, /metrics       │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│               Feature Modules                   │
│  • Auth (인증/인가)                             │
│  • Storybook (동화책 생성/조회)                  │
│  • TTS (음성 합성)                              │
│  • User (사용자 관리)                            │
│  각 Feature: Service → Repository → ORM Models │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│              Core Layer                         │
│  • Auth (JWT, OAuth)                            │
│  • Database (Session, Base)                     │
│  • Cache (Redis, aiocache)                      │
│  • Events (Redis Streams)                       │
│  • Middleware (CORS, Auth)                      │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│          Infrastructure Layer                   │
│  • AI Providers (Google, Kling, ElevenLabs)     │
│  • Storage (Local/S3)                           │
└─────────────────────────────────────────────────┘
```

### 설계 원칙

1. **추상화 우선 (Abstraction First)**
   - AI Provider, Storage 모두 인터페이스(Abstract Base Class) 정의
   - 구현체 교체 시 비즈니스 로직 변경 없음

2. **의존성 주입 (Dependency Injection)**
   - FastAPI의 `Depends()`를 활용한 DI 패턴
   - 테스트 가능성 및 유지보수성 향상

3. **Repository 패턴**
   - 데이터 접근 계층을 추상화
   - ORM 직접 사용 대신 Repository를 통한 CRUD

4. **보안 By Design**
   - JWT 기반 인증/인가
   - Row Level Security (DB 레벨 격리)
   - bcrypt 비밀번호 해싱 (rounds=12)

---

## 📁 디렉토리 구조

```
backend/
├── api/                        # API Endpoints (버전별 라우터)
│   └── v1/
│       ├── endpoints/          # 개별 엔드포인트
│       │   ├── auth.py
│       │   ├── storybook.py
│       │   ├── tts.py
│       │   ├── user.py
│       │   ├── metrics.py
│       │   └── files.py
│       └── router.py           # v1 라우터 통합
│
├── core/                       # 핵심 모듈 (공통 기능)
│   ├── auth/                   # 인증/인가
│   │   ├── jwt_manager.py      # JWT 생성/검증
│   │   ├── dependencies.py     # FastAPI Depends 인증
│   │   └── providers/          # OAuth, Credentials
│   ├── cache/                  # 캐싱 (aiocache + Redis)
│   │   ├── config.py
│   │   └── service.py
│   ├── database/               # 데이터베이스 설정
│   │   ├── base.py             # SQLAlchemy Base
│   │   └── session.py          # AsyncSession 팩토리
│   ├── events/                 # 이벤트 버스 (Redis Streams)
│   │   ├── bus.py
│   │   ├── types.py
│   │   └── redis_streams_bus.py
│   ├── exceptions/             # 예외 처리
│   │   ├── base.py
│   │   ├── codes.py
│   │   ├── handlers.py
│   │   └── schemas.py
│   ├── middleware/             # 미들웨어
│   │   ├── auth.py             # 사용자 컨텍스트
│   │   └── cors.py             # CORS 설정
│   ├── services/               # 공통 서비스
│   │   ├── file_access.py
│   │   └── file_cache.py
│   ├── tasks/                  # 백그라운드 작업
│   │   ├── voice_sync.py       # 음성 동기화
│   │   └── voice_queue.py
│   ├── config.py               # 환경 설정 (Pydantic Settings)
│   └── dependencies.py         # 공통 의존성
│
├── domain/                     # 도메인 레이어 (공통 리포지토리)
│   └── repositories/
│       └── base.py             # AbstractRepository
│
├── features/                   # Feature 모듈 (비즈니스 로직)
│   ├── auth/                   # 인증 Feature
│   │   ├── models.py           # User ORM 모델
│   │   ├── repository.py       # UserRepository
│   │   ├── service.py          # AuthService (회원가입, 로그인)
│   │   ├── schemas.py          # Pydantic 스키마
│   │   └── exceptions.py       # Auth 관련 예외
│   ├── storybook/              # 동화책 Feature
│   │   ├── models.py           # Book, Page, Dialogue 모델
│   │   ├── repository.py       # BookRepository
│   │   ├── service.py          # BookOrchestratorService
│   │   ├── schemas.py
│   │   └── exceptions.py
│   ├── tts/                    # TTS Feature
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── service.py          # TTSService
│   │   ├── schemas.py
│   │   └── exceptions.py
│   └── user/                   # 사용자 프로필 Feature
│       ├── service.py
│       ├── schemas.py
│       └── exceptions.py
│
├── infrastructure/             # 외부 서비스 연동
│   ├── ai/                     # AI Provider 추상화
│   │   ├── base.py             # AIStoryProvider, AIImageProvider 등
│   │   ├── factory.py          # AIProviderFactory
│   │   └── providers/
│   │       ├── google_ai.py    # Google Gemini
│   │       ├── kling.py        # Kling Video
│   │       ├── elevenlabs_tts.py
│   │       └── custom_model.py # 자체 모델 Placeholder
│   └── storage/                # 스토리지 추상화
│       ├── base.py             # AbstractStorageService
│       ├── local.py            # 로컬 파일 시스템
│       └── s3.py               # AWS S3
│
├── migrations/                 # Alembic 마이그레이션
│   ├── env.py
│   ├── versions/               # 마이그레이션 파일
│   │   ├── 001_create_users_table.py
│   │   ├── 002_create_book_tables.py
│   │   └── ...
│   └── alembic.ini
│
├── scripts/                    # 유틸리티 스크립트
│   ├── migrate_backup.py       # 데이터 마이그레이션
│   └── ...
│
├── tests/                      # 테스트 코드
│   ├── unit/                   # 단위 테스트
│   │   ├── auth/
│   │   ├── repositories/
│   │   ├── storage/
│   │   └── ai/
│   ├── integration/            # 통합 테스트
│   └── e2e/                    # E2E 테스트
│
├── main.py                     # FastAPI 앱 진입점
├── requirements.txt            # Python 의존성
├── pytest.ini                  # pytest 설정
└── alembic.ini                 # Alembic 설정
```

---

## 🧠 핵심 개념

### 1. Feature-First 아키텍처

각 Feature는 다음과 같은 구조를 따릅니다:

```python
features/
└── {feature_name}/
    ├── models.py       # SQLAlchemy ORM 모델
    ├── repository.py   # 데이터 접근 계층
    ├── service.py      # 비즈니스 로직
    ├── schemas.py      # Pydantic 입출력 스키마
    └── exceptions.py   # Feature 전용 예외
```

**예시: Auth Feature**

```python
# features/auth/service.py
class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def register(self, email: str, password: str) -> User:
        # 비즈니스 로직
        hashed_password = CredentialsProvider.hash_password(password)
        user = await self.user_repo.create(email, hashed_password)
        return user
```

### 2. Repository 패턴

Repository는 데이터베이스 접근을 추상화합니다.

```python
# domain/repositories/base.py
class AbstractRepository(ABC):
    @abstractmethod
    async def get(self, id: UUID) -> Optional[Model]:
        pass

    @abstractmethod
    async def create(self, **kwargs) -> Model:
        pass
```

**사용 예시:**

```python
# features/auth/repository.py
class UserRepository(AbstractRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
```

### 3. 의존성 주입 (Dependency Injection)

FastAPI의 `Depends()`를 활용하여 의존성을 주입합니다.

```python
# api/v1/endpoints/auth.py
@router.post("/register")
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),  # DB 세션 주입
):
    user_repo = UserRepository(db)
    auth_service = AuthService(user_repo)
    user = await auth_service.register(request.email, request.password)
    return user
```

### 4. AI Provider 추상화

AI Provider는 교체 가능하도록 추상화되어 있습니다.

```python
# infrastructure/ai/base.py
class AIStoryProvider(ABC):
    @abstractmethod
    async def generate_story_with_images(
        self, prompt: str, num_images: int, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        pass

# infrastructure/ai/factory.py
class AIProviderFactory:
    def get_story_provider(self) -> AIStoryProvider:
        provider = settings.ai_story_provider
        if provider == "google":
            return GoogleAIProvider()
        elif provider == "custom":
            return CustomModelProvider()
        else:
            raise ValueError(f"Unknown provider: {provider}")
```

### 5. 비동기 처리 (Async/Await)

모든 데이터베이스 및 외부 API 호출은 비동기로 처리됩니다.

```python
# 비동기 DB 쿼리
result = await db.execute(select(User).where(User.email == email))
user = result.scalar_one_or_none()

# 비동기 외부 API 호출
async with httpx.AsyncClient() as client:
    response = await client.post(url, json=payload)
```

### 6. 인증/인가 시스템

#### JWT 기반 인증

```python
# core/auth/jwt_manager.py
class JWTManager:
    @staticmethod
    def create_token(user_id: str, token_type: str) -> str:
        expire_delta = timedelta(minutes=15) if token_type == "access" else timedelta(days=7)
        payload = {
            "sub": user_id,
            "type": token_type,
            "exp": datetime.utcnow() + expire_delta
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")
```

#### Depends를 활용한 인증

```python
# api/v1/endpoints/user.py
@router.get("/me")
async def get_me(
    current_user: User = Depends(get_current_user_object),  # 인증 필요
):
    return current_user
```

### 7. Row Level Security (RLS)

PostgreSQL의 RLS를 활용하여 사용자별 데이터를 격리합니다.

```sql
-- migrations/versions/002_create_book_tables.py
CREATE POLICY user_books_policy ON books
    FOR ALL
    TO test_user
    USING (user_id = current_setting('app.current_user_id')::uuid);
```

---

## 🔍 주요 모듈 설명

### 1. `main.py` - 애플리케이션 진입점

FastAPI 앱을 생성하고, 라우터, 미들웨어, 예외 핸들러를 등록합니다.

```python
# backend/main.py
app = FastAPI(
    title="MoriAI Storybook Service",
    version="2.0.0",
    lifespan=lifespan,  # Startup/Shutdown 이벤트
)

# 미들웨어
app.add_middleware(UserContextMiddleware)
setup_cors(app)

# 라우터
app.include_router(api_v1_router, prefix="/api/v1")

# 예외 핸들러
app.add_exception_handler(AppException, app_exception_handler)
```

**Lifespan 관리:**

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await engine.begin()  # DB 연결 확인
    initialize_cache()    # Redis 캐시 초기화
    await event_bus.start()  # Event Bus 시작

    yield

    # Shutdown
    await event_bus.stop()
    await engine.dispose()
```

### 2. `core/config.py` - 환경 설정

Pydantic Settings를 사용하여 환경변수를 관리합니다.

```python
# backend/core/config.py
class Settings(BaseSettings):
    # Application
    app_title: str = "MoriAI Storybook Service"
    app_version: str = "2.0.0"
    debug: bool = Field(default=False, env="DEBUG")

    # Database
    postgres_user: str = Field(default="moriai_user", env="POSTGRES_USER")
    postgres_password: str = Field(default="moriai_password", env="POSTGRES_PASSWORD")

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # JWT
    jwt_secret_key: str = Field(env="JWT_SECRET_KEY")
    jwt_access_token_expire_minutes: int = 15

    # AI Providers
    google_api_key: Optional[str] = Field(env="GOOGLE_API_KEY")
    elevenlabs_api_key: Optional[str] = Field(env="ELEVENLABS_API_KEY")

settings = Settings()  # 싱글톤
```

### 3. `core/database/session.py` - 데이터베이스 세션

비동기 SQLAlchemy 세션을 생성합니다.

```python
# backend/core/database/session.py
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### 4. `core/auth/dependencies.py` - 인증 의존성

JWT 토큰을 검증하고 사용자 정보를 반환합니다.

```python
# backend/core/auth/dependencies.py
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> dict:
    payload = JWTManager.verify_token(credentials.credentials, token_type="access")

    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    return {
        "user_id": payload["sub"],
        "email": payload.get("email"),
    }
```

### 5. `features/storybook/service.py` - 동화책 오케스트레이터

AI Provider와 Repository를 조율하여 동화책을 생성합니다.

```python
# backend/features/storybook/service.py
class BookOrchestratorService:
    def __init__(
        self,
        book_repo: BookRepository,
        storage_service: AbstractStorageService,
        ai_factory: AIProviderFactory,
        db_session: AsyncSession,
    ):
        self.book_repo = book_repo
        self.storage_service = storage_service
        self.ai_factory = ai_factory
        self.db_session = db_session

    async def create_storybook(
        self, user_id: UUID, prompt: str, num_pages: int = 5
    ) -> Book:
        # 1. 스토리 생성
        story_provider = self.ai_factory.get_story_provider()
        generated_data = await story_provider.generate_story_with_images(
            prompt=prompt, num_images=num_pages
        )

        # 2. 책 엔티티 생성
        book = await self.book_repo.create(user_id, title=generated_data["title"])

        # 3. 페이지 및 이미지 생성
        image_provider = self.ai_factory.get_image_provider()
        for page_data in generated_data["pages"]:
            image_url = await image_provider.generate_image(page_data["image_prompt"])
            await self.book_repo.add_page(book.id, content=page_data["content"], image_url=image_url)

        return book
```

### 6. `infrastructure/ai/factory.py` - AI Provider 팩토리

환경변수에 따라 적절한 AI Provider를 생성합니다.

```python
# backend/infrastructure/ai/factory.py
class AIProviderFactory:
    def get_story_provider(self) -> AIStoryProvider:
        provider = settings.ai_story_provider
        if provider == "google":
            return GoogleAIProvider()
        elif provider == "custom":
            return CustomModelProvider()
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def get_image_provider(self) -> AIImageProvider:
        # 이미지 생성 Provider 반환
        pass

    def get_tts_provider(self) -> AITTSProvider:
        # TTS Provider 반환
        pass
```

---

## 🛠️ 개발 환경 설정

### 1. 필수 요구사항

- **Python**: 3.11+
- **Docker**: 20.10+
- **Docker Compose**: 2.0+

### 2. 초기 설정

```bash
# 1. 리포지토리 클론
git clone <repository-url>
cd Hack-so42ety

# 2. 환경변수 설정
cp .env.example .env
# .env 파일을 열어 필요한 값 입력 (JWT_SECRET_KEY, GOOGLE_API_KEY 등)

# 3. Docker Compose 실행
docker-compose up -d

# 4. 데이터베이스 마이그레이션
docker-compose exec backend alembic upgrade head

# 5. 백엔드 API 확인
curl http://localhost:8000/health
# 응답: {"status":"ok","service":"MoriAI Storybook Service","version":"2.0.0"}
```

### 3. 로컬 개발 (Docker 없이)

```bash
# 1. 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 의존성 설치
pip install -r backend/requirements.txt

# 3. PostgreSQL 및 Redis 실행 (별도 설치 필요)
# ...

# 4. 환경변수 설정
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export REDIS_HOST=localhost

# 5. 마이그레이션
cd backend
alembic upgrade head

# 6. 서버 실행
uvicorn backend.main:app --reload --port 8000
```

### 4. API 문서 확인

서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🚀 API 개발 가이드

### 1. 새로운 Feature 추가하기

예시: `Comment` Feature를 추가한다고 가정합니다.

#### Step 1: 디렉토리 생성

```bash
mkdir -p backend/features/comment
touch backend/features/comment/{models.py,repository.py,service.py,schemas.py,exceptions.py,__init__.py}
```

#### Step 2: ORM 모델 정의 (`models.py`)

```python
# backend/features/comment/models.py
from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from backend.core.database import Base
import uuid

class Comment(Base):
    __tablename__ = "comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id = Column(UUID(as_uuid=True), ForeignKey("books.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
```

#### Step 3: Repository 작성 (`repository.py`)

```python
# backend/features/comment/repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .models import Comment
import uuid

class CommentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, book_id: uuid.UUID, user_id: uuid.UUID, content: str) -> Comment:
        comment = Comment(book_id=book_id, user_id=user_id, content=content)
        self.db.add(comment)
        await self.db.flush()
        await self.db.refresh(comment)
        return comment

    async def get_by_book(self, book_id: uuid.UUID) -> list[Comment]:
        result = await self.db.execute(
            select(Comment).where(Comment.book_id == book_id)
        )
        return result.scalars().all()
```

#### Step 4: Service 로직 작성 (`service.py`)

```python
# backend/features/comment/service.py
from .repository import CommentRepository
import uuid

class CommentService:
    def __init__(self, comment_repo: CommentRepository):
        self.comment_repo = comment_repo

    async def add_comment(self, book_id: uuid.UUID, user_id: uuid.UUID, content: str):
        return await self.comment_repo.create(book_id, user_id, content)
```

#### Step 5: Pydantic 스키마 정의 (`schemas.py`)

```python
# backend/features/comment/schemas.py
from pydantic import BaseModel, Field
from uuid import UUID

class CommentCreateRequest(BaseModel):
    book_id: UUID
    content: str = Field(..., min_length=1, max_length=1000)

class CommentResponse(BaseModel):
    id: UUID
    book_id: UUID
    user_id: UUID
    content: str

    class Config:
        from_attributes = True
```

#### Step 6: API 엔드포인트 작성

```python
# backend/api/v1/endpoints/comment.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.database import get_db
from backend.core.auth.dependencies import get_current_user
from backend.features.comment.service import CommentService
from backend.features.comment.repository import CommentRepository
from backend.features.comment.schemas import CommentCreateRequest, CommentResponse

router = APIRouter()

@router.post("/comments", response_model=CommentResponse)
async def create_comment(
    request: CommentCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    comment_repo = CommentRepository(db)
    comment_service = CommentService(comment_repo)
    comment = await comment_service.add_comment(
        book_id=request.book_id,
        user_id=current_user["user_id"],
        content=request.content
    )
    return comment
```

#### Step 7: 라우터 등록

```python
# backend/api/v1/router.py
from backend.api.v1.endpoints import auth, storybook, tts, user, comment

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(comment.router, prefix="/comment", tags=["Comment"])  # 추가
```

#### Step 8: 마이그레이션 생성

```bash
docker-compose exec backend alembic revision --autogenerate -m "create comments table"
docker-compose exec backend alembic upgrade head
```

---

## 🧪 테스트 작성 가이드

### 1. 테스트 구조

```
tests/
├── unit/           # 단위 테스트 (Repository, Service 개별)
├── integration/    # 통합 테스트 (API 엔드포인트)
└── e2e/            # E2E 테스트 (사용자 시나리오)
```

### 2. 단위 테스트 예시

```python
# tests/unit/repositories/test_user_repository.py
import pytest
from backend.features.auth.repository import UserRepository

@pytest.mark.asyncio
async def test_create_user(db_session):
    repo = UserRepository(db_session)
    user = await repo.create(email="test@example.com", password_hash="hashed")

    assert user.email == "test@example.com"
    assert user.id is not None
```

### 3. 통합 테스트 예시

```python
# tests/integration/test_auth_flow.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    # 회원가입
    register_response = await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "password123"
    })
    assert register_response.status_code == 201

    # 로그인
    login_response = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()
```

### 4. 테스트 실행

```bash
# 전체 테스트
docker-compose exec backend pytest

# 특정 테스트 파일
docker-compose exec backend pytest tests/unit/auth/

# 커버리지 리포트
docker-compose exec backend pytest --cov=backend --cov-report=html
```

---

## 🎨 자주 사용하는 패턴

### 1. Repository 패턴

```python
# features/{feature}/repository.py
class {Feature}Repository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, id: UUID) -> Optional[Model]:
        result = await self.db.execute(select(Model).where(Model.id == id))
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> Model:
        instance = Model(**kwargs)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance
```

### 2. Service 패턴

```python
# features/{feature}/service.py
class {Feature}Service:
    def __init__(self, repo: {Feature}Repository):
        self.repo = repo

    async def perform_action(self, data: dict) -> Model:
        # 비즈니스 로직
        result = await self.repo.create(**data)
        return result
```

### 3. Dependency Injection

```python
# api/v1/endpoints/{feature}.py
@router.post("/{feature}")
async def create_{feature}(
    request: {Feature}CreateRequest,
    current_user: dict = Depends(get_current_user),  # 인증
    db: AsyncSession = Depends(get_db),  # DB 세션
):
    repo = {Feature}Repository(db)
    service = {Feature}Service(repo)
    result = await service.perform_action(request.dict())
    return result
```

### 4. 예외 처리

```python
# features/{feature}/exceptions.py
from backend.core.exceptions import AppException
from backend.core.exceptions.codes import ErrorCode

class {Feature}NotFoundException(AppException):
    def __init__(self, feature_id: str):
        super().__init__(
            code=ErrorCode.NOT_FOUND,
            message=f"{Feature} not found: {feature_id}",
            status_code=404
        )

# 사용
if not feature:
    raise {Feature}NotFoundException(feature_id=feature_id)
```

### 5. Eager Loading (N+1 문제 방지)

```python
# Repository에서 selectinload 사용
from sqlalchemy.orm import selectinload

async def get_with_pages(self, book_id: UUID) -> Optional[Book]:
    result = await self.db.execute(
        select(Book)
        .options(selectinload(Book.pages))  # Eager Load
        .where(Book.id == book_id)
    )
    return result.scalar_one_or_none()
```

---

## 🔧 트러블슈팅

### 1. `MissingGreenlet` 에러

**문제:**
```
sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called
```

**원인:** Lazy Loading 시 비동기 컨텍스트에서 동기 접근

**해결:**
```python
# selectinload로 Eager Loading
from sqlalchemy.orm import selectinload

result = await db.execute(
    select(Book).options(selectinload(Book.pages))
)
```

### 2. Alembic 마이그레이션 충돌

**문제:** 여러 개발자가 동시에 마이그레이션 생성

**해결:**
```bash
# 최신 코드 pull 후
alembic upgrade head
alembic revision --autogenerate -m "merge migration"
```

### 3. JWT 토큰 검증 실패

**문제:** `Could not validate credentials`

**확인 사항:**
- JWT_SECRET_KEY가 일치하는지 확인
- 토큰 만료 시간 확인
- 토큰 타입 (access/refresh) 확인

### 4. CORS 오류

**문제:** 프론트엔드에서 API 호출 시 CORS 차단

**해결:**
```python
# .env 파일
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

---

## 📚 다음 단계

### 1. 필수 읽기 자료

- **REBUILDING_PLAN.md**: 프로젝트 전체 리빌딩 계획
- **API_VERSIONING_PLAN.md**: API 버전 관리 전략
- **CACHING_STRATEGY_ANALYSIS.md**: 캐싱 전략
- **VOICE_IMPLEMENTATION_PLAN.md**: TTS 음성 구현 계획

### 2. 주요 파일 탐색

| 파일 경로 | 설명 |
|-----------|------|
| `backend/main.py:1` | FastAPI 앱 진입점 |
| `backend/core/config.py:1` | 환경 설정 |
| `backend/core/auth/dependencies.py:18` | 인증 의존성 |
| `backend/features/storybook/service.py:23` | 동화책 오케스트레이터 |
| `backend/infrastructure/ai/factory.py:1` | AI Provider 팩토리 |

### 3. 실습 과제

#### 초급
1. `/api/v1/health` 엔드포인트를 읽고 이해하기
2. `UserRepository.get_by_email()` 메서드 구조 파악
3. JWT 토큰 생성 로직 추적 (`JWTManager.create_token()`)

#### 중급
1. 새로운 Feature 추가 (예: `Like` 기능)
2. 기존 API에 필터링 기능 추가
3. 캐싱 적용 (Redis)

#### 고급
1. AI Provider 새로운 구현체 추가
2. 성능 최적화 (N+1 문제 해결)
3. Event-Driven 아키텍처 적용

### 4. 코드 리뷰 체크리스트

코드 작성 시 다음 사항을 확인하세요:

- [ ] Repository 패턴 준수
- [ ] 비동기 처리 (async/await)
- [ ] 타입 힌트 작성
- [ ] 예외 처리 (AppException 활용)
- [ ] 테스트 커버리지 80% 이상
- [ ] Docstring 작성
- [ ] 보안 취약점 확인 (SQL Injection, XSS 등)

---

## ✅ 체크리스트

신입 개발자가 온보딩을 완료했다면 다음을 확인하세요:

- [ ] 로컬 환경에서 Docker Compose 실행 성공
- [ ] `/docs`에서 API 문서 확인
- [ ] 회원가입 → 로그인 → 동화책 생성 플로우 이해
- [ ] Repository 패턴 이해
- [ ] 의존성 주입 (Dependency Injection) 이해
- [ ] 테스트 작성 및 실행 가능
- [ ] 간단한 Feature 추가 가능

---

**작성일**: 2025-12-09
**작성자**: Claude Code (AI Assistant)
**대상**: 신입 백엔드 개발자

**피드백 및 질문**: 이 문서에 대한 피드백이나 질문은 팀 슬랙 채널에 남겨주세요.
