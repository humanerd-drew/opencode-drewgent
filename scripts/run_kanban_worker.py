#!/usr/bin/env python3
"""
Kanban Worker — executes tasks from the Drewgent kanban board.
Reads KANBAN_TASK_ID, fetches task details, runs the agent, reports completion.
"""
import json, os, sys, signal, time, tempfile, datetime
from pathlib import Path

DREW_HOME = Path(os.environ.get("DREW_HOME", Path.home() / ".drewgent"))
SRC_AGENT = DREW_HOME / "source" / "drewgent-agent"
DB_PATH = DREW_HOME / "P2-hippocampus" / "kanban" / "state" / "drewgent_tasks.db"
CONFIG_PATH = DREW_HOME / "config.yaml"

sys.path.insert(0, str(SRC_AGENT))


def _load_worker_config():
    """Load model config from config.yaml."""
    try:
        import yaml
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH) as f:
                cfg = yaml.safe_load(f)
            model_cfg = cfg.get("model", {})
            return model_cfg.get("model", ""), model_cfg.get("provider", "")
    except Exception:
        pass
    return "", ""


def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _resolve_parent_context(task_id: str) -> str:
    """Read parent task results and return as formatted context block.

    Tries JSON-parsed structured handoff (findings/risks/next).
    Falls back to plain text if result is not valid JSON.
    Logs warnings and records task_events for unparseable handoffs.
    """
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    parents = conn.execute(
        """SELECT p.id, p.title, p.result, p.skills
        FROM task_links tl JOIN tasks p ON p.id = tl.parent_id
        WHERE tl.child_id = ?
        ORDER BY p.completed_at""",
        (task_id,),
    ).fetchall()
    if not parents:
        conn.close()
        return ""

    blocks = []
    for pid, title, result, skills in parents:
        if not result or not result.strip():
            continue
        header = f"### {pid} ({title})"
        parsed = False
        try:
            data = json.loads(result)
            if isinstance(data, dict):
                parts = [header]
                for key, label in (("findings", "Findings"),
                                    ("risks", "Risks"),
                                    ("next", "Next Steps")):
                    items = data.get(key)
                    if items and isinstance(items, list):
                        parts.append(f"**{label}:**")
                        parts.extend(f"- {item}" for item in items)
                blocks.append("\n".join(parts))
                parsed = True
        except (json.JSONDecodeError, TypeError):
            pass

        if not parsed:
            preview = result[:200].replace("\n", " ").strip()
            print(f"[handoff] WARN parent {pid} ({title}): "
                  f"result is not valid JSON (len={len(result)}, "
                  f"preview=\"{preview}...\")")
            try:
                conn.execute(
                    "INSERT INTO task_events (task_id, run_id, kind, payload, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (pid, "", "handoff_failed",
                     json.dumps({
                         "child_id": task_id,
                         "preview": preview,
                         "skills": skills or "",
                     }),
                     _now()),
                )
                conn.commit()
            except Exception:
                pass
            blocks.append(
                f"{header}\n"
                f"*(⚠ Handoff format not recognized — raw output below)*\n"
                f"{result[:2000]}"
            )

    conn.close()
    if not blocks:
        return ""
    return "\n\n## ══ Context from previous steps ══\n\n" + "\n\n".join(blocks)


def _get_task(task_id):
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    row = conn.execute(
        """SELECT id, title, body, status, workspace_path, skills, max_runtime_seconds
        FROM tasks WHERE id=?""",
        (task_id,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0], "title": row[1], "body": row[2], "status": row[3],
        "workspace_path": row[4], "skills": row[5], "max_runtime_seconds": row[6],
    }


def _heartbeat(task_id, note=None):
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    now = _now()
    conn.execute("UPDATE tasks SET last_heartbeat_at=? WHERE id=?", (now, task_id))
    if note:
        conn.execute(
            "INSERT INTO task_events (task_id, run_id, kind, payload, created_at) VALUES (?, ?, ?, ?, ?)",
            (task_id, "", "heartbeat", json.dumps({"note": note}), now),
        )
    conn.commit()
    conn.close()
    return now


