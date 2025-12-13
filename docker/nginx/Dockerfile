# ==================== Optimized Nginx Dockerfile ====================
FROM nginx:alpine

# Build argument for environment (default: prod)
ARG APP_ENV=prod

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf /etc/nginx/nginx.conf

# Copy environment-specific nginx configuration
COPY docker/nginx/conf.d/nginx.${APP_ENV}.conf /etc/nginx/nginx.conf

# Create cache directory and set permissions
RUN mkdir -p /var/cache/nginx && \
    chown -R nginx:nginx /var/cache/nginx /var/log/nginx

EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=3s \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
