# T4 Gateway Cron Fix Recipe (2026-06-10 23:53)

## Root Cause

`d1ef68ced116` (kanban-dispatcher LLM agent job) blocked `tick()`'s sequential
job loop. `run_job()` hit the `task_qa_gate` neuron's contract phase
(auto-generates skeleton, logs "QA gate FAILED") and the LLM agent never returned,
stalling the entire tick for 15-26 minutes. `drewgent-cron-runner-001`
(script-based) could not fire behind it.

## Fix Applied

### 1. Disable redundant LLM job (`~/.drewgent/cron/jobs.json`)

`d1ef68ced116` was redundant — `cron_runner.py` (the script behind
`drewgent-cron-runner-001`) already dispatches all 3 boards: default, content,
integrations. The LLM job only handled "default".

```json
{
  "id": "d1ef68ced116",
  "enabled": false,
  "state": "paused",
  "paused_at": "2026-06-10T23:48:00",
  "paused_reason": "T4 fix: redundant with drewgent-cron-runner-001 (cron_runner.py handles all boards)"
}
```

### 2. Reorder tick loop (`cron/scheduler.py:tick()`)

Before (sequential — ALL jobs, LLM can block dispatchers):
```python
        for job in due_jobs:
```

After (script jobs FIRST, LLM jobs after):
```python
        _script_jobs = [j for j in due_jobs if j.get("script")]
        _llm_jobs = [j for j in due_jobs if not j.get("script")]
        for job in _script_jobs + _llm_jobs:
```

3 lines added, no new imports. Verified with 4 consecutive fires at 23:53–23:59.

### 3. Apply ALL protection layers

| Step | File | Change |
|------|------|--------|
| A.2 | `gateway/run.py:3260-3290` | Housekeeping try/except — each op in own try |
| T4.3 | `gateway/run.py:3236-3242` | Tick watchdog (`tick_elapsed > 5× interval` → warning) |
| T4.4 | `drewgent_harmony_check.sh` | Layer 3.5b: fire frequency detection |
| T4.6 | `drewgent_cron_watchdog.sh` | Auto kickstart on 0 fires in 5 min |

## Verification

```bash
# 1. Restart gateway
launchctl kickstart -k gui/$(id -u)/ai.drewgent.gateway

# 2. Wait 60s for first tick
sleep 60

# 3. Check cron-runner fired
grep -E '=== 2026-' ~/.drewgent/logs/cron-runner/$(date +%Y-%m-%d).log | tail -3

# 4. Check Running job order (script first)
grep "Running job" /Users/drew/.drewgent/P6-prefrontal/logs/gateway.log | tail -3

# 5. Harmony check
bash ~/.hermes/scripts/drewgent_harmony_check.sh | grep -A 1 "Layer 3.5"
```

Expected: cron-runner fire present, `drewgent-cron-runner-001` runs before any LLM job, Layer 3.5 shows ✓ or small gap (<120s).
