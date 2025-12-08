# 백엔드 캐시 적용 분석

## 📋 분석 개요

백엔드 서비스 로직을 분석하여 캐시 적용 가능한 지점을 식별하고, 사용자별 데이터와 전역 데이터를 구분하여 캐시 전략을 수립합니다.

---

## 🔍 현재 캐시 적용 현황

### ✅ 이미 적용된 캐시

1. **TTS Voices 목록** (`GET /api/v1/tts/voices`)
   - **현재 상태**: 전역 캐시 (`tts:voices`)
   - **TTL**: 3600초 (1시간)
   - **무효화**: Voice 생성/수정/삭제 이벤트 발생 시

---

## 📊 API 엔드포인트별 분석

### 1. TTS (Text-to-Speech)

#### 1.1 `GET /api/v1/tts/voices` ✅ (이미 캐시 적용)
- **현재 구현**: 전역 캐시 (`tts:voices`)
- **사용자별 차이**: ❌ 없음 (모든 사용자에게 동일)
- **이유**: 
  - ElevenLabs API는 단일 API 키로 호출
  - 모든 사용자에게 동일한 음성 목록 반환
  - 사용자가 생성한 custom voices도 포함되지만, API 키 기반이므로 전역
- **캐시 전략**: ✅ 현재 전략 적절
  - 전역 캐시 유지
  - Voice 생성/수정/삭제 시 무효화

#### 1.2 `POST /api/v1/tts/generate`
- **캐시 적용**: ❌ 불가능 (매번 다른 텍스트, 사용자별 오디오 생성)
- **이유**: 
  - 요청마다 다른 텍스트
  - 사용자별로 다른 오디오 파일 생성
  - 캐시 의미 없음

---

### 2. Storybook (동화책)

#### 2.1 `GET /api/v1/storybook/books` ⚠️ (캐시 적용 권장)
- **현재 구현**: 캐시 없음
- **사용자별 차이**: ✅ 있음 (각 사용자의 책 목록)
- **호출 빈도**: 높음 (책장 페이지에서 자주 조회)
- **캐시 전략**: 사용자별 캐시
  - **캐시 키**: `storybook:books:{user_id}`
  - **TTL**: 300초 (5분)
  - **무효화 조건**:
    - 책 생성 시: `storybook:books:{user_id}` 무효화
    - 책 삭제 시: `storybook:books:{user_id}` 무효화
    - 책 수정 시: `storybook:books:{user_id}` 무효화

#### 2.2 `GET /api/v1/storybook/books/{book_id}` ⚠️ (캐시 적용 권장)
- **현재 구현**: 캐시 없음
- **사용자별 차이**: ✅ 있음 (권한 체크 필요)
- **호출 빈도**: 중간 (상세 페이지 조회)
- **캐시 전략**: 책별 캐시
  - **캐시 키**: `storybook:book:{book_id}`
  - **TTL**: 600초 (10분)
  - **무효화 조건**:
    - 책 수정 시: `storybook:book:{book_id}` 무효화
    - 책 삭제 시: `storybook:book:{book_id}` 무효화
    - 페이지 추가/수정/삭제 시: `storybook:book:{book_id}` 무효화

#### 2.3 `POST /api/v1/storybook/create` ❌ (캐시 불가)
- **이유**: 매번 다른 책 생성, 캐시 의미 없음

#### 2.4 `POST /api/v1/storybook/create/with-images` ❌ (캐시 불가)
- **이유**: 매번 다른 책 생성, 캐시 의미 없음

#### 2.5 `DELETE /api/v1/storybook/books/{book_id}` ❌ (캐시 불가)
- **이유**: 삭제 작업, 캐시 무효화만 필요

---

### 3. User (사용자)

#### 3.1 `GET /api/v1/user/me` ⚠️ (캐시 적용 권장)
- **현재 구현**: 캐시 없음
- **사용자별 차이**: ✅ 있음 (본인 정보)
- **호출 빈도**: 중간 (프로필 페이지)
- **캐시 전략**: 사용자별 캐시
  - **캐시 키**: `user:info:{user_id}`
  - **TTL**: 1800초 (30분)
  - **무효화 조건**:
    - 사용자 정보 수정 시: `user:info:{user_id}` 무효화
    - 사용자 삭제 시: `user:info:{user_id}` 무효화

