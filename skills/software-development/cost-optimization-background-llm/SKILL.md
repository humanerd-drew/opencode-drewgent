---
name: cost-optimization-background-llm
current_routing: "opencode-go/deepseek-v4-flash (2026-06-14+ — all tasks use same model via $10/mo subscription, no per-call cost to optimize)"
title: Cost Optimization — Background LLM Calls in Drewgent
description: Reduce LLM token spend on cron + background + kanban-worker without touching interactive (CLI/ACP/Discord) paths. Inventory → classify → apply config/scheduler/worker patches → verify with hard evidence.
domain: software-development
space: growth
type: skill
tags: [P4, cortex, llm, cost, optimization, background, cron, kanban]
created: 2026-06-02
updated: 2026-06-02
links:
  - "[[@memory/growth/KANBAN-REVIEW-20260520]]"
  - "[[@identity/SELF_MODEL]]"
  - "[[@action/gateway/drewgent-architecture-dataflow]]"
  - "[[@identity/brain/rules]]"
---

# Cost Optimization — Background LLM Calls

Reduce LLM token spend on background/scheduled work in Drewgent **without
touching the user-facing interactive path** (CLI / ACP / Discord messages).
Terminal-direct calls are off-scope by user preference.

## Related skills

- `hermes-model-routing` — broader framework for model selection across all 4 routing levels
  (main/delegation/auxiliary/provider_routing). This skill focuses on the cost dimension;
  the routing skill covers the complete selection framework.

## When to use

Trigger words from user: "cost optimization", "background LLM",
"cron LLM", "token cost", "cheap model", "스케줄 작업과 백그라운드".

## Decision tree

```
Background LLM call site discovered
    │
    ├── (1) Is the LLM call essential?
    │     │
    │     ├── Yes (report synthesis, MCP query, instruction) → keep LLM
    │     │   but route to cheaper model via config.yaml
    │     │
    │     └── No (simple shell interpretation) → make deterministic
    │
    ├── (2) What cost lever is available?
    │     │
    │     ├── Smart-routing cheap_model != main model
    │     │   → config.yaml smart_model_routing.cheap_model.{provider,model}
    │     │
    │     ├── Auxiliary task model override
    │     │   → config.yaml auxiliary.{task}.{provider,model}
    │     │     tasks: vision, web_extract, compression, session_search,
    │     │            skills_hub, approval, mcp, flush_memories
    │     │
    │     ├── Script-based fast path (cron)
    │     │   → jobs.json add `script:` field + scheduler.py branch
    │     │
    │     └── Task body classification (kanban worker)
    │         → classify first non-empty line; shell-prefix → subprocess
    │
    └── (3) Verify with hard evidence, not just "Done ✅" claims.
```

## Procedure (5 phases)

### Phase 1 — Inventory

```bash
# 1a) Cron jobs: list all jobs
jq '.jobs[] | {id, name, enabled, schedule, last_status, last_run_at}' \
   ~/.drewgent/cron/jobs.json

# 1b) Find scheduler entry point
grep -n "run_job\|run_conversation\|AIAgent" \
   ~/.drewgent/source/drewgent-agent/cron/scheduler.py

# 1c) Background threads / fire-and-forget
grep -rn "threading.Thread\|daemon=True" \
   ~/.drewgent/source/drewgent-agent/ | grep -v test_

# 1d) Kanban worker LLM path
grep -n "AIAgent\|agent.chat\|run_conversation" \
   ~/.drewgent/scripts/run_kanban_worker.py

# 1e) Auxiliary task consumers
grep -rn "call_llm\|async_call_llm" \
   ~/.drewgent/source/drewgent-agent/agent/ | grep -v test_
```

### Phase 2 — Classify

For each LLM call site, label it:

| Label | Action |
|-------|--------|
| **LLM essential** | keep; route to cheap model if possible |
| **LLM partial** (analysis + report) | extract deterministic part, LLM only for synthesis |
| **Deterministic possible** | bypass LLM entirely (script path) |

For 2026-06-02 inventory, the labels were:
- `dispatch_once_default/content/integrations` → **deterministic** (already LLM 0)
- `cron-output-cleanup` → **deterministic possible** (was LLM)
- `kanban-maintenance` → **deterministic possible** (was LLM)
- `SEO/Trend Harvester` → **LLM partial** (60% score, 40% report)
- `site-spec-audit-weekly` → **LLM essential** (MCP synthesis)
- `title_generator` / `context_compressor` → **LLM essential but small**
  → route to cheap model
