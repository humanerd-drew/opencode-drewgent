#!/usr/bin/env python3
"""Wrapper for SEO Article Harvester cron job — runs scripts directly, no AIAgent."""

import subprocess, json, os, sys
from pathlib import Path

HOME = Path(os.environ.get("DREW_HOME", str(Path.home() / ".drewgent")))
VENV_PYTHON = str(HOME / "venv" / "bin" / "python3")

def run(script: str, *args, timeout=120):
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

# Step 1: Harvester
try:
    r = run("skills/seo-article-harvester/scripts/harvester.py", timeout=300)
    report["harvester"] = "ok"
except Exception as e:
    report["harvester"] = f"fail: {e}"
    print(f"[SEO] Harvester failed: {e}")

# Step 2: Heritage labeling
try:
    r = run("skills/seo-article-harvester/scripts/label_heritage.py", "--limit", "0", timeout=120)
    report["labeling"] = "ok"
except Exception as e:
    report["labeling"] = f"fail: {e}"
    print(f"[SEO] Heritage labeling failed: {e}")

# Step 3: Summary from report
try:
    with open(HOME / "P2-hippocampus" / "knowledge" / "seo-articles" / "report.json") as f:
        data = json.load(f)
    total = data.get("total", 0)
    print(f"\n[SEO] Total articles: {total}")
except Exception as e:
    print(f"\n[SEO] Report read failed: {e}")

print(f"\n[SEO] Done — harvester={report.get('harvester','?')} labeling={report.get('labeling','?')}")
