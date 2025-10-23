#!/usr/bin/env bash
set -euo pipefail

# Lightweight health monitor for FreeHekim RAG
# - Checks external health (via Cloudflare) and local readiness
# - Sends alert to Slack or Telegram on failure
# - Designed to be run by systemd --user timer

# Configuration via env (loaded from ~/.config/freehekim-rag/.env by default)
ENV_FILE_DEFAULT="$HOME/.config/freehekim-rag/.env"
ENV_FILE="${ENV_FILE:-$ENV_FILE_DEFAULT}"
if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

MONITOR_URL_HEALTH="${MONITOR_URL_HEALTH:-https://rag.hakancloud.com/health}"
MONITOR_URL_READY="${MONITOR_URL_READY:-http://127.0.0.1:8080/ready}"
MONITOR_EXPECT_HEALTH="${MONITOR_EXPECT_HEALTH:-200}"
MONITOR_EXPECT_READY="${MONITOR_EXPECT_READY:-200}"
MONITOR_TIMEOUT="${MONITOR_TIMEOUT:-8}"

ALERT_SLACK_WEBHOOK="${ALERT_SLACK_WEBHOOK:-}"
ALERT_TG_TOKEN="${ALERT_TELEGRAM_BOT_TOKEN:-}"
ALERT_TG_CHAT="${ALERT_TELEGRAM_CHAT_ID:-}"

ts() { date '+%Y-%m-%d %H:%M:%S%z'; }

notify() {
  local msg="$1"
  # Slack
  if [ -n "$ALERT_SLACK_WEBHOOK" ]; then
    curl -fsS -m 5 -H 'Content-Type: application/json' \
      -d "{\"text\": $(jq -Rs . <<<"$msg") }" \
      "$ALERT_SLACK_WEBHOOK" >/dev/null 2>&1 || true
  fi
  # Telegram
  if [ -n "$ALERT_TG_TOKEN" ] && [ -n "$ALERT_TG_CHAT" ]; then
    curl -fsS -m 5 \
      --data-urlencode "chat_id=$ALERT_TG_CHAT" \
      --data-urlencode "text=$msg" \
      "https://api.telegram.org/bot${ALERT_TG_TOKEN}/sendMessage" >/dev/null 2>&1 || true
  fi
}

curl_code() {
  local url="$1"; shift
  curl -ksS -m "$MONITOR_TIMEOUT" -o /dev/null -w '%{http_code}\n' "$url" || echo 000
}

fail=0
c_health=$(curl_code "$MONITOR_URL_HEALTH")
if [ "$c_health" != "$MONITOR_EXPECT_HEALTH" ]; then
  fail=1
fi
c_ready=$(curl_code "$MONITOR_URL_READY")
if [ "$c_ready" != "$MONITOR_EXPECT_READY" ]; then
  fail=1
fi

if [ "$fail" -ne 0 ]; then
  host=$(hostname -s 2>/dev/null || echo server)
  msg="[$(ts)] RAG monitor ALERT on $host: health=$c_health (expect $MONITOR_EXPECT_HEALTH), ready=$c_ready (expect $MONITOR_EXPECT_READY)"
  notify "$msg"
  echo "$msg"
else
  echo "[$(ts)] RAG monitor OK: health=$c_health, ready=$c_ready"
fi