- `kanban worker` → **mixed** (instruction LLM, shell deterministic)

### Phase 3 — Apply (in order of risk/cost)

**3a) Auxiliary model override** (cheapest first, 0 risk):

```yaml
# --- With single-model subscription routing, no patching needed ---
# Everything uses opencode-go/deepseek-v4-flash ($10/mo, zero marginal cost).
# The cost optimization below was for a per-call era and no longer applies.
# See current_routing in this skill's frontmatter and hermes-model-routing skill.

Apply to BOTH `~/.drewgent/config.yaml` and `~/.drewgent/P5-ego/config/config.yaml`
(they're duplicated; see Pitfall #1).

**3b) Script-based cron fast path** (medium effort, 0 risk):

In `jobs.json`, add `script:` field for jobs whose prompt is just a shell command:
```json
{
  "id": "a130ff5768c1",
  "name": "cron-output-cleanup",
  "script": "~/.drewgent/scripts/cron_output_cleanup.py",
  ...
}
```

In `cron/scheduler.py`, add early-return branch at the top of `run_job()`'s
`try:` block:
```python
script_path = (job.get("script") or "").strip()
if script_path:
    return _run_script_subprocess(
        job, script_path, origin, _cron_session_id, _session_db
    )
```

And add a `_run_script_subprocess()` helper that calls `subprocess.run()`
directly and returns the same `(success, output, final_response, error)`
tuple shape as `run_job()` so `tick()`'s delivery logic stays uniform.

**3c) Kanban worker task body classifier** (medium effort, low risk):

Add `_is_shell_only_task(prompt: str) -> bool` that inspects the first
non-empty line for shell prefixes (`python3`, `bash`, `sh`, `node`,
`ruby`, `perl`, `./`, `/bin/`, `/usr/bin/`).

Add `_run_shell_only_task()` that calls `subprocess.run(shell=True)`
with timeout=600s and writes completion/failure to kanban DB.

Add an early-return branch in `run_worker()` between heartbeat and
LLM path.

### Phase 4 — Verify

**4a) Syntax check** (every change):
```bash
python3 -m py_compile <modified_file>.py
python3 -c "import json; json.load(open('<modified>.json'))"
python3 -c "import yaml; yaml.safe_load(open('<modified>.yaml'))"
```

**4b) Dry-run** (deterministic paths):
```python
import sys, json, os
sys.path.insert(0, '/Users/drew/.drewgent/source/drewgent-agent')
os.chdir('/Users/drew/.drewgent/source/drewgent-agent')
from cron.scheduler import run_job

with open('/Users/drew/.drewgent/cron/jobs.json') as f:
    jobs = json.load(f)['jobs']

job = next(j for j in jobs if j['id'] == '<target_id>')
success, output, final, error = run_job(job)
print(f"success={success} final[:200]={final[:200]!r}")
```

**4c) Integration test** (kanban worker):
```python
import sqlite3, subprocess, os, time
DB = '/Users/drew/.drewgent/P2-hippocampus/kanban/state/drewgent_tasks.db'
# NOT ~/.drewgent/state/drewgent_tasks.db — see Pitfall #2

# Insert shell task
conn = sqlite3.connect(DB)
task_id = f't_test_{int(time.time())}'
conn.execute("""
    INSERT INTO tasks (id, title, body, status, board, trigger_source, created_at, workspace_path)
    VALUES (?, ?, ?, 'ready', 'default', 'manual', datetime('now'), ?)
""", (task_id, 'shell test', 'python3 -c "print(\'ok\')"', '/Users/drew/.drewgent'))
conn.commit()
conn.close()

# Run dispatcher
subprocess.run(
    [VENV, '/Users/drew/.drewgent/scripts/dispatch_once_default.py'],
    env={**os.environ, 'DREW_HOME': '/Users/drew/.drewgent'},
    timeout=60,
)

