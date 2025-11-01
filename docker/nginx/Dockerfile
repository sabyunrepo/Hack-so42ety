# Nginx Dockerfile - Production (Cloudflare Tunnel - HTTP Only)
FROM nginx:alpine

# Copy production nginx configuration (HTTP only, no SSL)
COPY docker/nginx/nginx.conf.prod /etc/nginx/conf.d/default.conf

EXPOSE 80

# Use default nginx entrypoint
CMD ["nginx", "-g", "daemon off;"]
