#!/usr/bin/env bash
set -euo pipefail

# User-space Qdrant backup via Docker (no root required)
# Output: ~/backups/qdrant/qdrant-YYYYmmdd-HHMM.tgz

BACKUP_DIR="$HOME/backups/qdrant"
mkdir -p "$BACKUP_DIR"
TS=$(date +%Y%m%d-%H%M)
OUT="$BACKUP_DIR/qdrant-$TS.tgz"

if ! /usr/bin/docker ps --format '{{.Names}}' | grep -q '^docker-qdrant-1$'; then
  echo "qdrant container not running; aborting" >&2
  exit 1
fi

echo "Creating backup: $OUT"
/usr/bin/docker exec docker-qdrant-1 sh -c 'tar czf - /qdrant/storage' > "$OUT"

echo "Backup completed: $OUT"

# Retention: keep 7 days
find "$BACKUP_DIR" -type f -name 'qdrant-*.tgz' -mtime +7 -print -delete || true

