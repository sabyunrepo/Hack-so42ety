# DB 테이블 자동 생성 구현 계획

## 📋 현재 상황 분석

### 1. 현재 DB 초기화 방식
```python
# backend/main.py - lifespan()
if settings.app_env == "dev" and settings.debug:
    await conn.run_sync(Base.metadata.create_all)
    print("✓ Database tables created (development mode)")
```

**문제점**:
- ❌ `Base.metadata.create_all`은 빈 스키마만 생성 (데이터 없음)
- ❌ 마이그레이션 이력 관리 안 됨 (alembic_version 테이블 누락)
- ❌ 수동으로 `alembic upgrade head` 실행 필요
- ❌ 최신 마이그레이션 상태로 시작 불가

### 2. 현재 Dockerfile
```dockerfile
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

**문제점**:
- ❌ DB 마이그레이션 자동 실행 안 됨
- ❌ 컨테이너 재시작 시마다 수동 마이그레이션 필요

---

## 🎯 목표

### 요구사항
1. **DB 컨테이너 시작 시**: 테이블이 없으면 자동 생성
2. **테이블이 이미 있으면**: 패스 (스킵)
3. **최신 마이그레이션 상태**: 항상 최신 스키마로 시작
4. **실패 시 처리**: 마이그레이션 실패해도 백엔드는 시작 (개발 환경)

---

## 💡 해결 방안

### **Option A: Entrypoint 스크립트 (권장) ⭐⭐⭐⭐⭐**

**컨셉**:
- Docker 컨테이너 시작 시 엔트리포인트 스크립트 실행
- 스크립트에서 Alembic 마이그레이션 자동 실행
- 마이그레이션 후 Uvicorn 시작

**장점**:
✅ Docker 표준 패턴  
✅ DB 초기화와 애플리케이션 시작 분리  
✅ 마이그레이션 실패 시 에러 로그 명확  
✅ 프로덕션/개발 환경 분리 가능  

**구현**:
1. `docker/backend/entrypoint.sh` 생성
2. Dockerfile에서 ENTRYPOINT 설정
3. Alembic 자동 실행 후 Uvicorn 시작

---

### **Option B: Lifespan에서 마이그레이션 (간단)**

**컨셉**:
- FastAPI `lifespan` 이벤트에서 Alembic 실행
- 애플리케이션 코드 내에서 마이그레이션 관리

**장점**:
✅ 코드만으로 해결 (스크립트 불필요)  
✅ 구현 간단  

**단점**:
❌ DB 마이그레이션과 애플리케이션 로직 혼재  
❌ 마이그레이션 실패 시 앱 시작 안 될 수 있음  
❌ 프로덕션 환경에서 권장되지 않음  

---

## 📝 구현 계획 (Option A)

### Phase 1: Entrypoint 스크립트 생성

#### 1.1 파일 생성
```bash
# docker/backend/entrypoint.sh
#!/bin/bash
set -e

echo "=========================================="
echo "MoriAI Backend - Starting Initialization"
echo "=========================================="

# 1. PostgreSQL 연결 대기
echo "⏳ Waiting for PostgreSQL..."
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "postgres" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' 2>/dev/null; do
  echo "   PostgreSQL is unavailable - sleeping"
  sleep 2
done
echo "✓ PostgreSQL is ready"

# 2. Alembic 마이그레이션 실행
echo "🔄 Running database migrations..."
cd /app/backend

if alembic upgrade head; then
  echo "✓ Database migrations completed successfully"
else
  echo "⚠ Database migrations failed, but continuing..."
fi

# 3. Uvicorn 시작
echo "🚀 Starting Uvicorn server..."
echo "=========================================="
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 1.2 실행 권한 설정
```bash
chmod +x docker/backend/entrypoint.sh
```

---

### Phase 2: Dockerfile 수정

#### 2.1 Entrypoint 추가
```dockerfile
# Dockerfile 수정
# Copy entrypoint script
COPY docker/backend/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
```

#### 2.2 CMD 제거
```dockerfile
# 기존 CMD 제거 (entrypoint에서 처리)
# CMD ["uvicorn", "backend.main:app", ...]
```

---

### Phase 3: lifespan 수정

#### 3.1 중복 로직 제거
```python
# backend/main.py

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("=" * 60)
    print(f"{settings.app_title} Starting...")
    print("=" * 60)

    # 데이터베이스 연결 확인만 (테이블 생성 제거)
    try:
        async with engine.begin() as conn:
            # 연결 확인
            await conn.execute(text("SELECT 1"))
            print("✓ Database connection verified")
    except Exception as e:
        print(f"⚠ Database connection failed: {e}")
    
    # ... 나머지 로직 ...
```

**변경 사항**:
- ❌ 제거: `Base.metadata.create_all` (Alembic으로 대체)
- ✅ 추가: DB 연결 확인만

---

### Phase 4: docker-compose.yml 확인