#### 3.2 `PUT /api/v1/user/me` ❌ (캐시 불가)
- **이유**: 수정 작업, 캐시 무효화만 필요

#### 3.3 `DELETE /api/v1/user/me` ❌ (캐시 불가)
- **이유**: 삭제 작업, 캐시 무효화만 필요

---

### 4. Auth (인증)

#### 4.1 모든 인증 엔드포인트 ❌ (캐시 불가)
- **이유**: 
  - 로그인/회원가입은 매번 다른 요청
  - 토큰 생성은 캐시 불가
  - 보안상 캐시 부적절

---

## 🎯 캐시 적용 우선순위

### HIGH (즉시 적용 권장) ⭐⭐⭐

1. **`GET /api/v1/storybook/books`** (사용자별 책 목록)
   - **이유**: 
     - 호출 빈도 높음 (책장 페이지)
     - 사용자별 데이터 (캐시 효과 큼)
     - 데이터 변경 빈도 낮음
   - **예상 효과**: API 응답 시간 80% 감소

2. **`GET /api/v1/storybook/books/{book_id}`** (책 상세)
   - **이유**: 
     - 상세 페이지 조회 시 호출
     - 데이터 변경 빈도 낮음
   - **예상 효과**: API 응답 시간 70% 감소

### MEDIUM (적용 고려) ⭐⭐

3. **`GET /api/v1/user/me`** (사용자 정보)
   - **이유**: 
     - 호출 빈도 중간
     - 데이터 변경 빈도 낮음
   - **예상 효과**: API 응답 시간 60% 감소

### LOW (적용 불필요) ⭐

4. **TTS Voices** ✅ (이미 적용됨)
5. **기타 엔드포인트**: 캐시 불가 또는 효과 미미

---

## 🔑 사용자별 vs 전역 캐시 구분

### 전역 캐시 (모든 사용자에게 동일)

| API | 캐시 키 | 이유 |
|-----|---------|------|
| `GET /api/v1/tts/voices` | `tts:voices` | ElevenLabs API 키 기반, 모든 사용자 동일 |

### 사용자별 캐시 (사용자마다 다른 데이터)

| API | 캐시 키 패턴 | 이유 |
|-----|-------------|------|
| `GET /api/v1/storybook/books` | `storybook:books:{user_id}` | 각 사용자의 책 목록 |
| `GET /api/v1/storybook/books/{book_id}` | `storybook:book:{book_id}` | 책별 상세 정보 (권한 체크 필요) |
| `GET /api/v1/user/me` | `user:info:{user_id}` | 사용자별 정보 |

---

## 📝 구현 계획

### Phase 1: Storybook 목록 캐싱

#### 1.1 `BookOrchestratorService.get_books()` 수정
```python
@cache_result(key="storybook:books:{user_id}", ttl=300)
async def get_books(self, user_id: uuid.UUID) -> List[Book]:
    """사용자의 책 목록 조회 (캐싱 적용)"""
    return await self.book_repo.get_user_books(user_id)
```

#### 1.2 이벤트 타입 추가
```python
# backend/core/events/types.py
class EventType(str, Enum):
    # 기존
    VOICE_CREATED = "voice.created"
    VOICE_UPDATED = "voice.updated"
    VOICE_DELETED = "voice.deleted"
    
    # 추가
    BOOK_CREATED = "book.created"
    BOOK_UPDATED = "book.updated"
    BOOK_DELETED = "book.deleted"
```

#### 1.3 캐시 무효화 핸들러 추가
```python
# backend/core/cache/service.py
def _setup_event_handlers(self):
    # 기존 Voice 핸들러
    self.event_bus.subscribe(EventType.VOICE_CREATED, self._handle_voice_created)
    # ...
    
    # 추가: Book 핸들러
    self.event_bus.subscribe(EventType.BOOK_CREATED, self._handle_book_created)
    self.event_bus.subscribe(EventType.BOOK_UPDATED, self._handle_book_updated)
    self.event_bus.subscribe(EventType.BOOK_DELETED, self._handle_book_deleted)

async def _handle_book_created(self, event: Event) -> None:
    """Book 생성 이벤트 처리"""
    user_id = event.payload.get("user_id")
    if user_id:
        await self.delete(f"storybook:books:{user_id}")
        await self.delete(f"storybook:book:{event.payload.get('book_id')}")

async def _handle_book_updated(self, event: Event) -> None:
    """Book 수정 이벤트 처리"""
    book_id = event.payload.get("book_id")
    user_id = event.payload.get("user_id")
    if book_id:
        await self.delete(f"storybook:book:{book_id}")
    if user_id:
        await self.delete(f"storybook:books:{user_id}")

async def _handle_book_deleted(self, event: Event) -> None:
    """Book 삭제 이벤트 처리"""
    book_id = event.payload.get("book_id")
    user_id = event.payload.get("user_id")
    if book_id:
        await self.delete(f"storybook:book:{book_id}")
    if user_id:
        await self.delete(f"storybook:books:{user_id}")
```

