#!/usr/bin/env bash
set -euo pipefail

# Compose helper for dev environment. Removes old backend container/image and starts fresh.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
ROOT_DIR="${SCRIPT_DIR}/.."
cd "${ROOT_DIR}"

COMPOSE_CMD=""
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
else
  echo "Error: neither 'docker compose' nor 'docker-compose' found. Please install Docker Compose plugin or docker-compose binary." >&2
  exit 1
fi

echo "Using compose command: ${COMPOSE_CMD}"

echo "Stopping existing containers (if any): backend, frontend, redis"
set -x
${COMPOSE_CMD} stop backend || true
${COMPOSE_CMD} stop frontend || true
${COMPOSE_CMD} stop redis || true
set +x

echo "Removing stale containers to avoid docker-compose bugs dealing with container.image_config values..."
set -x
${COMPOSE_CMD} rm -f backend || true
${COMPOSE_CMD} rm -f frontend || true
${COMPOSE_CMD} rm -f redis || true
set +x

echo "Removing backend image to ensure fresh image metadata (this preserves named volumes)."
set -x
docker image rm -f shipahoi_backend || true
set +x

echo "Building images"
set -x
${COMPOSE_CMD} build --no-cache
set +x

echo "Start services"
set -x
${COMPOSE_CMD} up -d
set +x

echo "All done. Use '${COMPOSE_CMD} logs -f' to follow logs, or '${COMPOSE_CMD} ps' to see running containers."
