# generate_image_task 구현 구조 분석

## 개요

`generate_image_task`는 스토리북 생성 파이프라인의 Task 2로, 모든 페이지의 이미지를 배치 처리하며 재시도를 지원합니다.

- **파일 위치**: `features/storybook/tasks/core.py:301-498`
- **역할**: 이미지 생성 (배치 처리 - 모든 페이지, 재시도 지원)

---

## 1. 전체 의존성 구조도

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         generate_image_task()                                │
│                 features/storybook/tasks/core.py:301-498                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐          ┌───────────────┐          ┌───────────────┐
│  TaskStore    │          │ AIProvider    │          │ StorageService│
│  (Redis)      │          │ Factory       │          │ (S3/Local)    │
└───────────────┘          └───────────────┘          └───────────────┘
        │                           │                           │
        │                           ▼                           │
        │                  ┌───────────────┐                    │
        │                  │ RunwareProvider│                   │
        │                  │ (Image Gen)   │                    │
        │                  └───────────────┘                    │
        │                                                       │
        ▼                                                       ▼
┌───────────────────┐                              ┌───────────────────┐
│ BatchRetryTracker │                              │  BookRepository   │
│ (Retry Logic)     │                              │  (PostgreSQL)     │
└───────────────────┘                              └───────────────────┘
```

---

## 2. 실행 흐름 (Phase별)

### Phase 1: 초기화

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ TaskStore    │───▶│ story:{id}   │───▶│ dialogues[]  │
│ .get()       │    │ (Redis)      │    │ 추출         │
└──────────────┘    └──────────────┘    └──────────────┘
        │
        ▼
┌──────────────────────────────────────────┐
│ BatchRetryTracker 생성                    │
│ - total_items: len(images)               │
│ - max_retries: settings.task_image_max_retries (2)
└──────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────┐
│ Redis 캐시 복구 (재시도 시)               │
│ Key: images_cache:{book_id}              │
└──────────────────────────────────────────┘
```

### Phase 2: Prompt 생성

```python
prompts = [
    GenerateImagePrompt(stories=dialogue, style_keyword="cartoon").render()
    for dialogue in dialogues
]
ai_factory = get_ai_factory()
image_provider = ai_factory.get_image_provider()  # → RunwareProvider
```

### Phase 3: 재시도 루프

```
while not tracker.is_all_completed():
    │
    ▼
┌───────────────────┐
│ pending_indices = │
│ tracker.get_      │
│ pending_indices() │
└───────────────────┘
    │
    ▼
┌───────────────────────────────────────────────────────────────┐
│ tasks = [                                                      │
│   image_provider.generate_image_from_image(                   │
│     image_data=images[idx],                                   │
│     prompt=prompts[idx]                                       │
│   )                                                           │
│   for idx in pending_indices                                  │
│ ]                                                             │
└───────────────────────────────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────────────────────────────┐
│ results = await asyncio.gather(*tasks, return_exceptions=True)│
└───────────────────────────────────────────────────────────────┘
    │
    ├──▶ 성공: tracker.mark_success(idx, {imageUUID, imageURL})
    └──▶ 실패: tracker.mark_failure(idx, str(error))
    │
    ▼
┌───────────────────────────────────────────────────────────────┐
│ Redis 중간 저장: images_cache:{book_id}                       │
│ {                                                             │
│   "completed": {idx: imageInfo, ...},                        │
│   "retry_counts": {...},                                     │
│   "last_errors": {...}                                       │
│ }                                                            │
└───────────────────────────────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────────────────────────────┐
│ delay = await calculate_retry_delay(retry_count)              │
│ await asyncio.sleep(delay)   # Exponential Backoff            │
└───────────────────────────────────────────────────────────────┘
```

### Phase 4: 결과 평가

```python
if tracker.is_all_completed():
    status = TaskStatus.COMPLETED
elif tracker.is_partial_failure():
    status = TaskStatus.COMPLETED  # 부분 성공도 COMPLETED로 처리
else:
    status = TaskStatus.FAILED
```

### Phase 5: Cover Image 저장

