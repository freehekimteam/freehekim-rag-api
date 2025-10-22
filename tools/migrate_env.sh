#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)
SRC="$HOME/.hakancloud/.env"
DST="$REPO_ROOT/.env"
if [ -f "$DST" ]; then
  echo "Repo .env already exists: $DST"; exit 0
fi
if [ -f "$SRC" ]; then
  mkdir -p "$REPO_ROOT"
  cp "$SRC" "$DST"
  echo "Copied $SRC -> $DST"
else
  echo "Source $SRC not found; create $DST manually from .env.example"
fi
