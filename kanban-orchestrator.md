---
title: Kanban Orchestrator
type: document
space: concept
tags: [concept]
created: 2026-05-23
updated: 2026-05-30
links:
  - "[[P4-cortex/knowledge/NEURONFS_RULES]]"
  - "[[scripts/run_kanban_worker.py]]"
---

# Kanban Orchestrator

Autonomous task queue system for Drewgent — workers claim tasks from the kanban board, execute them via AIAgent, and report completion.

## Architecture

```
kanban_create()    → dispatch_once_*    → run_kanban_worker.py → AIAgent → kanban_complete/fail()
     ↑                                                                   ↓
  user/agent                    claim+spawn workers              heartbeat (60s)
```

## Components

### `scripts/run_kanban_worker.py`

Worker script that:
1. Reads `KANBAN_TASK_ID` from environment
2. Loads `model` and `provider` from `~/.drewgent/config.yaml` via `_load_worker_config()`
3. Initializes `AIAgent(model, provider)` with `kanban_complete` and `kanban_fail` tools available
4. Sends heartbeat to kanban DB every 60s
5. Executes task body through AIAgent conversation loop
6. Calls `kanban_complete(task_id)` on success or `kanban_fail(task_id, error)` on failure

### `scripts/dispatch_once_content.py` / `scripts/dispatch_once_default.py`

Dispatch scripts that:
1. Scan kanban board for `ready` tasks
2. Claim first available task (set status=`claimed`, worker_id=hostname)
3. Spawn `run_kanban_worker.py` as subprocess via tempfile + venv python
4. Return immediately (non-blocking)

### Kanban Tools (`tools/kanban_tools.py`)

11 tools + multi-action entry point:

| Tool | Action | Description |
|------|--------|-------------|
| `kanban_list` | list | List tasks by board/status |
| `kanban_create` | create | Create new task |
| `kanban_update` | update | Update task fields |
| `kanban_delete` | delete | Delete task |
| `kanban_claim` | claim | Claim/assign task |
| `kanban_complete` | complete | Mark completed |
| `kanban_fail` | fail | Mark failed |
| `kanban_reclaim_stale` | reclaim_stale | Reclaim stale in-progress tasks |
| `kanban_archive` | archive | Archive task |
| `kanban_get` | get | Get single task |
| `kanban_board_list` | board_list | List boards |

Multi-action: `kanban` — dispatches by `action` field.

### State Storage

SQLite DB: `~/.drewgent/P2-hippocampus/kanban/state/drewgent_tasks.db`

Schema:
- `tasks` — id, board, title, body, status, priority, worker_id, result, created_at, updated_at
- `task_events` — id, task_id, event_type, payload (JSON), created_at

## Workflow

### Creating a Task

```python
from tools.kanban_tools import kanban_create

result = kanban_create(
    title="Deploy Drewgent update",
    body="Run: drewgent tools update && drewgent restart",
    board="default",
    priority=1
)
# Returns: {"task_id": "t_xxx", "status": "ready"}
```

### Dispatching Tasks

```bash
# Dispatch from content board
python3 ~/.drewgent/scripts/dispatch_once_content.py

# Dispatch from default board
python3 ~/.drewgent/scripts/dispatch_once_default.py
```

Output: `claimed=N | spawned=N | reclaimed=N | skipped=N`

### Task Lifecycle

```
ready → claimed → completed
             ↘ failed
             ↘ in_progress (via heartbeat)
```

Stale tasks (in_progress > 30 min, no heartbeat) are auto-reclaimed by dispatch scripts.

## Provider Support

Third-party Anthropic-compatible providers automatically configured:

| Provider | Model prefix | Endpoint |
|----------|-------------|----------|
| minimax | minimax-* | `https://api.minimax.io/anthropic/v1/messages` |
| minimax-cn | minimax-* | `https://api.minimax.io/anthropic/v1/messages` |
| alibaba | anthropic/* | `https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation` |
| deepseek | deepseek-* | `https://api.deepseek.com/anthropic/v1/messages` |

## Environment Variables

| Variable | Used by | Description |
|----------|---------|-------------|
| `KANBAN_TASK_ID` | `run_kanban_worker.py` | Task ID for worker to execute |
| `MINIMAX_API_KEY` | `resolve_api_key_provider_credentials` | MiniMax API key |
| `HERMES_HOME` | All components | Drewgent config directory |
