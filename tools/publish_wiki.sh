#!/usr/bin/env bash
set -euo pipefail

# Publish docs/wiki/* to GitHub Wiki: <repo>.wiki.git
# Requirements: git access to wiki repo

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"

ORIGIN_URL=$(git remote get-url origin)
WIKI_URL=${ORIGIN_URL%.git}.wiki.git

TMP_DIR="$ROOT_DIR/.wiki-publish"
SRC_DIR="$ROOT_DIR/docs/wiki"

echo "Origin: $ORIGIN_URL"
echo "Wiki:   $WIKI_URL"

rm -rf "$TMP_DIR"
git clone "$WIKI_URL" "$TMP_DIR"

rm -rf "${TMP_DIR:?}"/*
mkdir -p "$TMP_DIR"
cp -R "$SRC_DIR"/* "$TMP_DIR"/

cd "$TMP_DIR"
git add -A
if git diff --cached --quiet; then
  echo "No changes to publish."
  exit 0
fi
git commit -m "docs(wiki): sync from docs/wiki"
git push origin HEAD:master || git push origin HEAD:main || git push
echo "Wiki published successfully."
