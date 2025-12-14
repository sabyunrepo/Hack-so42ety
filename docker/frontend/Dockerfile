# ==================== Multi-Stage Build (Optimized) ====================
# Frontend 빌드만 담당 (nginx는 별도 컨테이너에서 실행)

# Stage 1: Dependencies (캐시 최적화)
FROM node:20-alpine AS dependencies

WORKDIR /app

# package.json만 먼저 복사 (레이어 캐싱)
COPY frontend/package*.json ./

# 모든 의존성 설치 (devDependencies 포함 - vite, rollup 등 빌드 도구 필요)
RUN npm ci --ignore-scripts && \
    npm cache clean --force

# ==================== Stage 2: Builder ====================
FROM node:20-alpine AS builder

WORKDIR /app

# Dependencies 복사
COPY --from=dependencies /app/node_modules ./node_modules

# 소스 코드 복사
COPY frontend/ .

# Production 빌드
ENV NODE_ENV=production
RUN npm run build && \
    # 빌드 결과물 검증
    ls -lah /app/dist

# ==================== Stage 3: Production (Nginx Serving) ====================
FROM nginx:alpine AS production

# Build argument for environment (default: prod)
ARG APP_ENV=prod

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf /etc/nginx/nginx.conf

# Copy environment-specific nginx configuration
COPY docker/frontend/nginx/nginx.${APP_ENV}.conf /etc/nginx/nginx.conf

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
