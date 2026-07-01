#!/usr/bin/env python3
"""Wrapper for content-graph-engine CLI. Called by cron. Builds graph and applies top links."""
import subprocess, sys

cli = [sys.executable, "-u", "/Users/drew/.drewgent/content-graph-engine/cli/main.py"]

r = subprocess.run([*cli, "build"], capture_output=True, text=True, timeout=120)
out = (r.stdout or "").strip()
err = (r.stderr or "").strip()
if out:
    print(out)
if err:
    print("STDERR:", err[:500], file=sys.stderr)

if r.returncode != 0:
    sys.exit(r.returncode)

r2 = subprocess.run([*cli, "apply", "--limit", "10"], capture_output=True, text=True, timeout=300)
out2 = (r2.stdout or "").strip()
err2 = (r2.stderr or "").strip()
if out2:
    print(out2)
if err2:
    print("STDERR:", err2[:500], file=sys.stderr)
sys.exit(r2.returncode)
