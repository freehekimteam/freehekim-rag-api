#!/usr/bin/env bash
# Provision FreeHekim RAG API as a system service with Docker Compose.
# - Installs code to /opt/freehekim-rag-api
# - Sets production env at /etc/freehekim-rag/.env
# - Moves Qdrant data to /srv/qdrant and updates compose override
# - Creates/Enables systemd unit freehekim-rag.service

set -euo pipefail

REPO_SRC="${REPO_SRC:-/home/freehekim/freehekim-rag-api}"
INSTALL_DIR="/opt/freehekim-rag-api"
ENV_DIR="/etc/freehekim-rag"
ENV_FILE="$ENV_DIR/.env"
STATE_DIR="/var/lib/freehekim-rag"
SYSTEMD_UNIT="/etc/systemd/system/freehekim-rag.service"
QDRANT_OLD="/var/lib/qdrant_data"
QDRANT_NEW="/srv/qdrant"
OVERRIDE_FILE="$INSTALL_DIR/deployment/docker/docker-compose.local.yml"
DOCKER_DAEMON_JSON_SRC="$REPO_SRC/deployment/docker/daemon.json"
DOCKER_DAEMON_JSON_DST="/etc/docker/daemon.json"
PROM_DIR="/home/freehekim/data/prometheus"
GRAFANA_DIR="/home/freehekim/data/grafana"

need_root() {
  if [ "${EUID:-$(id -u)}" -ne 0 ]; then
    echo "[ERROR] Please run as root: sudo $0" >&2
    exit 1
  fi
}

ensure_user_and_groups() {
  echo "[INFO] Ensuring system user 'ragsvc' and docker group".
  if ! id -u ragsvc >/dev/null 2>&1; then
    useradd --system --home-dir /nonexistent --shell /usr/sbin/nologin ragsvc
  fi
  if ! getent group docker >/dev/null 2>&1; then
    groupadd docker
  fi
  usermod -aG docker ragsvc || true
}

prepare_dirs() {
  echo "[INFO] Creating directories: $INSTALL_DIR, $ENV_DIR, $QDRANT_NEW, $STATE_DIR"
  mkdir -p "$INSTALL_DIR" "$ENV_DIR" "$QDRANT_NEW" "$STATE_DIR"
  chown -R root:root "$INSTALL_DIR"
  chown -R root:ragsvc "$ENV_DIR"
  chmod 0755 "$INSTALL_DIR"
  chmod 0750 "$ENV_DIR"
  chown -R root:docker "$QDRANT_NEW"
  chmod -R 0775 "$QDRANT_NEW"
  chown -R ragsvc:docker "$STATE_DIR"
  chmod 0750 "$STATE_DIR"
}

sync_repo() {
  echo "[INFO] Syncing repository from $REPO_SRC to $INSTALL_DIR"
  if ! command -v rsync >/dev/null 2>&1; then
    apt-get update -y && apt-get install -y rsync
  fi
  rsync -a --delete \
    --exclude ".git/" \
    --exclude ".venv*/" \
    --exclude "__pycache__/" \
    "$REPO_SRC/" "$INSTALL_DIR/"
  # Ensure world/group-readable files for compose usage
  find "$INSTALL_DIR" -type d -exec chmod 0755 {} +
  find "$INSTALL_DIR" -type f -exec chmod 0644 {} +
}

write_compose_override() {
  echo "[INFO] Writing compose override: $OVERRIDE_FILE"
  cat >"$OVERRIDE_FILE" <<'YAML'
services:
  qdrant:
    volumes:
      - /srv/qdrant:/qdrant/storage
  api:
    # Prefer ENV_FILE env var; fallback to /etc path for production
    env_file: ${ENV_FILE:-/etc/freehekim-rag/.env}
YAML
  chown root:root "$OVERRIDE_FILE"
  chmod 0644 "$OVERRIDE_FILE"
  # Ensure base compose .env is readable by service user
  if [ -f "$INSTALL_DIR/deployment/docker/.env" ]; then
    chmod 0644 "$INSTALL_DIR/deployment/docker/.env"
  fi
}

generate_env() {
  echo "[INFO] Generating production env at $ENV_FILE"
  local src_env="$REPO_SRC/.env"
  if [ ! -f "$src_env" ]; then
    src_env="$REPO_SRC/.env.example"
  fi
  echo "[INFO] Source env: $src_env"
  umask 007
  tmpfile=$(mktemp)
  # Keep existing keys, but drop ones we will override
  grep -v -E '^(ENV|QDRANT_HOST|QDRANT_PORT|REQUIRE_API_KEY)=' "$src_env" >"$tmpfile" || true
  {
    echo "ENV=production"
    echo "QDRANT_HOST=127.0.0.1"
    echo "QDRANT_PORT=6333"
    echo "REQUIRE_API_KEY=true"
  } >>"$tmpfile"

  # If API_KEY is missing, generate one
  if ! grep -q '^API_KEY=' "$tmpfile"; then
    if command -v openssl >/dev/null 2>&1; then
      apikey="$(openssl rand -hex 24)"
    else
      apikey="$(head -c 24 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 32)"
    fi
    echo "API_KEY=$apikey" >>"$tmpfile"
  fi

  install -o root -g ragsvc -m 0640 "$tmpfile" "$ENV_FILE"
  rm -f "$tmpfile"
}

