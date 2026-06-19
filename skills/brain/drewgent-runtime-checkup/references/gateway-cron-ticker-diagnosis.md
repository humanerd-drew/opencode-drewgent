# Gateway Cron-Ticker Diagnosis (2026-06-10)

Three distinct failure modes with different root causes and fixes.

## Root Cause A: Housekeeping Block Broken Try/Except

**Symptom**: Cron ticker fires once after kickstart, then stops silently. 1-2
ticks observed, then 20+ minutes of 0 fires. Gateway process alive but no
cron activity.

**Cause**: `gateway/run.py:3260-3290` (pre-fix) — wiki maintenance, image
cache cleanup, and document cache cleanup shared a broken nested try/except
structure:

```python
# BAD — pre-fix structure
if tick_count % WIKI_MAINTENANCE_EVERY == 0:
    try:
        learner.run_maintenance(dry_run=False)
    except Exception as e:
        logger.debug("...", e)
        if removed:   # ← removed NOT DEFINED YET
            logger.info("Image cache cleanup...", removed)
    except Exception as e:   # ← 2nd except for same try (odd)
        logger.debug("...", e)
    try:
        removed = cleanup_document_cache(...)  # nested inside except
```

**Fix**: Each housekeeping op in own try/except with logger.warning:

```python
if tick_count % WIKI_MAINTENANCE_EVERY == 0:
    try: learner.run_maintenance(dry_run=False)
    except Exception as e:
        logger.warning("Wiki maintenance error (continuing): %s", e)

if tick_count % IMAGE_CACHE_EVERY == 0:
    try: removed = cleanup_image_cache(max_age_hours=24)
    except Exception as e:
        logger.warning("Image cache error (continuing): %s", e)
```

**Verify**: 5-min observation → 4-5 fires vs 1 fire + stall pre-fix.

## Root Cause B: Sequential Tick-Loop Blocked by LLM Job

**Symptom**: Script-based dispatcher fire 0 for 26+ min. LLM-based
dispatcher stuck in "Running job" state.

**Cause**: `tick()` runs jobs sequentially. An LLM job (QA gate fail, API
hang) blocks the entire loop — script jobs after it never execute.

**Diagnosis**:
```bash
grep "Running job" gateway.log | tail -20
# Only d1ef68ced116 entries, NO drewgent-cron-runner-001 = block
```

**Fix**: Disable redundant LLM job (`d1ef68ced116`) when cron_runner.py
already handles all boards. Or convert to `script:` field.

**Systemic fix** (2026-06-10 23:50): `cron/scheduler.py:tick()` reorders
due jobs so script-based jobs (dispatchers) run BEFORE LLM agent jobs.
This prevents ANY slow LLM job from blocking dispatchers:

```python
_script_jobs = [j for j in due_jobs if j.get("script")]
_llm_jobs = [j for j in due_jobs if not j.get("script")]
for job in _script_jobs + _llm_jobs:
    # ... existing loop body
```

**Verify**: `grep "Running job.*d1ef68ced116" gateway.log` → zero after fix.
And `grep "Running job.*drewgent-cron-runner-001" gateway.log` → fires
every 60s regardless of concurrent LLM jobs.

## Root Cause C: Stale File Lock

**Symptom**: "Cron ticker started" then zero log entries for 3+ min.

**Cause**: Previous gateway crashed holding `.tick.lock`.

**Fix**: `rm -f ~/.drewgent/cron/.tick.lock`

## Tick Watchdog (T4.3 patch)

Added to `gateway/run.py:_start_cron_ticker`. Each tick measures elapsed time;
if `tick_elapsed > 5 × interval` (e.g. 300s for 60s interval), logs warning:

```python
tick_elapsed = _time.time() - tick_start
if tick_elapsed > 5 * interval:
    logger.warning("Cron tick #%d took %.1fs — gateway may be CPU-starved", ...)
```

Outer try/except also upgraded from `logger.debug` to `logger.warning`
(was silent on tick errors).

## Fire-Frequency Detection (Layer 3.5b)

Detect 0 fires (= stall) or ≥12 fires (= abnormal frequency) in last 5 min.

```bash
CR_LOG="$DREW_HOME/logs/cron-runner/$(date +%Y-%m-%d).log"
CUTOFF=$(($(date +%s) - 300))
FIRE_COUNT=$(awk -v cutoff="$CUTOFF" '
    /^=== [0-9]{4}/ {
        ts = $2; gsub(/[+].*$|Z$/, "", ts); gsub(/T/, " ", ts)
        cmd = "date -u -j -f \"%Y-%m-%d %H:%M:%S\" \"" ts "\" +%s"
        cmd | getline ep; close(cmd)
        if (ep+0 >= cutoff) count++
    } END { print count+0 }
' "$CR_LOG")
# 0 = stall, 12+ = abnormal, 1-11 = ok
```

## Auto-Kickstart Watchdog

Full script at `~/.hermes/scripts/drewgent_cron_watchdog.sh`. Covers:
- Gateway uptime check (>300s before acting)
- `date -u -j -f` TZ-aware parsing (cron-runner uses UTC +00:00)
- `launchctl kickstart` when 0 fires in 5 min
