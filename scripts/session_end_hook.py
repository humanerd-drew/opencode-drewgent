#!/usr/bin/env python3
"""
Drewgent Session End Hook
- Checks if session_checkpoint.json was modified more than 5 minutes ago
- If session end detected → runs brain_nodes.py dashboard
- Saves output to ~/.drewgent/logs/brain_YYYYMMDD_HHMMSS.log
- Updates .last_hook_run timestamp
"""

import os, sys, json, subprocess, time
from pathlib import Path
from datetime import datetime

DREW_DIR      = Path.home() / ".drewgent"
CHECKPOINT    = DREW_DIR / "session_checkpoint.json"
LAST_HOOK     = DREW_DIR / ".last_hook_run"
LOGS_DIR      = DREW_DIR / "logs"
BRAIN_SCRIPT  = DREW_DIR / "scripts" / "brain_nodes.py"

IDLE_THRESHOLD = 5 * 60  # 5 minutes in seconds

def now_ts():
    return time.time()

def read_last_hook():
    if LAST_HOOK.exists():
        try:
            return float(LAST_HOOK.read_text().strip())
        except (ValueError, OSError):
            pass
    return 0.0

def write_last_hook(ts):
    LAST_HOOK.write_text(str(ts))

def checkpoint_mtime():
    if CHECKPOINT.exists():
        return CHECKPOINT.stat().st_mtime
    return 0.0

def session_completed(checkpoint_data):
    """Return True if any session has status COMPLETED."""
    for entry in checkpoint_data.values():
        if isinstance(entry, dict) and entry.get("status") == "COMPLETED":
            return True
    return False

def run():
    last_run  = read_last_hook()
    cp_mtime  = checkpoint_mtime()
    current   = now_ts()

    # Nothing to do if checkpoint is newer than last run
    # (i.e. an active session modified it recently)
    if cp_mtime > last_run:
        return  # No session end to process

    # Check if enough idle time has passed since last checkpoint modification
    idle = current - cp_mtime
    if idle < IDLE_THRESHOLD:
        return  # Still within idle threshold

    # Load checkpoint to confirm there are completed sessions
    if not CHECKPOINT.exists():
        return

    try:
        data = json.loads(CHECKPOINT.read_text())
    except (json.JSONDecodeError, OSError):
        return

    if not session_completed(data):
        return

    # ── Session end detected ────────────────────────────────
    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOGS_DIR / f"brain_{ts_str}.log"

    # Run brain_nodes.py and capture output
    result = subprocess.run(
        [sys.executable, str(BRAIN_SCRIPT)],
        capture_output=True,
        text=True,
        timeout=30,
    )

    output = result.stdout + result.stderr

    # Save log
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path.write_text(output)

    # Update last hook run timestamp
    write_last_hook(current)

    # Print to stdout (captured by cron/notification system)
    print(output)
    print(f"\n[SESSION END HOOK] Dashboard saved to {log_path}")

if __name__ == "__main__":
    run()
