FROM nginx:1.25-alpine

# Build argument for environment (default: dev)
ARG APP_ENV=dev

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf /etc/nginx/nginx.conf

# Copy environment-specific nginx configuration
COPY docker/nginx/conf.d/nginx.${APP_ENV}.conf /etc/nginx/nginx.conf

# Create cache directory and set permissions
RUN mkdir -p /var/cache/nginx && \
    chown -R nginx:nginx /var/cache/nginx /var/log/nginx

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
