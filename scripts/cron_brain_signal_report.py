#!/usr/bin/env python3
"""Wrapper for brain-signal-report cron job — runs the report script directly."""

import subprocess, sys, os
from pathlib import Path

HOME = Path(os.environ.get("DREW_HOME", str(Path.home() / ".drewgent")))
VENV_PYTHON = str(HOME / "source" / "drewgent-agent" / ".venv" / "bin" / "python3")

script = str(HOME / "scripts" / "brain_signal_report.py")
result = subprocess.run(
    [VENV_PYTHON, script, "--hours", "24", "--severity", "medium"],
    capture_output=True, text=True, timeout=60, cwd=str(HOME),
)
if result.stdout:
    print(result.stdout.rstrip())
if result.stderr:
    print(result.stderr.rstrip(), file=sys.stderr)
if result.returncode != 0:
    print(f"[brain-signal] Script exited {result.returncode}")
else:
    print(f"[brain-signal] Report complete")
