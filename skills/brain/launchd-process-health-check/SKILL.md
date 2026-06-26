---
title: Launchd Process Health Check
name: launchd-process-health-check
type: skill
space: outcome
description: Diagnose launchd service state when launchctl list shows stale exit codes but process is actually running
tags: [skill, launchd, troubleshooting, diagnostics]
created: 2026-05-31
updated: 2026-06-12
links:
  - "[[@action/skills/SKILL-INDEX]]"
  - "[[@memory/growth/harness-autonomous-behaviors]]"
  - "[[@identity/brain/rules]]"---

# Launchd Process Health Check

## Problem

When checking `launchctl list | grep <name>`, the Exit code and PID columns can be **misleading**. A process can:
- Show "Exit -15" but actually be running (someone else restarted it)
- Show old PID but have been replaced by a new process
- Be managed by launchd but running under a different binary

## Always Verify With These 3 Commands

```bash
# 1. launchd's view (may be stale)
launchctl list | grep <service-name>

# 2. Is it actually listening? (ground truth)
lsof -i :<port> 2>/dev/null

# 3. Is there a process? (ground truth)
ps aux | grep -i <process-name> | grep -v grep
```

## Common Exit Codes Explained

| Exit Code | Meaning |
|-----------|---------|
| 0 | Clean exit (normal) |
| -15 | SIGTERM received (killed) |
| -64 | Exit with signal 64 (often network/socket issue) |
| 87299 | Large number — usually a PID shown as "last exit status", not an exit code |

**Important**: The PID column shows the LAST process that exited, not the current one. A "running" service can show an old PID with a non-zero exit code.

## Reverse Pattern: Process Died and launchd Didn't Restart

The opposite case is more dangerous and is the one that actually broke Drewgent infra on 2026-06-10 (cron / n8n / quartz-fswatch all dead, never restarted, undetected for 6+ days):

**Symptoms:**
- `launchctl list | grep <name>` → row is present but **PID is `-` and Exit is non-zero** (e.g. -15 for SIGTERM, 1 for crash)
- `lsof -i :<port>` → empty (nothing listening)
- `ps aux | grep <name>` → empty (no process)
- `cron-runner.log` / `n8n.log` / `quartz-fswatch.log` → last entry is hours/days old, often a graceful shutdown ("Received SIGTERM. Shutting down...")

**Why this is the dangerous case (2026-06-10 incident):**
- Checking `~/.drewgent/cron/jobs.json` showed stale state — easy to skip
- `last_status=ok` in `jobs.json` was a stale marker from before the gateway died
- No `infrastructure watchdog` was polling for "is launchd keeping services alive" — there was no alert path
- User/agent didn't notice for 6+ days until they ran a checkup

**Sub-patterns 1–9 (verified 2026-06-10 — six of nine caused the undetected 4-6 day outage):**

### Sub-pattern 1: KeepAlive is set but the process exits with code 0

```xml
<key>KeepAlive</key>
<true/>
```

With a bare `<true/>` or no `SuccessfulExit` qualifier, launchd **only restarts on non-zero exit**. If a process is killed with SIGTERM (signal 15, but cleanly handled → exit 0), launchd considers it a normal exit and does NOT restart. Many Node.js / Python apps catch SIGTERM and shut down gracefully → exit 0.

**Fix:** Use the dict form to specify non-restart conditions explicitly:
```xml
<key>KeepAlive</key>
<dict>
    <key>SuccessfulExit</key>
    <false/>
    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
```
`SuccessfulExit: false` means "only treat exit 0 as 'this is a normal stop, don't restart'; restart on anything else (including graceful SIGTERM exits)."

This is the **canonical pattern** for any Node.js / Python daemon. Verified on 2026-06-10: n8n (Node.js) hit exactly this — SIGTERM at 6/4 16:41, graceful exit 0, no resurrection, undetected for 6 days.

### Sub-pattern 2: Plist has no KeepAlive at all

Many older launchd plists rely on `StartInterval` (periodic re-launch) instead of `KeepAlive`. If the process crashes, the next `StartInterval` tick will start a new one — but the gap is the interval length. A 60-second `StartInterval` means up to 60s of downtime per crash.

**Fix:** Add `KeepAlive` with explicit `ThrottleInterval` to bound restart rate:
```xml
<key>KeepAlive</key>
<dict>
    <key>SuccessfulExit</key>
    <false/>
    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
```

### Sub-pattern 3: launchd has no awareness the service should exist

If the plist was deleted, or the path inside the plist points to a file that no longer exists, launchd silently drops the service. `launchctl list` shows nothing — not even a stale row.

**Fix:** Verify plist is loaded and the program path is real:
```bash
launchctl print gui/$(id -u)/<label> | grep -E 'state|path|program'
ls -la <plist ProgramArguments path>
```

