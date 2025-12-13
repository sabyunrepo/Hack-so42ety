#!/bin/bash
set -e

# Configuration
VERSION_FILE="VERSION"

# Initialize VERSION file if it doesn't exist
if [ ! -f "$VERSION_FILE" ]; then
    echo "0.0.1" > "$VERSION_FILE"
fi

# Read current version
CURRENT_VERSION=$(cat "$VERSION_FILE")
IFS='.' read -r -a PARTS <<< "$CURRENT_VERSION"

# Increment patch version
NEW_PATCH=$((PARTS[2] + 1))
NEW_VERSION="${PARTS[0]}.${PARTS[1]}.$NEW_PATCH"

# Update VERSION file
echo "$NEW_VERSION" > "$VERSION_FILE"

echo "=========================================="
echo "🚀 Auto-incrementing version: $CURRENT_VERSION -> $NEW_VERSION"
echo "=========================================="

# Export variables for docker-compose
export IMAGE_TAG="$NEW_VERSION"
export COMMIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

echo "Building images with tags:"
echo "  - :$NEW_VERSION"
echo "  - :latest"
echo "  - :$COMMIT_SHA"

# Build with docker-compose
# We pass the version as an environment variable which docker-compose can use
# Note: You need to update docker-compose.yml to use ${IMAGE_TAG} if you want strict versioning there,
# or we can tag explicitly here after build. 
# For this verification step, we will use the environment variable approach.

docker-compose build

# Tagging images explicitly to ensure they exist (Docker Compose might only build 'latest' if configured that way)
# Assuming service names: backend, frontend
echo "🏷️  Applying tags..."
docker tag moriai-backend:latest moriai-backend:$NEW_VERSION
docker tag moriai-backend:latest moriai-backend:$COMMIT_SHA

docker tag moriai-frontend:dev moriai-frontend:$NEW_VERSION
docker tag moriai-frontend:dev moriai-frontend:$COMMIT_SHA

echo "=========================================="
echo "✅ Build complete! Version: $NEW_VERSION"
echo "=========================================="
