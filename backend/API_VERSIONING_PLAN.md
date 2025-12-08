# 백엔드 API 버전 관리 및 구조 재편 계획

## 목표
현재의 "기능 중심(Feature-First)" 아키텍처를 리팩토링하여, 도메인 주도 설계(DDD)의 장점을 유지하면서 API 버전 관리(예: v1, v2)를 지원하도록 합니다.

## 현재 구조 (Feature-First)
현재 구조는 API 정의와 기능 로직이 강하게 결합되어 있어, 여러 API 버전을 동시에 유지보수하기 어렵습니다.
```
backend/
  features/
    auth/
      api.py      <-- API 정의 (v1이 섞여 있음)
      service.py  <-- 도메인 로직
      schemas.py  <-- 데이터 전송 객체 (DTO)
  main.py         <-- "/api/v1" 접두사가 하드코딩됨
```

## 제안된 구조 (API 버전 관리 + 도메인 기능)
**API 인터페이스**(버전별)와 **도메인 로직**(기능별)을 분리합니다.

```
backend/
  api/                 <-- 신규: 중앙화된 API 계층
    v1/
      router.py        <-- 모든 v1 엔드포인트 통합
      endpoints/
        auth.py        <-- v1 인증 엔드포인트 (features/auth/api.py에서 이동)
        storybook.py   <-- v1 동화책 엔드포인트
    v2/                <-- 향후 추가될 버전
      router.py
      endpoints/
        auth.py
  features/            <-- 기존: 도메인 로직 (공유됨)
    auth/
      service.py       <-- 재사용 가능한 비즈니스 로직
      repository.py
    storybook/
      service.py
  main.py              <-- backend.api.v1, backend.api.v2 라우터 포함
```

## 마이그레이션 전략

### 1단계: 디렉토리 구조 생성
API 계층을 위한 새로운 폴더 구조를 생성합니다.
```bash
mkdir -p backend/api/v1/endpoints
touch backend/api/__init__.py
touch backend/api/v1/__init__.py
touch backend/api/v1/router.py
```

### 2단계: API 정의 이동
`backend/features/{feature}/api.py`의 코드를 `backend/api/v1/endpoints/{feature}.py`로 이동합니다.
- **Import 수정**: 이동된 파일에서 `backend.features.{feature}.service` 및 `backend.features.{feature}.schemas`를 참조하도록 import 경로를 수정해야 합니다.
- **라우터 정의**: 개별 엔드포인트 파일에서 `prefix="/auth"` 등을 제거합니다. 접두사는 중앙 라우터나 `main.py`에서 처리합니다.

### 3단계: 중앙 V1 라우터 생성
`backend/api/v1/router.py`에서 모든 기능별 라우터를 통합합니다.
```python
from fastapi import APIRouter
from backend.api.v1.endpoints import auth, storybook, tts, user

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(storybook.router, prefix="/storybook", tags=["Storybook"])
# ...
```

### 4단계: Main.py 업데이트
`backend/main.py`가 새로운 중앙 라우터를 사용하도록 수정합니다.
```python
from backend.api.v1.router import api_router as api_v1_router

app.include_router(api_v1_router, prefix="/api/v1")
```

### 5단계: 스키마 버전 관리 (선택/고급)
버전 간에 `schemas.py`가 변경되는 경우, `backend/api/v1/schemas/{feature}.py`로 이동시킵니다. 변경이 없다면 기존 `backend/features/{feature}/schemas.py`를 그대로 유지합니다.

## 장점
1.  **확장성**: 전체 기능 로직을 복제하지 않고도 `v2`를 쉽게 추가할 수 있습니다.
2.  **명확성**: "API가 어떻게 보이는지"(인터페이스)와 "어떻게 작동하는지"(서비스)가 명확히 분리됩니다.
3.  **유지보수성**: 레거시 버전(v1)을 동결한 상태로 v2를 발전시킬 수 있으며, 두 버전 모두 동일한 기본 서비스(또는 필요시 버전별 서비스)를 사용할 수 있습니다.