### Sub-pattern 4 (verified 2026-06-10): bare `<false/>` KeepAlive — deliberate death

```xml
<key>KeepAlive</key>
<false/>
```

This is the **literal value** "do not restart" — and it can appear in plists that were written to start once and stay gone, or copy-pasted from a "run-once" template. Verified on `com.drewgent.quartz-fswatch.plist` 2026-06-10: fswatch died (likely on macOS fswatch binary upgrade or unrelated crash) and stayed dead because the plist explicitly told launchd "if it exits, leave it dead." **This is the worst-case launchd config for a daemon.**

**Fix:** Same canonical pattern as Sub-pattern 1:
```xml
<key>KeepAlive</key>
<dict>
    <key>SuccessfulExit</key>
    <false/>
    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
```

### Sub-pattern 5 (verified 2026-06-10): plist Label ≠ filename — silent command failure

If `<key>Label</key>` inside the plist differs from the plist filename, all `launchctl bootout/kickstart/load` commands that use the filename will **silently fail** (e.g. `launchctl bootout ai.drewgent.gateway` → "No such process" because the registered label is `ai.custom-agent.gateway`).

Verified on 2026-06-10: `~/Library/LaunchAgents/ai.drewgent.gateway.plist` had `Label = ai.custom-agent.gateway`. Only commands using the registered label worked. Watchdog scripts that hardcode the filename (e.g. `ai.drewgent.gateway`) silently miss the service.

**Fix:** Always read `<Label>` directamente from the plist, not the filename:
```bash
/usr/libexec/PlistBuddy -c "Print :Label" ~/Library/LaunchAgents/<file>.plist
```
Then rename the label to match the filename (or vice versa). Convention: **Label = filename minus `.plist`**. Drewgent labels that must match filenames: `ai.drewgent.{cron-runner,gateway,kanban-dashboard,n8n}` + `com.drewgent.quartz-{fswatch,deploy}`.

### Sub-pattern 6 (verified 2026-06-10): jobs.json patch has zero effect on a dead scheduler

If the gateway/cron-runner process is dead, editing `~/.drewgent/cron/jobs.json` to set `next_run_at = now-5s` does **NOT** trigger a spawn. The in-memory state was loaded at process start; file edits do not propagate. Verified 2026-06-10: a Pattern A recovery patch from 5/30/6/1 incident was correct in code, but the gateway died 4 days later and the patch could not help.

**Fix:** Restart the gateway first. Verified behavior: on restart, `cron.jobs.get_due_jobs()` fast-forwards missed schedules with a grace window (e.g. 7200s for 6h jobs):
```
INFO cron.jobs: Job 'SEO Article Harvester' missed its scheduled time (2026-05-19T18:00:00, grace=7200s).
                Fast-forwarding to next run: 2026-06-10T18:00:00
```

**Sequence for any cron-stall incident**:
1. Verify scheduler is alive (gateway `ps aux | grep drewgent_cli.main.*gateway`).
2. If dead, restart gateway. Don't patch jobs.json first.
3. After restart, verify `next_run_at` is future-dated for all enabled jobs.
4. **Then** if a specific job is still dormant, force-due it (see `cron-jobs-stalled` skill Pattern D verification).

### Sub-pattern 7 (verified 2026-06-10 17:50): gateway scheduler double-fires `interval` jobs

When a `jobs.json` entry has `schedule.kind: 'interval'`, `schedule.minutes: 1` (or any value), the gateway's `cron/scheduler.py` may fire the entry **twice within 0.15 seconds**, then sleep for the interval, then fire twice again. Verified by counting `=== YYYY-MM-DDTHH:MM:SS ===` separators in `logs/cron-runner/<date>.log`: 2 entries per minute instead of 1.

**Why this happens** (hypothesis, not confirmed): the cron scheduler's "due" detection runs at startup, picks the same entry twice due to two code paths (e.g. one for `interval`, one for `cron expression`), or fires before and after in-memory state update.

**Impact**: 2x dispatcher work. If the dispatcher script is **idempotent** (e.g. `cron_runner.py` uses sqlite UPSERT/claim logic), no corruption. If not, this can cause double-claim, double-deploy, double-notification bugs.

**Detection**:
```bash
# Should be 1 per minute for a 1-minute interval job
grep -cE '=== 2026-' ~/.drewgent/logs/cron-runner/$(date +%Y-%m-%d).log
# If the count is consistently 2x the expected, this bug is firing.
```

**Workaround**: make dispatcher scripts idempotent (the cron_runner.py at `~/.drewgent/scripts/cron_runner.py` already is — uses sqlite claim logic). **Fix**: TBD; tracked in incident doc section 6.7.

