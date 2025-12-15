#!/bin/bash

# Configuration
CONFIG_FILE="backend/core/config.py"

# Check if file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: $CONFIG_FILE not found!"
    exit 1
fi

# Extract current version
CURRENT_VERSION=$(grep 'app_version: str =' "$CONFIG_FILE" | sed -E 's/.*"([0-9]+\.[0-9]+\.[0-9]+)".*/\1/')

if [ -z "$CURRENT_VERSION" ]; then
    echo "Error: Could not find version in $CONFIG_FILE"
    exit 1
fi

echo "Current version: $CURRENT_VERSION"

# Split version into array
IFS='.' read -r -a VERSION_PARTS <<< "$CURRENT_VERSION"

# Increment patch version
NEW_PATCH=$((VERSION_PARTS[2] + 1))
NEW_VERSION="${VERSION_PARTS[0]}.${VERSION_PARTS[1]}.$NEW_PATCH"

echo "New version: $NEW_VERSION"

# Update file (cross-platform compatible sed)
# backend/core/config.py format is: app_version: str = "2.0.0"
escaped_current="${CURRENT_VERSION//./\\.}"
escaped_new="${NEW_VERSION//./\\.}"

sed -i.bak "s/app_version: str = \"$escaped_current\"/app_version: str = \"$escaped_new\"/" "$CONFIG_FILE"
rm "${CONFIG_FILE}.bak"

echo "Updated $CONFIG_FILE to version $NEW_VERSION"

# Also update package.json if it exists (optional but good for consistency)
PACKAGE_JSON="frontend/package.json"
if [ -f "$PACKAGE_JSON" ]; then
    # Simple sed for package.json (assuming "version": "0.0.0" format)
    # Using a slightly loose regex to match standard json format
    sed -i.bak -E "s/\"version\": \"[0-9]+\.[0-9]+\.[0-9]+\"/\"version\": \"$NEW_VERSION\"/" "$PACKAGE_JSON"
    rm "${PACKAGE_JSON}.bak"
    echo "Updated $PACKAGE_JSON to version $NEW_VERSION"
fi
