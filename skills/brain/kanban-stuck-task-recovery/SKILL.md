---
name: kanban-stuck-task-recovery
description: Diagnose and recover stuck kanban in_progress tasks (worker dead, claim_expires expired, dispatcher down). Includes SQL reset script, root cause analysis, and preventive monitoring.
type: skill
space: outcome
tags: [skill, kanban, operations]
created: 2026-05-31
updated: 2026-05-31
links:
  - "[[@memory/kanban/KANBAN_INDEX]]"
  - "[[@memory/growth/kanban-maintenance-guide]]"
  - "[[@identity/brain/rules]]"---

# Kanban Stuck Task Diagnosis & Recovery

## When to Use

- `task_list(status='in_progress')` returns tasks with no worker running
- Worker processes (PID) are dead but tasks remain stuck in `in_progress`
- `claim_expires` timestamps are past the current time
- After a dispatcher outage, tasks need to be reset before the system resumes

## Diagnosis

```python
# 1. Find all in_progress tasks with their worker status
python3 -c "
import sqlite3
db = '/Users/drew/.drewgent/P2-hippocampus/kanban/state/drewgent_tasks.db'
conn = sqlite3.connect(db)
cur = conn.cursor()
for id_, title, board, pid, expires in cur.execute(
    'SELECT id, title, board, worker_pid, claim_expires FROM tasks WHERE status=\"in_progress\"'
):
    print(f'{id_} | board={board} | pid={pid} | expires={expires}')
conn.close()
"

# 2. Check if worker PIDs are alive
ps -p 68898 -o pid,etime 2>/dev/null || echo "worker PID 68898 is DEAD"
```

## Recovery Script

```python
# Reclaim all stale in_progress tasks (expired claim_expires)
python3 -c "
import sqlite3
from datetime import datetime, timezone

db = '/Users/drew/.drewgent/P2-hippocampus/kanban/state/drewgent_tasks.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

stale = cur.execute('''
    SELECT id, title, worker_pid, claim_expires
    FROM tasks
    WHERE status='in_progress'
    AND (worker_pid IS NULL OR claim_expires < datetime('now'))
''').fetchall()

print(f'Found {len(stale)} stale in_progress tasks')
reclaimed = 0
for row in stale:
    tid = row[0]
    cur.execute('''
        UPDATE tasks
        SET status='ready', worker_pid=NULL, claim_expires=NULL, started_at=NULL
        WHERE id=? AND status='in_progress'
    ''', (tid,))
    if cur.rowcount > 0:
        print(f'RECLAIMED: {tid}')
        reclaimed += 1

conn.commit()
print(f'Total reclaimed: {reclaimed}')
conn.close()
"
```

## Root Causes

1. **Dispatcher disabled**: `kanban-dispatcher-*` jobs `enabled=false` → no `_reclaim_stale_tasks()` runs → orphans accumulate
2. **Worker crash mid-execution**: `_spawn_worker_for_task` starts worker, worker dies, `claim_expires` passes, dispatcher doesn't reclaim (dispatcher is down)
3. **Reclaim logic gap**: `_reclaim_stale_tasks` only runs inside `dispatch_once()` — if dispatcher is stopped, reclaim never fires

## Preventive Monitoring

```bash
# Quick health check
python3 -c "
import sqlite3
db = '/Users/drew/.drewgent/P2-hippocampus/kanban/state/drewgent_tasks.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

orphans = cur.execute('''
    SELECT id, title, claim_expires FROM tasks
    WHERE status='in_progress'
    AND (worker_pid IS NULL OR claim_expires < datetime('now'))
''').fetchall()
print(f'Orphan in_progress: {len(orphans)}')
for r in orphans:
    print(f'  {r[0]} | {r[1][:40]}')

ready = cur.execute('SELECT COUNT(*) FROM tasks WHERE status=\"ready\"').fetchone()[0]
print(f'Ready: {ready}')

conn.close()
"
```

## Cron Job Status Check

```bash
python3 -c "
import json
with open('/Users/drew/.drewgent/cron/jobs.json') as f:
    data = json.load(f)
jobs = data['jobs'] if 'jobs' in data else data
for j in jobs:
    status = 'ENABLED' if j.get('enabled', True) else 'DISABLED'
    last = (j.get('last_run_at') or 'never')[-20:]
    nxt = (j.get('next_run_at') or 'null')
    print(f'{status:9} | {j[\"name\"]:35} | last={last} | next={nxt[-20:]}')
"
```

## Key Insight

When dispatcher is down AND workers die mid-job → stuck `in_progress` tasks accumulate. Solution: SQL reset + re-enable dispatcher. Investigate why dispatcher was disabled (gateway restart? manual toggle? bug?).