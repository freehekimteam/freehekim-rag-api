#!/usr/bin/env bash
set -euo pipefail

REPO_SLUG="freehekimteam/freehekim-rag-api"
REPO_URL="https://github.com/${REPO_SLUG}"
# Use /tmp to avoid /home permission constraints
RUNNER_DIR="/tmp/gha-runner"
LOG_FILE="/tmp/setup_runner.log"

echo "[INFO] Starting self-hosted runner setup for ${REPO_SLUG}" | tee -a "$LOG_FILE"
mkdir -p "$RUNNER_DIR"
cd "$RUNNER_DIR"

echo "[INFO] Fetching latest actions/runner release tag" | tee -a "$LOG_FILE"
LATEST_TAG=$(curl -fsSL https://api.github.com/repos/actions/runner/releases/latest | python3 -c 'import sys,json;print(json.load(sys.stdin)["tag_name"])')
VER=${LATEST_TAG#v}
FILE="actions-runner-linux-x64-${VER}.tar.gz"
URL="https://github.com/actions/runner/releases/download/${LATEST_TAG}/${FILE}"

if [ ! -d "bin" ]; then
  echo "[INFO] Downloading runner ${VER} from ${URL}" | tee -a "$LOG_FILE"
  # resume if partial
  curl -fL --retry 10 --retry-delay 2 -C - -o "$FILE" "$URL"
  echo "[INFO] Extracting..." | tee -a "$LOG_FILE"
  tar xzf "$FILE"
fi

echo "[INFO] Requesting registration token via gh api" | tee -a "$LOG_FILE"
REG_TOKEN=$(gh api -X POST repos/${REPO_SLUG}/actions/runners/registration-token -q .token)

NAME="FH-RAG-Runner-$(hostname)"
LABELS="self-hosted,linux,deploy"
echo "[INFO] Configuring runner (name=${NAME}, labels=${LABELS})" | tee -a "$LOG_FILE"
./config.sh --unattended --replace --url "$REPO_URL" --token "$REG_TOKEN" --name "$NAME" --labels "$LABELS" | tee -a "$LOG_FILE"

if command -v sudo >/dev/null 2>&1; then
  echo "[INFO] Installing as service" | tee -a "$LOG_FILE"
  sudo ./svc.sh install | tee -a "$LOG_FILE" || true
  if getent group docker >/dev/null 2>&1; then
    sudo usermod -aG docker "$USER" || true
  fi
  echo "[INFO] Starting service" | tee -a "$LOG_FILE"
  sudo ./svc.sh start | tee -a "$LOG_FILE" || true
else
  echo "[WARN] sudo not found; starting in background with nohup" | tee -a "$LOG_FILE"
  nohup ./run.sh >> "$LOG_FILE" 2>&1 & disown || true
fi

echo "[INFO] Verifying runner status" | tee -a "$LOG_FILE"
sleep 3
gh api repos/${REPO_SLUG}/actions/runners -q '.runners[] | "\(.name) | status=\(.status) | busy=\(.busy)"' | tee -a "$LOG_FILE" || true
echo "[INFO] Done." | tee -a "$LOG_FILE"
