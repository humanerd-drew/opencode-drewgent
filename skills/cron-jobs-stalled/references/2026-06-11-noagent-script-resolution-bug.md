# Pattern H — no_agent Script Resolution Bug

**Date:** 2026-06-11
**Cron IDs:** `2d9a31f2b661` (watchdog), `6596a0876cb9` (log_rotate), `80bda2815f40` (harmony_check)
**Symptom:** All 3 no_agent jobs show `last_status=error`, `last_error="Script not found: <filename>.sh"` despite scripts existing at `~/.{{AGENT_NAME_LOWER}}/scripts/`

## Root Cause

{{AGENT_NAME}}'s cron scheduler (`~/.{{AGENT_NAME_LOWER}}/source/{{AGENT_NAME_LOWER}}-agent/cron/scheduler.py`) has a bug in `_run_script_subprocess()` (line 801–851):

1. **Relative path not resolved to scripts_dir**: The function calls `os.path.expanduser(script_path)` then `os.path.isfile(expanded_script)`. For relative paths like `"{{AGENT_NAME_LOWER}}_launchd_watchdog.sh"`, this checks the **current working directory** (`~/.{{AGENT_NAME_LOWER}}/source/{{AGENT_NAME_LOWER}}-agent/`) instead of `scripts_dir` (`~/.{{AGENT_NAME_LOWER}}/scripts/`).

2. **`.sh` files run with Python**: Line 831 uses `[sys.executable, expanded_script]` for ALL scripts — even `.sh` files that need bash.

```python
# scheduler.py line 817, 823 — BUG
expanded_script = os.path.expanduser(script_path)
if not os.path.isfile(expanded_script):  # checks CWD, not scripts_dir
    error_msg = f"Script not found: {expanded_script}"
```

## Contrast with Hermes Version

The official Hermes scheduler (`~/.hermes/hermes-agent/cron/scheduler.py` line 984–1017) does this correctly: `scripts_dir = _get_hermes_home() / "scripts"` and resolves relative paths against it. It also chooses bash for `.sh` files and Python for everything else.

## Fix Applied 2026-06-11

Patched `_run_script_subprocess()` in `~/.{{AGENT_NAME_LOWER}}/source/{{AGENT_NAME_LOWER}}-agent/cron/scheduler.py`:

```python
def _run_script_subprocess(job, script_path, ...):
    import shutil
    from pathlib import Path
    from {{AGENT_NAME_LOWER}}_constants import get_{{AGENT_NAME_LOWER}}_home

    # 1) Resolve relative paths against scripts_dir
    raw = Path(script_path)
    if raw.is_absolute():
        resolved = raw
    else:
        resolved = get_{{AGENT_NAME_LOWER}}_home() / "scripts" / raw
    expanded_script = str(resolved.expanduser().resolve())

    # 2) Check file exists
    if not os.path.isfile(expanded_script):
        error_msg = f"Script not found: {expanded_script}"
        return False, "", "", error_msg

    # 3) Choose interpreter: bash for .sh, Python for everything else
    suffix = Path(expanded_script).suffix.lower()
    if suffix in (".sh", ".bash"):
        interpreter = shutil.which("bash") or "/bin/bash"
        argv = [interpreter, expanded_script]
    else:
        argv = [sys.executable, expanded_script]

    try:
        env = {**os.environ, "DREW_HOME": str(get_{{AGENT_NAME_LOWER}}_home())}
        result = subprocess.run(
            argv,
            capture_output=True, text=True, timeout=300,
            env=env, cwd=str(get_{{AGENT_NAME_LOWER}}_home()),
        )
        # ... rest of existing logic
```

## Post-Patch: Gateway Restart Mandatory

Patching `scheduler.py` on disk does NOT affect the running gateway. The Python module cache (`.pyc`) updates, but the in-memory scheduler code is only refreshed on process start.

**Always restart the gateway after a scheduler code patch:**

```bash
launchctl kickstart -k gui/$(id -u)/ai.{{AGENT_NAME_LOWER}}.gateway
sleep 5
grep "Cron ticker started" ~/.{{AGENT_NAME_LOWER}}/logs/gateway.log | tail -1
```

**Verification:** The watchdog job (5-min interval) runs within 5 minutes of restart. Check:
```bash
python3 -c "
import json
j = json.load(open('~/.{{AGENT_NAME_LOWER}}/cron/jobs.json'))
for job in j['jobs']:
    if job['id'] == '2d9a31f2b661':
        print(f'status={job[\"last_status\"]} error={job.get(\"last_error\",\"\")}')
"
# Expect: status=ok, error=(none)
```

**Stale error clearing:** After restart, old `last_error` from before the patch persists in `jobs.json`. It auto-clears on next successful tick. For cycles over 1h, manually patch:
```python
import json
j = json.load(open('~/.{{AGENT_NAME_LOWER}}/cron/jobs.json'))
for job in j['jobs']:
    if job['id'] in ('96ad18409db7',):  # target job ids that need clearing
        job['last_status'] = 'ok'
        job['last_error'] = None
json.dump(j, open('~/.{{AGENT_NAME_LOWER}}/cron/jobs.json', 'w'), indent=2)
```

## Script Location Double-Check

When diagnosing "Script not found" for no_agent jobs, always check BOTH locations:

| Location | Verified by | Scheduler context |
|----------|-------------|-------------------|
| `~/.{{AGENT_NAME_LOWER}}/scripts/<name>` | {{AGENT_NAME}} scheduler | `get_{{AGENT_NAME_LOWER}}_home() / "scripts"` |
| `~/.hermes/scripts/<name>` | Hermes scheduler | `get_hermes_home() / "scripts"` |

The {{AGENT_NAME}} customize layer redirects `HERMES_HOME` → `~/.{{AGENT_NAME_LOWER}}`, so the active scheduler reads from `~/.{{AGENT_NAME_LOWER}}/scripts/`. But the canonical origin of these scripts is `~/.hermes/scripts/` — they need to exist at both paths.

## How This Was Found

1. 3 no_agent jobs showed "Script not found" despite scripts existing at `~/.hermes/scripts/`
2. Inspected `_run_script_subprocess()` in {{AGENT_NAME}}'s `cron/scheduler.py` — relative paths not resolved to scripts_dir
3. Also found .sh files would be run with Python, not bash
4. Patched the function, but error persisted — discovered gateway restart is required
5. After restart, watchdog ran successfully

## Two jobs.json Files

There are TWO `jobs.json` files — don't confuse them:

| File | Purpose |
|------|---------|
| `~/.{{AGENT_NAME_LOWER}}/cron/jobs.json` | **Active** — the `cronjob` tool writes here, {{AGENT_NAME}} scheduler reads from here |
| `~/.{{AGENT_NAME_LOWER}}/P3-sensors/cron/jobs.json` | **Stale** — old copy from May 14, not actively used |

Always modify `~/.{{AGENT_NAME_LOWER}}/cron/jobs.json`. The `P3-sensors` copy can be ignored.
