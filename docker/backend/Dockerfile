# ==================== Multi-Stage Build (Optimized) ====================

# Stage 1: Builder (빌드 도구 포함)
FROM python:3.12-slim AS builder

# ARM64 크로스 컴파일 최적화
ARG TARGETPLATFORM
ARG BUILDPLATFORM

WORKDIR /app

# 빌드 전용 시스템 패키지 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Production 의존성만 설치
COPY backend/requirements-prod.txt ./requirements-prod.txt
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements-prod.txt

# ==================== Stage 2: Runtime (최소 이미지) ====================
FROM python:3.12-slim AS runtime

WORKDIR /app

# Runtime 필수 패키지만 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    libpq5 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 및 실행 파일 복사 (빌드 도구 제외)
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Non-root 사용자 생성
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app

# 애플리케이션 코드 복사 (기존 구조에 맞춤)
COPY --chown=appuser:appuser backend/ /app/backend/
COPY --chown=appuser:appuser docker/backend/entrypoint.sh /app/entrypoint.sh

# 불필요한 파일 제거로 이미지 크기 감소
RUN find /usr/local/lib/python3.12/site-packages -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.12/site-packages -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.12/site-packages -name "*.pyc" -delete && \
    find /usr/local/lib/python3.12/site-packages -name "*.pyo" -delete

# 실행 권한 설정
RUN chmod +x /app/entrypoint.sh

# Non-root 사용자로 전환
USER appuser

# 환경 변수 설정
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 포트 노출
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8000/health || exit 1

# Entrypoint 설정
ENTRYPOINT ["/app/entrypoint.sh"]
