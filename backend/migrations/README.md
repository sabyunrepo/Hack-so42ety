# Database Migrations (Alembic)

이 디렉토리는 Alembic을 사용한 데이터베이스 마이그레이션 파일을 포함합니다.

## 사용법

### 새로운 마이그레이션 생성

```bash
# 자동 생성 (모델 변경 감지)
alembic revision --autogenerate -m "migration message"

# 수동 생성
alembic revision -m "migration message"
```

### 마이그레이션 적용

```bash
# 최신 버전으로 업그레이드
alembic upgrade head

# 특정 버전으로 업그레이드
alembic upgrade <revision_id>

# 한 단계 업그레이드
alembic upgrade +1
```

### 마이그레이션 롤백

```bash
# 한 단계 다운그레이드
alembic downgrade -1

# 특정 버전으로 다운그레이드
alembic downgrade <revision_id>

# 모두 롤백
alembic downgrade base
```

### 마이그레이션 히스토리 확인

```bash
# 현재 버전 확인
alembic current

# 마이그레이션 히스토리 보기
alembic history

# 상세 히스토리
alembic history --verbose
```

## Docker 환경에서 사용

```bash
# 컨테이너 내부에서 마이그레이션 실행
docker-compose exec backend alembic upgrade head

# 또는 Makefile 사용
make db-migrate
```

## 주의사항

- **자동 생성 후 반드시 검토**: `--autogenerate`는 완벽하지 않으므로 생성된 마이그레이션 파일을 반드시 검토하세요.
- **프로덕션 백업**: 프로덕션 환경에서 마이그레이션 전 반드시 데이터베이스를 백업하세요.
- **테스트**: 개발/스테이징 환경에서 충분히 테스트한 후 프로덕션에 적용하세요.
