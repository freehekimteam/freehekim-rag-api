#!/usr/bin/env bash
set -euo pipefail
SNAP_DIR=/srv/qdrant/backups
mkdir -p "$SNAP_DIR"
TS=$(date +%Y%m%d-%H%M)
rsync -a /srv/qdrant/ "$SNAP_DIR/$TS/"
find "$SNAP_DIR" -maxdepth 1 -type d -mtime +14 -exec rm -rf {} +
