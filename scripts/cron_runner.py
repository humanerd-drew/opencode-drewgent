#!/usr/bin/env python3
"""
Cron Runner — every 60s by launchd/drewgent-cron-runner-001.

Calls `hermes kanban dispatch` once per tick.  The old dispatch_once_*.py
scripts pointed at a stale legacy DB and are replaced by this single
Hermes-native dispatch command.

Why this exists (2026-06-01):
- ai.drewgent.cron-runner plist 부재 → 5/30 21:55부터 cron job들이 dormant.
- dispatcher는 결정론적 CLI 명령어라서 cron tick마다 안전하게 실행 가능.

Output: logs/cron-runner/YYYY-MM-DD.log
"""
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DREW_HOME = Path(os.environ.get("DREW_HOME", str(Path.home() / ".drewgent")))
LOG_DIR = DREW_HOME / "logs" / "cron-runner"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# The system hermes CLI (Drewgent wrapper at ~/.local/bin/hermes,
# which resolves to the Hermes-agent venv).
HERMES = os.environ.get("HERMES_BIN", "/Users/drew/.local/bin/hermes")

ts = datetime.now(timezone.utc).isoformat()
log_file = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.log"

results = []

# ── 1. Kanban dispatch ──────────────────────────────────────────────
# Replaces the 3 old dispatch_once_*.py scripts that pointed at a stale
# legacy DB (P2-hippocampus/kanban/state/).  Hermes native kanban at
# ~/.drewgent/kanban.db is the single source of truth.
try:
    r = subprocess.run(
        [HERMES, "kanban", "dispatch", "--json", "--max", "5"],
        capture_output=True,
        text=True,
        timeout=50,
        # Strip trailing colon from PYTHONPATH to prevent ~/.drewgent
        # leaking into sys.path and shadowing hermes-agent modules.
        env={**os.environ,
             "PYTHONPATH": "/Users/drew/.drewgent/customize",
             "HERMES_HOME": str(Path.home() / ".drewgent"),
             "HERMES_KANBAN_BOARD": "default"},
    )
    if r.returncode == 0 and r.stdout.strip():
        out = r.stdout.strip().splitlines()[-5:]
        results.append(f"[kanban] dispatch: exit={r.returncode} | {' '.join(out)}")
    else:
        summary = r.stdout.strip()[-200:] if r.stdout.strip() else "(no output)"
        err = r.stderr.strip()[-200:] if r.stderr.strip() else ""
        results.append(f"[kanban] dispatch: exit={r.returncode} | {summary}"
                       + (f" | err={err}" if err else ""))
except subprocess.TimeoutExpired:
    results.append("[kanban] dispatch: TIMEOUT (50s)")
except Exception as e:
    results.append(f"[kanban] dispatch: ERROR {type(e).__name__}: {e}")

# ── 2. Write daily log ──────────────────────────────────────────────
with open(log_file, "a") as f:
    f.write(f"\n=== {ts} ===\n")
    for r in results:
        f.write(f"  {r}\n")

# stdout: brief summary (launchd/stdout consumer sees this)
print(f"[{ts}] cron_runner: {len(results)} ops")
for r in results:
    print(f"  {r}")
