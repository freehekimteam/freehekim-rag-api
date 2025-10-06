#!/usr/bin/env bash
set -euo pipefail
cd ~/hakancloud
docker compose -f docker/docker-compose.server.yml pull
docker compose -f docker/docker-compose.server.yml up -d
curl -fsS http://127.0.0.1:8080/health || (echo "Health failed" && exit 1)