### Sub-pattern 8 (verified 2026-06-10 17:50–18:00): two scheduler sources for one dispatcher — `cron-runner.plist` + jobs.json gateway entry

Drewgent historically had **two parallel paths** running the same dispatcher logic:
- (a) `ai.drewgent.cron-runner.plist` → `scripts/cron_runner.py` (launchd StartInterval=60)
- (b) gateway internal scheduler → `drewgent-cron-runner-001` jobs.json entry (script=scripts/cron_runner.py, interval=1min)

Both run the SAME `cron_runner.py` (which invokes 3 dispatcher scripts: default, content, integrations). The 6/10 incident doc section 6.6 sweep unified this — disabled (a) and kept (b). **Why this is dangerous**:

- **Double-fire**: if both run, you get 4 dispatcher invocations per minute (Sub-pattern 7 double × 2 sources). Cron-runner.py is idempotent so no corruption, but 4x CPU.
- **Hidden single-source failure**: if (a) silently dies (e.g. bootout forgotten) and (b) has a bug (e.g. gateway cron tick stalled), there's *no scheduler at all* and you don't notice until human checkup.

**Detecting two-source duplication**:
```bash
# Compare: how many `=== ISO ===` lines per minute in cron-runner daily log?
grep -E '=== 2026-' ~/.drewgent/logs/cron-runner/$(date +%Y-%m-%d).log \
  | awk -F'[T:]' '{print $2":"$3}' | sort | uniq -c
# Expected: 1 per minute for one source, 2 per minute for double-fire, 4 per minute for two-source + double-fire
```

**Safe unification sequence** (verified 6/10):
1. Add a single jobs.json entry with `script: ~/.drewgent/scripts/cron_runner.py` and `schedule: interval=1min`
2. Restart gateway: `launchctl kickstart -k gui/$(id -u)/ai.drewgent.gateway`
3. Wait 60s; verify the entry fired in `cron-runner/<date>.log` (look for new `=== ISO ===` line)
4. `launchctl bootout gui/$(id -u)/ai.drewgent.cron-runner` to disable the launchd plist
5. Keep the plist on disk for rollback: `mv ~/Library/LaunchAgents/ai.drewgent.cron-runner.plist ~/Library/LaunchAgents/disabled/`
6. **Watch for 24h**: if the new entry's logs look healthy, delete the plist. If regression, re-`launchctl bootstrap` and investigate.

### Sub-pattern 9 (verified 2026-06-10 19:38): gateway cron tick **stops** mid-session, not just at startup

Different from Sub-pattern 6 (jobs.json patch no-op on dead scheduler). Here the gateway is alive (PID present, launchd tracking healthy) but the **internal cron ticker loop stops firing** after running for ~80 minutes. Verified 6/10: gateway started at 17:50, "Cron ticker started" logged, dispatcher fired every minute until 19:18, then **no further "Cron ticker" log lines**. Process still alive, but `cron/scheduler.py` tick loop is stuck.

**Why this is dangerous**: Layer 3.5 of `drewgent_harmony_check.sh` correctly detects ("⚠ jobs.json modified 6270s after last dispatcher tick"), but the Layer 1/2 launchd check shows the gateway is *alive* — so the alert surfaces a real condition without obvious cause. Manual intervention (`launchctl kickstart -k`) revives it.

**Sub-pattern 10 (verified 2026-06-10 20:55) — ROOT CAUSE of Sub-pattern 9**:

Sub-pattern 9's *symptom* (cron tick stops mid-session) was traced to a real bug in `gateway/run.py:3260-3290` — the housekeeping block in `_start_cron_ticker`'s while loop. **The original code had broken nested try/except**:

```python
# BROKEN — gateway/run.py:3260-3290 (pre-fix)
if tick_count % WIKI_MAINTENANCE_EVERY == 0:
    try:
        from agent.auto_learn import AutoLearner
        from drewgent_constants import get_drewgent_home
        wiki_path = get_drewgent_home() / 'memories'
        if wiki_path.exists():
            learner = AutoLearner(enabled=True)
            learner.enable(wiki_path)
            result = learner.run_maintenance(dry_run=False)
            logger.debug(...)
    except Exception as e:
        logger.debug("Wiki maintenance tick error: %s", e)
        if removed:                            # ← `removed` undefined here!
            logger.info("Image cache cleanup: ...")
    except Exception as e:                      # ← syntax oddity
        logger.debug("Image cache cleanup error: %s", e)
    try:
        removed = cleanup_document_cache(max_age_hours=24)
        if removed:
            logger.info("Document cache cleanup: ...")
    except Exception as e:
        logger.debug("Document cache cleanup error: %s", e)
```

