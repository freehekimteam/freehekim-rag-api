#!/usr/bin/env bash
set -euo pipefail

# FreeHekim RAG API – Restore helper (from backup .env)
# Usage: tools/restore_local_secrets.sh secrets/backup.freehekim-rag-api.<stamp>.env [--write-files]

SRC_FILE="${1:-}"
WRITE_FILES="${2:-}"
if [ -z "${SRC_FILE}" ] || [ ! -f "${SRC_FILE}" ]; then
  echo "Usage: $0 <backup.env> [--write-files]" >&2
  exit 1
fi

# shellcheck disable=SC1090
set -a; . "$SRC_FILE"; set +a

restore_b64() {
  local var="$1"; shift
  local path="$1"; shift
  local val="${!var-}"
  [ -n "$val" ] || return 0
  if [ "${WRITE_FILES:-}" = "--write-files" ]; then
    mkdir -p "$(dirname "$path")"
    printf "%s" "$val" | base64 -d > "$path"
    echo "Restored $path"
  else
    echo "Would restore: $path"
  fi
}

# Examples (adjust as needed)
restore_b64 GH_HOSTS_YML_B64 "$HOME/.config/gh/hosts.yml"
restore_b64 NPMRC_B64 "$HOME/.npmrc"
restore_b64 DOCKER_CONFIG_JSON_B64 "$HOME/.docker/config.json"
restore_b64 AWS_CREDENTIALS_B64 "$HOME/.aws/credentials"
restore_b64 AWS_CONFIG_B64 "$HOME/.aws/config"
restore_b64 CLOUDFLARE_TUNNEL_JSON_B64 "$HOME/.cloudflared/cert.json"
restore_b64 CLOUDFLARE_CONFIG_YML_B64 "$HOME/.cloudflared/config.yml"
restore_b64 HAKANCLOUD_ENV_B64 "$HOME/.hakancloud/.env"

echo "Done."

