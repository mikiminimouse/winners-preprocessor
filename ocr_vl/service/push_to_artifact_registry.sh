#!/bin/bash
set -e

echo "======================================"
echo "Push PaddleOCR-VL Service to Artifact Registry"
echo "======================================"

# Проверка переменных окружения
if [ -z "$REGISTRY_ENDPOINT" ]; then
    echo "❌ Error: REGISTRY_ENDPOINT environment variable is not set"
    echo "   Example: export REGISTRY_ENDPOINT=registry-xxxxx.cr.cloud.ru"
    exit 1
fi

if [ -z "$KEY_ID" ]; then
    echo "❌ Error: KEY_ID environment variable is not set"
    echo "   Get it from Cloud.ru Artifact Registry → Access Keys"
    exit 1
fi

if [ -z "$KEY_SECRET" ]; then
    echo "❌ Error: KEY_SECRET environment variable is not set"
    echo "   Get it from Cloud.ru Artifact Registry → Access Keys"
    exit 1
fi

IMAGE_NAME="paddleocr-vl-service"
VERSION="${VERSION:-1.0.0}"
FULL_IMAGE_LATEST="$REGISTRY_ENDPOINT/$IMAGE_NAME:latest"
FULL_IMAGE_VERSION="$REGISTRY_ENDPOINT/$IMAGE_NAME:$VERSION"

echo ""
echo "Configuration:"
echo "  Registry: $REGISTRY_ENDPOINT"
echo "  Image: $IMAGE_NAME"
echo "  Version: $VERSION"
echo "  Tags:"
echo "    - $FULL_IMAGE_LATEST"
echo "    - $FULL_IMAGE_VERSION"
echo ""

# Проверка существования локального образа
if ! docker images | grep -q "^${IMAGE_NAME}.*latest"; then
    echo "❌ Error: Local image $IMAGE_NAME:latest not found"
    echo "   Build it first: docker build -t $IMAGE_NAME:latest ."
    exit 1
fi

# Аутентификация в Artifact Registry
echo "Authenticating to Artifact Registry..."
echo "$KEY_SECRET" | docker login $REGISTRY_ENDPOINT -u $KEY_ID --password-stdin

if [ $? -ne 0 ]; then
    echo "❌ Authentication failed"
    exit 1
fi

echo "✅ Authentication successful"
echo ""

# Тегирование образа
echo "Tagging images..."
docker tag $IMAGE_NAME:latest $FULL_IMAGE_LATEST
docker tag $IMAGE_NAME:latest $FULL_IMAGE_VERSION

echo "✅ Images tagged"
echo ""

# Push образа (latest)
echo "Pushing $FULL_IMAGE_LATEST..."
echo "  Size: ~18GB, this may take 10-30 minutes..."
docker push $FULL_IMAGE_LATEST

if [ $? -eq 0 ]; then
    echo "✅ $FULL_IMAGE_LATEST pushed successfully"
else
    echo "❌ Push failed for $FULL_IMAGE_LATEST"
    exit 1
fi

echo ""

# Push образа (versioned)
echo "Pushing $FULL_IMAGE_VERSION..."
docker push $FULL_IMAGE_VERSION

if [ $? -eq 0 ]; then
    echo "✅ $FULL_IMAGE_VERSION pushed successfully"
else
    echo "❌ Push failed for $FULL_IMAGE_VERSION"
    exit 1
fi

echo ""
echo "======================================"
echo "✅ Successfully pushed to Artifact Registry"
echo "======================================"
echo ""
echo "Image available at:"
echo "  - $FULL_IMAGE_LATEST"
echo "  - $FULL_IMAGE_VERSION"
echo ""
echo "Use this image URL in ML Inference:"
echo "  $FULL_IMAGE_LATEST"
echo ""