Three issues:
1. `if removed:` (line 3277) references `removed` *before* it's defined (line 3284) — `NameError` risk
2. Two `except Exception as e:` at the same indentation as if they were sequential, but they're both at the same try-block level — Python parses this OK but the second `except` catches from the same try as the first
3. `cleanup_document_cache` had its own try nested *inside* the wiki maintenance except handler's scope — variable scope confusion

**Result**: an unhandled exception in `learner.run_maintenance()` could escape the while loop entirely (or, more commonly in Python, raise an `UnboundLocalError` on `if removed:` that *does* get caught by the first except, but then the second `except` *also* fires on the same error, and the loop continues with corrupted state). Either way: cron ticker silently dies within 1-2 housekeeping cycles.

**Fix** (verified 2026-06-10 20:55, 5-minute observation passed):

```python
# FIXED — gateway/run.py:3260-3290
# Wiki maintenance: keep the brain healthy without user interaction
if tick_count % WIKI_MAINTENANCE_EVERY == 0:
    try:
        from agent.auto_learn import AutoLearner
        from drewgent_constants import get_drewgent_home
        wiki_path = get_drewgent_home() / 'memories'
        if wiki_path.exists():
            learner = AutoLearner(enabled=True)
            learner.enable(wiki_path)
            result = learner.run_maintenance(dry_run=False)
            logger.debug(...)
    except Exception as e:
        logger.warning("Wiki maintenance tick error (continuing): %s", e)

# Image cache cleanup: once per hour (own try/except)
if tick_count % IMAGE_CACHE_EVERY == 0:
    try:
        removed = cleanup_image_cache(max_age_hours=24)
        if removed:
            logger.info("Image cache cleanup: ...")
    except Exception as e:
        logger.warning("Image cache cleanup error (continuing): %s", e)

# Document cache cleanup: once per hour (own try/except)
if tick_count % IMAGE_CACHE_EVERY == 0:
    try:
        removed = cleanup_document_cache(max_age_hours=24)
        if removed:
            logger.info("Document cache cleanup: ...")
    except Exception as e:
        logger.warning("Document cache cleanup error (continuing): %s", e)
```

**Key changes**:
- Each housekeeping op in **own** try/except (no shared `removed` variable)
- `logger.debug` → `logger.warning` for these errors (so we can see if they fire)
- Operations placed at the same indentation as the wiki block (siblings, not nested)

**Why this fixes Sub-pattern 9**: even if `learner.run_maintenance()` raises a totally new exception type, the `try/except Exception` is the only thing that can catch it. With separate try blocks per op, no op's failure can leak into another's scope, and the while loop is guaranteed to continue.

**Defensive verification** (post-fix): 5-minute gateway observation showed 4 cron-runner fires in 6 minutes. Pre-fix: 1 fire then stall within 1-2 minutes, observed 3 times across 4 hours.

**Pitfall when applying this fix to other codebases**:
- **Don't just wrap the *whole* housekeeping block in one outer try/except** — that hides WHICH op failed. The fix is to give each op its own try.
- **Don't use `logger.debug` for housekeeping errors** — they'll fire and you'll never know. `logger.warning` is the minimum; consider `logger.error` for "this should never happen" cases.
- **Don't introduce a top-level `try/except` around the entire while body as a "defense in depth" measure** — that just hides the problem. Fix the housekeeping code instead.

**Sub-pattern 11 (verified 2026-06-10 22:06–22:26) — gateway process **silently stuck** (not crashed, not crashed-and-restarted)**

Different from Sub-pattern 9 (cron tick loop stuck, A.2 housekeeping try/except fix). Different from Sub-pattern 6 (dead scheduler). **Here the process is *alive* and *running* but *not doing anything***.

**Symptoms** (verified 22:06 → 22:26, 20 min span):
- `launchctl list | grep <name>` → row present, **PID stable, Exit -9** (or -15)
- `launchctl print gui/$(id -u)/<name>` → `state = running, pid = 36947, active count = 1`
- `ps aux | grep <name>` → **empty** (sandbox isolation hides launchd-spawned processes!)
- `ps -A -o pid,etime,command | grep <name>` → **shows the process** (use this, not `ps aux`)
- `lsof -p <pid>` → **shows file descriptors** (log file open, write mode)
- **log file mtime stays frozen** at the last activity moment — no appending despite process being "alive"
- cron ticks / scheduled tasks **stop firing** but the process is not crashed

**Why this is the most dangerous sub-pattern**:
- launchd's view says "running" — KeepAlive will NOT trigger (process hasn't exited)
- No crash → no log entry explaining the cause
- `ps aux` returning empty misleads you into thinking "the process is dead, just kickstart"
- The user/agent has to assemble evidence from **5+ sources** (launchctl + ps -A + lsof -p + log mtime + cron tick absence) to conclude "process stuck, not dead"

