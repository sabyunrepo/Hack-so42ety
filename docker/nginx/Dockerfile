# Nginx Dockerfile - Static File Hosting with HTTPS
FROM nginx:alpine

# Install OpenSSL (already included in alpine, but explicit for clarity)
RUN apk add --no-cache openssl

# Copy entrypoint script
COPY docker/nginx/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Copy nginx configuration template
COPY docker/nginx/nginx.conf.template /etc/nginx/templates/default.conf.template

EXPOSE 80 443

# nginx 공식 이미지는 /etc/nginx/templates/*.template 파일을
# 자동으로 envsubst 처리하여 /etc/nginx/conf.d/에 생성
# entrypoint에서 SSL 인증서 생성 후 nginx 실행
ENTRYPOINT ["/entrypoint.sh"]
