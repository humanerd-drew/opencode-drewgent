#!/bin/bash
# office_autopilot.sh — OmO-powered kanban dispatcher
# Picks one pending task, dispatches via OmO Sisyphus orchestrator.
set -e

DB="$HOME/.drewgent/kanban.db"
PID_FILE="$HOME/.drewgent/.ultrawork.pid"
LOG="$HOME/.drewgent/logs/office-autopilot.log"

# === DUPLICATE SPAWN GUARD ===
# Only one ultrawork at a time — token limit 방지
if [ -f "$PID_FILE" ]; then
  OLD_PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "[$(date '+%Y-%m-%d %H:%M')] Duplicate blocked — PID $OLD_PID still running" >> "$LOG"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

ULTRACOUNT=$(ps aux | grep -c "opencode run.*ultrawork" 2>/dev/null || true)
if [ "${ULTRACOUNT:-0}" -gt 1 ]; then
  echo "[$(date '+%Y-%m-%d %H:%M')] Duplicate blocked — $ULTRACOUNT already running" >> "$LOG"
  exit 0
fi

# Pick ONE task only — 순차 처리
TASK=$(sqlite3 "$DB" "SELECT id, title FROM tasks WHERE status IN ('todo','ready') AND claim_lock IS NULL ORDER BY priority DESC, created_at ASC LIMIT 1;" 2>/dev/null || echo "")

if [ -z "$TASK" ]; then
  echo "silent"
  exit 0
fi

TASK_ID=$(echo "$TASK" | cut -d'|' -f1)
TASK_TITLE=$(echo "$TASK" | cut -d'|' -f2)

echo "[$(date '+%Y-%m-%d %H:%M')] Dispatching 1 task: $TASK_TITLE ($TASK_ID)" >> "$LOG"

ULTRALOG="$HOME/.drewgent/logs/ultrawork-$(date '+%Y%m%d-%H%M%S').log"
opencode run --attach http://localhost:8642 \
  "ultrawork: process ONE kanban task.

Task ID: $TASK_ID
Task title: $TASK_TITLE

1. Read task: sqlite3 $DB \"SELECT id, title, body FROM tasks WHERE id='$TASK_ID';\"
2. Claim it: sqlite3 $DB \"UPDATE tasks SET claim_lock='ultrawork-$(date +%s)' WHERE id='$TASK_ID';\"
3. Process it:
   - content-write:* → delegate to content-manager agent via task(subagent_type=\"content-manager\")
   - trend-* → delegate to implementer via task()
   - creative-write:* → delegate to content-manager (status=draft)
   - other → handle directly
4. Mark complete: sqlite3 $DB \"UPDATE tasks SET status='completed', completed_at=datetime('now') WHERE id='$TASK_ID';\"
5. Report result in 1-2 sentences.
Do NOT look at any other tasks. One task only." >> "$ULTRALOG" 2>&1 &

ULTRAPID=$!
echo "$ULTRAPID" > "$PID_FILE"
echo "[$(date '+%Y-%m-%d %H:%M')] Spawned ultrawork PID=$ULTRAPID task=$TASK_ID log=$ULTRALOG" >> "$LOG"
