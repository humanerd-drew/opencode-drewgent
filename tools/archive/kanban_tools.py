#!/usr/bin/env python3
"""
Kanban Tool Module - Drewgent Task Queue Management

Provides persistent task queue with dependency tracking, hallucination detection,
and worker ownership enforcement via drewgent_tasks.db.

Tools:
    kanban_create, kanban_complete, kanban_block, kanban_unblock,
    kanban_claim, kanban_heartbeat, kanban_list, kanban_get,
    kanban_link, kanban_add_comment, kanban_get_events

DB: ~/.drewgent/state/drewgent_tasks.db
"""

import json
import logging
import os
import re
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DREW_HOME = Path(os.environ.get("DREW_HOME", Path.home() / ".drewgent"))
_DB_PATH = _DREW_HOME / "P2-hippocampus" / "kanban" / "state" / "drewgent_tasks.db"

_lock = threading.Lock()


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH), timeout=30)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


# =============================================================================
# Helpers
# =============================================================================


def _task_exists(conn: sqlite3.Connection, task_id: str) -> bool:
    cur = conn.execute("SELECT 1 FROM tasks WHERE id = ?", (task_id,))
    return cur.fetchone() is not None


def _next_id() -> str:
    import uuid
    return f"t_{uuid.uuid4().hex[:12]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# =============================================================================
# kanban_create
# =============================================================================