```
cover_image = tracker.completed[0]  # 첫 페이지를 커버로 사용
        │
        ▼
┌──────────────────────────────────────────────────────────────┐
│ httpx.AsyncClient                                             │
│   .get(cover_image["imageURL"])                              │
│   timeout=(http_timeout, http_read_timeout)                  │
└──────────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────────┐
│ storage_service.save(                                         │
│   image_bytes,                                               │
│   f"{book.base_path}/images/cover.png",                      │
│   content_type="image/png"                                   │
│ )                                                            │
└──────────────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────────────┐
│ repo.update(                                                  │
│   book_uuid,                                                 │
│   pipeline_stage="image",                                    │
│   progress_percentage=60,                                    │
│   cover_image=file_name,                                     │
│   task_metadata=task_metadata                                │
│ )                                                            │
└──────────────────────────────────────────────────────────────┘
```

### Phase 6: 최종 결과 저장

```python
await task_store.set(
    f"images:{book_id}",
    {
        "images": [info for info in image_infos if info],
        "page_count": len(images),
        "failed_pages": tracker.get_failed_indices()
    },
    ttl=3600
)

return TaskResult(
    status=status,
    result={
        "image_infos": image_infos,
        "page_count": len(images),
        "completed_count": len(tracker.completed),
        "failed_count": len(tracker.get_failed_indices()),
        "summary": tracker.get_summary()
    }
)
```

---

## 3. 핵심 컴포넌트 상세

### 3.1 TaskStatus (Enum)

**파일**: `features/storybook/tasks/schemas.py:11-17`

```python
class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
```

### 3.2 TaskResult (Pydantic Model)

**파일**: `features/storybook/tasks/schemas.py:20-34`

```python
class TaskResult(BaseModel):
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
```

### 3.3 TaskContext (Pydantic Model)

**파일**: `features/storybook/tasks/schemas.py:37-51`

```python
class TaskContext(BaseModel):
    book_id: str
    user_id: str
    execution_id: str
    retry_count: int = 0
```

### 3.4 BatchRetryTracker

**파일**: `features/storybook/tasks/retry.py:93-180`

```python
class BatchRetryTracker:
    """배치 처리 재시도 추적기"""

    def __init__(self, total_items: int, max_retries: int)

    # 주요 속성
    completed: Dict[int, Any]      # 성공 결과 저장
    retry_counts: Dict[int, int]   # 재시도 횟수 추적
    last_errors: Dict[int, str]    # 마지막 에러 메시지
    total_items: int               # 전체 아이템 수
    max_retries: int               # 최대 재시도 횟수

    # 주요 메서드
    def mark_success(self, idx: int, result: Any)
    def mark_failure(self, idx: int, error: str)
    def get_pending_indices(self) -> List[int]
    def get_failed_indices(self) -> List[int]
    def is_all_completed(self) -> bool
    def is_partial_failure(self) -> bool
    def get_summary(self) -> dict
```

### 3.5 TaskStore (Redis 기반)

**파일**: `features/storybook/tasks/store.py:17-324`

```python
class TaskStore:
    """Redis 기반 Task 결과 저장소"""

    async def set(key: str, value: Any, ttl: Optional[int] = None) -> bool
    async def get(key: str) -> Optional[Any]
    async def delete(key: str) -> bool
```

**Redis Key 패턴**:
- `story:{book_id}` - 스토리 데이터 (페이지, 콘텐츠)
- `images_cache:{book_id}` - 이미지 생성 중간 결과 캐시
- `images:{book_id}` - 최종 이미지 결과

### 3.6 GenerateImagePrompt

**파일**: `features/storybook/prompts/generate_image_prompt.py:20-45`

```python
@dataclass
class GenerateImagePrompt:
    stories: list[str]
    style_keyword: ArtStyle  # WATERCOLOR, VAN_GOGH, FANTASY, CARTOON

    def render(self) -> str:
        # 스타일별 프롬프트 생성
```

### 3.7 ImageGenerationProvider Interface

**파일**: `infrastructure/ai/base.py:95-168`

```python
class ImageGenerationProvider(ABC):
    @abstractmethod
    async def generate_image_from_image(
        self,
        image_data: bytes,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        style: Optional[str] = None,
    ) -> bytes:
        pass
```

### 3.8 RunwareProvider Implementation

**파일**: `infrastructure/ai/providers/runware.py:20-247`