**Diagnostic sequence** (verified 2026-06-10 22:26):
```bash
# 1. launchd's view
launchctl print gui/$(id -u)/<name> | grep -E "state|pid"

# 2. macOS-aware process check (NOT ps aux — sandbox hides launchd children)
ps -A -o pid,etime,command | grep <name>

# 3. Is the process actually writing to its log?
lsof -p <pid> | grep "REG.*\.log"

# 4. Log mtime — if it's frozen for minutes, the process is stuck
ls -la <path-to-log-file>
# Compare to: date '+%Y-%m-%d %H:%M:%S'

# 5. Cron/scheduled activity check (if applicable)
grep -E '=== 2026-' <log-path> | tail -3
# Last fire time vs current time = gap = how long it's been stuck
```

**Recovery** (verified 2026-06-10 22:26, kickstart revived immediately):
```bash
# Kickstart (NOT bootout + bootstrap — keep current state)
launchctl kickstart -k gui/$(id -u)/<name>
# -k = kill existing, restart
# Without -k, kickstart signals but doesn't kill a stuck process

# Wait 5-10s, then verify
sleep 8
ps -A -o pid,etime,command | grep <name>  # new PID
ls -la <log-file>  # mtime should be fresh
```

**Why this is hard to fix at the gateway level** (deferred root cause):
- A.2 fix (Sub-pattern 10) addresses housekeeping try/except — that was a *specific* code path bug
- Sub-pattern 11 looks like a *different* failure mode: process loop itself stops (no exception, no signal, just... halts)
- Possible causes: deadlock on file lock, I/O hang on stdout/stderr FD, OOM killer without logging, signal mask issue
- **Real fix requires**: gateway code self-restart (try/except in `_start_cron_ticker` with `os._exit(1)` on detection) or systemd-style watchdog. **Tracked as T4 follow-up, deferred.**

**Pitfall when diagnosing**:
- **Don't trust `ps aux` for launchd-spawned processes** — macOS sandbox/namespace isolation can hide them. Always use `ps -A` (all processes) or `launchctl print` for the canonical view.
- **Don't confuse "process is alive" with "process is doing work"** — `lsof -p` showing log FD open doesn't mean it's writing. Check log mtime.
- **Don't skip the kickstart because launchd says "running"** — kickstart works for stuck processes. The KeepAlive logic only fires on *exit*.

**Related sub-pattern**: 2 gateway processes running simultaneously (PID 29156 *foreground* + PID 36947 *background*) can each have their own cron ticker. If you see cron-runner.log showing 2 fires per minute, check `ps -A | grep -c drewgent_cli.main` — if > 1, you have duplicate gateways. Kill the foreground one (the one with a TTY in `ps -o tty`).

**Why the gateway cron loop is structured this way** (Drewgent-specific): housekeeping is bundled into the cron tick thread to avoid running a separate scheduler. If you have a similar architecture, this Sub-pattern 10 applies. If your housekeeping is in a separate process (e.g. a cron job), it can't kill the main scheduler, so the impact is limited to "housekeeping runs less often."

**Related sub-pattern (NEW, discovered 6/10 23:53)**: "gateway alive, cron fires stop" can ALSO be caused by an LLM-based cron job blocking the sequential `tick()` loop. The process is fully alive, doing work (running an LLM agent), but script-based jobs stuck behind it can't execute. **Diagnosis**: check gateway log for `Running job <ID>` — if the latest Running job has no `script:` field in jobs.json and the previous Running job of `drewgent-cron-runner-001` is 5+ min old → `cron-jobs-stalled` Pattern G.

**Fix**: `cron/scheduler.py:tick()` — sort script jobs before LLM jobs (3-line patch). See `cron-jobs-stalled` skill Pattern G for full recipe.

**Related sub-pattern (NEW, discovered 6/10 21:00)**: macOS Sonoma+ `launchctl list <label>` returns plist-format JSON, not tab-separated text. `_get_service_pids()` in hermes's `gateway.py` silently returns `[]` on the new format. **Override `find_gateway_pids` must handle both formats.** Recipe: `references/2026-06-10-customize-layer-recipe.md`.

**Threshold tuning** (verified 2026-06-10 19:38–20:22): the initial Layer 3.5 threshold of "last dispatcher tick > 60s ago = alert" was too tight. A 1-minute interval job with normal double-fire and the gateway's cron.jobs fast-forward save right after the tick routinely produces a 60–110s gap between mtimes even when everything is healthy. The tuned threshold is **> 90s** for the mtime-mtime branch (jobs.json mtime > last tick mtime); **> 120s** (2 ticks of silence) for the now-tick branch (now > last tick + 120s). 60s ≤ gap ≤ 90s = ✓ (no alert). Recipe in `references/2026-06-10-harmony-check-recipe.md`.

