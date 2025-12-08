# aioredis 2.0.1 + Python 3.12 호환성 문제

## 문제 상황

Python 3.12로 업그레이드 후 발생한 오류:
```
ModuleNotFoundError: No module named 'distutils'
File "/usr/local/lib/python3.12/site-packages/aioredis/connection.py", line 11
from distutils.version import StrictVersion
```

## 원인

1. **Python 3.12에서 `distutils` 완전 제거**
   - Python 3.12에서는 `distutils` 모듈이 표준 라이브러리에서 완전히 제거됨
   - `setuptools`를 설치해도 `distutils`가 자동으로 제공되지 않음

2. **aioredis 2.0.1의 의존성**
   - `aioredis 2.0.1`이 `distutils.version.StrictVersion`을 직접 import
   - Python 3.12와 호환되지 않음

## 해결 방안

### Option 1: Python 3.11로 되돌리기 (권장) ⭐⭐⭐⭐⭐

**장점**:
- 가장 빠른 해결
- 기존 코드 수정 불필요
- 안정적

**단점**:
- Python 3.12의 성능 개선 포기

### Option 2: aioredis 패치 (복잡) ⭐⭐

**방법**:
- `aioredis` 소스 코드를 직접 수정
- `distutils.version.StrictVersion` → `packaging.version.Version`로 변경

**단점**:
- 유지보수 어려움
- 업데이트 시 재적용 필요

### Option 3: Python 3.11 유지 + 다른 해결책 ⭐⭐⭐

**방법**:
- Python 3.11 유지
- `aioredis 2.0.1` 정상 동작
- 다른 최적화 방법 모색

## 권장 사항

**Python 3.11로 되돌리기**를 권장합니다.

이유:
- `aioredis 2.0.1`은 Python 3.11에서 정상 동작
- Python 3.12의 성능 개선(10-15%)보다 안정성이 우선
- 추가 작업 없이 즉시 해결 가능