def _update_affinity(task_id, success):
    """Update worker affinity stats on task completion/failure."""
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=10)
        row = conn.execute("SELECT skills FROM tasks WHERE id=?", (task_id,)).fetchone()
        conn.close()
        if not row or not row[0]:
            return
        skills = [s.strip() for s in row[0].split(",") if s.strip()]
        if not skills:
            return
        aff_path = DREW_HOME / "P2-hippocampus" / "kanban" / "state" / "worker_affinity.json"
        affinity = {}
        if aff_path.exists():
            affinity = json.loads(aff_path.read_text())
        now_ts = datetime.datetime.now(datetime.timezone.utc).timestamp()
        for skill in skills:
            if skill not in affinity:
                affinity[skill] = {"success_count": 0, "failure_count": 0, "consecutive_failures": 0, "cooldown_until": 0}
            if success:
                affinity[skill]["success_count"] += 1
                affinity[skill]["consecutive_failures"] = 0
                affinity[skill]["cooldown_until"] = 0
            else:
                affinity[skill]["failure_count"] += 1
                affinity[skill]["consecutive_failures"] = affinity[skill].get("consecutive_failures", 0) + 1
                if affinity[skill]["consecutive_failures"] >= 3:
                    affinity[skill]["cooldown_until"] = now_ts + 3600  # 1 hour cooldown
        aff_path.parent.mkdir(parents=True, exist_ok=True)
        aff_path.write_text(json.dumps(affinity, indent=2))
    except Exception:
        pass


def _complete(task_id, result, summary, metadata=None):
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    now = _now()
    conn.execute(
        "UPDATE tasks SET status='completed', completed_at=?, result=? WHERE id=?",
        (now, summary or result or "", task_id),
    )
    conn.execute(
        "INSERT INTO task_events (task_id, run_id, kind, payload, created_at) VALUES (?, ?, ?, ?, ?)",
        (task_id, "", "completed", json.dumps({"result": result, "summary": summary}), now),
    )
    conn.commit()
    conn.close()
    _update_affinity(task_id, success=True)


def _fail(task_id, error_msg):
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    now = _now()
    conn.execute(
        "UPDATE tasks SET status='failed', consecutive_failures=consecutive_failures+1 WHERE id=?",
        (task_id,),
    )
    conn.execute(
        "INSERT INTO task_events (task_id, run_id, kind, payload, created_at) VALUES (?, ?, ?, ?, ?)",
        (task_id, "", "failed", json.dumps({"error": error_msg}), now),
    )
    conn.commit()
    conn.close()
    _update_affinity(task_id, success=False)


def run_worker(task_id):
    task = _get_task(task_id)
    if not task:
        print(f"Task {task_id} not found")
        return

    print(f"[worker] Starting task: {task['title']}")
    body_preview = task['body'][:200] if task['body'] else '(empty)'
    print(f"[worker] Body preview: {body_preview}...")

    ws_path = task["workspace_path"] if task["workspace_path"] and task["workspace_path"] != "None" else str(DREW_HOME)

    _heartbeat(task_id, note=f"Worker started at {_now()}")

    parent_context = _resolve_parent_context(task_id)
    venv_python = str(SRC_AGENT / ".venv" / "bin" / "python")

    prompt = task["body"] or task["title"]
    if parent_context:
        prompt += parent_context

    # Task classification: shell-only → 결정론적 subprocess (no LLM)
    if _is_shell_only_task(prompt):
        _run_shell_only_task(task_id, task, prompt, ws_path)
        return

    heartbeat_interval = 60
    last_heartbeat = time.time()

    model_name, model_provider = _load_worker_config()
    if not model_name:
        model_name = "MiniMax-M3"
    if not model_provider:
        model_provider = "minimax"

    escaped_prompt = prompt.replace("\\", "\\\\").replace("'", "\\'").replace("\r", "\\r").replace("\n", "\\n")

    script_content = (
        f"import sys, os, json\n"
        f"sys.path.insert(0, '{SRC_AGENT}')\n"
        f"os.environ['DREW_HOME'] = '{DREW_HOME}'\n"
        f"os.environ['KANBAN_TASK_ID'] = '{task_id}'\n"
        f"os.environ['KANBAN_WORKER_MODE'] = '1'\n"
        f"\n"
        f"from run_agent import AIAgent\n"
        f"\n"
        f"prompt = '{escaped_prompt}'.replace('\\\\\\\\n', '\\\\n').replace('\\\\\\\\x27', \"'\")\n"
        f"\n"
        f"agent = AIAgent(\n"
        f"    enabled_toolsets=['terminal', 'web', 'brain'],\n"
        f"    model='{model_name}',\n"
        f"    provider='{model_provider}',\n"
        f")\n"
        f"result = agent.chat(prompt)\n"
        f"print(json.dumps({{'success': True, 'result': result}}))\n"
    )

    env = os.environ.copy()
    env.update({
        'KANBAN_TASK_ID': task_id,
        'KANBAN_WORKER_MODE': '1',
        'DREW_HOME': str(DREW_HOME),
    })

    import subprocess as sp

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(script_content)
        script_path = f.name

    try:
        proc = sp.Popen(
            [venv_python, script_path],
            env=env, cwd=ws_path,
            stdout=sp.PIPE, stderr=sp.PIPE,
        )

        output = ""
        try:
            while True:
                ret = proc.poll()
                if ret is not None:
                    stdout, stderr = proc.communicate()
                    output = stdout.decode(errors="replace")
                    break

                if time.time() - last_heartbeat > heartbeat_interval:
                    _heartbeat(task_id, note=f"Heartbeat at {_now()}")
                    last_heartbeat = time.time()

                time.sleep(5)

            if proc.returncode != 0:
                stderr_str = stderr.decode(errors="replace") if stderr else ""
                error_msg = f"Worker exited with code {proc.returncode}: {stderr_str[:500]}"
                print(f"[worker] ERROR: {error_msg}")
                _fail(task_id, error_msg)
                return

            try:
                result_data = json.loads(output)
                agent_result = result_data.get("result", "")
            except Exception:
                agent_result = output[:2000]

            _complete(task_id, result=agent_result, summary=f"Completed: {task['title']}")
            print(f"[worker] Task {task_id} completed successfully")

        except KeyboardInterrupt:
            proc.terminate()
            proc.wait()
            _heartbeat(task_id, note=f"Worker interrupted at {_now()}")
            _fail(task_id, "Worker interrupted by signal")
            print(f"[worker] Task {task_id} interrupted")
        finally:
            try:
                os.unlink(script_path)
            except Exception:
                pass

    except Exception as e:
        print(f"[worker] SPAWN FAILED: {e}")
        _fail(task_id, f"Spawn failed: {e}")