**TZ-aware parsing** (verified 6/10 21:08): cron-runner logs UTC timestamps with `+00:00` suffix. macOS `date -j -f` naively parses them as system local time, causing a 9h drift. Use Python's `datetime.fromisoformat()` for TZ-aware parsing:
```python
from datetime import datetime
dt = datetime.fromisoformat("2026-06-10T11:59:25.760351+00:00".replace("Z", "+00:00"))
print(int(dt.timestamp()))
# Correct: parses as UTC, returns unix epoch
```
This is a footgun for any harmony check script that uses `date -j` for log timestamps. Bake it into the script via Python for ISO 8601 strings with offset suffixes.

## The Lesson: Watchdog the Watchdog

`launchd` keeps processes alive, but **nothing keeps launchd honest**. The 2026-06-10 incident proved that a long-dead service can sit in `launchctl list` showing a stale exit code indefinitely — there is no built-in "your service has been dead for 24h" alarm.

**Pattern that prevents recurrence** (apply to any launchd-managed service, not just one):

1. **Watchdog cron** (`no_agent: true`) — every 5 minutes. **CRITICAL CONSTRAINT**: with Hermes `cronjob` tool, `no_agent=True` requires the script to live under `~/.hermes/scripts/` and be referenced by bare filename (the tool rejects absolute paths with "Place scripts in ~/.hermes/scripts/ and use just the filename"). Symlink the actual implementation to that path.

   The verified script (drewgent_launchd_watchdog.sh) is in `references/2026-06-10-incident-fix-recipe.md` section 0. Copy verbatim, symlink under `~/.hermes/scripts/`, then register with `cronjob(action="create", no_agent=True, schedule="every 5m", script="drewgent_launchd_watchdog.sh")`.

2. **Apply the canonical KeepAlive pattern to every plist** (Sub-patterns 1, 2, 4 all fixed by the same dict form):
   ```xml
   <key>KeepAlive</key>
   <dict>
     <key>SuccessfulExit</key>
     <false/>
     <key>ThrottleInterval</key>
     <integer>10</integer>
   </dict>
   ```
   This handles: bare `<true/>` (Sub-pattern 1), bare `<false/>` (Sub-pattern 4), missing key (Sub-pattern 2). Audit all plists, find any of those three, replace with the dict form.

3. **Verify Label key matches filename** (Sub-pattern 5) before issuing any launchctl command. Cross-check with `PlistBuddy -c "Print :Label"`. Convention: Label = filename minus `.plist`.

4. **Make `drewgent doctor` include a launchd health row** — table of (label, PID, last-log-mtime, ok/stale) — so a checkup surfaces dead services in one screen.

5. **Log rotation cron** (`no_agent: true`) — daily 04:00. Without it, a long-running service accumulates multi-GB error logs that make `grep` slow and disk pressure real. Verified on 6/10: 1.7GB error log rotated to 9.6MB .gz + 0B live + service restart. Script and recipe in **`references/2026-06-10-log-rotation-recipe.md`**.

6. **Harmony check cron** (`no_agent: true`) — daily 09:00 KST. Compares 4 layers: launchd view, ps aux, jobs.json next_run_at, memory claims. **Layer 3.5** of `drewgent_harmony_check.sh` is the *stalled detection* that catches Sub-pattern 9 — when the gateway cron ticker stops mid-session. Threshold: `last dispatcher tick > 60s ago = alert`. Verified 6/10 19:38 to detect the gateway stall that started 1.7h earlier. Recipe: **`references/2026-06-10-harmony-check-recipe.md`**.

## Customize Layer for Drewgent + Hermes (verified 2026-06-10 17:30)

When the user wants hermes-cli to work *for Drewgent's environment* (not
the upstream generic hermes) — e.g. override a hardcoded label, patch a
parser that breaks on macOS Sonoma+ — use the customize layer pattern in
`~/.drewgent/customize/`. **Do not edit `~/.hermes/hermes-agent/` files
directly** — upstream reinstalls overwrite silently.

The pattern is verified on 2026-06-10 17:30 (incident doc section 6.6).
Three activation paths are required simultaneously; missing any one is
silent break:

1. Gateway plist `<key>PYTHONPATH</key><string>/Users/drew/.drewgent/customize</string>` in `EnvironmentVariables`
2. `~/.zshrc` exports `PYTHONPATH="$HOME/.drewgent/customize:${PYTHONPATH:-}"`
3. **`~/.local/bin/hermes` wrapper patch**: the upstream wrapper contains `unset PYTHONPATH` which *deliberately* defeats the layer. The fix is to back up as `hermes.bak` and remove just that line, keeping `unset PYTHONHOME` (required for venv detection). Without this patch, all other activation paths are dead.

Two more gotchas that will silently break the layer:

