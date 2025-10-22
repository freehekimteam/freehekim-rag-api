#!/usr/bin/env bash
set -euo pipefail

# FreeHekim RAG API – Local Secrets Backup
# Creates a single .env backup with tokens/keys and base64-encoded config files.
# Output is written to ./secrets and .gitignore already excludes it.

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
OUT_DIR="$ROOT_DIR/secrets"
mkdir -p "$OUT_DIR"
STAMP=$(date +%Y%m%d_%H%M%S)
OUT_FILE="$OUT_DIR/backup.freehekim-rag-api.$STAMP.env"

write_header() {
  {
    echo "# FreeHekim RAG API – Local Secrets Backup"
    echo "# Generated: $(date -Iseconds)"
    echo "# WARNING: Sensitive content. Do NOT commit."
    echo
  } >> "$OUT_FILE"
}

add_kv() {
  local k="$1"; shift
  local v="${1:-}"
  if [ -n "${v:-}" ]; then
    printf '%s=%s\n' "$k" "$v" >> "$OUT_FILE"
  fi
}

add_file_b64() {
  local var="$1"; shift
  local path="$1"; shift
  if [ -f "$path" ]; then
    # shellcheck disable=SC2002
    local b64
    if base64 --version >/dev/null 2>&1; then
      b64=$(base64 -w 0 < "$path")
    else
      b64=$(base64 < "$path" | tr -d '\n')
    fi
    printf '%s=%s\n' "$var" "$b64" >> "$OUT_FILE"
  fi
}

write_header

# 1) Environment variables (common names)
{
  echo "# ==== ENVIRONMENT VARIABLES ===="
} >> "$OUT_FILE"

VARS=(
  OPENAI_API_KEY QDRANT_API_KEY QDRANT_HOST QDRANT_PORT
  RAG_API_URL RAG_API_KEY EMBED_PROVIDER
  API_HOST API_PORT LOG_LEVEL LOG_JSON
  REQUIRE_API_KEY API_KEY UVICORN_WORKERS
  GH_TOKEN GITHUB_TOKEN NPM_TOKEN
  AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY
  CLOUDFLARE_API_TOKEN DOCKERHUB_USERNAME DOCKERHUB_TOKEN
)
for k in "${VARS[@]}"; do add_kv "$k" "${!k-}"; done

echo >> "$OUT_FILE"
echo "# ==== FILES (BASE64) ==== " >> "$OUT_FILE"

# 2) GitHub CLI hosts
add_file_b64 GH_HOSTS_YML_B64 "$HOME/.config/gh/hosts.yml"

# 3) NPM
add_file_b64 NPMRC_B64 "$HOME/.npmrc"

# 4) Docker config
add_file_b64 DOCKER_CONFIG_JSON_B64 "$HOME/.docker/config.json"

# 5) SSH private keys (id_*)
if [ -d "$HOME/.ssh" ]; then
  for f in "$HOME"/.ssh/id_*; do
    [ -f "$f" ] || continue
    case "$f" in *.pub) continue;; esac
    base=$(basename "$f")
    var="SSH_$(echo "$base" | tr '[:lower:].-' '[:upper:]__')_B64"
    add_file_b64 "$var" "$f"
  done
  add_file_b64 SSH_CONFIG_B64 "$HOME/.ssh/config"
  add_file_b64 SSH_KNOWN_HOSTS_B64 "$HOME/.ssh/known_hosts"
fi

# 6) AWS
add_file_b64 AWS_CREDENTIALS_B64 "$HOME/.aws/credentials"
add_file_b64 AWS_CONFIG_B64 "$HOME/.aws/config"

# 7) Cloudflare (cloudflared tunnel creds if exists)
add_file_b64 CLOUDFLARE_TUNNEL_JSON_B64 "$HOME/.cloudflared/cert.json"
add_file_b64 CLOUDFLARE_CONFIG_YML_B64 "$HOME/.cloudflared/config.yml"

# 8) Project/compose specific env
add_file_b64 HAKANCLOUD_ENV_B64 "$HOME/.hakancloud/.env"
add_file_b64 PROJECT_ENV_EXAMPLE_B64 "$ROOT_DIR/.env.example"

# 9) Infrastructure credentials (if present)
add_file_b64 CLOUDFLARE_CREDENTIALS_FILE_JSON_B64 "$ROOT_DIR/infrastructure/cloudflare/credentials-file.json"

# Footer
{
  echo
  echo "# Restore notes:"
  echo "# - *_B64 entries are base64-encoded file contents. To restore: echo \$VAR | base64 -d > <path>"
  echo "# - This file is sensitive. Store offline and never commit."
} >> "$OUT_FILE"

echo "Backup written to: $OUT_FILE"
