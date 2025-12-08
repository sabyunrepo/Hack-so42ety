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

