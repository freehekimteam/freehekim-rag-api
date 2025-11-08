#!/usr/bin/env bash
set -euo pipefail
curl -fsS http://127.0.0.1:8080/health
curl -fsS -X POST -H 'Content-Type: application/json' \
  -d '{"q":"test"}' http://127.0.0.1:8080/rag/query