```python
class RunwareProvider(VideoGenerationProvider, ImageGenerationProvider):
    async def generate_image_from_image(
        self,
        image_data: bytes,
        prompt: str,
        width: int = 864,
        height: int = 1184,
        ...
    ) -> Dict[str, Any]:
        """
        Returns:
            {
                "data": [{
                    "imageUUID": str,
                    "imageURL": str,
                    ...
                }]
            }
        """
```

---

## 4. 설정값 (Settings)

**파일**: `core/config.py`

| 설정 | 기본값 | 환경변수 | 설명 |
|------|--------|----------|------|
| `task_image_max_retries` | 2 | `TASK_IMAGE_MAX_RETRIES` | 이미지별 최대 재시도 횟수 |
| `http_timeout` | 60.0 | `HTTP_TIMEOUT` | HTTP 요청 타임아웃 |
| `http_read_timeout` | 300.0 | `HTTP_READ_TIMEOUT` | HTTP 읽기 타임아웃 |
| `task_retry_delay` | 2.0 | `TASK_RETRY_DELAY` | 재시도 대기 시간 (초) |
| `task_retry_exponential_backoff` | True | `TASK_RETRY_EXPONENTIAL_BACKOFF` | Exponential Backoff 사용 |

---

## 5. 데이터 흐름

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Redis      │    │  Runware API │    │   S3/Local   │    │  PostgreSQL  │
│   (Cache)    │    │  (External)  │    │  (Storage)   │    │   (DB)       │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
       ▲                   ▲                   ▲                   ▲
       │                   │                   │                   │
┌──────┴───────┐    ┌──────┴───────┐    ┌──────┴───────┐    ┌──────┴───────┐
│  TaskStore   │    │ Runware      │    │StorageService│    │BookRepository│
│              │    │ Provider     │    │              │    │              │
│ Key Patterns:│    │              │    │ Methods:     │    │ Methods:     │
│ story:{id}   │    │ Methods:     │    │ • save()     │    │ • get()      │
│ images:{id}  │    │ • generate_  │    │ • get()      │    │ • update()   │
│ images_cache │    │   image_     │    │              │    │              │
│ :{id}        │    │   from_image │    │              │    │              │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
       ▲                   ▲                   ▲                   ▲
       │                   │                   │                   │
       └───────────────────┴───────────────────┴───────────────────┘
                                    │
                         ┌─────────────────────┐
                         │ generate_image_task │
                         └─────────────────────┘
```

---

## 6. 파일 위치 요약

| 컴포넌트 | 파일 경로 | 라인 |
|----------|-----------|------|
| `generate_image_task` | `features/storybook/tasks/core.py` | 301-498 |
| `TaskStatus`, `TaskResult`, `TaskContext` | `features/storybook/tasks/schemas.py` | 11-51 |
| `TaskStore` | `features/storybook/tasks/store.py` | 17-324 |
| `BatchRetryTracker` | `features/storybook/tasks/retry.py` | 93-180 |
| `calculate_retry_delay` | `features/storybook/tasks/retry.py` | 17-35 |
| `GenerateImagePrompt` | `features/storybook/prompts/generate_image_prompt.py` | 20-45 |
| `ImageGenerationProvider` | `infrastructure/ai/base.py` | 95-168 |
| `RunwareProvider` | `infrastructure/ai/providers/runware.py` | 20-247 |
| `AIProviderFactory` | `infrastructure/ai/factory.py` | 43-52 |
| `get_storage_service` | `core/dependencies.py` | 48-59 |
| `BookRepository` | `features/storybook/repository.py` | 17-60 |
| `AsyncSessionLocal` | `core/database/session.py` | 24-30 |
| `Settings` | `core/config.py` | 192-228 |

---

## 7. 에러 처리 전략

1. **개별 이미지 실패 허용**: `asyncio.gather(*tasks, return_exceptions=True)`
2. **재시도 메커니즘**: `BatchRetryTracker`로 실패한 이미지만 재시도
3. **Exponential Backoff**: 재시도 간격을 점진적으로 증가
4. **중간 결과 캐싱**: Redis에 성공한 결과 저장하여 재시도 시 복구
5. **부분 성공 처리**: 일부 이미지만 성공해도 `COMPLETED` 상태로 진행

---

*마지막 업데이트: 2025-12-19*
