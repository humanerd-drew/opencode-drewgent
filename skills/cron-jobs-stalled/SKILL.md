---
name: cron-jobs-stalled
description: Diagnose and recover cron jobs in jobs.json that stopped running (next_run_at=null, no recent execution). Distinguishes scheduler bug vs script quality issue. Applies 60-second recovery patch.
category: devops
created: 2026-06-01
updated: 2026-06-14
links:
  - "[[P0-brainstem/brain/rules]]"
---

# Cron Jobs Stalled — Diagnostic & Recovery

When user reports "X cron not running" or "X job stopped" or jobs.json shows enabled jobs with no recent execution, this skill diagnoses and recovers.

**Triggers:**
- "X cron stopped", "X job not running for N days"
- `~/.drewgent/cron/jobs.json` enabled jobs with `last_run_at` > 1 day old
- All enabled jobs may have `next_run_at: null`
- `~/.drewgent/cron/output/{job_id}/` has no recent files
- Output files exist but contain junk (empty body, trivial title)

## Step 1: Read jobs.json directly (filesystem truth)

```bash
python3 -c "import json; d=json.load(open('$HOME/.drewgent/cron/jobs.json')); [print(f'{j.get(\"name\",\"?\"):30} enabled={j.get(\"enabled\")} last={str(j.get(\"last_run_at\",\"\"))[:19]} next={str(j.get(\"next_run_at\",\"\"))[:19] or \"NULL\"} status={j.get(\"last_status\",\"\")}') for j in d.get('jobs',[])]"

ls -lt ~/.drewgent/cron/output/*/ 2>/dev/null | head -30
```

Don't trust `last_status=ok` — it's a stale marker. `next_run_at` is the source of truth for whether the scheduler will run the job.

**Output dir name = job_id (12-char hex), NOT job name.** `cron/output/{job_id}/` directory names are auto-generated from `jobs.json` `id` field. To find the dir for a job, read its `id` from jobs.json, don't guess from the name. (e.g. `kanban-dispatcher-integrations` has id `cb909be06e0e` → dir is `cron/output/cb909be06e0e/`, not `cron/output/integrations-board-dispatcher/`.)

## Step 2: Classify the failure

Five distinct patterns. Diagnose carefully — fix is different for each.

### Pattern A: `next_run_at: null` for recurring jobs (scheduler bug)

**Symptoms:**
- All (or most) enabled jobs have `next_run_at: null`
- `last_run_at` 1-2 days old
- Output dir has no recent files

**Root cause:** `cron/jobs.py` `get_due_jobs()` only calls `_recoverable_oneshot_run_at()` for null `next_run_at`. Recurring jobs (`schedule.kind in {'cron', 'interval'}`) get dropped silently.

**Documented incidents:**
- `P6-prefrontal/incidents/cron-jobs-stalled-20260601.md` (5 enabled jobs, ~36h dormant)
- `P6-prefrontal/incidents/cron-job-failure-20260518.md` (related — double-run fix, qa_evidence_dir KeyError)

**Fix (immediate, 60s recovery):**
```python
from cron.jobs import load_jobs, save_jobs, _drewgent_now
from datetime import timedelta

now = _drewgent_now()
jobs = load_jobs()
patched = 0
for j in jobs:
    if (j.get('enabled')
        and j.get('next_run_at') is None
        and j.get('schedule', {}).get('kind') in ('cron', 'interval')):
        j['next_run_at'] = (now - timedelta(seconds=5)).isoformat()
        patched += 1
save_jobs(jobs)
print(f"patched: {patched} jobs")
```

**Fix (permanent, in `cron/jobs.py` `get_due_jobs()`):** Add branch for recurring jobs that recomputes `next_run_at` from `schedule` when null. Applied 2026-06-01, takes effect on gateway restart.

### Pattern B: Scheduler runs but script produces junk

**Symptoms:**
- `last_run_at` updates every 6h (cron ticks normally)
- Output dir has recent files but content is trivial
- Articles saved with empty body or trivial title (e.g. "안녕하세요")

**Root cause:** Bad RSS feed added (e.g. letspl.me 밋업 feed → "안녕하세요" event intros), or extraction script broke.

**Diagnostic:**
```bash
# Find junk articles
ls -lt ~/.drewgent/cron/output/{job_id}/ | head -10
# Check content of recent files
for f in $(ls -t ~/.drewgent/cron/output/{job_id}/2026-*.md | head -5); do
  echo "=== $f ==="
  head -20 "$f"
done
```

**Fix:** 
1. Audit the RSS_FEEDS / source list — remove obviously off-topic sources
2. Add content min-length guards in main() (e.g. `MIN_TITLE_LENGTH=10`, `MIN_BODY_LENGTH=200`)
3. Add explicit `⏭️ SKIP (reason): url` log line
4. Add skip counter to final summary

See `skills/seo-article-harvester/scripts/harvester.py` (line 33-36 constants, line 514-552 main loop) for the canonical fix pattern.

### Pattern C: launchd isn't running cron_runner at all

**Symptoms:**
- jobs.json state looks fine
- `last_run_at` is stale (1+ days)
- `launchctl list | grep drewgent` shows no `ai.drewgent.cron-runner` plist

**Use skill:** `launchd-process-health-check` (separate skill)

### Pattern D: False alarm (system healthy, user perceives stall)

**Symptoms:**
- User reports "X job stopped" or "X not running for days" but `next_run_at` is valid (future-dated)
- `cron-runner.log` has recent "dispatchers run" lines (within last 1-2 min)
- `cron/output/{job_id}/` has recent files (within cycle window)
- Only `launchctl list` shows PID=- or output dir for one job looks empty

**Root cause — three sub-patterns, all look like stalls but aren't:**

**D1. Long-cycle job with valid next_run_at.** A 6h-cycle job (e.g. SEO/Trend harvester with `0 */6 * * *`) had its last run 1.5 days ago because the schedule is `0 */6 * * *` and next_run falls in 6h intervals. User sees "1.5 days since last run" and assumes stopped. **Verify by reading `next_run_at`** — if it's a valid future timestamp, the scheduler is correct.

**D2. launchctl tracking failure.** `launchctl list | grep cron-runner` shows PID=- but cron-runner is actually running. **launchd cannot track detached processes** — even when cron-runner is alive and producing output every minute, launchctl reports PID=-. Don't conclude "stopped" from this alone. (Verified 2026-06-01: cron output 🟢 4 dirs + log 1-min tick + 3 dispatchers run, despite `launchctl list PID=-`.)

