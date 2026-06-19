---
name: drewgent-llm-cost-opt-impl
title: Drewgent LLM Cost Optimization — 3-Round Implementation
description: 3-round implementation playbook (config → scheduler → worker) for reducing background/cron LLM calls in Drewgent. Use after `llm-cost-audit` produces candidate list. Captures verified pitfalls from 2026-06-02 production patch.
domain: devops
space: growth
type: skill
tags: [devops, cost, llm, optimization, implementation, drewgent]
created: 2026-06-02
updated: 2026-06-02
links:
  - "[[skills/devops/llm-cost-audit]]"
  - "[[skills/devops/cron-script-fastpath]]"
  - "[[skills/software-development/yaml-config-patch-drewgent]]"
  - "[[skills/software-development/llm-model-migration]]"
  - "[[P4-cortex/growth/KANBAN-REVIEW-20260520]]"
  - "[[P0-brainstem/brain/rules]]"---

# Drewgent LLM Cost Optimization — 3-Round Implementation

After `llm-cost-audit` produces candidate list, execute patches in this order
to minimize risk and maximize verifiable progress. Round 1 is cheap config-only
(0 risk, 5 min). Round 2 is scheduler bypass (medium risk, 1-2 hours, biggest
immediate savings). Round 3 is worker classifier (higher risk, regression test
required, future-proof safety net).

## When to use

- `llm-cost-audit` produced H1~H4 candidates with non-zero value
- Want to reduce LLM calls in background/cron without losing functionality
- Need to verify each round independently before moving on

Out of scope (different skills): token compression on tool output
(`token-compression-headroom`), model migration (`llm-model-migration`).

## Preflight: Verify "Done" claims (5 min, do this first)

Past reviews in `P4-cortex/growth/KANBAN-REVIEW-20260520.md` claimed
"✅ Done 결정론적 shell script" for `run_kanban_worker.py`, but **code drift
had made that claim false** — worker still calls LLM via AIAgent. Always
re-grep before relying on prior review claims:

```bash
# Verify scheduler/worker code matches the documented behavior
grep -n "AIAgent\|chat.completions\|messages.create" \
  ~/.drewgent/scripts/run_kanban_worker.py \
  ~/.drewgent/source/drewgent-agent/cron/scheduler.py

# Verify smart_routing cheap_model != main model (else routing effect 0)
grep -E "model:|cheap_model:" ~/.drewgent/config.yaml
```

Also check **DB path canonical** — `~/.drewgent/P2-hippocampus/kanban/state/drewgent_tasks.db`
is canonical. The top-level `~/.drewgent/state/` is stale. Verify:

```bash
find ~/.drewgent -name drewgent_tasks.db -not -path '*/.git/*' -not -path '*/node_modules/*' -not -path '*/archive/*'
# Two files will appear. Use the P2-hippocampus one for INSERT/SELECT.
```

## Round 1 — Config-only (5 min, 0 risk)

**Scope**: `auxiliary.compression` in BOTH `~/.drewgent/config.yaml` AND
`~/.drewgent/P5-ego/config/config.yaml`. Affects `title_generator.py:38` and
`context_compressor.py:364` (side tasks, max_tokens=30 summary).

**Change**:
```yaml
auxiliary:
  compression:
    provider: minimax     # was: auto
    model: 'MiniMax-M2.5'  # was: ''
    ...
```

**Verification**:
```python
import yaml
for p in [
    '/Users/drew/.drewgent/config.yaml',
    '/Users/drew/.drewgent/P5-ego/config/config.yaml',
]:
    c = yaml.safe_load(open(p))
    aux = c['auxiliary']['compression']
    assert aux['provider'] == 'minimax' and aux['model'] == 'MiniMax-M2.5', p
    # Confirm 7 other auxiliary tasks (vision, web_extract, session_search,
    # skills_hub, approval, mcp, flush_memories) are UNCHANGED
```

