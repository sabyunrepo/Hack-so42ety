# Python 버전 업그레이드 계획

## 오류 원인 분석

### 발생한 오류
```
TypeError: duplicate base class TimeoutError
File "/usr/local/lib/python3.11/site-packages/aioredis/exceptions.py", line 14
class TimeoutError(asyncio.TimeoutError, builtins.TimeoutError, RedisError):
```

### 원인
- `aioredis 2.0.1`에서 `TimeoutError` 클래스가 `asyncio.TimeoutError`와 `builtins.TimeoutError`를 모두 상속
- Python 3.11에서 `asyncio.TimeoutError`가 `builtins.TimeoutError`의 별칭(alias)이 되어 중복 상속 오류 발생
- Python 3.10 이하에서는 문제 없었지만, Python 3.11+에서 발생하는 호환성 문제

### 해결 방안
Python 3.12 이상으로 업그레이드하면 해결됩니다:
- Python 3.12+에서는 `asyncio.TimeoutError`가 독립적인 클래스로 분리되어 중복 상속 문제가 해결됨
- `aioredis 2.0.1`이 Python 3.12+에서 정상 동작

---

## 업그레이드 계획

### 변경 사항
1. **Dockerfile 수정**
   - `FROM python:3.11-slim` → `FROM python:3.12-slim`
   - Python 경로도 `3.11` → `3.12`로 변경

2. **의존성 확인**
   - 기존 패키지들이 Python 3.12와 호환되는지 확인
   - 대부분의 패키지는 Python 3.12를 지원

### 예상 영향
- ✅ `aioredis 2.0.1` 정상 동작
- ✅ 기존 패키지 호환성 유지
- ✅ 성능 개선 (Python 3.12는 3.11보다 약 10-15% 빠름)

---

## 수정할 파일

1. `docker/backend/Dockerfile`
   - Line 4: `FROM python:3.11-slim` → `FROM python:3.12-slim`
   - Line 31: `/usr/local/lib/python3.11/site-packages` → `/usr/local/lib/python3.12/site-packages`

---

## 진행 순서

1. Dockerfile 수정
2. 빌드 캐시 초기화 후 재빌드
3. 백엔드 재시작
4. 로그 확인 및 테스트

---

## 롤백 계획

문제 발생 시:
- Dockerfile을 Python 3.11로 되돌리기
- 기존 이미지로 재빌드

