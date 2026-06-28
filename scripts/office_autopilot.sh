#!/bin/bash
# office_autopilot.sh — OmO-powered kanban dispatcher
# Picks one pending task, dispatches via OmO Sisyphus orchestrator.
set -e

DB="$HOME/.drewgent/kanban.db"
PENDING=$(sqlite3 "$DB" "SELECT count(*) FROM tasks WHERE status IN ('todo','ready') AND claim_lock IS NULL;" 2>/dev/null || echo 0)

if [ "$PENDING" -eq 0 ]; then
  echo "silent"
  exit 0
fi

LOG="$HOME/.drewgent/logs/office-autopilot.log"
echo "[$(date '+%Y-%m-%d %H:%M')] OmO dispatching $PENDING pending tasks" >> "$LOG"

# Process ALL pending tasks in one OmO session.
# OmO's ultrawork mode handles multiple tasks sequentially.
opencode run --attach http://localhost:8642 \
  "ultrawork: process all pending kanban tasks.

1. Read pending tasks: sqlite3 $DB \"SELECT id, title, body FROM tasks WHERE status IN ('todo','ready') AND claim_lock IS NULL ORDER BY priority DESC, created_at ASC;\"
2. For each task, process it fully:
   - Parse the body JSON for steps, assignee, completion criteria
   - Delegate work via task() or category routing
   - Mark complete: sqlite3 $DB \"UPDATE tasks SET status='completed', completed_at=datetime('now') WHERE id='<task_id>';\"
3. After all tasks, report summary of what was done." 2>&1