def _is_shell_only_task(prompt: str) -> bool:
    """Classify a task as shell-only if its first non-empty line starts with a shell command.

    Shell-only tasks (e.g. "python3 cleanup.py", "bash run.sh") can be executed
    directly via subprocess without an LLM round-trip. Anything else
    (instruction prose, skill loads, plain notes) falls through to the LLM path.
    """
    if not prompt or not prompt.strip():
        return False
    first_line = next(
        (line.strip() for line in prompt.split("\n") if line.strip()), ""
    )
    if not first_line:
        return False
    # Common shell prefixes — conservative list to avoid false positives.
    shell_prefixes = (
        "python3", "python ",
        "bash ", "sh ",
        "node ", "ruby ", "perl ",
        "./", "/bin/", "/usr/bin/", "/usr/local/bin/",
    )
    return first_line.startswith(shell_prefixes)


def _run_shell_only_task(task_id: str, task: dict, prompt: str, ws_path: str) -> None:
    """Execute a shell-only task via direct subprocess — bypasses LLM entirely."""
    import subprocess as sp

    # First non-empty line is the command; rest is ignored (could be notes/comments)
    cmd_line = next(
        (line.strip() for line in prompt.split("\n") if line.strip()), ""
    )
    print(f"[worker] Shell-only task (no LLM): {cmd_line[:80]}")

    try:
        env = os.environ.copy()
        proc = sp.run(
            cmd_line, shell=True, capture_output=True, text=True,
            timeout=600, env=env, cwd=ws_path,
        )
        output_parts = [proc.stdout] if proc.stdout else []
        if proc.stderr:
            output_parts.append(f"\nstderr:\n{proc.stderr}")
        output = ("".join(output_parts)).strip() or "(no output)"

        if proc.returncode == 0:
            _complete(
                task_id,
                result=f"Shell-only completed: {cmd_line[:60]}",
                summary=output[:2000],
            )
            print(f"[worker] Task {task_id} completed (shell-only, exit=0)")
        else:
            _fail(task_id, f"Shell exit {proc.returncode}: {proc.stderr[:500]}")
            print(f"[worker] Task {task_id} failed (shell-only exit {proc.returncode})")
    except sp.TimeoutExpired:
        _fail(task_id, f"Shell timeout (600s): {cmd_line[:60]}")
        print(f"[worker] Task {task_id} failed (shell-only timeout)")
    except Exception as e:
        _fail(task_id, f"Shell error: {type(e).__name__}: {e}")
        print(f"[worker] Task {task_id} failed (shell-only error)")


def main():
    task_id = os.environ.get("KANBAN_TASK_ID")
    if not task_id:
        print("KANBAN_TASK_ID not set — nothing to do")
        sys.exit(0)

    run_worker(task_id)


if __name__ == "__main__":
    main()