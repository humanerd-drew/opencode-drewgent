---
title: Protocol
type: document
space: concept
tags: [concept]
created: 2026-05-20
updated: 2026-05-20
links:
  - "[[../SKILL]]"
  - "[[@action/skills/SKILL-INDEX]]"
  - "[[@memory/growth/drewgent-kanban-implementation-plan]]"
---





# Kanban Worker Protocol

Reference for kanban worker agents. Full task lifecycle protocol, API schema, and examples.

---

## Task Lifecycle Protocol

### Phase 1: Acquire

**Trigger**: Worker starts with `KANBAN_TASK_ID` set, OR worker self-claims from board.

**Steps**:
1. Read `KANBAN_TASK_ID` env var
2. If set: call `kanban_get(task_id)` to fetch task details
3. If not set: call `kanban_list(status="ready")`, pick one, call `kanban_claim(task_id, ttl_seconds=3600)`
4. Record `workspace_path` as current working directory

### Phase 2: Execute

**Trigger**: Task claimed, worker begins work.

**Steps**:
1. Send first heartbeat: `kanban_heartbeat(task_id, note="Starting task")`
2. Execute task — see Task Types below
3. Send periodic heartbeat every ~60 seconds during long operations
4. If blocked: call `kanban_block(task_id, reason="<reason>")` and stop heartbeat
5. If unblocked: call `kanban_unblock(task_id)` and resume heartbeat

### Phase 3: Complete

**Trigger**: Task work is done (success or failure).

**Steps**:
1. Call `kanban_complete(task_id, result=..., summary=..., metadata=...)`
2. For success: `outcome="completed"`
3. For failure: `outcome="failed"`, include `error` in metadata
4. If sub-tasks were created: include `created_cards=["t_xxx", ...]`

---

## API Schema

### kanban_get

```yaml
tool: kanban_get
args:
  task_id: string  # required
```

Returns full task record:
```json
{
  "id": "t_abc123",
  "title": "Implement feature X",
  "body": "Detailed spec...",
  "status": "claimed",
  "assignee": "worker-1",
  "priority": "medium",
  "workspace_kind": "local",
  "workspace_path": "/tmp/kanban-workspace/t_abc123",
  "skills": ["python", "testing"],
  "max_runtime_seconds": 7200,
  "created_by": "dispatcher",
  "created_at": "2026-05-18T10:00:00Z",
  "started_at": "2026-05-18T10:05:00Z",
  "claim_lock": "worker-1",
  "claim_expires": "2026-05-18T11:05:00Z",
  "last_heartbeat_at": "2026-05-18T10:35:00Z",
  "consecutive_failures": 0
}
```

### kanban_claim

```yaml
tool: kanban_claim
args:
  task_id: string
  ttl_seconds: integer  # default: 3600
```

Claims a task. Fails if:
- Task is not in `ready` or `claimed` status
- Task already claimed by another worker
- TTL must be > 0 and <= 86400

Returns: `{"claimed": true, "task": {...}}`

### kanban_heartbeat

```yaml
tool: kanban_heartbeat
args:
  task_id: string
  note: string  # optional: current progress note
```

Extends claim TTL by `ttl_seconds` from original claim.
Records heartbeat timestamp + optional progress note in `task_events`.

Returns: `{"ok": true, "next_heartbeat_due": "..."}`

### kanban_complete

```yaml
tool: kanban_complete
args:
  task_id: string
  result: string  # required: what was produced
  summary: string  # required: one-line board summary
  metadata: object  # optional
  created_cards: list[string]  # optional: sub-task IDs created
  expected_run_id: string  # optional: verify this run_id matches
```

**Hallucination detection**: If `created_cards` is provided:
1. Each ID is looked up in `tasks` table
2. Each ID's `created_by` must match caller's profile
3. If any ID is fake or belongs to another profile: raise `HallucinationError`

**Prose scan**: Extract all `t_<hex>` patterns from `result` and `summary`. If any extracted ID is not in `tasks`, record as unresolved reference.

Returns: `{"completed": true, "task": {...}}`

### kanban_block

```yaml
tool: kanban_block
args:
  task_id: string
  reason: string  # required
```

Moves task to `blocked` status. Records `reason` in `task_events`.