**⚠ P5-ego config duplication hazard**: P5-ego config has BOTH root-level
`compression:` (lines 43-50, with `summary_provider`/`summary_model`) AND
`auxiliary.compression:` (lines 72-77). When patching `auxiliary.compression`,
the `old_string` must include enough context to match only ONE of these.
A loose `old_string` of just `compression: ... enabled: true` can match BOTH
and the `new_string` will be inserted twice. Recovery: re-patch with full
multi-line context covering the second `compression:` block.

**Code path verification** (no LLM call needed): `auxiliary_client.py:1700-1762`
shows `cfg_provider != "auto"` branch returns `("minimax", "MiniMax-M2.5", ...)`
without falling through to the auto chain. So `call_llm(task="compression")`
will call minimax provider with M2.5. Verified 2026-06-02.

## Round 2 — Scheduler bypass (1-2 hours, medium risk, biggest immediate savings)

**Scope**: jobs.json cron jobs whose prompt is just `Run: python3 <script>.py`.
Pattern: prompt's effective action is "run this script and report the
output". LLM is overkill — `subprocess.run()` does the same thing.

**Add `script:` field to jobs.json** for jobs that fit:
- `cron-output-cleanup` (a130ff5768c1) — prompt is `Run: python3 .../cron_output_cleanup.py`
- `kanban-maintenance` (e402e47447c1) — same pattern, but no script exists yet

**In `cron/scheduler.py:run_job()`**, add script: branch INSIDE the try block
(after `try:` and BEFORE env-injection / AIAgent setup) so the `finally` block
(env cleanup, `session_db.end_session`) still runs:

```python
def run_job(job: dict) -> tuple[bool, str, str, Optional[str]]:
    # ... existing setup ...
    try:
        # Script-based fast path: LLM 거치지 않고 직접 subprocess 실행
        script_path = (job.get("script") or "").strip()
        if script_path:
            return _run_script_subprocess(
                job, script_path, origin, _cron_session_id, _session_db
            )
        # ... existing LLM path follows ...
```

**Add helper `_run_script_subprocess()`** (place after `def run_job()` and
its finally block, before `def tick()`):

```python
def _run_script_subprocess(
    job, script_path, origin, cron_session_id, session_db,
) -> tuple[bool, str, str, Optional[str]]:
    """Execute script-based cron job via direct subprocess (no LLM).
    Returns same tuple shape as run_job() so tick() delivery logic stays uniform."""
    expanded = os.path.expanduser(script_path)
    if not os.path.isfile(expanded):
        return False, "", "", f"Script not found: {expanded}"
    try:
        result = subprocess.run(
            [sys.executable, expanded],
            capture_output=True, text=True, timeout=300,
            env={**os.environ, "DREW_HOME": str(_drewgent_home)},
            cwd=str(_drewgent_home),
        )
        output = result.stdout.strip()
        if result.returncode != 0:
            return False, output, "", f"Script exit {result.returncode}: {result.stderr[:500]}"
        return True, output, output, None
    except subprocess.TimeoutExpired:
        return False, "", "", f"Script timeout (300s): {expanded}"
    except Exception as e:
        return False, "", "", f"{type(e).__name__}: {e}"
```

**If the cron job has no script yet** (e.g., `kanban-maintenance`):
- Write the script under `~/.drewgent/scripts/<job_name>.py` following the
  pattern in `P4-cortex/growth/kanban-maintenance-guide.md` if it exists
- Best-effort HTML refresh is OK (fail silently if script missing)
- Add the script path to jobs.json

**Verification** — dry-run with the real scheduler:

```python
import sys, json
sys.path.insert(0, '/Users/drew/.drewgent/source/drewgent-agent')
from cron.scheduler import run_job
jobs = json.load(open('/Users/drew/.drewgent/cron/jobs.json'))['jobs']
for job_id in ('a130ff5768c1', 'e402e47447c1'):
    job = next(j for j in jobs if j['id'] == job_id)
    success, output, final, error = run_job(job)
    # final_response is the script's stdout (e.g. "[SILENT]" or "Deleted: 0...")
    # No AIAgent instance was created — verify by absence of "Running job" log
```