def kanban_create(
    title: str,
    body: Optional[str] = None,
    assignee: Optional[str] = None,
    workspace_kind: Optional[str] = None,
    workspace_path: Optional[str] = None,
    priority: int = 0,
    parent_task_ids: Optional[List[str]] = None,
    idempotency_key: Optional[str] = None,
    skills: Optional[List[str]] = None,
    max_runtime_seconds: int = 3600,
    trigger_source: str = "manual",
    board: str = "default",
) -> str:
    """
    Create a new task in Drewgent's task store.

    Args:
        title: Task title (required)
        body: Task description/body
        assignee: Assignee name (default: "drewgent")
        workspace_kind: "cli" | "gateway" | None
        workspace_path: Working directory path
        priority: 0=low, 1=medium, 2=high
        parent_task_ids: Parent task IDs — task goes to 'todo' if any parent is not completed
        idempotency_key: If set and a task with this key already exists, return existing task_id
        skills: List of skill names for the worker
        max_runtime_seconds: TTL for worker (default 3600)
        trigger_source: 'manual' | 'cron' | 'subagent' | 'activity_logger'
        board: Board name (default: "default")

    Returns:
        JSON string with task_id
    """
    with _lock:
        conn = _get_conn()
        try:
            # Idempotency check
            if idempotency_key:
                existing = conn.execute(
                    "SELECT id FROM tasks WHERE idempotency_key = ?",
                    (idempotency_key,),
                ).fetchone()
                if existing:
                    return json.dumps({"task_id": existing[0], "status": "existing"})

            task_id = _next_id()
            now_ts = _now()

            # Determine initial status based on parent completion
            if parent_task_ids:
                parent_statuses = conn.execute(
                    "SELECT status FROM tasks WHERE id IN (%s)"
                    % ",".join(["?"] * len(parent_task_ids)),
                    parent_task_ids,
                ).fetchall()
                all_done = all(s[0] == "completed" for s in parent_statuses)
                initial_status = "ready" if all_done else "todo"
            else:
                initial_status = "ready"

            conn.execute(
                """INSERT INTO tasks
                (id, title, body, assignee, status, priority, board,
                 created_by, created_at, workspace_kind, workspace_path,
                 idempotency_key, skills, max_runtime_seconds, trigger_source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    task_id,
                    title,
                    body or "",
                    assignee or "drewgent",
                    initial_status,
                    priority,
                    board,
                    os.getenv("USER", "unknown"),
                    now_ts,
                    workspace_kind or "",
                    workspace_path or "",
                    idempotency_key or "",
                    ",".join(skills) if skills else "",
                    max_runtime_seconds,
                    trigger_source,
                ),
            )

            # Create parent-child links
            if parent_task_ids:
                for parent_id in parent_task_ids:
                    conn.execute(
                        "INSERT OR IGNORE INTO task_links (parent_id, child_id) VALUES (?, ?)",
                        (parent_id, task_id),
                    )

            conn.commit()

            # Emit tool activity signal
            try:
                from agent.brain_signals import get_signal_emitter
                emitter = get_signal_emitter()
                if emitter:
                    emitter.emit_tool_complete(
                        tool_name="kanban:create",
                        result=task_id,
                        success=True,
                    )
            except Exception:
                pass

            return json.dumps({"task_id": task_id, "status": initial_status})

        finally:
            conn.close()


# =============================================================================
# kanban_complete
# =============================================================================


def kanban_complete(
    task_id: str,
    result: Optional[str] = None,
    summary: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    created_cards: Optional[List[str]] = None,
) -> str:
    """
    Mark a task as completed.

    Args:
        task_id: Task ID (required)
        result: Task result description
        summary: Summary of what was done
        metadata: Dict of additional metadata (changed_files, etc.)
        created_cards: List of task IDs created as subtasks during this task.
                       Each ID is verified against the DB (hallucination detection).

    Returns:
        JSON string with completion status

    Raises:
        ValueError: If any ID in created_cards is not in the DB (hallucination blocked)
    """
    with _lock:
        conn = _get_conn()
        try:
            # Hallucination detection
            invalid_ids = []
            if created_cards:
                for cid in created_cards:
                    if not _task_exists(conn, cid):
                        invalid_ids.append(cid)

            if invalid_ids:
                # Fire completion_blocked_hallucination event
                try:
                    from agent.brain_signals import get_signal_emitter
                    emitter = get_signal_emitter()
                    if emitter:
                        emitter.emit_tool_complete(
                            tool_name="kanban:complete",
                            result=f"hallucination_blocked: {invalid_ids}",
                            success=False,
                        )
                except Exception:
                    pass

                return json.dumps({
                    "error": f"Hallucination detected: invalid task IDs {invalid_ids}",
                    "blocked": True,
                })

            # Prose scan: extract t_<hex> patterns from result/summary
            prose_text = f"{result or ''} {summary or ''}"
            found_ids = re.findall(r"t_[0-9a-f]{12}", prose_text)
            unresolved = [fid for fid in found_ids if not _task_exists(conn, fid)]

            now_ts = _now()
            metadata_json = json.dumps(metadata) if metadata else ""

            conn.execute(
                """UPDATE tasks SET status='completed', completed_at=?,
                result=?, consecutive_failures=0 WHERE id=?""",
                (now_ts, summary or result or "", task_id),
            )

            # Log event
            conn.execute(
                "INSERT INTO task_events (task_id, run_id, kind, payload, created_at) VALUES (?, ?, ?, ?, ?)",
                (task_id, "", "completed", json.dumps({"result": result, "summary": summary}), now_ts),
            )

            conn.commit()

            # Promote children that were waiting for this parent
            children = conn.execute(
                "SELECT child_id FROM task_links WHERE parent_id = ?",
                (task_id,),
            ).fetchall()
            for (child_id,) in children:
                # Check if all other parents are completed
                other_parents = conn.execute(
                    """SELECT COUNT(*) FROM task_links tl
                    JOIN tasks t ON t.id = tl.parent_id
                    WHERE tl.child_id = ? AND tl.parent_id != ? AND t.status != 'completed'""",
                    (child_id, task_id),
                ).fetchone()[0]
                if other_parents == 0:
                    # All parents done — promote to ready
                    conn.execute(
                        "UPDATE tasks SET status='ready' WHERE id=? AND status='todo'",
                        (child_id,),
                    )

            conn.commit()

# Emit tool activity signal (existing infrastructure)
            try:
                from agent.brain_signals import get_signal_emitter
                emitter = get_signal_emitter()
                if emitter:
                    emitter.emit_tool_complete(
                        tool_name="kanban:complete",
                        result="ok",
                        success=True,
                    )
            except Exception:
                pass

            return json.dumps({"task_id": task_id, "status": "completed", "unresolved_refs": unresolved})

        finally:
            conn.close()


# =============================================================================
# kanban_block / kanban_unblock
# =============================================================================


def kanban_block(task_id: str, reason: Optional[str] = None) -> str:
    """Block a task with a reason."""
    with _lock:
        conn = _get_conn()
        try:
            now_ts = _now()
            conn.execute(
                "UPDATE tasks SET status='blocked' WHERE id=? AND status NOT IN ('completed','blocked')",
                (task_id,),
            )
            conn.execute(
                "INSERT INTO task_events (task_id, run_id, kind, payload, created_at) VALUES (?, ?, ?, ?, ?)",
                (task_id, "", "blocked", json.dumps({"reason": reason}), now_ts),
            )
            conn.commit()

            try:
                from agent.brain_signals import get_signal_emitter
                emitter = get_signal_emitter()
                if emitter:
                    emitter.emit_tool_complete(
                        tool_name="kanban:block",
                        result=task_id,
                        success=True,
                    )
            except Exception:
                pass

            return json.dumps({"task_id": task_id, "status": "blocked"})
        finally:
            conn.close()


def kanban_unblock(task_id: str) -> str:
    """Unblock a blocked task. Returns to 'ready' status."""
    with _lock:
        conn = _get_conn()
        try:
            conn.execute(
                "UPDATE tasks SET status='ready' WHERE id=? AND status='blocked'",
                (task_id,),
            )
            conn.execute(
                "INSERT INTO task_events (task_id, run_id, kind, payload, created_at) VALUES (?, ?, ?, ?, ?)",
                (task_id, "", "unblocked", "{}", _now()),
            )
            conn.commit()
            return json.dumps({"task_id": task_id, "status": "ready"})
        finally:
            conn.close()


# =============================================================================
# kanban_claim / kanban_heartbeat
# =============================================================================


def kanban_claim(task_id: str, ttl_seconds: int = 3600) -> str:
    """Claim a task for the current worker."""
    with _lock:
        conn = _get_conn()
        try:
            import time
            expires = datetime.fromtimestamp(time.time() + ttl_seconds, tz=timezone.utc).isoformat()
            conn.execute(
                """UPDATE tasks SET status='in_progress', claim_lock=?,
                claim_expires=?, worker_pid=? WHERE id=? AND status IN ('todo','ready')""",
                (os.getpid(), expires, os.getpid(), task_id),
            )
            conn.commit()

            row = conn.execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()
            if row and row[0] == "in_progress":
                return json.dumps({"task_id": task_id, "status": "in_progress", "expires": expires})
            return json.dumps({"error": "Task not available or already claimed"})
        finally:
            conn.close()


def kanban_heartbeat(task_id: str, note: Optional[str] = None) -> str:
    """Send a heartbeat for a running task."""
    with _lock:
        conn = _get_conn()
        try:
            now_ts = _now()
            conn.execute(
                "UPDATE tasks SET last_heartbeat_at=? WHERE id=?",
                (now_ts, task_id),
            )
            if note:
                conn.execute(
                    "INSERT INTO task_events (task_id, run_id, kind, payload, created_at) VALUES (?, ?, ?, ?, ?)",
                    (task_id, "", "heartbeat", json.dumps({"note": note}), now_ts),
                )
            conn.commit()
            return json.dumps({"task_id": task_id, "heartbeat": now_ts})
        finally:
            conn.close()


# =============================================================================
# kanban_list
# =============================================================================


def kanban_list(
    status: Optional[str] = None,
    assignee: Optional[str] = None,
    board: str = "default",
) -> str:
    """List tasks with optional filters."""
    conn = _get_conn()
    try:
        query = "SELECT id, title, body, assignee, status, priority, board, created_at, completed_at FROM tasks WHERE 1=1"
        args: List[str] = []
        if status:
            query += " AND status=?"
            args.append(status)
        if assignee:
            query += " AND assignee=?"
            args.append(assignee)
        if board:
            query += " AND board=?"
            args.append(board)
        query += " ORDER BY created_at DESC LIMIT 50"

        rows = conn.execute(query, args).fetchall()
        tasks = [
            {
                "id": r[0],
                "title": r[1],
                "body": r[2],
                "assignee": r[3],
                "status": r[4],
                "priority": r[5],
                "board": r[6],
                "created_at": r[7],
                "completed_at": r[8],
            }
            for r in rows
        ]
        return json.dumps({"tasks": tasks, "count": len(tasks)})
    finally:
        conn.close()


# =============================================================================
# kanban_get
# =============================================================================


def kanban_get(task_id: str) -> str:
    """Get a single task by ID."""
    conn = _get_conn()
    try:
        row = conn.execute(
            """SELECT id, title, body, assignee, status, priority, board, created_at,
            started_at, completed_at, claim_lock, claim_expires, result,
            worker_pid, max_runtime_seconds, last_heartbeat_at, trigger_source, board
            FROM tasks WHERE id=?""",
            (task_id,),
        ).fetchone()
        if not row:
            return json.dumps({"error": f"Task {task_id} not found"})

        return json.dumps({
            "id": row[0],
            "title": row[1],
            "body": row[2],
            "assignee": row[3],
            "status": row[4],
            "priority": row[5],
            "board": row[6],
            "created_at": row[7],
            "started_at": row[8],
            "completed_at": row[9],
            "claim_lock": row[10],
            "claim_expires": row[11],
            "result": row[12],
            "worker_pid": row[13],
            "max_runtime_seconds": row[14],
            "last_heartbeat_at": row[15],
            "trigger_source": row[16],
        })
    finally:
        conn.close()


# =============================================================================
# kanban_link
# =============================================================================


def kanban_link(parent_id: str, child_id: str) -> str:
    """Create a parent-child dependency between two tasks."""
    with _lock:
        conn = _get_conn()
        try:
            # Cycle detection using DFS
            visited = set()

            def has_cycle(current: str) -> bool:
                if current == parent_id:
                    return True
                if current in visited:
                    return False
                visited.add(current)
                children = conn.execute(
                    "SELECT child_id FROM task_links WHERE parent_id=?",
                    (current,),
                ).fetchall()
                for (child,) in children:
                    if has_cycle(child):
                        return True
                return False

            if has_cycle(child_id):
                return json.dumps({"error": "Cycle detected — link refused"})

            conn.execute(
                "INSERT OR IGNORE INTO task_links (parent_id, child_id) VALUES (?, ?)",
                (parent_id, child_id),
            )
            conn.commit()
            return json.dumps({"parent_id": parent_id, "child_id": child_id, "linked": True})
        finally:
            conn.close()


# =============================================================================
# kanban_add_comment
# =============================================================================


def kanban_add_comment(task_id: str, author: str, body: str) -> str:
    """Add a comment to a task."""
    with _lock:
        conn = _get_conn()
        try:
            now_ts = _now()
            conn.execute(
                "INSERT INTO task_comments (task_id, author, body, created_at) VALUES (?, ?, ?, ?)",
                (task_id, author, body, now_ts),
            )
            conn.commit()
            return json.dumps({"task_id": task_id, "comment_at": now_ts})
        finally:
            conn.close()


# =============================================================================
# kanban_get_events
# =============================================================================


def kanban_get_events(task_id: str, limit: int = 20) -> str:
    """Get events for a task."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT task_id, run_id, kind, payload, created_at
            FROM task_events WHERE task_id=? ORDER BY created_at DESC LIMIT ?""",
            (task_id, limit),
        ).fetchall()
        events = [
            {
                "task_id": r[0],
                "run_id": r[1],
                "kind": r[2],
                "payload": r[3],
                "created_at": r[4],
            }
            for r in rows
        ]
        return json.dumps({"events": events})
    finally:
        conn.close()


# =============================================================================
# Schema for registry
# =============================================================================


KANBAN_TOOLS_SCHEMA = {
    "kanban_create": {
        "type": "function",
        "function": {
            "name": "kanban_create",
            "description": "Create a new task in Drewgent's persistent task queue. Use this to track work items, sub-tasks, and integration workflow steps. Parent-child dependencies are supported — a task with incomplete parents goes to 'todo' status until parents are completed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title (required)"},
                    "body": {"type": "string", "description": "Task description"},
                    "assignee": {"type": "string", "description": "Assignee name (default: 'drewgent')"},
                    "workspace_kind": {"type": "string", "description": "cli|gateway|None"},
                    "workspace_path": {"type": "string", "description": "Working directory"},
                    "priority": {"type": "integer", "description": "0=low, 1=medium, 2=high"},
                    "parent_task_ids": {"type": "array", "items": {"type": "string"}, "description": "Parent task IDs for dependency tracking"},
                    "idempotency_key": {"type": "string", "description": "Deduplication key"},
                    "skills": {"type": "array", "items": {"type": "string"}, "description": "Skill names for the worker"},
                    "max_runtime_seconds": {"type": "integer", "description": "TTL for worker (default 3600)"},
                    "trigger_source": {"type": "string", "description": "manual|cron|subagent|activity_logger"},
                    "board": {"type": "string", "description": "Board name (default: 'default')"},
                },
                "required": ["title"],
            },
        },
    },
    "kanban_complete": {
        "type": "function",
        "function": {
            "name": "kanban_complete",
            "description": "Mark a task as completed. Hallucination detection: if you created sub-tasks (new kanban cards) during work, pass their IDs in created_cards — the system verifies each exists in the DB. A fake ID will block completion and fire a completion_blocked_hallucination event. Also performs prose scan for t_<hex> patterns in result/summary and warns on unresolved refs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID (required)"},
                    "result": {"type": "string", "description": "Task result description"},
                    "summary": {"type": "string", "description": "Summary of what was done"},
                    "metadata": {"type": "object", "description": "Additional metadata (changed_files, etc.)"},
                    "created_cards": {"type": "array", "items": {"type": "string"}, "description": "Sub-task IDs created during this task (for hallucination detection)"},
                },
                "required": ["task_id"],
            },
        },
    },
    "kanban_block": {
        "type": "function",
        "function": {
            "name": "kanban_block",
            "description": "Block a task with a reason. Blocked tasks cannot be claimed until unblocked.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID (required)"},
                    "reason": {"type": "string", "description": "Reason for blocking"},
                },
                "required": ["task_id"],
            },
        },
    },
    "kanban_unblock": {
        "type": "function",
        "function": {
            "name": "kanban_unblock",
            "description": "Unblock a blocked task. Task returns to 'ready' status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID (required)"},
                },
                "required": ["task_id"],
            },
        },
    },
    "kanban_claim": {
        "type": "function",
        "function": {
            "name": "kanban_claim",
            "description": "Claim a task for the current worker process. Sets status='in_progress' and records worker PID and claim expiry. Only claims tasks that are 'todo' or 'ready'. Workers should send kanban_heartbeat every ~5 minutes during long tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID (required)"},
                    "ttl_seconds": {"type": "integer", "description": "Time-to-live in seconds (default: 3600)"},
                },
                "required": ["task_id"],
            },
        },
    },
    "kanban_heartbeat": {
        "type": "function",
        "function": {
            "name": "kanban_heartbeat",
            "description": "Send a heartbeat for a running task. Updates last_heartbeat_at timestamp. Workers should call this every ~5 minutes during long tasks to prevent automatic reclaim.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID (required)"},
                    "note": {"type": "string", "description": "Optional progress note"},
                },
                "required": ["task_id"],
            },
        },
    },
    "kanban_list": {
        "type": "function",
        "function": {
            "name": "kanban_list",
            "description": "List tasks from Drewgent's task store with optional filters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Filter by status: todo|ready|in_progress|blocked|completed"},
                    "assignee": {"type": "string", "description": "Filter by assignee"},
                    "board": {"type": "string", "description": "Board name (default: 'default')"},
                },
            },
        },
    },
    "kanban_get": {
        "type": "function",
        "function": {
            "name": "kanban_get",
            "description": "Get a single task by ID. Returns all fields including current status, body, assignee, claim info, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID (required)"},
                },
                "required": ["task_id"],
            },
        },
    },
    "kanban_link": {
        "type": "function",
        "function": {
            "name": "kanban_link",
            "description": "Create a parent-child dependency between two tasks. Child task is automatically set to 'todo' if parent is not yet completed. Uses DFS cycle detection to prevent circular dependencies.",
            "parameters": {
                "type": "object",
                "properties": {
                    "parent_id": {"type": "string", "description": "Parent task ID"},
                    "child_id": {"type": "string", "description": "Child task ID"},
                },
                "required": ["parent_id", "child_id"],
            },
        },
    },
    "kanban_add_comment": {
        "type": "function",
        "function": {
            "name": "kanban_add_comment",
            "description": "Add a comment to a task. Comments are used for human guidance, revision requests, and approval/rejection feedback.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID (required)"},
                    "author": {"type": "string", "description": "Comment author name"},
                    "body": {"type": "string", "description": "Comment text"},
                },
                "required": ["task_id", "author", "body"],
            },
        },
    },
    "kanban_get_events": {
        "type": "function",
        "function": {
            "name": "kanban_get_events",
            "description": "Get events for a task. Returns the event log including created, claimed, heartbeat, blocked, completed, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID (required)"},
                    "limit": {"type": "integer", "description": "Max events to return (default: 20)"},
                },
                "required": ["task_id"],
            },
        },
    },
}


# =============================================================================
# Register tools with registry
# =============================================================================


def kanban_tool(input: str) -> str:
    """
    Kanban tool entry point — routes to individual kanban_* functions.

    Input format: JSON string with 'action' and 'args' fields.
    Example: '{"action":"kanban_create","args":{"title":"My task"}}'
    """
    try:
        parsed = json.loads(input)
    except (json.JSONDecodeError, TypeError):
        return json.dumps({"error": "Invalid JSON input"})

    action = parsed.get("action", "")
    args = parsed.get("args", {})

    handlers = {
        "kanban_create": kanban_create,
        "kanban_complete": kanban_complete,
        "kanban_block": kanban_block,
        "kanban_unblock": kanban_unblock,
        "kanban_claim": kanban_claim,
        "kanban_heartbeat": kanban_heartbeat,
        "kanban_list": kanban_list,
        "kanban_get": kanban_get,
        "kanban_link": kanban_link,
        "kanban_add_comment": kanban_add_comment,
        "kanban_get_events": kanban_get_events,
    }

    handler = handlers.get(action)
    if not handler:
        return json.dumps({"error": f"Unknown kanban action: {action}"})

    try:
        return handler(**args)
    except TypeError as e:
        return json.dumps({"error": f"Argument error in {action}: {e}"})


from tools.registry import registry

# Register all kanban tools individually
for tool_name, schema in KANBAN_TOOLS_SCHEMA.items():
    handler_fn = globals()[tool_name]
    registry.register(
        name=tool_name,
        toolset="kanban",
        schema=schema,
        handler=handler_fn,
    )

# Also register the multi-action kanban_tool entry point
registry.register(
    name="kanban",
    toolset="kanban",
    schema={
        "type": "function",
        "function": {
            "name": "kanban",
            "description": "Multi-action kanban tool entry point. Use 'action' field to specify which kanban operation to perform: kanban_create, kanban_complete, kanban_list, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Kanban action: kanban_create, kanban_complete, kanban_block, kanban_unblock, kanban_claim, kanban_heartbeat, kanban_list, kanban_get, kanban_link, kanban_add_comment, kanban_get_events",
                    },
                    "args": {
                        "type": "object",
                        "description": "Arguments for the specified action",
                    },
                },
                "required": ["action", "args"],
            },
        },
    },
    handler=kanban_tool,
)