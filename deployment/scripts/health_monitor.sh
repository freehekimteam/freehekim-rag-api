#!/usr/bin/env bash
set -euo pipefail

# Lightweight health monitor for FreeHekim RAG
# - Checks external health (via Cloudflare) and local readiness
# - Sends alert to Slack or Telegram on failure
# - False-positive filter with consecutive failures threshold
# - Quiet hours support (suppress alerts during a time window)
# - Designed to be run by systemd --user timer

# Configuration via env (loaded from ~/.config/freehekim-rag/.env by default)
ENV_FILE_DEFAULT="$HOME/.config/freehekim-rag/.env"
ENV_FILE="${ENV_FILE:-$ENV_FILE_DEFAULT}"
if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

# Derive external health URL from HC_CF_TUNNEL_HOST if MONITOR_URL_HEALTH not set
if [ -z "${MONITOR_URL_HEALTH:-}" ] && [ -n "${HC_CF_TUNNEL_HOST:-}" ]; then
  MONITOR_URL_HEALTH="https://${HC_CF_TUNNEL_HOST}/health"
fi
MONITOR_URL_HEALTH="${MONITOR_URL_HEALTH:-https://rag.hakancloud.com/health}"
MONITOR_URL_READY="${MONITOR_URL_READY:-http://127.0.0.1:8080/ready}"
MONITOR_EXPECT_HEALTH="${MONITOR_EXPECT_HEALTH:-200}"
MONITOR_EXPECT_READY="${MONITOR_EXPECT_READY:-200}"
MONITOR_TIMEOUT="${MONITOR_TIMEOUT:-8}"

# False-positive filter / quiet hours / cooldown
MONITOR_CONSECUTIVE_FAILS="${MONITOR_CONSECUTIVE_FAILS:-3}"
MONITOR_STATE_DIR="${MONITOR_STATE_DIR:-$HOME/.local/state/freehekim}"
MONITOR_STATE_FILE="$MONITOR_STATE_DIR/rag_monitor.state"
MONITOR_SEND_RECOVERY="${MONITOR_SEND_RECOVERY:-true}"
MONITOR_QUIET_START="${MONITOR_QUIET_START:-}"
MONITOR_QUIET_END="${MONITOR_QUIET_END:-}"
MONITOR_SUPPRESS_ALERTS_DURING_QUIET="${MONITOR_SUPPRESS_ALERTS_DURING_QUIET:-true}"
# Minimum minutes between consecutive alerts while a failure persists
MONITOR_ALERT_COOLDOWN_MINUTES="${MONITOR_ALERT_COOLDOWN_MINUTES:-240}"
COOLDOWN_SECONDS=$((10#$MONITOR_ALERT_COOLDOWN_MINUTES * 60))

ALERT_SLACK_WEBHOOK="${ALERT_SLACK_WEBHOOK:-}"
ALERT_TG_TOKEN="${ALERT_TELEGRAM_BOT_TOKEN:-}"
ALERT_TG_CHAT="${ALERT_TELEGRAM_CHAT_ID:-}"

ts() { date '+%Y-%m-%d %H:%M:%S%z'; }

notify() {
  local msg="$1"
  # Slack
  if [ -n "$ALERT_SLACK_WEBHOOK" ]; then
    # Minimal JSON escaping for Slack
    local esc
    esc=$(printf '%s' "$msg" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g')
    curl -fsS -m 5 -H 'Content-Type: application/json' \
      -d "{\"text\": \"$esc\"}" \
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

# Ensure state dir exists
mkdir -p "$MONITOR_STATE_DIR"
[ -f "$MONITOR_STATE_FILE" ] || echo "fails=0
was_down=0
last_alert_epoch=0" > "$MONITOR_STATE_FILE"

# shellcheck disable=SC1090
. "$MONITOR_STATE_FILE"

# Quiet hours helper
in_quiet_hours() {
  [ -z "$MONITOR_QUIET_START" ] || [ -z "$MONITOR_QUIET_END" ] && return 1
  # HH:MM to minutes
  sm=${MONITOR_QUIET_START%:*}; ss=${MONITOR_QUIET_START#*:}
  em=${MONITOR_QUIET_END%:*}; es=${MONITOR_QUIET_END#*:}
  start=$((10#$sm*60 + 10#$ss))
  end=$((10#$em*60 + 10#$es))
  now_h=$(date +%H); now_m=$(date +%M); now=$((10#$now_h*60 + 10#$now_m))
  if [ $start -lt $end ]; then
    [ $now -ge $start ] && [ $now -lt $end ]
  else
    # window crosses midnight
    [ $now -ge $start ] || [ $now -lt $end ]
  fi
}

host=$(hostname -s 2>/dev/null || echo server)

if [ "$fail" -ne 0 ]; then
  fails=$((fails + 1))
  was_down=1
  now_epoch=$(date +%s)
  : "${last_alert_epoch:=0}"
  # Decide to alert only if threshold reached and not suppressed by quiet hours
  if [ "$fails" -ge "$MONITOR_CONSECUTIVE_FAILS" ]; then
    if in_quiet_hours && [ "$MONITOR_SUPPRESS_ALERTS_DURING_QUIET" = "true" ]; then
      echo "[$(ts)] RAG monitor FAIL (suppressed due to quiet hours): health=$c_health, ready=$c_ready (streak=$fails)"
    else
      # Cooldown guard to avoid spamming while still failing
      if [ $(( now_epoch - last_alert_epoch )) -ge $COOLDOWN_SECONDS ] || [ "$last_alert_epoch" = "0" ]; then
        msg="[$(ts)] RAG monitor ALERT on $host: health=$c_health (expect $MONITOR_EXPECT_HEALTH), ready=$c_ready (expect $MONITOR_EXPECT_READY), streak=$fails"
        notify "$msg"
        echo "$msg"
        last_alert_epoch=$now_epoch
      else
        remain=$(( COOLDOWN_SECONDS - (now_epoch - last_alert_epoch) ))
        echo "[$(ts)] RAG monitor FAIL (cooldown $remain s remaining): health=$c_health, ready=$c_ready (streak=$fails)"
      fi
    fi
  else
    echo "[$(ts)] RAG monitor FAIL (no alert yet): health=$c_health, ready=$c_ready (streak=$fails/<$MONITOR_CONSECUTIVE_FAILS)"
  fi
  echo "fails=$fails
was_down=$was_down
last_alert_epoch=$last_alert_epoch" > "$MONITOR_STATE_FILE"
else
  # If recovering from a down state, optionally notify
  if [ "${was_down:-0}" = "1" ] && [ "$MONITOR_SEND_RECOVERY" = "true" ]; then
    if in_quiet_hours && [ "$MONITOR_SUPPRESS_ALERTS_DURING_QUIET" = "true" ]; then
      echo "[$(ts)] RAG monitor RECOVERY (suppressed due to quiet hours): health=$c_health, ready=$c_ready"
    else
      msg="[$(ts)] RAG monitor RECOVERY on $host: health=$c_health, ready=$c_ready"
      notify "$msg"
      echo "$msg"
    fi
  else
    echo "[$(ts)] RAG monitor OK: health=$c_health, ready=$c_ready"
  fi
  # reset counters
  echo "fails=0
was_down=0
last_alert_epoch=0" > "$MONITOR_STATE_FILE"
fi
