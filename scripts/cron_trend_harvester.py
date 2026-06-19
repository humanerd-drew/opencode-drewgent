#!/usr/bin/env python3
"""Wrapper for Trend Harvester cron job — runs scripts directly, no AIAgent."""

import subprocess, json, os, sys
from pathlib import Path

HOME = Path(os.environ.get("DREW_HOME", str(Path.home() / ".drewgent")))
VENV_PYTHON = str(HOME / "source" / "drewgent-agent" / ".venv" / "bin" / "python3")

def run(script: str, *args, timeout=300):
    full = script if script.startswith("/") else str(HOME / script)
    result = subprocess.run(
        [VENV_PYTHON, full, *args],
        capture_output=True, text=True, timeout=timeout, cwd=str(HOME),
    )
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"Script exited {result.returncode}: {full}")
    return result

report = {}

# Step 1: Trend harvester
try:
    r = run("scripts/trend_harvester.py", timeout=600)
    report["harvester"] = "ok"
except Exception as e:
    report["harvester"] = f"fail: {e}"
    print(f"[Trend] Harvester failed: {e}")

# Step 2: Memory sync
try:
    r = run("scripts/harvester_memory_sync.py", timeout=120)
    report["memory_sync"] = "ok"
except Exception as e:
    report["memory_sync"] = f"fail: {e}"
    print(f"[Trend] Memory sync failed: {e}")

# Step 3: Summary from report
try:
    with open(HOME / "P4-cortex" / "growth" / "trend-harvester" / "report.json") as f:
        data = json.load(f)
    keep = data.get("keep", 0)
    review = data.get("review", 0)
    graveyard = data.get("graveyard", 0)
    print(f"\n[Trend] Results: keep={keep} review={review} graveyard={graveyard}")
except Exception as e:
    print(f"\n[Trend] Report read failed: {e}")

print(f"\n[Trend] Done — harvester={report.get('harvester','?')} sync={report.get('memory_sync','?')}")