- **`hermes_cli/__init__.py` cannot be shadowed with an empty file** — the real package defines `__version__` / `__release_date__` that downstream code imports. Use the `importlib.util` proxy pattern (load real package separately, register override submodules explicitly).
- **macOS Sonoma+ `launchctl list <label>` returns plist-format JSON**, not tab-separated text. hermes's `_get_service_pids()` parser silently returns `[]` on the new format. The override `find_gateway_pids` must handle both formats (regex `"PID"\s*=\s*(\d+)\s*;` for plist format).

Full recipe (directory layout, all source code verbatim, smoke test cron, 8 pitfalls) in **`references/2026-06-10-customize-layer-recipe.md`**.

## False Alarm Verification (verified 2026-06-10 — F2, F3 follow-ups)

When a checkup reports "X is broken" but the actual symptoms don't reproduce on re-verification, **resist the urge to fix what isn't broken**. Two specific 6/10 examples:

- **Port mismatch (F2)**: "kanban-dashboard port 5555 HTTP 000" turned out to be testing the wrong port — kanban-dashboard listens on **8765** (`ultraseek-http`). `curl http://localhost:8765/kanban` returned 200. Lesson: always `lsof -i :<port>` to confirm the actual port before patching anything.
- **Phantom error in log dump (F3)**: a 9.6M-line error log visually appeared to contain thousands of `NameError: api_start_time` errors, but `grep -c 'api_start_time is not defined' gateway.error.log` returned **0**. The visual scan was an artifact of scrolling through a huge file. Lesson: when a log file is large, use `grep -c` to verify error frequency before treating an error as a real problem.

**Rule of thumb**: if the symptom doesn't reproduce in a clean re-test, treat it as a hypothesis, not a fact. Verify with `grep -c`, `lsof`, `ps aux`, or whatever the *counting* tool is. Spending 5 minutes to confirm "the bug is real" saves hours of "fixing" a bug that isn't.

## Real Example (Kanban Dashboard)

```
$ launchctl list | grep kanban-dashboard
87299  -15  ai.drewgent.kanban-dashboard
```

This looks crashed. But:

```
$ lsof -i :8765
Python  87299  ...  TCP *:ultraseek-http (LISTEN)  ✅ RUNNING

$ ps aux | grep kanban_dashboard
drew  87299  ...  python@3.14 ... kanban_dashboard_server.py  ✅ RUNNING
```

**Interpretation**: The process IS running. The "Exit -15" is a stale snapshot — launchd saw the process die at some point, but something (another launchd restart attempt, manual start) brought it back. The Exit code reflects that historical death, not current state.

## When the Plist Path Doesn't Match Reality

In the kanban dashboard case:
- **plist**: `.venv/bin/python` (drewgent-agent venv)
- **actual**: `python@3.14` (homebrew system Python)

This mismatch means launchd can't properly manage/restart the service. Fix:

```bash
# Stop
launchctl stop ai.drewgent.kanban-dashboard

# Fix plist to use actual python path
# Or reinstall the service

# Start
launchctl start ai.drewgent.kanban-dashboard

# Verify
lsof -i :<port>
ps aux | grep <process-name>
```

## Bash 3.2 Pitfalls (verified 2026-06-10 throughout)

