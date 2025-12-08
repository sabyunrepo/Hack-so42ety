# Features 구조 검토 및 개선 제안

## 📋 현재 구조 분석

### 1. Feature 구조 현황

각 feature는 다음과 같은 구조를 가지고 있습니다:

```
backend/features/
├── auth/          ✅ 완전한 구조 (api, models, repository, service, schemas, exceptions)
├── storybook/     ✅ 완전한 구조
├── tts/           ✅ 완전한 구조
└── user/          ❌ 불완전한 구조 (api, schemas만 존재)
```

### 2. 실제 사용되는 API 라우터

**현재 사용 중**: `backend/api/v1/endpoints/` (v1 API 엔드포인트)
- `auth.py` - AuthService 의존성 주입 사용 ✅
- `storybook.py` - BookOrchestratorService 의존성 주입 사용 ✅
- `tts.py` - TTSService 의존성 주입 사용 ✅
- `user.py` - UserRepository 직접 사용 ❌

**사용되지 않음**: `backend/features/*/api.py`
- `features/auth/api.py` - 구버전, 사용 안 함
- `features/storybook/api.py` - 사용 안 함
- `features/tts/api.py` - 사용 안 함

---

## 🔍 발견된 문제점

### 1. **User Feature 불완전** ⚠️ HIGH

**문제**:
- `features/user/`에 `api.py`, `schemas.py`만 존재
- `service.py`, `repository.py`, `models.py`, `exceptions.py` 없음
- `auth`의 `UserRepository`를 직접 사용
- 비즈니스 로직이 API 레이어에 있음 (비밀번호 해싱 등)

**현재 코드** (`api/v1/endpoints/user.py`):
```python
@router.put("/me")
async def update_me(...):
    repo = UserRepository(db)  # 직접 사용
    if request.password:
        current_user.password_hash = pwd_context.hash(request.password)  # API 레이어에서 비즈니스 로직
    await repo.save(current_user)
```

**문제점**:
- Feature 간 결합도 높음 (user가 auth에 의존)
- 비즈니스 로직이 API 레이어에 있어 테스트 어려움
- 다른 feature와 일관성 없음

**권장 해결책**:
1. `UserService` 생성하여 비즈니스 로직 이동
2. `UserRepository`는 `auth`에 두되, `user` feature에서도 사용 가능하도록 구조 조정
3. 또는 `user` feature를 `auth`에 통합

---

### 2. **중복된 의존성 주입 함수** ⚠️ MEDIUM

**문제**:
- `get_storage_service()`, `get_ai_factory()`가 `storybook`과 `tts`에 중복

**현재 코드**:
```python
# backend/api/v1/endpoints/storybook.py
def get_storage_service():
    if settings.storage_provider == "s3":
        return S3StorageService()
    return LocalStorageService()

def get_ai_factory():
    return AIProviderFactory()

# backend/api/v1/endpoints/tts.py
def get_storage_service():  # 동일한 코드 중복
    if settings.storage_provider == "s3":
        return S3StorageService()
    return LocalStorageService()

def get_ai_factory():  # 동일한 코드 중복
    return AIProviderFactory()
```

**권장 해결책**:
- `backend/core/dependencies.py` 또는 `backend/infrastructure/dependencies.py`로 이동
- 재사용 가능한 공통 의존성으로 통합

---

### 3. **AudioRepository 불필요한 래퍼** ⚠️ LOW

**문제**:
- `AudioRepository`는 `AbstractRepository`를 상속만 하고 추가 메서드 없음
- 단순 CRUD만 필요하면 직접 사용 가능

**현재 코드**:
```python
class AudioRepository(AbstractRepository[Audio]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Audio)
```

**권장 해결책**:
- 추가 메서드가 필요 없으면 유지 (향후 확장 가능성 고려)
- 또는 `AbstractRepository` 직접 사용 고려

---

### 4. **예외 처리 일관성 부족** ⚠️ MEDIUM

**문제**:
- `tts/api.py`에서 불필요한 try-except로 HTTPException 변환
- 커스텀 예외가 이미 적절히 처리되는데 중복 처리

**현재 코드** (`api/v1/endpoints/tts.py`):
```python
try:
    audio = await service.generate_speech(...)
    return audio
except Exception as e:
    raise HTTPException(...)  # 불필요 - 커스텀 예외가 이미 처리됨
```

**권장 해결책**:
- try-except 제거 (FastAPI 예외 핸들러가 처리)
- 커스텀 예외는 그대로 전파

---

### 5. **사용되지 않는 파일** ⚠️ LOW

**문제**:
- `backend/features/*/api.py` 파일들이 사용되지 않음
- 혼란 야기 가능

**파일 목록**:
- `backend/features/auth/api.py` (구버전)
- `backend/features/storybook/api.py` (미사용)
- `backend/features/tts/api.py` (미사용)

**권장 해결책**:
- 삭제 또는 `_deprecated` 접두사 추가
- README에 명시

---

### 6. **AuthService 생성자 일관성** ⚠️ LOW

**문제**:
- `features/auth/api.py` (구버전)에서는 `AuthService(db)` 단일 인자
- `api/v1/endpoints/auth.py` (신버전)에서는 의존성 주입 사용

**현재 코드**:
```python
# 구버전 (features/auth/api.py)
auth_service = AuthService(db)  # 단일 인자

# 신버전 (api/v1/endpoints/auth.py)
def get_auth_service(...) -> AuthService:
    user_repo = UserRepository(db)
    credentials_provider = CredentialsAuthProvider()
    google_oauth_provider = GoogleOAuthProvider()
    jwt_manager = JWTManager()
    return AuthService(user_repo, credentials_provider, google_oauth_provider, jwt_manager, db)
```

**권장 해결책**:
- 구버전 파일 삭제 (이미 신버전 사용 중)

---

## ✅ 개선 제안 우선순위

### HIGH Priority
1. **User Feature 완성**
   - `UserService` 생성
   - 비즈니스 로직을 Service 레이어로 이동
   - `auth`와의 의존성 관계 명확화

### MEDIUM Priority
2. **공통 의존성 함수 통합**
   - `get_storage_service()`, `get_ai_factory()` 공통 모듈로 이동

3. **예외 처리 일관성**
   - 불필요한 try-except 제거
   - 커스텀 예외 활용

### LOW Priority
4. **사용되지 않는 파일 정리**
   - `features/*/api.py` 삭제 또는 명시

5. **AudioRepository 검토**
   - 필요 시 추가 메서드 구현 또는 직접 사용

---

## 📝 권장 액션 아이템

### 즉시 처리 (HIGH)
- [ ] `UserService` 생성 및 비즈니스 로직 이동
- [ ] `user` feature 구조 완성 또는 `auth`에 통합 결정

### 단기 처리 (MEDIUM)
- [ ] 공통 의존성 함수 통합 (`core/dependencies.py` 생성)
- [ ] `tts/api.py`의 불필요한 try-except 제거

### 장기 처리 (LOW)
- [ ] 사용되지 않는 파일 정리
- [ ] Repository 패턴 일관성 검토

---

## 🎯 예상 효과

1. **코드 일관성 향상**: 모든 feature가 동일한 구조와 패턴 사용
2. **유지보수성 향상**: 중복 코드 제거, 공통 의존성 통합
3. **테스트 용이성**: 비즈니스 로직이 Service 레이어에 있어 단위 테스트 쉬움
4. **확장성 향상**: 새로운 feature 추가 시 일관된 패턴 적용 가능

