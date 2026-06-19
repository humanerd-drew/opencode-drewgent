---
title: Kanban Worker
name: kanban-worker
type: document
space: concept
tags: [concept]
created: 2026-05-20
updated: 2026-06-10
links:
  - "[[P3-sensors/skills/SKILL-INDEX]]"
  - "[[P4-cortex/growth/drewgent-kanban-implementation-plan]]"
  - "[[kanban-dashboard]]"
  - "[[kanban-orchestrator]]"
  - "[[references/protocol.md]]"
  - "[[P0-brainstem/brain/rules]]"---





# Kanban Worker Skill

Task execution skill for kanban worker agents. A worker agent picks up tasks from the Drewgent kanban board, executes them, and reports results.

## Overview

A **kanban worker** is an autonomous agent that:
1. Claims a task from the board (or receives a task_id via env)
2. Reports heartbeat while working
3. Executes the task (code, research, writing, etc.)
4. Reports completion with result/summary

Workers are dispatched by the kanban dispatcher cron job or receive tasks via `KANBAN_TASK_ID` in the environment.

## Workflow

### Startup — Acquire Task

A worker can acquire a task in two ways:

**Option A: Dispatcher assigns task_id via env**
```
KANBAN_TASK_ID=t_abc123
KANBAN_WORKER_PID=12345
```
Read `KANBAN_TASK_ID` to know which task to work on.

**Option B: Self-claim from board**
```
kanban_list(status="ready")
# Pick a task
kanban_claim(task_id, ttl_seconds=3600)
```

### During Work — Heartbeat

Long-running tasks must send heartbeats every ~60 seconds:
```
kanban_heartbeat(task_id, note="Step 2/5: running tests")
```

Heartbeat purpose:
- Prevents claim expiry (default TTL: 1 hour)
- Lets dispatcher monitor progress
- Provides audit trail in task_events

### Task Completion

When done, call `kanban_complete`:
```
kanban_complete(
    task_id,
    result="<what was produced or accomplished>",
    summary="<one-line summary for board display>",
    metadata={
        "changed_files": ["file1", "file2"],
        "steps_completed": 3,
    },
    created_cards=["t_xxx", "t_yyy"],  # optional: any sub-tasks created
)
```

**Hallucination check**: `created_cards` IDs are verified against the DB. Any fake IDs cause a `completion_blocked_hallucination` event and exception.

### Task Failure

If task cannot be completed:
```
kanban_complete(
    task_id,
    result="FAILED: <reason>",
    summary="<short summary>",
    metadata={"error": "<error details>"},
)
```

Consecutive failures are tracked. After `max_retries` failures, task is moved to `failed` state.

### Blocking a Task

If task cannot proceed due to a dependency or external blocker:
```
kanban_block(task_id, reason="Blocked by upstream: need API credentials")
```

Unblock when ready:
```
kanban_unblock(task_id)
```

## Task Lifecycle

```
ready → claimed → in_progress → completed
              ↘ blocked (can return to claimed)
              ↘ failed (max retries exceeded)
```

| Transition | Trigger | Tool Call |
|-----------|---------|-----------|
| ready → claimed | Worker claims task | `kanban_claim()` |
| claimed → in_progress | First heartbeat sent | `kanban_heartbeat()` |
| in_progress → completed | Task done | `kanban_complete()` |
| in_progress → blocked | Dependency unmet | `kanban_block()` |
| blocked → in_progress | Blocker cleared | `kanban_unblock()` |
| in_progress → failed | max_retries hit | `kanban_complete()` with failure |

## Workspace

Workers operate in their own workspace:

| Field | Description |
|-------|-------------|
| `workspace_kind` | 'local' \| 'docker' \| 'ssh' |
| `workspace_path` | Path to working directory |

Use `workspace_path` as the working directory for all file operations.

## Reference

See [[references/protocol.md]] for the full task lifecycle protocol, API schema, and examples.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `KANBAN_TASK_ID` | Task ID assigned by dispatcher (if dispatched) |
| `KANBAN_WORKER_PID` | PID of the worker process |
| `KANBAN_BOARD` | Board name (default: 'default') |
| `DREWENT_HOME` | Drewgent home path (`~/.drewgent`) |

## Dispatcher Notes (for cron job agents)

The kanban dispatcher is **not** invoked via `from tools.drewgent_kanban_db import dispatch_once` — that import path does not resolve in production. The actual dispatch mechanism uses standalone scripts:

**Scripts**: `~/.drewgent/scripts/dispatch_once_{board}.py` (one per board: `default`, `content`, `integrations`)

**Execution** (run directly, no import gymnastics):
```bash
~/.drewgent/source/drewgent-agent/.venv/bin/python ~/.drewgent/scripts/dispatch_once_default.py
```

Each script opens its own SQLite connection and runs 5 phases:
1. **Phase 0 (watchdog)**: `os.kill(pid, 0)` to check worker liveness; dead workers reclaimed immediately
2. **Phase 0.5 (affinity)**: Skips tasks with 3+ consecutive failures (cooldown)
3. **Phase 1 (TTL reclaim)**: Reclaims tasks past `claim_expires` (but skips if worker PID is still alive)
4. **Phase 2 (claim)**: Claims ready tasks with adaptive `MAX_CLAIM` (scales with queue depth)
5. **Phase 3 (spawn)**: Spawns `run_kanban_worker.py` via `Popen` with logfile redirect (no PIPE deadlock)

**Worker logs**: `~/.drewgent/P4-cortex/scripts/kanban/logs/workers/{task_id}.log`

**Output protocol**: `[SILENT]` if no work done; otherwise detailed breakdown with per-task details.

## Related Skills

- [[kanban-orchestrator]] — Task decomposition and linking
- [[kanban-dashboard]] — Board visualization via n8n
- [[kanban-dispatcher-hardening]] — Dispatcher watchdog + logfile redirect internals
- [[kanban-dispatcher-stalled]] — Diagnose dispatcher stalls when cron stops running

## Related

- [[P4-cortex/growth/drewgent-kanban-implementation-plan]]
- [[P3-sensors/skills/SKILL-INDEX]]