#!/usr/bin/env bash
set -euo pipefail
SNAP_DIR=/var/lib/qdrant_data/backups
mkdir -p "$SNAP_DIR"
TS=$(date +%Y%m%d-%H%M)
rsync -a /var/lib/qdrant_data/ "$SNAP_DIR/$TS/"
find "$SNAP_DIR" -maxdepth 1 -type d -mtime +14 -exec rm -rf {} +
