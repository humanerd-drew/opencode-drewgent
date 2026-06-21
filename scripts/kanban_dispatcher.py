#!/usr/bin/env python3
"""
kanban_dispatcher.py — Pick one pending kanban task and dispatch it.
Replaces office_autopilot.sh. Called by cron every 5 minutes.
"""
import json, subprocess, sqlite3, sys
from pathlib import Path
from datetime import datetime

HOME = Path.home()
DREW = HOME / ".drewgent"
DB = DREW / "kanban.db"
LOG = DREW / "logs" / "kanban-dispatcher.log"

# Agent name per assignee
AGENT_MAP = {
    "sre": "sre",
    "implementer": "implementer",
    "explorer": "explorer",
    "planner": "planner",
    "designer": "designer",
    "analyst": "analyst",
}

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG, "a") as f:
        f.write(f"[{ts}] {msg}\n")
    print(f"[{ts}] {msg}")

def get_next_task():
    db = sqlite3.connect(str(DB))
    c = db.cursor()
    c.execute("SELECT id, title, body, assignee FROM tasks WHERE status IN ('todo','ready') AND claim_lock IS NULL ORDER BY priority DESC, created_at ASC LIMIT 1")
    row = c.fetchone()
    db.close()
    return row

def claim_task(task_id):
    db = sqlite3.connect(str(DB))
    c = db.cursor()
    now = datetime.utcnow().isoformat()
    c.execute("UPDATE tasks SET status='in_progress', started_at=? WHERE id=? AND status IN ('todo','ready')", (now, task_id))
    db.commit()
    affected = c.rowcount
    db.close()
    return affected > 0

def complete_task(task_id, result):
    db = sqlite3.connect(str(DB))
    c = db.cursor()
    now = datetime.utcnow().isoformat()
    c.execute("UPDATE tasks SET status='completed', completed_at=?, result=? WHERE id=?", (now, result, task_id))
    db.commit()
    db.close()

def fail_task(task_id, error):
    db = sqlite3.connect(str(DB))
    c = db.cursor()
    c.execute("UPDATE tasks SET status='blocked', last_failure_error=? WHERE id=?", (error[:500], task_id))
    db.commit()
    db.close()

def dispatch(task_id, title, body, assignee):
    agent = AGENT_MAP.get(assignee, "implementer")
    log(f"Dispatching {task_id} ({title}) → {agent}")

    try:
        prompt = f"Process kanban task '{task_id}': {title}\n\nTask details:\n{json.dumps(body, indent=2) if isinstance(body, str) else body}\n\nComplete the task described in the body steps. Mark it done when finished."
        r = subprocess.run(
            ["opencode", "run", "--attach", "http://localhost:8642",
             "--model", "opencode-go/deepseek-v4-flash",
             prompt],
            capture_output=True, text=True, timeout=600
        )
        output = (r.stdout or "") + "\n" + (r.stderr or "")
        log(f"{task_id} result: {output[:300]}")
        complete_task(task_id, output[:1000])
        return True
    except subprocess.TimeoutExpired:
        log(f"{task_id} TIMEOUT after 600s")
        fail_task(task_id, "Timeout: 600s exceeded")
        return False
    except Exception as e:
        log(f"{task_id} error: {e}")
        fail_task(task_id, str(e))
        return False

def main():
    task = get_next_task()
    if not task:
        print("silent")
        return
    task_id, title, body, assignee = task
    parsed = json.loads(body) if body else {}
    if claim_task(task_id):
        dispatch(task_id, title, parsed, assignee)

if __name__ == "__main__":
    main()
