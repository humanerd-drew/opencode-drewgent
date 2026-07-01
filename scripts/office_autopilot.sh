#!/bin/bash
# office_autopilot.sh — OmO-powered kanban dispatcher
# Picks one pending task, dispatches via OmO Sisyphus orchestrator.
set -e

DB="$HOME/.drewgent/kanban.db"
PID_FILE="$HOME/.drewgent/.ultrawork.pid"
LOG="$HOME/.drewgent/logs/office-autopilot.log"

# === DUPLICATE SPAWN GUARD ===
# PID file: check if previous ultrawork is still alive
if [ -f "$PID_FILE" ]; then
  OLD_PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "[$(date '+%Y-%m-%d %H:%M')] Duplicate spawn blocked — PID $OLD_PID still running" >> "$LOG"
    exit 0
  fi
  # Stale PID — remove
  rm -f "$PID_FILE"
fi

# pgrep backup guard — count other ultrawork processes (grep -c returns 0 on no match, no exit code issue)
ULTRACOUNT=$(ps aux | grep -c "opencode run.*ultrawork" 2>/dev/null || true)
if [ "${ULTRACOUNT:-0}" -gt 1 ]; then
  echo "[$(date '+%Y-%m-%d %H:%M')] Duplicate spawn blocked — $ULTRACOUNT ultrawork processes already running" >> "$LOG"
  exit 0
fi

PENDING=$(sqlite3 "$DB" "SELECT count(*) FROM tasks WHERE status IN ('todo','ready') AND claim_lock IS NULL;" 2>/dev/null || echo 0)

if [ "$PENDING" -eq 0 ]; then
  echo "silent"
  exit 0
fi

echo "[$(date '+%Y-%m-%d %H:%M')] OmO dispatching $PENDING pending tasks" >> "$LOG"

# Process ALL pending tasks in one OmO session.
ULTRALOG="$HOME/.drewgent/logs/ultrawork-$(date '+%Y%m%d-%H%M%S').log"
opencode run --attach http://localhost:8642 \
  "ultrawork: process all pending kanban tasks.

1. Read pending tasks: sqlite3 $DB \"SELECT id, title, body FROM tasks WHERE status IN ('todo','ready') AND claim_lock IS NULL ORDER BY priority DESC, created_at ASC;\"
2. For each task, process it fully:
   - Parse the body JSON for steps, assignee, completion criteria
   - Delegate work via task() or category routing
   - Mark complete: sqlite3 $DB \"UPDATE tasks SET status='completed', completed_at=datetime('now') WHERE id='<task_id>';\"
3. After all tasks, report summary of what was done." >> "$ULTRALOG" 2>&1 &

ULTRAPID=$!
echo "$ULTRAPID" > "$PID_FILE"
echo "[$(date '+%Y-%m-%d %H:%M')] Spawned ultrawork PID=$ULTRAPID log=$ULTRALOG" >> "$LOG"
