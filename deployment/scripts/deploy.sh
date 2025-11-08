#!/usr/bin/env bash
set -euo pipefail

# Deploy using the repo's server compose file
# Optional: REPO_DIR env to override autodetection

if [ -n "${REPO_DIR:-}" ]; then
  ROOT_DIR="$REPO_DIR"
else
  # Resolve repo root relative to this script
  ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fi

COMPOSE_YML="$ROOT_DIR/deployment/docker/docker-compose.server.yml"

echo "[+] Using compose file: $COMPOSE_YML"
docker compose -f "$COMPOSE_YML" pull || true
docker compose -f "$COMPOSE_YML" up -d
curl -fsS http://127.0.0.1:8080/health || (echo "Health failed" && exit 1)
