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

# 만약 APP_ENV 가 설정되어 있고 dev라면 테스트 DB 생성
if [ "$APP_ENV" = "dev" ]; then
  echo "🔧 Creating test database & user (if not exists)..."
  DEFAULT_DB="postgres"

  PGPASSWORD=$POSTGRES_PASSWORD psql -h postgres -U "$POSTGRES_USER" -d $DEFAULT_DB -tc \
    "SELECT 1 FROM pg_roles WHERE rolname='test_user';" | grep -q 1 || \
    PGPASSWORD=$POSTGRES_PASSWORD psql -h postgres -U "$POSTGRES_USER" -d $DEFAULT_DB -c \
      "CREATE USER test_user WITH PASSWORD 'test_password';"

  PGPASSWORD=$POSTGRES_PASSWORD psql -h postgres -U "$POSTGRES_USER" -d $DEFAULT_DB -tc \
    "SELECT 1 FROM pg_database WHERE datname='test_db';" | grep -q 1 || \
    PGPASSWORD=$POSTGRES_PASSWORD psql -h postgres -U "$POSTGRES_USER" -d $DEFAULT_DB -c \
      "CREATE DATABASE test_db OWNER test_user;"

  echo "✓ Test DB ready"
else
  echo "ℹ️ Skipping test database setup (ENABLE_TEST_DB not true)"
fi

# 2. Alembic 마이그레이션 실행
echo "🔄 Running database migrations..."
cd /app/backend

if alembic upgrade head; then
  echo "✓ Database migrations completed successfully"
else
  echo "⚠ Database migrations failed, but continuing..."
  echo "   You may need to run migrations manually: docker-compose exec backend alembic upgrade head"
fi

# 3. 현재 마이그레이션 버전 출력
echo ""
echo "📊 Current migration status:"
alembic current 2>/dev/null || echo "   (Unable to determine current revision)"

# 4. Uvicorn 시작
echo ""
echo "🚀 Starting Uvicorn server..."
echo "=========================================="
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

