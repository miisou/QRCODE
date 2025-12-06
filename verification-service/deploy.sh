#!/bin/bash
set -e

# Usage: ./deploy.sh [DOCKER_HUB_USERNAME]

if [ -z "$1" ]; then
    echo "Usage: ./deploy.sh [DOCKER_HUB_USERNAME]"
    exit 1
fi

DOCKER_USER=$1
IMAGE_NAME="bebra-verifier"
TAG="latest" # Or use git commit hash: $(git rev-parse --short HEAD)

echo "--- Building Docker Image ---"
docker build -t $IMAGE_NAME .

echo "--- Testing Image ---"
# Run container in background (using port 8002 to avoid conflicts with running app or compose)
CONTAINER_ID=$(docker run -d -p 8002:8000 --env REDIS_HOST=host.docker.internal $IMAGE_NAME)

# Wait for startup
echo "Waiting for service to start..."
sleep 5

# Check health (using docs endpoint as simple check)
if curl --fail http://localhost:8002/docs > /dev/null; then
    echo "✅ Service is up and running!"
else
    echo "❌ Service failed to start or respond."
    docker logs $CONTAINER_ID
    docker stop $CONTAINER_ID
    exit 1
fi

# Cleanup test container
docker stop $CONTAINER_ID
docker rm $CONTAINER_ID

echo "--- Tagging and Pushing to Docker Hub ---"
# Generate timestamp tag (YYYYMMDD-HHMMSS format)
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
TIMESTAMP_TAG="$DOCKER_USER/$IMAGE_NAME:$TIMESTAMP"
LATEST_TAG="$DOCKER_USER/$IMAGE_NAME:latest"

# Tag with both timestamp and latest
docker tag $IMAGE_NAME $TIMESTAMP_TAG
docker tag $IMAGE_NAME $LATEST_TAG

# Push both tags
echo "Pushing timestamped version: $TIMESTAMP_TAG"
docker push $TIMESTAMP_TAG

echo "Pushing latest version: $LATEST_TAG"
docker push $LATEST_TAG

echo "--- Deployment Complete ---"
echo "✅ Timestamped image: $TIMESTAMP_TAG"
echo "✅ Latest image: $LATEST_TAG"
echo ""
echo "📋 To deploy on Render, use this Image URL:"
echo "   docker.io/$DOCKER_USER/$IMAGE_NAME:$TIMESTAMP"