migrate_qdrant_data() {
  if [ -d "$QDRANT_OLD" ] && [ -n "$(ls -A "$QDRANT_OLD" 2>/dev/null || true)" ]; then
    echo "[INFO] Migrating Qdrant data from $QDRANT_OLD to $QDRANT_NEW"
    rsync -a "$QDRANT_OLD/" "$QDRANT_NEW/"
  else
    echo "[INFO] No existing Qdrant data to migrate from $QDRANT_OLD"
  fi
}

compose_down_old() {
  echo "[INFO] Stopping old compose stack if running"
  if [ -d "$REPO_SRC/deployment/docker" ]; then
    (cd "$REPO_SRC/deployment/docker" && docker compose down) || true
  fi
}

start_new_stack() {
  echo "[INFO] Starting new stack from $INSTALL_DIR"
  (cd "$INSTALL_DIR/deployment/docker" && \
    ENV_FILE="$ENV_FILE" docker compose --env-file "$ENV_FILE" \
      -f docker-compose.server.yml -f docker-compose.local.yml -f docker-compose.monitoring.yml up -d)
}

install_systemd() {
  echo "[INFO] Installing systemd unit: $SYSTEMD_UNIT"
  cat >"$SYSTEMD_UNIT" <<UNIT
[Unit]
Description=FreeHekim RAG API (Docker Compose)
Wants=docker.service
After=docker.service network.target

[Service]
Type=oneshot
RemainAfterExit=yes
User=ragsvc
Group=ragsvc
SupplementaryGroups=docker
Environment=HOME=$STATE_DIR
Environment=ENV_FILE=$ENV_FILE
WorkingDirectory=$INSTALL_DIR/deployment/docker
ExecStart=/usr/bin/docker compose --env-file $ENV_FILE -f $INSTALL_DIR/deployment/docker/docker-compose.server.yml -f $INSTALL_DIR/deployment/docker/docker-compose.local.yml -f $INSTALL_DIR/deployment/docker/docker-compose.monitoring.yml up -d
ExecStop=/usr/bin/docker compose --env-file $ENV_FILE -f $INSTALL_DIR/deployment/docker/docker-compose.server.yml -f $INSTALL_DIR/deployment/docker/docker-compose.local.yml -f $INSTALL_DIR/deployment/docker/docker-compose.monitoring.yml down
TimeoutStartSec=0
TimeoutStopSec=120

[Install]
WantedBy=multi-user.target
UNIT
  systemctl daemon-reload
  systemctl enable freehekim-rag.service
}

install_docker_log_rotation() {
  if [ -f "$DOCKER_DAEMON_JSON_SRC" ]; then
    echo "[INFO] Installing Docker daemon log rotation config"
    if [ -f "$DOCKER_DAEMON_JSON_DST" ]; then
      cp "$DOCKER_DAEMON_JSON_DST" "/etc/docker/daemon.json.backup.$(date +%Y%m%d-%H%M%S)"
    fi
    install -o root -g root -m 0644 "$DOCKER_DAEMON_JSON_SRC" "$DOCKER_DAEMON_JSON_DST"
    systemctl restart docker
    sleep 2
  fi
}

setup_monitoring_dirs() {
  echo "[INFO] Ensuring monitoring data dirs"
  mkdir -p "$PROM_DIR" "$GRAFANA_DIR"
  # Prometheus runs as nobody
  chown -R nobody:nogroup "$PROM_DIR" || true
  chmod -R 0755 "$PROM_DIR"
  # Grafana runs as 472:472
  chown -R 472:472 "$GRAFANA_DIR" || true
  chmod -R 0755 "$GRAFANA_DIR"
}

copy_extra_configs() {
  # Optional additional config files used by ops
  if [ -f "$REPO_SRC/.cf_rules.json" ]; then
    echo "[INFO] Copying Cloudflare rules file to $ENV_DIR/.cf_rules.json"
    install -o root -g ragsvc -m 0640 "$REPO_SRC/.cf_rules.json" "$ENV_DIR/.cf_rules.json"
  fi
  # Cloudflared creds/config backup to /etc/freehekim-rag/cloudflared (does not change runtime)
  if [ -d "/home/freehekim/.cloudflared" ]; then
    mkdir -p "$ENV_DIR/cloudflared"
    for f in cert.json config.yml; do
      if [ -f "/home/freehekim/.cloudflared/$f" ]; then
        echo "[INFO] Backing up cloudflared $f to $ENV_DIR/cloudflared/$f"
        install -o root -g ragsvc -m 0640 \
          "/home/freehekim/.cloudflared/$f" "$ENV_DIR/cloudflared/$f"
      fi
    done
  fi
}

health_check() {
  echo "[INFO] Waiting for API health..."
  for i in $(seq 1 20); do
    if curl -fsS http://127.0.0.1:8080/health >/dev/null 2>&1; then
      echo "[INFO] API healthy at http://127.0.0.1:8080/health"
      return 0
    fi
    sleep 2
  done
  echo "[WARN] API health endpoint not responding yet" >&2
  return 1
}

main() {
  need_root
  ensure_user_and_groups
  prepare_dirs
  sync_repo
  write_compose_override
  generate_env
  compose_down_old
  migrate_qdrant_data
  install_docker_log_rotation
  setup_monitoring_dirs
  copy_extra_configs
  start_new_stack
  install_systemd
  health_check || true
  echo "[DONE] Provisioning complete. Use: systemctl start freehekim-rag.service"
}

main "$@"
