# ==================== Multi-Stage Build (Optimized) ====================
# Frontend 빌드만 담당 (nginx는 별도 컨테이너에서 실행)

# ==================== Stage 1: Builder ====================
FROM node:20-alpine AS builder

# ARM64 크로스 컴파일 최적화
ARG TARGETPLATFORM
ARG BUILDPLATFORM

WORKDIR /app

# package.json만 먼저 복사 (레이어 캐싱)
COPY frontend/package*.json ./

# 모든 의존성 설치 (devDependencies 포함)
# ARM64 빌드 시 안정성 향상을 위한 옵션 추가
RUN npm ci --prefer-offline --no-audit --legacy-peer-deps && \
    npm cache clean --force

# 소스 코드 복사
COPY frontend/ .

# Environment variables for build
ARG VITE_GOOGLE_CLIENT_ID
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ARG VITE_PUBLIC_POSTHOG_KEY
ENV VITE_PUBLIC_POSTHOG_KEY=$VITE_PUBLIC_POSTHOG_KEY
ARG VITE_PUBLIC_POSTHOG_HOST
ENV VITE_PUBLIC_POSTHOG_HOST=$VITE_PUBLIC_POSTHOG_HOST

# Production 빌드
# 빌드 결과물 검증
RUN npm run build && \
    ls -lah /app/dist

# ==================== Stage 3: Production (Nginx Serving) ====================
FROM nginx:alpine AS production

# Build argument for environment (default: prod)
ARG APP_ENV=prod

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf /etc/nginx/nginx.conf

# Copy environment-specific nginx configuration
COPY docker/frontend/nginx/conf.d/nginx.${APP_ENV}.conf /etc/nginx/nginx.conf

# Create cache directory and set permissions
RUN mkdir -p /var/cache/nginx && \
    chown -R nginx:nginx /var/cache/nginx /var/log/nginx

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=3s \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