# Wait for worker log
log = Path(f'~/.drewgent/P4-cortex/scripts/kanban/logs/workers/{task_id}.log')
# Look for: [worker] Shell-only task (no LLM): ...
```

**4d) Hard evidence** (cron tick):
```bash
# After next cron tick:
grep "Script-based job\|Shell-only" ~/.drewgent/logs/cron-runner.log
ls -lt ~/.drewgent/cron/output/<board>/ | head -5
```

### Phase 5 — Doc honesty check

Whenever you claim "Done ✅" for a kanban/cron/worker change, verify
with `grep` that the code actually does what you say. Common gotcha:
`KANBAN_WORKER_MODE=1` is set as an env flag but `run_kanban_worker.py`
still spawns `AIAgent` and calls `agent.chat()` — the "LLM 없음" claim
was inaccurate until 2026-06-02's task body classifier was added.

## Pitfalls

### 1. Two config.yaml files

`~/.drewgent/config.yaml` and `~/.drewgent/P5-ego/config/config.yaml`
are duplicated. Path-integrity-report-2026-05-17 already noted
"potential drift". Both must be patched in sync.

When patching the root-level `compression:` section, do NOT duplicate
it. The structure is:
```yaml
compression:
  enabled: true
  threshold: 0.9
  target_ratio: 0.2
  protect_last_n: 20
  summary_model: 'MiniMax-M2.5'   # patched line
  summary_provider: minimax
  summary_base_url: null
```
If your patch turns this into two consecutive `compression:` keys, you
have a bug — restore by replacing both blocks in one patch.

### 2. Two kanban DB files

`~/.drewgent/state/drewgent_tasks.db` (top-level, stale, 32KB)
`~/.drewgent/P2-hippocampus/kanban/state/drewgent_tasks.db` (canonical)

The dispatcher / worker / scheduler all use the P2 path. If you
`INSERT` into the top-level path, dispatcher won't see it (silent
failure — claim=0, spawned=0). Always use:
```python
DB = '/Users/drew/.drewgent/P2-hippocampus/kanban/state/drewgent_tasks.db'
```

### 3. smart_routing.cheap_model = main model = no effect

`config.yaml`:
```yaml
model: opencode-go/deepseek-v4-flash
```
→ Everything uses the same model via $10/mo subscription. No smart routing
needed — there's zero cost difference between "cheap" and "main" calls under
subscription billing.

### 4. KANBAN_WORKER_MODE=1 is not "deterministic"

`run_kanban_worker.py` sets `KANBAN_WORKER_MODE=1` env var, but that
flag is only honored by `acp_adapter/entry.py` (a different code path).
With single-model subscription routing (opencode-go/deepseek-v4-flash),
there is no per-call cost difference between model tiers — the cost
optimization this skill documents no longer applies.

### 5. Subscription routing removes cost optimization incentives

Under the current single-model subscription routing (opencode-go, $10/mo),
all tasks use `deepseek-v4-flash` at zero marginal cost. The per-call
cost optimization patterns below (using MiniMax-M2.5 as a cheaper model)
are retained for reference but no longer applicable to the active config.

## Supersession Notice (2026-06-13)

This skill documents the **per-call era** cost optimization strategy (MiniMax Token Plan credits). As of 2026-06-13, the system routes all traffic through OpenCode Go ($10/mo subscription, zero marginal cost). The cost optimization problem has moved from "minimize per-token spend" to "match model capability to task complexity."

The **model-routing** skill (`software-development/model-routing`) supersedes this skill. It covers:
- The 3-tier flash/pro/max selection strategy
- Agent profile system (8 predefined roles)
- Pipeline design with cost-aware model assignment
- OpenCode Go vs MiniMax direct fallback decision

This skill is retained for reference when working with the legacy per-call path (direct MiniMax API) or when comparing before/after cost profiles.

## Reference docs (already updated 2026-06-02)

- `P4-cortex/growth/KANBAN-REVIEW-20260520.md` — Leak 1 / Missing 10 cell
  corrected (✅ Done → ⚠ Partial); 6/2 follow-up section added
- `~/.drewgent/config.yaml` — `auxiliary.compression.{provider,model}`
- `~/.drewgent/P5-ego/config/config.yaml` — same
- `~/.drewgent/cron/jobs.json` — cron-output-cleanup + kanban-maintenance
  have `script:` field
- `~/.drewgent/source/drewgent-agent/cron/scheduler.py` — `run_job()`
  has script-based fast path
- `~/.drewgent/scripts/kanban_maintenance.py` — newly written
- `~/.drewgent/scripts/run_kanban_worker.py` — `_is_shell_only_task()`
  + `_run_shell_only_task()`

## Follow-up checklist (not in scope, but tracked)

- [ ] DB path 중복 follow-up (top-level state vs P2) — path drift
- [ ] 1주일 usage data + display.show_cost: true 켜서 효과 측정
- [ ] smart_routing.cheap_model M2.5 변경 (현재 M3, 효과 0)
- [ ] cron-output-cleanup / kanban-maintenance 다음 자동 실행 후 LLM 0회 hard evidence
- [ ] H2 future-proof: kanban-create task kind 명시 옵션 (over-engineering 위험)