Then check `~/.drewgent/cron/output/{board}/<job_id>_<timestamp>.md` exists
and matches LLM-path output format (since `tick()` reuses the same delivery
logic for both paths).

## Round 3 — Worker classifier (higher risk, regression test required)

**Scope**: `run_kanban_worker.py` spawns AIAgent for every kanban task.
Pattern: task body = `python3 <script>` is shell-only and can bypass LLM.
Currently 0 shell-prefix tasks in DB, so effect is 0 — but **future-proof
safety net** when shell tasks do enter the queue.

**⚠ DB path canonical (recheck)**: Insert tasks into
`P2-hippocampus/kanban/state/drewgent_tasks.db`, NOT `~/.drewgent/state/`.
The top-level is stale. `dispatch_once_default.py` only sees the P2 path.

**Add classifier + shell-only path to `run_kanban_worker.py`**:

```python
import re
SHELL_PREFIXES = (
    "python3", "python ", "bash ", "sh ", "node ", "ruby ", "perl ",
    "./", "/bin/", "/usr/bin/", "/usr/local/bin/",
)

def _is_shell_only_task(prompt: str) -> bool:
    """First non-empty line of prompt starts with a shell prefix → shell-only."""
    if not prompt or not prompt.strip():
        return False
    first = next((ln.strip() for ln in prompt.split("\n") if ln.strip()), "")
    return first.startswith(SHELL_PREFIXES)


def _run_shell_only_task(task_id, task, prompt, ws_path) -> None:
    """Execute shell-only task via subprocess — bypasses LLM entirely."""
    cmd_line = next((ln.strip() for ln in prompt.split("\n") if ln.strip()), "")
    try:
        proc = sp.run(cmd_line, shell=True, capture_output=True, text=True,
                      timeout=600, env=os.environ.copy(), cwd=ws_path)
        if proc.returncode == 0:
            _complete(task_id, result=f"Shell-only: {cmd_line[:60]}",
                      summary=(proc.stdout + proc.stderr).strip()[:2000] or "(no output)")
        else:
            _fail(task_id, f"Shell exit {proc.returncode}: {proc.stderr[:500]}")
    except Exception as e:
        _fail(task_id, f"{type(e).__name__}: {e}")


def run_worker(task_id):
    task = _get_task(task_id)
    if not task: return
    _heartbeat(task_id, note=f"Worker started at {_now()}")
    prompt = task["body"] or task["title"]
    if _is_shell_only_task(prompt):
        _run_shell_only_task(task_id, task, prompt, ws_path)
        return
    # ... existing LLM path (AIAgent) follows ...
```

**Verification — integration test**:

```python
import sqlite3, subprocess, time
DB = '/Users/drew/.drewgent/P2-hippocampus/kanban/state/drewgent_tasks.db'
VENV = '/Users/drew/.drewgent/source/drewgent-agent/.venv/bin/python'

# 1. Insert shell + instruction tasks
conn = sqlite3.connect(DB)
shell_id = f't_r3shell_{int(time.time())}'
instr_id  = f't_r3instr_{int(time.time())}'
conn.execute("INSERT INTO tasks ... VALUES (?, 'ready', 'default', 'python3 -c \"print(1)\"', ...)", (shell_id,))
conn.execute("INSERT INTO tasks ... VALUES (?, 'ready', 'default', 'Run kanban cleanup', ...)",  (instr_id,))
conn.commit(); conn.close()

# 2. Run dispatcher
subprocess.run([VENV, '/Users/drew/.drewgent/scripts/dispatch_once_default.py'],
               env={'DREW_HOME': '/Users/drew/.drewgent', **os.environ}, check=True)

# 3. Wait for workers, check logs
log_dir = Path('/Users/drew/.drewgent/P4-cortex/scripts/kanban/logs/workers')
for _ in range(30):
    if (log_dir / f'{shell_id}.log').exists() and (log_dir / f'{instr_id}.log').exists():
        time.sleep(2)  # let write settle
        break
    time.sleep(1)

# 4. Shell log: "Shell-only task (no LLM): python3 ..." then "completed (shell-only, exit=0)"
# 5. DB: shell task → status=completed, instruction task → status=in_progress (LLM still working)

# 6. Cleanup test tasks
conn = sqlite3.connect(DB)
conn.execute("DELETE FROM tasks WHERE id IN (?, ?)", (shell_id, instr_id))
conn.commit()
```