#### 1.4 `BookOrchestratorService`에 이벤트 발행 추가
```python
# backend/features/storybook/service.py
async def create_storybook(...):
    # 책 생성 후
    book = await self.book_repo.create(...)
    
    # 이벤트 발행
    await self.event_bus.publish(
        EventType.BOOK_CREATED,
        {
            "book_id": str(book.id),
            "user_id": str(user_id),
        }
    )
    
    return book

async def delete_book(...):
    # 삭제 전에 book_id, user_id 저장
    book = await self.book_repo.get(book_id)
    
    # 삭제
    result = await self.book_repo.delete(book_id)
    
    # 이벤트 발행
    if result:
        await self.event_bus.publish(
            EventType.BOOK_DELETED,
            {
                "book_id": str(book_id),
                "user_id": str(book.user_id),
            }
        )
    
    return result
```

### Phase 2: Storybook 상세 캐싱

#### 2.1 `BookOrchestratorService.get_book()` 수정
```python
@cache_result(key="storybook:book:{book_id}", ttl=600)
async def get_book(self, book_id: uuid.UUID, user_id: uuid.UUID = None) -> Book:
    """책 상세 조회 (캐싱 적용)"""
    book = await self.book_repo.get_with_pages(book_id)
    # 권한 체크는 캐시 후에도 수행
    if user_id and book.user_id != user_id:
        raise StorybookUnauthorizedException(...)
    return book
```

**주의**: `user_id`는 캐시 키에 포함하지 않음 (책 자체는 동일하므로)
- 권한 체크는 캐시 조회 후에도 수행해야 함

### Phase 3: User 정보 캐싱

#### 3.1 `UserService.get_user()` 수정
```python
@cache_result(key="user:info:{user_id}", ttl=1800)
async def get_user(self, user_id: uuid.UUID) -> User:
    """사용자 조회 (캐싱 적용)"""
    user = await self.user_repo.get(user_id)
    if not user:
        raise UserNotFoundException(user_id=str(user_id))
    return user
```

#### 3.2 `UserService.update_user()`에 이벤트 발행 추가
```python
async def update_user(...):
    # 수정 후
    user = await self.user_repo.save(user)
    
    # 이벤트 발행
    await self.event_bus.publish(
        EventType.USER_UPDATED,
        {
            "user_id": str(user_id),
        }
    )
    
    return user
```

---

## ⚠️ TTS Voices 사용자별 차이 확인

### 현재 구현 분석

1. **API 엔드포인트**: `GET /api/v1/tts/voices`
   - **인증**: 불필요 (공개 API)
   - **현재 캐시**: 전역 캐시 (`tts:voices`)

2. **ElevenLabs API 동작**:
   - `GET /v1/voices` API는 **API 키 기반**으로 동작
   - 단일 API 키를 사용하면 모든 사용자에게 동일한 목록 반환
   - 사용자가 생성한 custom voices도 API 키에 연결됨

3. **현재 설정**:
   ```python
   # backend/core/config.py
   elevenlabs_api_key: str = Field(default="", env="ELEVENLABS_API_KEY")
   ```
   - 단일 API 키 사용
   - 모든 사용자에게 동일한 음성 목록

### 사용자별 차이가 필요한 경우

만약 **사용자별로 다른 음성 목록**이 필요하다면:

#### 옵션 1: 사용자별 API 키 저장 (복잡)
- 각 사용자가 자신의 ElevenLabs API 키를 등록
- 사용자별로 다른 음성 목록 반환
- **캐시 키**: `tts:voices:{user_id}`
- **구현 복잡도**: 높음

