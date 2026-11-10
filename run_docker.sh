#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

IMAGE_NAME="cherry-blossom-backend"
CONTAINER_NAME="cherry-blossom-backend"
HOST_PORT=8000
CONTAINER_PORT=7860

echo "Building image..."
docker build -t "$IMAGE_NAME" .

echo "Removing any existing container..."
docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

echo "Starting container..."
docker run -d \
  --name "$CONTAINER_NAME" \
  -p "$HOST_PORT:$CONTAINER_PORT" \
  --env-file backend/.env \
  -e OLLAMA_HOST=http://host.docker.internal:11434 \
  -v "$(pwd)/backend/ai_module/app/data:/app/backend/ai_module/app/data" \
  "$IMAGE_NAME"

echo "Running at http://localhost:$HOST_PORT (docs at /docs)"
echo "Tail logs with: docker logs -f $CONTAINER_NAME"
