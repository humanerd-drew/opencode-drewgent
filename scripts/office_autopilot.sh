#!/bin/bash
# office_autopilot.sh — OmO-powered kanban dispatcher
set -e

# Check if another ultrawork session is already running
if pgrep -f "opencode run.*ultrawork" > /dev/null 2>&1; then
  echo "another session running, skip"
  exit 0
fi

DB="$HOME/.drewgent/kanban.db"
PENDING=$(sqlite3 "$DB" "SELECT count(*) FROM tasks WHERE status IN ('todo','ready') AND claim_lock IS NULL;" 2>/dev/null || echo 0)

if [ "$PENDING" -eq 0 ]; then
  echo "silent"
  exit 0
fi

LOG="$HOME/.drewgent/logs/office-autopilot.log"
echo "[$(date '+%Y-%m-%d %H:%M')] OmO dispatching $PENDING pending tasks" >> "$LOG"

# Process tasks via ultrawork
opencode run --attach http://localhost:8642 \
  "ultrawork: process pending kanban tasks.

1. Read pending tasks: sqlite3 $DB \"SELECT id, title, body FROM tasks WHERE status IN ('todo','ready') AND claim_lock IS NULL ORDER BY priority DESC, created_at ASC;\"
2. For each task, process it fully:
   - trend-evaluate / trend-apply: run the evaluation, call kanban complete
   - content-news / content-insight / content-series: write blog post (Gutenberg HTML, correct category). Update narrative_arc.md + content-inventory.md after publish.
   - trend-discuss: discussion tasks — read body, analyze, report summary
   - other: process per task body
3. After ALL tasks processed: report summary." 2>&1
