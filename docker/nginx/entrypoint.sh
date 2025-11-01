#!/bin/sh
set -e

echo "📋 Processing nginx templates with envsubst..."

# envsubst로 환경변수 치환
if [ -f "/etc/nginx/templates/default.conf.template" ]; then
  envsubst '${TTS_API_PORT} ${STORYBOOK_API_PORT}' \
    < /etc/nginx/templates/default.conf.template \
    > /etc/nginx/conf.d/default.conf
  echo "✅ Template processed: /etc/nginx/conf.d/default.conf"
else
  echo "❌ Template not found!"
  exit 1
fi

echo "🚀 Starting nginx..."
exec nginx -g "daemon off;"