The shell task should reach `status=completed` within 5 seconds without any
LLM call. The instruction task will stay `in_progress` (LLM path working).

## Update docs after the work

If `P4-cortex/growth/KANBAN-REVIEW-20260520.md` had stale "✅ Done" claims
(e.g., "Missing 10: Worker KANBAN_WORKER_MODE env var not used"), correct
those cells to "⚠ Partial" and add a `## 2026-06-02 Follow-up` section at
the end. This is critical — future sessions will trust the docs.

## Pitfalls

- **P5-ego config duplication** (Round 1): root-level `compression:` and
  `auxiliary.compression:` both exist. Use unique multi-line `old_string`.
- **DB path stale** (Round 3): `~/.drewgent/state/` is stale; P2-hippocampus
  path is canonical. Two separate `drewgent_tasks.db` files exist.
- **Scheduler run_job() try-block placement** (Round 2): the `if script_path:`
  branch MUST be inside the try block so the finally cleanup runs
  (env vars popped, `session_db.end_session` called).
- **smart_routing.cheap_model = main model** (preflight): zero routing
  effect. If you only change config.yaml main model, also update the
  cheap_model entry.
- **"Done ✅" claims in old reviews** (preflight): code drifts. Re-grep
  every claim before relying on it.
- **Worker timeout mismatch** (Round 3): LLM path uses 600s for
  `agent.run_conversation`, but shell-only path uses 600s `subprocess.run`
  timeout. These are independent — adjust if your shell tasks need
  longer.
- **dispatch_once_default.py uses 'default' board, but board='integrations'
  or 'content' use their own dispatchers**: If a script-based job is on
  integrations/content board, patch those dispatchers too, not just
  `dispatch_once_default.py`. Actually NO — the scheduler branch is in
  `run_job()` in `cron/scheduler.py`, not in the dispatchers. So one
  patch covers all boards.

## Related skills

- `llm-cost-audit` — generates the candidate list (Steps 1-5 framework)
- `cron-script-fastpath` — Round 2 only (scheduler script: branch)
- `yaml-config-patch-drewgent` — Round 1 only (dual-config patching)
- `llm-model-migration` — M2.7→M3 catalog flip
- `token-compression-headroom` — tool output 4-layer cap (different lever)

## Verification checklist

- [ ] Preflight: KANBAN_REVIEW "Done" claims re-grepped, real state confirmed
- [ ] Preflight: smart_routing.cheap_model != main model
- [ ] Preflight: kanban DB path canonical (P2-hippocampus)
- [ ] R1: yaml.safe_load passes both configs, M2.5 set, 7 other aux unchanged
- [ ] R1: call_llm(task="compression") code path returns (minimax, M2.5)
- [ ] R2: scheduler.py syntax OK, _run_script_subprocess() defined
- [ ] R2: jobs.json script: field added (2 jobs), JSON valid
- [ ] R2: dry-run with run_job() — final_response = script stdout, no AIAgent
- [ ] R2: cron/output/ shows new .md file with script-style output
- [ ] R3: run_kanban_worker.py syntax OK, _is_shell_only_task + _run_shell_only_task defined
- [ ] R3: classifier test 21/21 (shell/non-shell/multiline)
- [ ] R3: integration test — shell task → completed (no LLM), instruction → in_progress
- [ ] KANBAN-REVIEW-20260520.md stale "Done" cells corrected + 6/2 follow-up section added
