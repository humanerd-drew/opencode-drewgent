# T4 — Gateway Sequential Tick Stall

## Reproduction Recipe

### Pattern

```
cron-runner log: 0 fires in 5+ minutes
gateway log: "Running job" for LLM-based job, no subsequent entries
gateway process: alive (PID in launchctl)
```

### Confirm

```bash
# 1. Gateway alive?
launchctl print gui/$(id -u)/ai.drewgent.gateway | grep pid

# 2. Last cron-runner fire?
ls -lt ~/.drewgent/logs/cron-runner/*.log
grep -E '=== 2026-' ~/.drewgent/logs/cron-runner/YYYY-MM-DD.log | tail -3

# 3. Last gateway cron job?
grep "Running job" ~/.drewgent/P6-prefrontal/logs/gateway.log | tail -5

# 4. What jobs are due?
python3 -c "
import json
d = json.load(open('/Users/drew/.drewgent/cron/jobs.json'))
for j in d.get('jobs', []):
    if j.get('enabled'):
        print(f'{j[\"id\"]:40} script={bool(j.get(\"script\"))} next={j.get(\"next_run_at\",\"?\"):25}')
"
```

### Root Cause

`scheduler.py:tick()` processes all due jobs **sequentially** in one `for` loop:

```python
for job in due_jobs:
    advance_next_run(job["id"])
    try:
        success, output, final_response, error = run_job(job)
        ...
```

If an LLM-based job (no `script` field) runs first and hangs (e.g. `task_qa_gate` neuron contract phase fail), it blocks ALL subsequent jobs including script-based dispatchers.

### Fix Applied (cron/scheduler.py:897)

```python
# Script-based jobs (dispatchers) run FIRST, LLM jobs after
_script_jobs = [j for j in due_jobs if j.get("script")]
_llm_jobs = [j for j in due_jobs if not j.get("script")]
for job in _script_jobs + _llm_jobs:
```

### Immediate Workaround

```bash
# Kickstart gateway to clear blocked state
launchctl kickstart -k gui/$(id -u)/ai.drewgent.gateway

# Clear stale file lock (if tick can't acquire)
rm -v ~/.drewgent/cron/.tick.lock
```

### Prevention

1. **Layer 3.5b** in harmony check counts `=== ISO ===` blocks in cron-runner log (5-min window). 0 = stall alert. ≥12 = abnormal frequency.
2. **`drewgent_cron_watchdog.sh`** auto-kickstarts if 0 fires in 5 min.
3. **Disable redundant LLM jobs** — if a script-based job already does the same work (e.g. `cron_runner.py` handles all 3 boards), disable the LLM version.

### Verification

```bash
# After fix: only script-based jobs run
grep "Running job" ~/.drewgent/P6-prefrontal/logs/gateway.log | tail -5
# Expected:
#   ... Running job 'kanban-dispatcher (all boards, consolidated)' (ID: drewgent-cron-runner-001)
# NOT expected:
#   ... Running job 'kanban-dispatcher' (ID: d1ef68ced116)
```
