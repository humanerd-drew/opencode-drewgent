#!/bin/bash
# drewgent_log_rotate.sh
# Daily log rotation for launchd-managed services. macOS newsyslog does not
# handle launchd stdout/stderr files, so we do it manually.
#
# Strategy: rename old log → .YYYY-MM-DD.gz, restart service so launchd
# recreates the file (launchd holds the FD open across renames).
#
# Triggers: any log file > $MAX_SIZE (default 100MB) OR any log file > 7 days
# old. Gzipped old logs are kept for 30 days, then deleted.
#
# no_agent=True cron job, runs daily 04:00 KST.

set -euo pipefail

DREW_LOGS="$HOME/.drewgent/logs"
LIB_LOGS="$HOME/Library/Logs"
MAX_SIZE_BYTES=$((100 * 1024 * 1024))   # 100MB
MAX_AGE_DAYS=7
KEEP_DAYS=30

# (label, current_log_path, restart_command)
LOGS=(
  "ai.drewgent.gateway|$DREW_LOGS/gateway.log|gateway"
  "ai.drewgent.gateway|$DREW_LOGS/gateway.error.log|gateway"
  "ai.drewgent.cron-runner|$DREW_LOGS/cron-runner.log|cron-runner"
  "ai.drewgent.cron-runner|$DREW_LOGS/cron-runner.error.log|cron-runner"
  "com.drewgent.quartz-fswatch|$LIB_LOGS/quartz-fswatch.log|quartz-fswatch"
  "com.drewgent.quartz-deploy|$LIB_LOGS/quartz-deploy.log|quartz-deploy"
  "ai.drewgent.n8n|$DREW_LOGS/n8n.log|n8n"
  "ai.drewgent.n8n|$DREW_LOGS/n8n.error.log|n8n"
)

UID_NUM=$(id -u)
TODAY=$(date +%Y-%m-%d)
rotated=()

for entry in "${LOGS[@]}"; do
  IFS='|' read -r label path service <<< "$entry"
  if [ ! -f "$path" ]; then
    continue
  fi

  size=$(stat -f %z "$path" 2>/dev/null || echo 0)
  age_days=$(( ( $(date +%s) - $(stat -f %m "$path") ) / 86400 ))

  rotate=0
  reason=""
  if [ "$size" -gt "$MAX_SIZE_BYTES" ]; then
    rotate=1
    reason="size=${size}B > ${MAX_SIZE_BYTES}B"
  elif [ "$age_days" -gt "$MAX_AGE_DAYS" ]; then
    rotate=1
    reason="age=${age_days}d > ${MAX_AGE_DAYS}d"
  fi

  if [ "$rotate" -eq 1 ]; then
    archive="${path}.${TODAY}.gz"
    # Compress the old log, then truncate the live file (this keeps the FD).
    # launchd will keep writing to the same FD but the file appears empty.
    gzip -c "$path" > "$archive" 2>/dev/null || true
    : > "$path"   # truncate live file, FD preserved
    rotated+=("$path ($reason) → $archive")

    # kickstart the service so launchd reopens the file. Safe — KeepAlive
    # respawns, so this is just a forced restart.
    launchctl kickstart -k "gui/${UID_NUM}/${label}" 2>/dev/null || true
  fi
done

# Cleanup: gzipped logs older than $KEEP_DAYS
deleted=$(find "$DREW_LOGS" "$LIB_LOGS" -name "*.log.*.gz" -mtime "+${KEEP_DAYS}" -delete -print 2>/dev/null | wc -l | tr -d ' ')

if [ ${#rotated[@]} -eq 0 ] && [ "$deleted" -eq 0 ]; then
  # silent when nothing to do (no_agent=True convention)
  exit 0
fi

echo "📦 **Drewgent log rotation** @ $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "Rotated: ${#rotated[@]} files"
for r in "${rotated[@]}"; do echo "  - $r"; done
echo "Deleted old archives: $deleted (kept last ${KEEP_DAYS} days)"
