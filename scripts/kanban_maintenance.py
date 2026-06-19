#!/usr/bin/env python3
"""Kanban Maintenance — periodic cleanup of junk tasks and orphan links.

Runs Sunday 03:00 KST (jobs.json: kanban-maintenance). Triggered as a
script-based fast path in cron/scheduler.py — no LLM involved.

Phases:
  1. trigger-based bulk delete (test/verify/manual_test/activity_logger-completed)
  2. title-based cleanup (manual trigger + known junk titles)
  3. orphan task_links cleanup (parent/child refs that no longer exist)
  4. HTML dashboard refresh (best effort, fails silently if script missing)
"""
import sqlite3
import subprocess
import sys
from pathlib import Path

DREW_HOME = Path.home() / ".drewgent"
DB = DREW_HOME / "P2-hippocampus" / "kanban" / "state" / "drewgent_tasks.db"
HTML_REFRESH_SCRIPT = DREW_HOME / "P4-cortex" / "scripts" / "generate_kanban_html.py"

if not DB.exists():
    print(f"DB not found: {DB}")
    sys.exit(0)

conn = sqlite3.connect(str(DB), timeout=30)
conn.execute("PRAGMA foreign_keys = ON")

# Phase 1: trigger-based bulk delete
deleted = 0
for trigger in ("test", "verify", "manual_test"):
    n = conn.execute("DELETE FROM tasks WHERE trigger_source=?", (trigger,)).rowcount
    deleted += n

n = conn.execute(
    "DELETE FROM tasks WHERE status='completed' AND trigger_source='activity_logger'"
).rowcount
deleted += n

# Phase 2: title-based cleanup (manual trigger only — leave production titles alone)
JUNK_TITLES = [
    "A", "B", "C",
    "Test", "Test A", "Test B", "Test C",
    "Child task", "Child2",
    "Block test",
    "Link Child", "Link Bug Child",
    "Ready task for dispatcher",
    "Default board task", "Another default",
    "integration test",
    "[tool] super_tool", "[tool] test_tool",
    "Notify test",
    "Parent task", "Parent2",
    "Link Parent", "Link Bug Parent",
    "[Discord] Test task from Activity Logger",
    "[Discord] p3g integration test",
    "[test] Activity logger test card",
]
if JUNK_TITLES:
    placeholders = ",".join(["?"] * len(JUNK_TITLES))
    n = conn.execute(
        f"DELETE FROM tasks WHERE trigger_source='manual' AND title IN ({placeholders})",
        JUNK_TITLES,
    ).rowcount
    deleted += n

# Phase 3: orphan task_links cleanup
task_ids = {r[0] for r in conn.execute("SELECT id FROM tasks").fetchall()}
orphans = [
    (p, c)
    for p, c in conn.execute("SELECT parent_id, child_id FROM task_links").fetchall()
    if p not in task_ids or c not in task_ids
]
for p, c in orphans:
    conn.execute("DELETE FROM task_links WHERE parent_id=? AND child_id=?", (p, c))

conn.commit()

# Report
remaining = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
by_status = dict(
    conn.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status").fetchall()
)
conn.close()

print(f"Deleted: {deleted}")
print(f"Orphan task_links cleaned: {len(orphans)}")
print(f"Remaining tasks: {remaining}")
for status, count in sorted(by_status.items()):
    print(f"  {status}: {count}")

# Phase 4: HTML dashboard refresh (best effort — skip if script missing)
if HTML_REFRESH_SCRIPT.is_file():
    try:
        result = subprocess.run(
            [sys.executable, str(HTML_REFRESH_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if result.returncode == 0:
            print("HTML dashboard refreshed.")
        else:
            print(f"HTML refresh exit={result.returncode}: {result.stderr[:200]}")
    except Exception as e:
        print(f"HTML refresh skipped (error: {type(e).__name__}: {e})")
else:
    print(f"HTML refresh skipped (script not found: {HTML_REFRESH_SCRIPT})")