Returns: `{"blocked": true}`

### kanban_unblock

```yaml
tool: kanban_unblock
args:
  task_id: string
```

Moves task back to `in_progress` status.

Returns: `{"unblocked": true}`

### kanban_list

```yaml
tool: kanban_list
args:
  status: string  # optional: "ready" | "claimed" | "in_progress" | "blocked" | "completed" | "failed"
  assignee: string  # optional: filter by assignee
  limit: integer  # optional: max results (default: 50)
```

Returns list of tasks matching filter.

### kanban_link

```yaml
tool: kanban_link
args:
  parent_id: string
  child_id: string
```

Creates parent-child dependency. Fails if:
- Either task does not exist
- Link would create a cycle (DFS check)

Child is demoted from `ready` to `todo` if parent is not `completed`.

### kanban_add_comment

```yaml
tool: kanban_add_comment
args:
  task_id: string
  author: string
  body: string
```

Adds a comment to a task. Comments are stored in `task_comments` table.

---

## Task Types

### Coding Task

```python
# 1. Read workspace spec
task = kanban_get(task_id)
workspace = task["workspace_path"]

# 2. Implement
# ... code changes ...

# 3. Report changed files
kanban_complete(
    task_id,
    result=f"Implemented {task['title']}. Changes: ...",
    summary="Feature X implemented",
    metadata={
        "changed_files": ["src/feature_x.py", "tests/test_x.py"],
        "tests_run": 42,
        "tests_passed": 42,
    }
)
```

### Research Task

```python
# 1. Acquire
task = kanban_get(task_id)

# 2. Research
# ... web search, reading, synthesis ...

# 3. Report
kanban_complete(
    task_id,
    result="## Research Findings\n\n...",
    summary="Research on X completed",
    metadata={
        "sources_consulted": 12,
        "key_findings": ["...", "..."],
    }
)
```

### Writing Task

```python
# 1. Acquire
task = kanban_get(task_id)

# 2. Write
# ... document creation ...

# 3. Report
kanban_complete(
    task_id,
    result="# Document Title\n\n...",
    summary="Blog post on X written",
    metadata={
        "word_count": 1200,
        "files_created": ["content/blog/x.md"],
    }
)
```

---

## Worker Ownership Enforcement

Workers can only mutate tasks where:
- `claim_lock == KANBAN_WORKER_PID`, OR
- `created_by == current_session_profile`

Without a valid claim, mutation is rejected with `PermissionError`.

Heartbeats are the exception — any worker can send a heartbeat for any claimed task to keep it alive.

---

## Error Handling

| Error | Cause | Recovery |
|-------|-------|----------|
| `TaskNotFoundError` | Task ID does not exist | Check ID spelling |
| `ClaimExpiredError` | Claim TTL expired | Re-claim task |
| `AlreadyClaimedError` | Another worker holds the lock | Pick a different task |
| `HallucinationError` | Fake ID in `created_cards` | Verify IDs before calling complete |
| `CycleDetectedError` | `kanban_link` would create a cycle | Redesign dependency graph |
| `MaxRetriesExceeded` | `consecutive_failures >= max_retries` | Task moved to `failed` state |

---

## Examples

### Self-contained worker script

```python
import os
from drewgent_kanban_db import DrewgentTaskStore

task_store = DrewgentTaskStore()

task_id = os.getenv("KANBAN_TASK_ID")
if task_id:
    task = task_store.get_task(task_id)
    print(f"Working on: {task['title']}")
    
    task_store.heartbeat(task_id, note="Starting")
    
    # ... do work ...
    
    task_store.complete(
        task_id,
        result="Work completed",
        summary="Done",
        metadata={"steps": 3},
    )
else:
    # Self-claim
    tasks = task_store.list_tasks(status="ready", limit=1)
    if tasks:
        task_id = tasks[0]["id"]
        task_store.claim(task_id, ttl_seconds=3600)
        # ... same flow ...
```

### Dispatched worker (env-based)

```bash
export KANBAN_TASK_ID=t_abc123
export KANBAN_WORKER_PID=$$
python3 worker_script.py
```

---

## Related

- [[../SKILL]] — Kanban Worker skill overview
- [[@memory/growth/drewgent-kanban-implementation-plan]] — Full implementation plan