When writing shell scripts that run on macOS (Drewgent's host), the default `bash` is **3.2** (legacy), which has significant differences from bash 4+:

- **No associative arrays**: `declare -A name=([key]=value)` is a syntax error. Use parallel indexed arrays: `arr=("v1" "v2")` and access by position. This is why `drewgent_harmony_check.sh` uses `PROC_PATTERNS=(...)` and iterates by index, not by key.
- **`set -u` is fragile**: with `set -u`, any reference to an unset variable exits with error. The dotted label keys (`"ai.drewgent.gateway"`) trip arithmetic-context parsing in some bash 3.2 versions. Use `set -o pipefail` (or nothing) instead. Verify with `bash -n <script>` before running.
- **No `date -d`**: use `date -j -f "%Y-%m-%d %H:%M:%S" "..." +%s` for date parsing. GNU `date` syntax (`date -d`) is not available.
- **TZ-aware parsing needs Python**: `date -j -f` naively interprets timezone-less timestamps as system local time. For ISO 8601 strings with `+00:00` or `Z` suffix, use `python3 -c "from datetime import datetime; print(int(datetime.fromisoformat('...').timestamp()))"`. The 6/10 harmony check uses this for cron-runner.log timestamps (UTC) — without it, 9-hour drift.

**Verification**: `bash --version` shows `3.2.x`. If a script needs bash 4+, prefix with `#!/usr/bin/env bash` and check the *invocation*, not just the shebang. macOS users can install bash 4+ via Homebrew.

## Checklist

- [ ] `launchctl list` → note PID and Exit
- [ ] `lsof -i :<port>` → confirm LISTEN
- [ ] `ps aux | grep <name>` → confirm process
- [ ] If process running but launchd shows dead → check plist ProgramArguments matches actual binary
- [ ] If running under wrong python → update plist or fix venv
- [ ] If port unresponsive → `lsof -i :<port>` to confirm the actual port (don't trust memory)
- [ ] If error appears in log dump → `grep -c` to confirm occurrence count before treating as real
- [ ] If smoke test reports failure → check for substring/header false positives before patching
- [ ] If two dispatchers run same script → count cron-runner log entries per minute (Sub-pattern 8)
- [ ] If gateway alive but cron silent > 80min → check `gateway/run.py:3260-3290` for Sub-pattern 10 first (broken nested try/except), then kickstart (Sub-pattern 9)
- [ ] If `declare -A` syntax error → bash 3.2, use parallel indexed arrays
- [ ] If `date -j -f` shows 9h drift on log timestamps → use Python `datetime.fromisoformat` for TZ-aware parsing

## Related
- [[@memory/growth/harness-autonomous-behaviors]] — harness self-healing patterns
- brain-dashboard-system skill
- `cron-jobs-stalled` — Pattern A/C: jobs.json looks fine but cron-runner is dead. **Sub-pattern 6 in this skill (jobs.json patch has zero effect on a dead scheduler) is the missing link**: cron-jobs-stalled Pattern A fix only helps if the scheduler is alive. Without watchdog + Sub-pattern 6 awareness, the Pattern A fix silently no-ops.
- `drewgent-runtime-checkup` — Phase 4b (cron-runner wrapper registration)
- `n8n-self-hosted-diagnostics` — n8n is the canonical case for Sub-pattern 1 (Node.js SIGTERM → exit 0 trap). Verified on 2026-06-10.
- `P6-prefrontal/incidents/launchd-mass-failure-20260610.md` — full incident doc (7 sections, 11KB)
- `P6-prefrontal/incidents/cron-runner-launchd-detached-20260601.md` — earlier partial incident (a) 2026-05-30/06-01 fix was correct in code but only delayed the next gateway death; (b) the gap analysis that predicted this incident
- `P6-prefrontal/incidents/gateway-scheduler-double-fire-20260610.md` — Sub-pattern 7 + Sub-pattern 8 + Sub-pattern 9 full diagnosis
- `P6-prefrontal/incidents/acp-spinner-attempts-20260602.md` — ACP thinking indicator 3-attempt rejection (non-retryable)
- `references/2026-06-10-launchd-mass-failure.md` — raw data from the 6/10 incident that motivated the new "Reverse Pattern" section
- **`references/gateway-watchdog-2026-06-11.md`** — launchd-based gateway watchdog (5-min interval, PID check + auto-restart). Independent of the gateway process so it works when gateway is crashed.
- **`references/2026-06-10-incident-fix-recipe.md`** — **the playbook actually executed on 6/10** (watchdog script verbatim, canonical KeepAlive block, restart sequence, jobs.json fast-forward behavior, verification checklist, common pitfalls). Read this when you need to do the fix, not just diagnose.
- **`references/2026-06-10-customize-layer-recipe.md`** — **Drewgent customize layer pattern (archived)**. How the customize layer used to work for Drewgent's environment. Directory layout, three activation paths (gateway plist / .zshrc / `~/.local/bin/hermes` wrapper), the importlib.util proxy pattern, the macOS Sonoma+ plist-format launchctl output, smoke test cron, 8 pitfalls. Verified 2026-06-10 17:30. **Note:** hermes CLI has been removed; this is historical reference only.
- **`references/2026-06-10-log-rotation-recipe.md`** — **log rotation for launchd services**. macOS newsyslog doesn't handle launchd stdout/stderr, so launchd services need manual rotation. The working strategy: `gzip -c` archive + `: >` truncate + `launchctl kickstart -k` to reopen the FD. Verified on 6/10: 1.7GB error log → 0B live + 9.6MB .gz archive. Includes the script, cron registration, tunables, and 8 pitfalls (forgetting the kickstart, symlinked paths, multi-service files, etc.).
- **`references/2026-06-10-harmony-check-recipe.md`** — 4-layer cross-diff script + Layer 3.5 mtime drift detection (catches Sub-pattern 9 stalls within 60s of occurrence). Verified 6/10 19:38 to detect a 1.7h+ gateway cron stall.
- **`references/2026-06-10-gateway-cron-stall-fix-recipe.md`** — Sub-pattern 10 root cause + fix. The actual code patch (gateway/run.py:3260-3290) verified 2026-06-10 20:55. Includes the broken code, the fixed code, the 5-minute observation that confirmed the fix, and the pattern for any "housekeeping in cron tick thread" architecture.