#### 4.1 환경 변수 전달
```yaml
backend:
  environment:
    - POSTGRES_USER=${POSTGRES_USER:-moriai_user}
    - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-moriai_password}
    - POSTGRES_DB=${POSTGRES_DB:-moriai_db}
```

**이유**: Entrypoint에서 psql 연결 시 필요

---

## 🔍 동작 흐름

### 컨테이너 시작 순서
```
1. docker-compose up
   ↓
2. PostgreSQL 컨테이너 시작 (healthcheck 대기)
   ↓
3. Backend 컨테이너 시작
   ↓
4. entrypoint.sh 실행
   ↓
5. PostgreSQL 연결 대기 (until 루프)
   ↓
6. alembic upgrade head 실행
   ├─ 테이블 없음 → 모든 마이그레이션 실행 (001~008)
   └─ 테이블 있음 → 최신 버전으로 업그레이드
   ↓
7. 마이그레이션 완료
   ↓
8. uvicorn 시작
   ↓
9. FastAPI lifespan 실행 (캐시, 이벤트 버스 초기화)
   ↓
10. ✓ 백엔드 준비 완료
```

---

## ✅ 검증 시나리오

### Scenario 1: 빈 DB에서 시작
```bash
# 1. DB 초기화
docker-compose down -v  # 볼륨 삭제

# 2. 컨테이너 시작
docker-compose up -d

# 3. 로그 확인
docker-compose logs backend | grep -E "(migration|table|alembic)"

# 기대 결과:
# ✓ Running database migrations...
# ✓ Database migrations completed successfully
# ✓ Tables: users, books, pages, dialogues, voices, ...
```

### Scenario 2: 기존 테이블 있음
```bash
# 1. 컨테이너 재시작
docker-compose restart backend

# 2. 로그 확인
docker-compose logs backend | tail -20

# 기대 결과:
# ✓ Database migrations completed successfully (already up to date)
# ✓ Backend started
```

### Scenario 3: 마이그레이션 실패
```bash
# 1. 마이그레이션 파일 오류 발생 (의도적)

# 2. 컨테이너 시작
docker-compose up -d

# 3. 로그 확인
docker-compose logs backend

# 기대 결과:
# ⚠ Database migrations failed, but continuing...
# 🚀 Starting Uvicorn server...  ← 앱은 시작됨
```

---

## 📊 장단점 비교

### Option A: Entrypoint 스크립트 (채택)

**장점**:
✅ DB 초기화와 앱 시작 명확히 분리  
✅ 마이그레이션 로그 명확  
✅ Docker 표준 패턴  
✅ 프로덕션 환경에 적합  
✅ 실패 시 처리 유연  

**단점**:
❌ 파일 추가 필요 (entrypoint.sh)  
❌ 스크립트 작성 필요  

---

### Option B: Lifespan 마이그레이션 (미채택)

**장점**:
✅ 코드만으로 해결  
✅ 구현 간단  

**단점**:
❌ 프로덕션 환경 비권장  
❌ 로직 혼재  
❌ 에러 처리 복잡  

---

## 🚀 실행 계획

### 단계별 구현

1. **Phase 1**: Entrypoint 스크립트 생성 (`docker/backend/entrypoint.sh`)
2. **Phase 2**: Dockerfile 수정 (ENTRYPOINT 추가)
3. **Phase 3**: lifespan 수정 (테이블 생성 로직 제거)
4. **Phase 4**: docker-compose.yml 환경 변수 추가
5. **Phase 5**: 테스트 및 검증
6. **Phase 6**: 스테이징 및 문서화

---

## 📝 예상 변경 파일

1. `docker/backend/entrypoint.sh` (신규)
2. `docker/backend/Dockerfile` (수정)
3. `backend/main.py` (수정)
4. `docker-compose.yml` (수정)

---

## 💡 추가 개선 사항

### 1. 초기 데이터 Seeding (선택)
```bash
# entrypoint.sh에 추가
if [ "$APP_ENV" = "dev" ]; then
  echo "🌱 Seeding initial data..."
  python3 -m backend.scripts.seed_data
fi
```

### 2. 마이그레이션 상태 확인
```bash
# 현재 마이그레이션 버전 출력
alembic current
```

### 3. 롤백 지원
```bash
# 환경 변수로 롤백 가능
if [ "$MIGRATION_ROLLBACK" = "true" ]; then
  alembic downgrade -1
fi
```

---

## 🎯 요약

**선택한 방안**: Option A (Entrypoint 스크립트)

**핵심 기능**:
1. ✅ 컨테이너 시작 시 자동 마이그레이션
2. ✅ 테이블 없으면 생성, 있으면 패스
3. ✅ 최신 스키마로 항상 시작
4. ✅ 실패해도 앱 시작 (개발 환경)

**예상 소요 시간**: 1시간 이내

**다음 단계**: 구현 진행할까요? 🚀