**D3. Output dir name mismatch.** Looking for `cron/output/integrations-board-dispatcher/` is empty, so you conclude the job is missing. Actually the job is registered as `kanban-dispatcher-integrations` (id `cb909be06e0e`) and outputs to `cron/output/cb909be06e0e/` — and that dir has plenty of recent files. **Always map job_name → job_id from jobs.json before checking output dirs.**

**Diagnostic — 2 hard evidence signals required (NOT launchctl list alone):**

```bash
# Signal 1: cron-runner.log "dispatchers run" timestamp
tail -5 ~/.drewgent/P6-prefrontal/logs/cron-runner.log
# If timestamp is 5min+ stale → really stopped (Pattern C)
# If timestamp is recent → system is alive

# Signal 2: latest cron output file mtime (across ALL jobs)
find ~/.drewgent/cron/output/*/ -name "*.md" -mmin -10
# If 1+ file modified in last 10min → at least one job is running
# If nothing in last 10min → really stopped (or all boards are empty queues)
```

**Soft evidence (NOT sufficient alone):**
- `launchctl list | grep ai.drewgent.cron-runner` PID=- → launchd may not track detached processes
- `last_status=ok` on all jobs → stale marker, not proof of recent run
- `last_run_at` older than 1 day on a 6h-cycle job → within cycle window, not stalled
- One specific output dir is empty → could be name mismatch (D3) or that specific job not running

**Verification fix (when in doubt — 90s):**
```python
# Force-due one specific job to verify scheduler is alive
import json
from datetime import datetime, timedelta
from pathlib import Path

JOBS = "/Users/drew/.drewgent/cron/jobs.json"
OUT = Path("/Users/drew/.drewgent/cron/output")

data = json.load(open(JOBS))
target = next(j for j in data['jobs'] if j['name'] == 'X Article Harvester')
target['next_run_at'] = (datetime.now() - timedelta(seconds=5)).isoformat()
json.dump(data, open(JOBS, 'w'), ensure_ascii=False, indent=2)

# Wait 75-90s for at least one tick
import time; time.sleep(75)

# Check the job's output dir (using job_id, NOT name)
d = OUT / target['id']
files = sorted(d.glob("*"), key=lambda f: f.stat().st_mtime, reverse=True)
if files and (datetime.now() - datetime.fromtimestamp(files[0].stat().st_mtime)).total_seconds() < 90:
    print(f"✅ spawn confirmed: {files[0].name}")
else:
    print(f"⚠ no spawn — investigate further")
```

**Fix:** None needed — the system is healthy. Communicate to user:
- "The 6h cycle (SEO/Trend) scheduled next run at 6/2 00:00. Last run 1.5 days ago is within cycle window."
- "If you want immediate verification, patched `next_run_at` to (now-5s) and confirmed spawn within 75-90s."

### Pattern E: Silent undetected scheduler death (the 2026-06-10 case)

**Symptoms:**
- All enabled jobs have `last_run_at` cluster around the same old date (e.g. 22 days stale)
- `launchctl list | grep opencode` shows the serve process with `PID=-` and old exit code
- `~/.drewgent/P6-prefrontal/logs/cron-runner.log` mtime is hours/days stale
- **Most importantly**: there is no `infrastructure watchdog` to surface this — Pattern A fix has been applied to jobs.json, but the gateway itself is dead, so the patch is invisible to the in-memory scheduler

**Root cause:** The gateway/cron-runner process is dead. Pattern A's recovery code in `cron/jobs.py get_due_jobs()` works correctly when the gateway restarts, but a dead gateway → no Pattern A patch path → no recovery. Verified 2026-06-10: a 6/1 incident's Pattern A fix was correct in code, but the gateway died 4 days later. The patch couldn't help because the patch needs a live process to load it.

