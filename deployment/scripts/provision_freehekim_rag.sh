#!/usr/bin/env bash
set -euo pipefail

# Provision FreeHekim RAG on a Linux host
# - Ensures Docker/Compose
# - Creates required directories
# - Installs systemd units using templates in deployment/systemd
# - Prepares an environment file at ~/.config/freehekim-rag/.env (if absent)
#
# Usage:
#   sudo bash deployment/scripts/provision_freehekim_rag.sh [--workdir /path/to/repo]
#

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  echo "Please run as root (sudo)." >&2
  exit 1
fi

WORKDIR_OVERRIDE=""
ENV_FILE_OVERRIDE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --workdir)
      WORKDIR_OVERRIDE="$2"; shift 2;;
    --env-file)
      ENV_FILE_OVERRIDE="$2"; shift 2;;
    *) echo "Unknown argument: $1"; exit 2;;
  esac
done

# Detect invoking user (target unprivileged user)
TARGET_USER="${SUDO_USER:-$(logname 2>/dev/null || echo ${USER})}"
TARGET_HOME="$(eval echo ~"$TARGET_USER")"

# Derive repo directory (default: the git toplevel if available, else caller override)
if [ -n "$WORKDIR_OVERRIDE" ]; then
  REPO_DIR="$WORKDIR_OVERRIDE"
elif git -C "$PWD" rev-parse --show-toplevel >/dev/null 2>&1; then
  REPO_DIR="$(git -C "$PWD" rev-parse --show-toplevel)"
else
  echo "--workdir is required when not running inside the repo." >&2
  exit 2
fi

echo "[+] Target user       : $TARGET_USER"
echo "[+] Target home       : $TARGET_HOME"
echo "[+] Repository dir    : $REPO_DIR"

# 1) Ensure Docker Engine + Compose
if ! command -v docker >/dev/null 2>&1; then
  echo "[+] Installing Docker Engine"
  if command -v apt-get >/dev/null 2>&1; then
    apt-get update -y
    apt-get install -y ca-certificates curl gnupg lsb-release
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/$(. /etc/os-release; echo "$ID")/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$(. /etc/os-release; echo "$ID") \
      $(. /etc/os-release; echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list
    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    systemctl enable --now docker
  else
    echo "Please install Docker and docker compose manually for your distro." >&2
    exit 3
  fi
fi

echo "[+] Ensuring user '$TARGET_USER' is in 'docker' group"
groupadd -f docker
usermod -aG docker "$TARGET_USER" || true

# 2) Directories and ENV file (secure path preferred under /etc)
SECURE_ENV_DIR="/etc/freehekim-rag"
if [ -n "$ENV_FILE_OVERRIDE" ]; then
  ENV_FILE="$ENV_FILE_OVERRIDE"
else
  ENV_FILE="$SECURE_ENV_DIR/.env"
fi

echo "[+] Preparing secure env file at: $ENV_FILE"
# Create secure group for env file if present (best-effort)
if ! getent group ragsvc >/dev/null 2>&1; then
  groupadd ragsvc || true
fi

install -d -m 0750 -o root -g ragsvc "$(dirname "$ENV_FILE")"
if [ ! -f "$ENV_FILE" ]; then
  # Copy template with restrictive permissions; owners root:ragsvc
  install -m 0640 -o root -g ragsvc "$REPO_DIR/.env.example" "$ENV_FILE"
fi

echo "[+] Ensuring Qdrant data dir /srv/qdrant exists"
mkdir -p /srv/qdrant
chown -R "$TARGET_USER":"docker" /srv/qdrant || chown -R "$TARGET_USER":"$TARGET_USER" /srv/qdrant || true

# 3) Install systemd units from templates
SYSTEMD_DIR_TPL="$REPO_DIR/deployment/systemd"
if [ ! -d "$SYSTEMD_DIR_TPL" ]; then
  echo "Systemd templates not found at $SYSTEMD_DIR_TPL" >&2
  exit 4
fi

echo "[+] Installing systemd units"
WORKDIR_ESC="$(printf '%s' "$REPO_DIR" | sed -e 's/[\/&]/\\&/g')"
USER_ESC="$(printf '%s' "$TARGET_USER" | sed -e 's/[\/&]/\\&/g')"
ENV_ESC="$(printf '%s' "$ENV_FILE" | sed -e 's/[\/&]/\\&/g')"

for unit in freehekim-rag.service freehekim-rag-health-monitor.service freehekim-rag-health-monitor.timer freehekim-rag-backup.service freehekim-rag-backup.timer; do
  src="$SYSTEMD_DIR_TPL/$unit"
  dst="/etc/systemd/system/$unit"
  if [ -f "$src" ]; then
    echo "  - $unit"
    sed -e "s/%USER%/$USER_ESC/g" \
        -e "s|%WORKDIR%|$WORKDIR_ESC|g" \
        -e "s|%ENV_FILE%|$ENV_ESC|g" \
        "$src" > "$dst"
  fi
done

echo "[+] Reloading systemd and enabling services"
systemctl daemon-reload
systemctl enable freehekim-rag.service
systemctl enable freehekim-rag-health-monitor.timer || true
systemctl enable freehekim-rag-backup.timer || true

# 4) Ensure deployment scripts are executable for manual runs
echo "[+] Ensuring deployment scripts are executable"
chmod +x "$REPO_DIR"/deployment/scripts/*.sh || true

echo "[+] You can start services now:"
echo "    systemctl start freehekim-rag.service"
echo "    systemctl start freehekim-rag-health-monitor.timer  # optional"
echo "    systemctl start freehekim-rag-backup.timer          # optional"
echo "[✓] Provisioning complete. Remember to edit $ENV_FILE"