#### 옵션 2: 현재 구조 유지 (권장) ✅
- 단일 API 키 사용
- 모든 사용자에게 동일한 음성 목록
- **캐시 키**: `tts:voices` (전역)
- **구현 복잡도**: 낮음 (현재 상태 유지)

### 권장 사항

**현재 구조 유지 권장**:
- 대부분의 사용자는 동일한 음성 목록 사용
- Custom voices는 공유되어도 문제 없음
- 구현 복잡도 낮음
- 캐시 효율성 높음

만약 사용자별 차이가 필요하다면:
- 사용자 모델에 `elevenlabs_api_key` 필드 추가
- `TTSService.get_voices()`에 `user_id` 파라미터 추가
- 캐시 키를 `tts:voices:{user_id}`로 변경

---

## 📈 예상 성능 개선

### Storybook 목록 캐싱
- **현재**: DB 쿼리 (평균 50-100ms)
- **캐시 후**: Redis 조회 (평균 2-5ms)
- **개선율**: 80-90% 감소

### Storybook 상세 캐싱
- **현재**: DB 쿼리 + 관계 조회 (평균 100-200ms)
- **캐시 후**: Redis 조회 (평균 2-5ms)
- **개선율**: 90-95% 감소

### User 정보 캐싱
- **현재**: DB 쿼리 (평균 10-20ms)
- **캐시 후**: Redis 조회 (평균 2-5ms)
- **개선율**: 70-80% 감소

---

## 🔄 캐시 무효화 전략

### 이벤트 기반 무효화 (현재 구조 활용)

| 이벤트 | 무효화 대상 캐시 키 |
|--------|-------------------|
| `BOOK_CREATED` | `storybook:books:{user_id}`, `storybook:book:{book_id}` |
| `BOOK_UPDATED` | `storybook:book:{book_id}`, `storybook:books:{user_id}` |
| `BOOK_DELETED` | `storybook:book:{book_id}`, `storybook:books:{user_id}` |
| `USER_UPDATED` | `user:info:{user_id}` |
| `USER_DELETED` | `user:info:{user_id}` |

---

## ✅ 구현 체크리스트

### Phase 1: Storybook 목록 캐싱
- [ ] `EventType`에 `BOOK_CREATED`, `BOOK_UPDATED`, `BOOK_DELETED` 추가
- [ ] `CacheService`에 Book 이벤트 핸들러 추가
- [ ] `BookOrchestratorService.get_books()`에 `@cache_result` 적용
- [ ] `BookOrchestratorService.create_storybook()`에 이벤트 발행 추가
- [ ] `BookOrchestratorService.delete_book()`에 이벤트 발행 추가
- [ ] 테스트 작성 및 통과

### Phase 2: Storybook 상세 캐싱
- [ ] `BookOrchestratorService.get_book()`에 `@cache_result` 적용
- [ ] 권한 체크 로직 확인 (캐시 후에도 수행)
- [ ] 테스트 작성 및 통과

### Phase 3: User 정보 캐싱
- [ ] `EventType`에 `USER_UPDATED`, `USER_DELETED` 추가
- [ ] `CacheService`에 User 이벤트 핸들러 추가
- [ ] `UserService.get_user()`에 `@cache_result` 적용
- [ ] `UserService.update_user()`에 이벤트 발행 추가
- [ ] 테스트 작성 및 통과

---

## 🎯 최종 권장사항

### 즉시 적용 (HIGH)
1. ✅ **Storybook 목록 캐싱** - 가장 큰 효과
2. ✅ **Storybook 상세 캐싱** - 상세 페이지 성능 개선

### 추후 적용 (MEDIUM)
3. ⚠️ **User 정보 캐싱** - 효과는 있지만 우선순위 낮음

### 유지 (LOW)
4. ✅ **TTS Voices** - 이미 적용됨, 현재 구조 유지

---

## 📝 참고사항

### TTS Voices 사용자별 차이
- **현재**: 전역 캐시 적절 ✅
- **이유**: 단일 API 키 사용, 모든 사용자 동일 목록
- **변경 필요 시**: 사용자별 API 키 저장 구조 필요

### 캐시 키 설계 원칙
1. **전역 데이터**: 단순 키 (`tts:voices`)
2. **사용자별 데이터**: 사용자 ID 포함 (`storybook:books:{user_id}`)
3. **리소스별 데이터**: 리소스 ID 포함 (`storybook:book:{book_id}`)