**Why this is the dangerous case (and why A/B/C/D don't capture it):**
- The 6/1 incident "fixed" Pattern A. From the *code* perspective, everything was correct.
- The 6/10 checkup found the system had been dead for 6+ days. The "fix" was real, but the system then died *again*, and there was no alert.
- This is a *meta-pattern* — failure of the recovery mechanism for Pattern A itself.

**Diagnostic — three signals together (any one is suspicious; all three = Pattern E):**
- `launchctl list | grep opencode` shows the serve process with `PID=-` and old exit code (likely -15 for SIGTERM, 0 for graceful stop)
- `jobs.json` all `last_run_at` values cluster within hours of each other (suggesting one failure event took everything down)

**Fix — restart gateway first, do NOT patch jobs.json first:**
```bash
# 1. Verify the gateway is actually dead (Pattern D2 soft evidence)
ps aux | grep drewgent_cli.main.*gateway | grep -v grep
# If empty → really dead. If present but PID=- → launchd tracking failure (Pattern D2)

# 2. Restart gateway. Do NOT patch jobs.json first.
launchctl kickstart -k gui/$(id -u)/ai.drewgent.gateway

# 3. Wait 5-10s for startup, verify log shows "Cron ticker started"
sleep 8
tail -5 ~/.drewgent/logs/gateway.log
# Expect: "Cron ticker started (interval=60s)" + "Job 'X' missed its scheduled time ... Fast-forwarding to next run: ..."

# 4. Verify jobs.json is now future-dated
python3 -c "import json; d=json.load(open('/Users/drew/.drewgent/cron/jobs.json')); [print(f\"{j.get('name','?'):30} next={str(j.get('next_run_at',''))[:19]}\") for j in d.get('jobs',[]) if j.get('enabled')]"
# Expect: all next_run_at are future-dated

# 5. Install the watchdog NOW so this doesn't recur. Script + registration in launchd-process-health-check skill.
```

**Why "restart first" order matters**: jobs.json is loaded into in-memory state at process start. File edits after the process is dead do not propagate. Verified 2026-06-10: a 6/1 incident's Pattern A recovery code was correct, but the gateway had died 4 days later and the patch path was effectively non-existent. The 6/10 watchdog (launchd health check every 5 min) prevents this from going undetected again.

## Pattern F (verified 2026-06-10 19:38): gateway cron tick stalls mid-session — Layer 3.5 catches it

Distinct from Pattern E (gateway entirely dead). Here the gateway process is alive, launchd tracking is healthy, but the **internal cron ticker loop stops firing** after ~80 minutes. Verified 6/10: gateway started at 17:50, dispatcher fired every minute until 19:18, then 1.7h+ idle.

**Layer 3.5 of `drewgent_harmony_check.sh` correctly detects this**:
```
## Layer 3.5: jobs.json mtime drift
  ⚠ jobs.json modified 6270s after last dispatcher tick — in-memory state may be stale
```

The Layer 1/2 launchd checks (gateway alive, port LISTEN) make it look healthy. The real condition is "scheduler stuck despite process alive." Manual kickstart revives:
```bash
launchctl kickstart -k gui/$(id -u)/ai.drewgent.gateway
```

**Recommended automation**: extend the harmony check cron (id `80bda2815f40`, daily 09:00) to run more frequently, AND add auto-kickstart when 3 consecutive Layer 3.5 alerts fire within 30 minutes. (Tracked in `gateway-scheduler-double-fire-20260610.md`.)

**Verified recovery sequence** (P1.1, 2026-06-10 20:19): when Pattern F fires, `launchctl kickstart -k gui/$(id -u)/ai.drewgent.gateway` reliably revives the cron ticker for ~80 minutes (until the next stall). The full session of kickstarts observed on 6/10: 20:15:07 → 20:16:10 fire → stall; 20:19:24 → 20:20:26 fire → stall; 20:23:17 → 20:24:20 fire → stall. **Pattern is consistent: 1 fire after kickstart, then stall within 1-2 minutes.** This suggests a 1-fires-then-quiet bug in the cron tick loop, distinct from a deadlock (which would also block 1 fire).

**Root cause hypothesis** (unverified): the cron tick thread starts a single fire then either (a) joins a thread that has already terminated, or (b) sets a flag that the next tick checks and exits. Both behaviors are consistent with the observed pattern. To diagnose: add `log.debug` calls inside the cron tick loop (in `cron/scheduler.py`) showing each tick's start/end and any caught exception. The fix likely involves either replacing `Thread.join()` semantics with a daemon thread or restructuring the tick loop to be event-driven rather than thread-based.

**User preference (6/10)**: when "defer" is suggested, user prefers **진짜 fix** (root cause over workaround). 3-line fix? Do it NOW.

## Pattern H (verified 2026-06-11, fixed 2026-06-11): no_agent script subprocess path resolution bug

**Symptoms:**
- `last_status=error`, `last_error="Script not found: <name>.sh"`
- Script file exists at `~/.drewgent/scripts/<name>.sh` and `~/.hermes/scripts/<name>.sh`
- The job is a `no_agent` job with relative `script` path
- Script runs fine when invoked directly via `bash ~/.hermes/scripts/<name>.sh`

**Root cause:** `_run_script_subprocess()` in `~/.drewgent/source/drewgent-agent/cron/scheduler.py` (line 801–851):

1. **Relative path not resolved to scripts_dir**: `os.path.expanduser(script_path)` + `os.path.isfile()` checks the **current working directory** (`~/.drewgent/source/drewgent-agent/`) instead of `scripts_dir` (`~/.drewgent/scripts/`).

2. **`.sh` files run with Python**: uses `[sys.executable, expanded_script]` for ALL scripts regardless of suffix. `.sh` files need bash.

**Contrast:** The official Hermes scheduler (`~/.hermes/hermes-agent/cron/scheduler.py` line 984-1017) resolves relative paths correctly against `get_hermes_home() / "scripts"` but shares the same interpreter bug: it runs `.sh`/`.bash` with bash and everything else (`.js`, `.py`, etc.) with `sys.executable` (Python). A `.js` file executed by Python produces a `SyntaxError` on non-ASCII characters like `—` (U+2014). The workaround is a `.sh` wrapper that calls the real interpreter.

**Fix applied 2026-06-11:** Patched `_run_script_subprocess()` in `cron/scheduler.py`:
1. Added `import shutil`
2. Relative paths resolved against `get_drewgent_home() / "scripts/"` (not cwd)
3. `.sh`/`.bash` files run via `shutil.which("bash")` (not `sys.executable`)
4. Stale `last_error` cleared in `jobs.json`; auto-clears on next scheduler tick

**Script location double-check:** no_agent scripts need to exist at BOTH locations. Canonical origin is `~/.hermes/scripts/` but the Drewgent customize layer redirects HERMES_HOME → `~/.drewgent`, so the active scheduler reads from `~/.drewgent/scripts/`. Copy scripts to both locations.

**Full recipe:** `references/2026-06-11-noagent-script-resolution-bug.md`

**Critical: Gateway restart required.** Patching `scheduler.py` on disk does NOT affect the running gateway process — the Python module cache (`.pyc`) may update, but the in-memory scheduler code is only refreshed on process start. Always follow a patch with:
```bash
launchctl kickstart -k gui/$(id -u)/ai.drewgent.gateway
sleep 5
grep "Cron ticker started" ~/.drewgent/logs/gateway.log | tail -1
```

**Stale error clearing:** After restart, old `last_error` from before the patch persists in `jobs.json`. It auto-clears on the next successful tick. For long-cycle jobs (e.g. 6h), manually patch `last_status` → `"ok"` and `last_error` → `null` in `~/.drewgent/cron/jobs.json`.

## Step 3: Apply recoveryscheduler reads from `~/.drewgent/scripts/`. Copy scripts to both locations.

**Full recipe:** `references/2026-06-11-noagent-script-resolution-bug.md`

**Critical: Gateway restart required.** Patching `scheduler.py` on disk does NOT affect the running gateway process — the Python module cache (`.pyc`) may update, but the in-memory scheduler code is only refreshed on process start. Always follow a patch with:
```bash
launchctl kickstart -k gui/$(id -u)/ai.drewgent.gateway
sleep 5
grep "Cron ticker started" ~/.drewgent/logs/gateway.log | tail -1
```

**Stale error clearing:** After restart, old `last_error` from before the patch persists in `jobs.json`. It auto-clears on the next successful tick. For long-cycle jobs (e.g. 6h), manually patch `last_status` → `"ok"` and `last_error` → `null` in `~/.drewgent/cron/jobs.json`.

## Step 3: Apply recovery
- Gateway log shows LLM job's QA gate or Dangerous operation in-progress
- After the LLM job finishes, script jobs fire again (cycle repeats)

**Root cause:** `tick()` runs all due jobs sequentially. An LLM job (>3 min) blocks script dispatchers (<1s).

**Fix:**
1. Disable redundant LLM cron jobs in jobs.json
2. In `cron/scheduler.py:tick()`, add 3 lines before the loop:
```python
_script_jobs = [j for j in due_jobs if j.get("script")]
_llm_jobs = [j for j in due_jobs if not j.get("script")]
for job in _script_jobs + _llm_jobs:
```
Verified 2026-06-10 23:53. Protection: T4.3 tick watchdog, T4.4 Layer 3.5b, T4.6 auto-kickstart, A.2 housekeeping fix.

**User preference (6/10)**: when "defer" is suggested, user prefers **진짜 fix** (root cause over workaround). 3-line fix? Do it NOW.

## Pattern H (verified 2026-06-11, fixed 2026-06-11): no_agent script subprocess path resolution bug

**Symptoms:**
- `last_status=error`, `last_error="Script not found: <name>.sh"`
- Script file exists at `~/.drewgent/scripts/<name>.sh` and `~/.hermes/scripts/<name>.sh`
- The job is a `no_agent` job with relative `script` path
- Script runs fine when invoked directly via `bash ~/.hermes/scripts/<name>.sh`

**Root cause:** `_run_script_subprocess()` in `~/.drewgent/source/drewgent-agent/cron/scheduler.py` (line 801–851):

1. **Relative path not resolved to scripts_dir**: `os.path.expanduser(script_path)` + `os.path.isfile()` checks the **current working directory** (`~/.drewgent/source/drewgent-agent/`) instead of `scripts_dir` (`~/.drewgent/scripts/`).

2. **`.sh` files run with Python**: uses `[sys.executable, expanded_script]` for ALL scripts regardless of suffix. `.sh` files need bash.

**Contrast:** The official Hermes scheduler (`~/.hermes/hermes-agent/cron/scheduler.py` line 984-1017) resolves relative paths correctly against `get_hermes_home() / "scripts"` but shares the same interpreter bug: it runs `.sh`/`.bash` with bash and everything else (`.js`, `.py`, etc.) with `sys.executable` (Python). A `.js` file executed by Python produces a `SyntaxError` on non-ASCII characters like `—` (U+2014). The workaround is a `.sh` wrapper that calls the real interpreter.

**Fix applied 2026-06-11:** Patched `_run_script_subprocess()` in `cron/scheduler.py`:
1. Added `import shutil`
2. Relative paths resolved against `get_drewgent_home() / "scripts/"` (not cwd)
3. `.sh`/`.bash` files run via `shutil.which("bash")` (not `sys.executable`)
4. Stale `last_error` cleared in `jobs.json`; auto-clears on next scheduler tick

**Script location double-check:** no_agent scripts need to exist at BOTH locations. Canonical origin is `~/.hermes/scripts/` but the Drewgent customize layer redirects HERMES_HOME → `~/.drewgent`, so the active scheduler reads from `~/.drewgent/scripts/`. Copy scripts to both locations.

**Full recipe:** `references/2026-06-11-noagent-script-resolution-bug.md`

**Critical: Gateway restart required.** Patching `scheduler.py` on disk does NOT affect the running gateway process — the Python module cache (`.pyc`) may update, but the in-memory scheduler code is only refreshed on process start. Always follow a patch with:
```bash
launchctl kickstart -k gui/$(id -u)/ai.drewgent.gateway
sleep 5
grep "Cron ticker started" ~/.drewgent/logs/gateway.log | tail -1
```

**Stale error clearing:** After restart, old `last_error` from before the patch persists in `jobs.json`. It auto-clears on the next successful tick. For long-cycle jobs (e.g. 6h), manually patch `last_status` → `"ok"` and `last_error` → `null` in `~/.drewgent/cron/jobs.json`.

## Step 3: Apply recovery

## Pattern G (verified 2026-06-10 23:53): LLM cron job blocks sequential tick loop

When hermes-cli shows "⚠ Gateway is not running" but the gateway *is* alive, that's a hermes-cli ↔ launchd label mismatch — *not* a real incident. The Customize Layer (under `~/.drewgent/customize/`) overrides hermes's hardcoded `get_launchd_label()` to return your actual launchd label. **However, this also creates a new failure mode** to watch for:

- **Sub-pattern (verified 6/10 19:35)**: smoke test of the customize layer may show *false positives* if regex is too loose. A naive `grep "unset PYTHONPATH"` matches `unset PYTHONHOME` (substring). Use anchored regex: `^[[:space:]]*unset[[:space:]]+PYTHONPATH[[:space:]]*$`. Similarly for "dangling wikilink" counts in `drewgent_graph_gap_analysis.sh` — count the *alert line* (`⚠ dangling:`), not the section header (`## Dangling wikilinks`).
- **Memory drift guard (verified 6/10 19:38)**: the `memory` tool refuses to `add` if MEMORY.md was modified *outside* the tool (e.g. by `write_file` or `patch`). It saves a `.bak.<timestamp>` and asks you to reconcile. This is a *safety feature* — preserves the round-trip assumption. When patching memory directly via `write_file`, expect subsequent `memory(action="add")` to fail until you either (a) rewrite the file as a clean §-delimited list, or (b) move the extra content out. **Lesson**: if you need to add a structural change to memory, plan to *not* use the `memory` tool afterward in the same session — go straight to direct write and accept the drift.

## GBrain 4-Pillar Pattern in Our Vault (verified 2026-06-10 19:30)

When memory has 12+ entries that have grown past the 8,000-char cap, the *Karpathy LLM Wiki* strategy applies: **convert raw incident reports into compiled procedures with vault wikilinks**. This is a *cross-cutting pattern* used in both `cron-jobs-stalled` skill (Pattern E "restart first" is a compiled procedure) and the broader memory system.

**The 4 pillars we adopt from [Garry Tan's GBrain](https://github.com/garrytan/gbrain)** (lightly adapted for a single-machine Drewgent):

1. **Repo (vault)**: our `~/.drewgent/P2-hippocampus/memories/MEMORY.md` + `~/.drewgent/skills/` + incidents directory, all wikilinked. ✓ already had this.
2. **Synthesis**: convert raw incident dumps into compiled procedures (e.g. "6/10 incident doc" → "Launchd Hardening template" + "Cron Discipline" + "Memory System" sections). ✓ applied 6/10 (12 → 9 entries, 21% size reduction).
3. **Graph traversal**: `~/.hermes/scripts/drewgent_graph_lookup.sh` — given a topic, walks wikilinks across MEMORY.md, P0-brainstem neurons, P4-cortex growth, P6-prefrontal incidents. Returns direct hits + incoming wikilinks + outgoing wikilinks. ✓ implemented 6/10.
4. **Gap analysis**: `~/.hermes/scripts/drewgent_graph_gap_analysis.sh` — detects (a) **dangling wikilinks** in MEMORY.md pointing to non-existent files, (b) **orphan vault files** not referenced from memory. ✓ implemented 6/10.

**Smoke test integration** (T5/T6/T7/T8 → `~/.hermes/scripts/customize_smoke_test.sh`): runs all 4 checks weekly via cron `f0b39d211970` (Sun 10:00 KST). All 4 checks pass as of 6/10 19:36.

**Script location double-check:** no_agent scripts need to exist at BOTH locations. Canonical origin is `~/.hermes/scripts/` but the Drewgent customize layer redirects HERMES_HOME → `~/.drewgent`, so the active scheduler reads from `~/.drewgent/scripts/`. Copy scripts to both locations.

**Full recipe:** `references/2026-06-11-noagent-script-resolution-bug.md`

**Critical: Gateway restart required.** Patching `scheduler.py` on disk does NOT affect the running gateway process — the Python module cache (`.pyc`) may update, but the in-memory scheduler code is only refreshed on process start. Always follow a patch with:
```bash
launchctl kickstart -k gui/$(id -u)/ai.drewgent.gateway
sleep 5
grep "Cron ticker started" ~/.drewgent/logs/gateway.log | tail -1
```

**Stale error clearing:** After restart, old `last_error` from before the patch persists in `jobs.json`. It auto-clears on the next successful tick. For long-cycle jobs (e.g. 6h), manually patch `last_status` → `"ok"` and `last_error` → `null` in `~/.drewgent/cron/jobs.json`.

## Step 3: Apply recovery

| Pattern | Recovery |
|---------|----------|
| A (next_run_at=null) | jobs.json patch above + wait 60s for tick |
| B (junk output) | Script-level fix: feed list + content guard |
| C (launchd) | `launchd-process-health-check` skill |
| D (false alarm) | No fix needed — communicate to user. Optionally force-due one job to verify (90s patch + wait). |
| E (silent scheduler death) | Restart gateway FIRST, then install watchdog. Don't patch jobs.json before restart. |
| G (LLM job blocks tick) | Step 1: disable redundant LLM job. Step 2: reorder tick loop (script jobs first). Both required. |

## Step 4: Verification (3-Phase QA Gate)

For Pattern A, after patch:
```bash
# Wait 60s for cron tick
sleep 60

# Verify: jobs.json next_run_at should be non-null and future-dated
python3 -c "import json; d=json.load(open('$HOME/.drewgent/cron/jobs.json')); [print(f'{j.get(\"name\",\"?\"):30} next={str(j.get(\"next_run_at\",\"\"))[:19] or \"NULL\"}') for j in d.get('jobs',[]) if j.get('enabled')]"

# Verify: output dir has new file from this tick
ls -lt ~/.drewgent/cron/output/*/ 2>/dev/null | head -5
```

## Internal-Tool Consolidation Workflow (user preference, 2026-06-10)

When a checkup produces a list of "follow-ups" (deferred fixes), before deferring ask: **"can any of these be handled by an existing internal tool?"** This preference was expressed by the user on 2026-06-10 in response to the 4 follow-ups from the 6/10 incident. The user's framing:

> "보류된 follow-up은 내부 기능으로 대체 가능한 건 그렇게 하고 정리하면 되지 않을까. 어떠니."

Translation: "If a deferred follow-up can be replaced by an existing internal tool, just do that and clean up. How about it?"

**Three user preferences emerged from 6/10 that this skill now encodes:**

1. **"보류된 follow-up은 내부 기능으로 대체 가능하면 그렇게 하고 정리"** — *consolidate first, defer last*. When a follow-up list grows, ask: can an existing internal tool handle this automatically? Can the symptom be re-verified as a false alarm? Long follow-up lists indicate "we're not done" — not "we're done with documentation."

2. **"꼼꼼하게, 찌꺼기 남기지 않게"** — *completeness over cleverness*. When a plan has phases, finish all phases. When a script creates temporary files, clean them up. When a follow-up emerges, decide: implement now, document in incident doc, or drop. No "we'll get to it later."

3. **"다른 문제 나오면 대기"** — *incremental disclosure*. When a checkup uncovers a new problem during a "complete the work" pass, stop and report. Don't cascade. The user's job is to *choose* the next thread; the agent's job is to *finish* the current one cleanly.

**Decision flow for each follow-up:**

1. **Can an existing cron, watchdog, or skill handle this automatically?**
   - YES → wire it up now, mark follow-up as resolved
   - NO → continue to step 2

2. **Does the symptom actually reproduce on re-verification?**
   - NO (false alarm — symptom doesn't match filesystem truth) → drop the follow-up entirely, document as "false alarm"
   - YES → continue to step 3

3. **Is this a real reliability improvement, or scope creep?**
   - Reliability fix needed → keep in incident doc section 6.5 "Open (deferred — not part of this incident)"
   - Scope creep / nice-to-have → drop it, "internal-tool-consolidation" rule says: don't accumulate follow-ups for marginal value

**Concrete examples from 6/10 sweep:**
- F1 (n8n plist missing) → consolidated: rewrote plist from memory template + bootstrap. Done.
- F2 (port 5555 HTTP 000) → false alarm. Re-verified with `lsof -i :8765` → 200. Dropped.
- F3 (api_start_time error) → false alarm. `grep -c` returned 0. Dropped.
- "log rotation infrastructure" (NEW follow-up that emerged from F1-F3 work) → consolidated: wrote `drewgent_log_rotate.sh` + cron registration. Done.

**Why this preference matters:** a long follow-up list in an incident doc signals "we're not done, we're not sure if we're done, please come back later." Consolidating follow-ups into the existing system — or proving they're false alarms — makes the incident closure real.

## Recurrence Watch (2026-06-10)

The 6/1 incident fix above (Pattern A recovery branch + jobs.json patch) was assumed to be sufficient, but the actual state on 2026-06-10 was that the **gateway itself had been dead for 6+ days**. The Pattern A fix only helps *if the scheduler is running*. A dead gateway → no Pattern A patch path → no recovery.

**Three signals that gateway/scheduler itself is dead (not just Pattern A):**
- `launchctl list | grep opencode` shows the serve process is dead (PID=- with old exit code)
- `~/.drewgent/P6-prefrontal/logs/cron-runner.log` mtime is hours/days stale
- All jobs.json `last_run_at` cluster around the same old date

**If gateway itself is dead → `launchd-process-health-check` is the next skill to load.** Pattern A fix is moot without a working scheduler. This is the 2026-06-10 gap: 6/1 fix solved Pattern A correctly, but didn't prevent a future gateway death from going unnoticed for a week.

**Sequence when gateway is dead** (verified 2026-06-10):
1. **Restart gateway first** (do NOT patch jobs.json first — patches are invisible to the dead process).
2. On restart, gateway's `cron.jobs.get_due_jobs()` fast-forwards missed schedules with grace window (e.g. 7200s for 6h jobs). Log: `Job 'X' missed its scheduled time (...), grace=7200s). Fast-forwarding to next run: ...`
3. Verify `next_run_at` is future-dated for all enabled jobs (Pattern A's recovery branch handles the rest).
4. **Then** if a specific job is still dormant, force-due it (Pattern D verification, 90s patch + wait).

**Why "restart first" order matters**: jobs.json is loaded into in-memory state at process start. File edits after the process is dead do not propagate. Verified 2026-06-10: a 6/1 incident's Pattern A recovery code was correct, but the gateway had died 4 days later and the patch path was effectively non-existent. The 6/10 watchdog (launchd health check every 5 min) prevents this from going undetected again.

## Pattern F (verified 2026-06-10 19:38): gateway cron tick stalls mid-session — Layer 3.5 catches it

Distinct from Pattern E (gateway entirely dead). Here the gateway process is alive, launchd tracking is healthy, but the **internal cron ticker loop stops firing** after ~80 minutes. Verified 6/10: gateway started at 17:50, dispatcher fired every minute until 19:18, then 1.7h+ idle.

**Layer 3.5 of `drewgent_harmony_check.sh` correctly detects this**:
```
## Layer 3.5: jobs.json mtime drift
  ⚠ jobs.json modified 6270s after last dispatcher tick — in-memory state may be stale
```

The Layer 1/2 launchd checks (gateway alive, port LISTEN) make it look healthy. The real condition is "scheduler stuck despite process alive." Manual kickstart revives:
```bash
launchctl kickstart -k gui/$(id -u)/ai.drewgent.gateway
```

**Recommended automation**: extend the harmony check cron (id `80bda2815f40`, daily 09:00) to run more frequently, AND add auto-kickstart when 3 consecutive Layer 3.5 alerts fire within 30 minutes. (Tracked in `gateway-scheduler-double-fire-20260610.md`.)

**Verified recovery sequence** (P1.1, 2026-06-10 20:19): when Pattern F fires, `launchctl kickstart -k gui/$(id -u)/ai.drewgent.gateway` reliably revives the cron ticker for ~80 minutes (until the next stall). The full session of kickstarts observed on 6/10: 20:15:07 → 20:16:10 fire → stall; 20:19:24 → 20:20:26 fire → stall; 20:23:17 → 20:24:20 fire → stall. **Pattern is consistent: 1 fire after kickstart, then stall within 1-2 minutes.** This suggests a 1-fires-then-quiet bug in the cron tick loop, distinct from a deadlock (which would also block 1 fire).

**Root cause hypothesis** (unverified): the cron tick thread starts a single fire then either (a) joins a thread that has already terminated, or (b) sets a flag that the next tick checks and exits. Both behaviors are consistent with the observed pattern. To diagnose: add `log.debug` calls inside the cron tick loop (in `cron/scheduler.py`) showing each tick's start/end and any caught exception. The fix likely involves either replacing `Thread.join()` semantics with a daemon thread or restructuring the tick loop to be event-driven rather than thread-based.

**User preference (6/10)**: when "defer" is suggested, user prefers **진짜 fix** (root cause over workaround). 3-line fix? Do it NOW.

## Pattern H (verified 2026-06-11, fixed 2026-06-11): no_agent script subprocess path resolution bug

**Symptoms:**
- `last_status=error`, `last_error="Script not found: <name>.sh"`
- Script file exists at `~/.drewgent/scripts/<name>.sh` and `~/.hermes/scripts/<name>.sh`
- The job is a `no_agent` job with relative `script` path
- Script runs fine when invoked directly via `bash ~/.hermes/scripts/<name>.sh`

**Root cause:** `_run_script_subprocess()` in `~/.drewgent/source/drewgent-agent/cron/scheduler.py` (line 801–851):

1. **Relative path not resolved to scripts_dir**: `os.path.expanduser(script_path)` + `os.path.isfile()` checks the **current working directory** (`~/.drewgent/source/drewgent-agent/`) instead of `scripts_dir` (`~/.drewgent/scripts/`).

2. **`.sh` files run with Python**: uses `[sys.executable, expanded_script]` for ALL scripts regardless of suffix. `.sh` files need bash.

**Contrast:** The official Hermes scheduler (`~/.hermes/hermes-agent/cron/scheduler.py` line 984-1017) resolves relative paths correctly against `get_hermes_home() / "scripts"` but shares the same interpreter bug: it runs `.sh`/`.bash` with bash and everything else (`.js`, `.py`, etc.) with `sys.executable` (Python). A `.js` file executed by Python produces a `SyntaxError` on non-ASCII characters like `—` (U+2014). The workaround is a `.sh` wrapper that calls the real interpreter.

**Fix applied 2026-06-11:** Patched `_run_script_subprocess()` in `cron/scheduler.py`:
1. Added `import shutil`
2. Relative paths resolved against `get_drewgent_home() / "scripts/"` (not cwd)
3. `.sh`/`.bash` files run via `shutil.which("bash")` (not `sys.executable`)
4. Stale `last_error` cleared in `jobs.json`; auto-clears on next scheduler tick

**Script location double-check:** no_agent scripts need to exist at BOTH locations. Canonical origin is `~/.hermes/scripts/` but the Drewgent customize layer redirects HERMES_HOME → `~/.drewgent`, so the active scheduler reads from `~/.drewgent/scripts/`. Copy scripts to both locations.

**Full recipe:** `references/2026-06-11-noagent-script-resolution-bug.md`

**Critical: Gateway restart required.** Patching `scheduler.py` on disk does NOT affect the running gateway process — the Python module cache (`.pyc`) may update, but the in-memory scheduler code is only refreshed on process start. Always follow a patch with:
```bash
launchctl kickstart -k gui/$(id -u)/ai.drewgent.gateway
sleep 5
grep "Cron ticker started" ~/.drewgent/logs/gateway.log | tail -1
```

**Stale error clearing:** After restart, old `last_error` from before the patch persists in `jobs.json`. It auto-clears on the next successful tick. For long-cycle jobs (e.g. 6h), manually patch `last_status` → `"ok"` and `last_error` → `null` in `~/.drewgent/cron/jobs.json`.

## Step 3: Apply recoveryscheduler reads from `~/.drewgent/scripts/`. Copy scripts to both locations.

**Full recipe:** `references/2026-06-11-noagent-script-resolution-bug.md`

**Critical: Gateway restart required.** Patching `scheduler.py` on disk does NOT affect the running gateway process — the Python module cache (`.pyc`) may update, but the in-memory scheduler code is only refreshed on process start. Always follow a patch with:
```bash
launchctl kickstart -k gui/$(id -u)/ai.drewgent.gateway
sleep 5
grep "Cron ticker started" ~/.drewgent/logs/gateway.log | tail -1
```

**Stale error clearing:** After restart, old `last_error` from before the patch persists in `jobs.json`. It auto-clears on the next successful tick. For long-cycle jobs (e.g. 6h), manually patch `last_status` → `"ok"` and `last_error` → `null` in `~/.drewgent/cron/jobs.json`.

## Step 3: Apply recovery
- Gateway log shows LLM job's QA gate or Dangerous operation in-progress
- After the LLM job finishes, script jobs fire again (cycle repeats)

**Root cause:** `tick()` runs all due jobs sequentially. An LLM job (>3 min) blocks script dispatchers (<1s).

**Fix:**
1. Disable redundant LLM cron jobs in jobs.json
2. In `cron/scheduler.py:tick()`, add 3 lines before the loop:
```python
_script_jobs = [j for j in due_jobs if j.get("script")]
_llm_jobs = [j for j in due_jobs if not j.get("script")]
for job in _script_jobs + _llm_jobs:
```
Verified 2026-06-10 23:53. Protection: T4.3 tick watchdog, T4.4 Layer 3.5b, T4.6 auto-kickstart, A.2 housekeeping fix.

**User preference (6/10)**: when "defer" is suggested, user prefers **진짜 fix** (root cause over workaround). 3-line fix? Do it NOW.

## Pattern H (verified 2026-06-11, fixed 2026-06-11): no_agent script subprocess path resolution bug

**Symptoms:**
- `last_status=error`, `last_error="Script not found: <name>.sh"`
- Script file exists at `~/.drewgent/scripts/<name>.sh` and `~/.hermes/scripts/<name>.sh`
- The job is a `no_agent` job with relative `script` path
- Script runs fine when invoked directly via `bash ~/.hermes/scripts/<name>.sh`

**Root cause:** `_run_script_subprocess()` in `~/.drewgent/source/drewgent-agent/cron/scheduler.py` (line 801–851):

1. **Relative path not resolved to scripts_dir**: `os.path.expanduser(script_path)` + `os.path.isfile()` checks the **current working directory** (`~/.drewgent/source/drewgent-agent/`) instead of `scripts_dir` (`~/.drewgent/scripts/`).

2. **`.sh` files run with Python**: uses `[sys.executable, expanded_script]` for ALL scripts regardless of suffix. `.sh` files need bash.

**Contrast:** The official Hermes scheduler (`~/.hermes/hermes-agent/cron/scheduler.py` line 984-1017) resolves relative paths correctly against `get_hermes_home() / "scripts"` but shares the same interpreter bug: it runs `.sh`/`.bash` with bash and everything else (`.js`, `.py`, etc.) with `sys.executable` (Python). A `.js` file executed by Python produces a `SyntaxError` on non-ASCII characters like `—` (U+2014). The workaround is a `.sh` wrapper that calls the real interpreter.

**Fix applied 2026-06-11:** Patched `_run_script_subprocess()` in `cron/scheduler.py`:
1. Added `import shutil`
2. Relative paths resolved against `get_drewgent_home() / "scripts/"` (not cwd)
3. `.sh`/`.bash` files run via `shutil.which("bash")` (not `sys.executable`)
4. Stale `last_error` cleared in `jobs.json`; auto-clears on next scheduler tick

**Script location double-check:** no_agent scripts need to exist at BOTH locations. Canonical origin is `~/.hermes/scripts/` but the Drewgent customize layer redirects HERMES_HOME → `~/.drewgent`, so the active scheduler reads from `~/.drewgent/scripts/`. Copy scripts to both locations.

**Full recipe:** `references/2026-06-11-noagent-script-resolution-bug.md`

**Critical: Gateway restart required.** Patching `scheduler.py` on disk does NOT affect the running gateway process — the Python module cache (`.pyc`) may update, but the in-memory scheduler code is only refreshed on process start. Always follow a patch with:
```bash
launchctl kickstart -k gui/$(id -u)/ai.drewgent.gateway
sleep 5
grep "Cron ticker started" ~/.drewgent/logs/gateway.log | tail -1
```

**Stale error clearing:** After restart, old `last_error` from before the patch persists in `jobs.json`. It auto-clears on the next successful tick. For long-cycle jobs (e.g. 6h), manually patch `last_status` → `"ok"` and `last_error` → `null` in `~/.drewgent/cron/jobs.json`.

## Step 3: Apply recovery

## Pattern G (verified 2026-06-10 23:53): LLM cron job blocks sequential tick loop

When hermes-cli shows "⚠ Gateway is not running" but the gateway *is* alive, that's a hermes-cli ↔ launchd label mismatch — *not* a real incident. The Customize Layer (under `~/.drewgent/customize/`) overrides hermes's hardcoded `get_launchd_label()` to return your actual launchd label. **However, this also creates a new failure mode** to watch for:

- **Sub-pattern (verified 6/10 19:35)**: smoke test of the customize layer may show *false positives* if regex is too loose. A naive `grep "unset PYTHONPATH"` matches `unset PYTHONHOME` (substring). Use anchored regex: `^[[:space:]]*unset[[:space:]]+PYTHONPATH[[:space:]]*$`. Similarly for "dangling wikilink" counts in `drewgent_graph_gap_analysis.sh` — count the *alert line* (`⚠ dangling:`), not the section header (`## Dangling wikilinks`).
- **Memory drift guard (verified 6/10 19:38)**: the `memory` tool refuses to `add` if MEMORY.md was modified *outside* the tool (e.g. by `write_file` or `patch`). It saves a `.bak.<timestamp>` and asks you to reconcile. This is a *safety feature* — preserves the round-trip assumption. When patching memory directly via `write_file`, expect subsequent `memory(action="add")` to fail until you either (a) rewrite the file as a clean §-delimited list, or (b) move the extra content out. **Lesson**: if you need to add a structural change to memory, plan to *not* use the `memory` tool afterward in the same session — go straight to direct write and accept the drift.

## GBrain 4-Pillar Pattern in Our Vault (verified 2026-06-10 19:30)

When memory has 12+ entries that have grown past the 8,000-char cap, the *Karpathy LLM Wiki* strategy applies: **convert raw incident reports into compiled procedures with vault wikilinks**. This is a *cross-cutting pattern* used in both `cron-jobs-stalled` skill (Pattern E "restart first" is a compiled procedure) and the broader memory system.

**The 4 pillars we adopt from [Garry Tan's GBrain](https://github.com/garrytan/gbrain)** (lightly adapted for a single-machine Drewgent):

1. **Repo (vault)**: our `~/.drewgent/P2-hippocampus/memories/MEMORY.md` + `~/.drewgent/skills/` + incidents directory, all wikilinked. ✓ already had this.
2. **Synthesis**: convert raw incident dumps into compiled procedures (e.g. "6/10 incident doc" → "Launchd Hardening template" + "Cron Discipline" + "Memory System" sections). ✓ applied 6/10 (12 → 9 entries, 21% size reduction).
3. **Graph traversal**: `~/.hermes/scripts/drewgent_graph_lookup.sh` — given a topic, walks wikilinks across MEMORY.md, P0-brainstem neurons, P4-cortex growth, P6-prefrontal incidents. Returns direct hits + incoming wikilinks + outgoing wikilinks. ✓ implemented 6/10.
4. **Gap analysis**: `~/.hermes/scripts/drewgent_graph_gap_analysis.sh` — detects (a) **dangling wikilinks** in MEMORY.md pointing to non-existent files, (b) **orphan vault files** not referenced from memory. ✓ implemented 6/10.

**Smoke test integration** (T5/T6/T7/T8 → `~/.hermes/scripts/customize_smoke_test.sh`): runs all 4 checks weekly via cron `f0b39d211970` (Sun 10:00 KST). All 4 checks pass as of 6/10 19:36.

**Reference**: `references/2026-06-10-vault-graph-recipe.md` (TBD) — full script sources, regex gotchas, and cron registration.

## Step 4: Verification (3-Phase QA Gate)

Use the 3-phase QA gate pattern for any code change. Evidence goes in `~/.drewgent/P2-hippocampus/qa-evidence/{task_id}/`.

**Contract** (write before coding):
- acceptance criteria as bullet list
- task_id is uuid4 string
- phase: "contract"

**Micro** (write after each step):
- per-step verification with `verified: true/false`
- accumulated across turns (not single-step overwrites)

**Full** (write at end):
- `all_criteria_met: true/false` boolean
- per-criterion evidence array
- `out_of_scope: [...]` for items deliberately excluded

See `禁task_qa_gate.neuron` for full HP-3 specification. `skills/qa/qa-cycle/` provides the workflow template.

## Pitfalls

- **Don't trust `last_status=ok`** — stale marker, not proof of recent execution.
- **Don't trust `launchctl list PID=-` alone** — launchd cannot track detached processes. cron-runner can be alive and producing output every minute while `launchctl list` shows PID=-. Use `cron-runner.log` timestamp + cron output dir mtime as the 2 hard evidence signals (Pattern D).
- **Don't trust `cron/output/{job_name}/`** — dir name = job_id (12-char hex), not job name. Read `id` from jobs.json first.
- **Don't just re-enable the job** — if `next_run_at` is null, `enabled=false→true` won't trigger a tick.
- **Don't just patch jobs.json** — without restart, the in-memory cron loop may overwrite your patch on next save. Permanent fix is in `cron/jobs.py`.
- **Don't add a NEW entry to jobs.json and expect immediate execution** — the in-memory cron loop loaded jobs.json at process start. New entries added after that are invisible to the loop until process restart (or file-watcher-based reload). The `get_due_jobs()` recovery branch in `cron/jobs.py` will set `next_run_at` for null entries on next load_jobs(), but if the process never re-reads jobs.json, the entry is dormant forever. Verified 2026-06-01: kanban-maintenance added at 18:38, 19:30 patch (now-5s) didn't trigger spawn because in-memory state is from 18:08.
- **Don't confuse cron-runner scope with jobs.json scheduler** — `ai.drewgent.cron-runner` plist runs 3 board dispatchers (default/content/integrations) only, processing kanban board tasks. jobs.json `schedule.kind in {cron, interval}` entries (SEO/Trend/kanban-maintenance/cron-output-cleanup) are processed by a SEPARATE process (likely gateway internal scheduler). Two different in-memory states, two different reload triggers.
- **Don't mix A with B** — scheduler stuck vs script producing junk need different fixes. User often says "stopped" but means "producing bad output."
- **Don't apply Pattern A fix to `kind: 'once'` jobs** — only recurring jobs (`kind in {cron, interval}`).
- **Don't fire the Pattern A fix without first checking launchd is alive** — if cron_runner isn't running, jobs.json patch does nothing.
- **Don't over-engineer a fix for a 0-risk residual** — when in-memory state is stale on a new entry, the practical impact is "job doesn't run until process restart or 6/7 cycle." If the job is non-critical (e.g. weekly cleanup) and the user is doing a checkup, recommend (H4) terminate + log follow-up. The 5-min on-call may not be worth the gateway restart.
- **Don't treat a follow-up list as final** — for each deferred item, ask: can an existing internal tool handle this? Can the symptom be re-verified as a false alarm? (See "Internal-Tool Consolidation Workflow" section above.) Long follow-up lists indicate "we're not done," not "we're done with documentation."

## Related

- `kanban-dispatcher-stalled` — parallel skill for kanban dispatcher
- `launchd-process-health-check` — for launchd-level issues. **Sub-pattern 6 in that skill (jobs.json patch has zero effect on a dead scheduler) is the missing link for Pattern E** in this skill.
- `drewgent-runtime-checkup` — broader system checkup
- `P6-prefrontal/incidents/cron-jobs-stalled-20260601.md` — incident report (5 enabled jobs, ~36h)
- `P6-prefrontal/incidents/cron-job-failure-20260518.md` — related incident (double-run)
- `P6-prefrontal/incidents/cron-runner-launchd-detached-20260601.md` — 5/30 incident false alarm analysis (PID=- soft evidence, plist StartInterval=60 already configured)
- `P6-prefrontal/incidents/launchd-mass-failure-20260610.md` — full incident doc for the Pattern E case (4 services dead 4-6 days, undetected)
- `cron/jobs.py` line 667-705 — `get_due_jobs()` recurring job recovery branch
- `禁task_qa_gate.neuron` — 3-phase QA gate specification
