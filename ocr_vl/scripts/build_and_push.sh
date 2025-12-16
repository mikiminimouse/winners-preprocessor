#!/bin/bash
set -e

# Конфигурация
DOCKER_USERNAME="${DOCKER_USERNAME:-mikimoose}"
IMAGE_NAME="${DOCKER_USERNAME}/paddleocr-vl-service"
VERSION="${VERSION:-1.0.0}"
REGISTRY="${REGISTRY:-docker.io}"

# Определяем, используется ли Cloud.ru Artifact Registry или Docker Hub
if [ -n "$CLOUDRU_REGISTRY" ]; then
    FULL_IMAGE_NAME="${CLOUDRU_REGISTRY}/${IMAGE_NAME}"
    echo "Using Cloud.ru Artifact Registry: $CLOUDRU_REGISTRY"
else
    FULL_IMAGE_NAME="${IMAGE_NAME}"
    echo "Using Docker Hub"
fi

echo "======================================"
echo "Building PaddleOCR-VL Service"
echo "======================================"
echo "Image: $FULL_IMAGE_NAME:$VERSION"
echo "Platform: linux/amd64"
echo ""

# Проверка Docker
if ! docker info >/dev/null 2>&1; then
    echo "❌ Error: Docker is not running or not accessible"
    exit 1
fi

# Проверка наличия buildx
if docker buildx version >/dev/null 2>&1; then
    echo "Using docker buildx for multi-platform builds..."
    
    # Создаем builder если его нет
    if ! docker buildx ls | grep -q "paddleocr-builder"; then
        docker buildx create --name paddleocr-builder --use --bootstrap
    else
        docker buildx use paddleocr-builder
    fi
    
    # Сборка для linux/amd64 (требование Cloud.ru)
    echo ""
    echo "Building Docker image for linux/amd64..."
    docker buildx build \
      --platform linux/amd64 \
      --build-arg BUILDKIT_INLINE_CACHE=1 \
      -t $FULL_IMAGE_NAME:$VERSION \
      -t $FULL_IMAGE_NAME:latest \
      --load \
      .
else
    echo "Using standard docker build (buildx not available)..."
    echo ""
    echo "Building Docker image..."
    docker build \
      -t $FULL_IMAGE_NAME:$VERSION \
      -t $FULL_IMAGE_NAME:latest \
      .
fi

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Build successful!"
    echo ""
    echo "Image tags:"
    echo "  - $FULL_IMAGE_NAME:$VERSION"
    echo "  - $FULL_IMAGE_NAME:latest"
    echo ""
    
    # Опциональный push
    if [ "$PUSH_AFTER_BUILD" = "true" ] || [ "$1" = "--push" ]; then
        echo "Pushing images..."
        
        if [ -n "$CLOUDRU_REGISTRY" ]; then
            # Push в Cloud.ru Artifact Registry
            docker push $FULL_IMAGE_NAME:$VERSION
            docker push $FULL_IMAGE_NAME:latest
        else
            # Push в Docker Hub
            docker push $FULL_IMAGE_NAME:$VERSION
            docker push $FULL_IMAGE_NAME:latest
        fi
        
        if [ $? -eq 0 ]; then
            echo "✅ Push successful!"
        else
            echo "❌ Push failed!"
            exit 1
        fi
    else
        echo "To push images, run:"
        echo "  docker push $FULL_IMAGE_NAME:$VERSION"
        echo "  docker push $FULL_IMAGE_NAME:latest"
        echo ""
        echo "Or set PUSH_AFTER_BUILD=true or use --push flag"
    fi
else
    echo "❌ Build failed!"
    exit 1
fi

