#!/usr/bin/env python3
"""System health metric: H = w1*cron_ok + w2*memory_ok + w3*knowledge_ok + w4*credential_ok.

Runs every 30 minutes as a cron job. If H < threshold, reports to user.
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DREW_HOME = Path(os.environ.get("DREW_HOME", str(Path.home() / ".drewgent")))
JOBS_FILE = DREW_HOME / "cron" / "jobs.json"
KNOWLEDGE_DB = DREW_HOME / ".agent" / "memory" / "knowledge.db"
CREDENTIAL_STATE = DREW_HOME / ".agent" / "memory" / "credential_state.json"


def check_cron() -> tuple[float, str]:
    jobs = json.loads(JOBS_FILE.read_text()).get("jobs", [])
    total = len(jobs)
    errors = sum(1 for j in jobs if j.get("last_status") == "error" and j.get("enabled"))
    never_ran = sum(1 for j in jobs if j.get("last_status") is None and j.get("enabled"))
    ok = total - errors - never_ran
    score = ok / max(total, 1)
    detail = f"{ok}/{total} ok, {errors} errors, {never_ran} never ran"
    return score, detail


def check_knowledge() -> tuple[float, str]:
    if not KNOWLEDGE_DB.exists():
        return 0.0, "knowledge.db does not exist"
    try:
        db = sqlite3.connect(str(KNOWLEDGE_DB))
        count = db.execute("SELECT COUNT(*) FROM memory_fts").fetchone()[0]
        db.close()
        if count >= 30:
            return 1.0, f"{count} entries"
        elif count >= 10:
            return 0.5, f"{count} entries (low)"
        else:
            return 0.2, f"{count} entries (critical)"
    except Exception as e:
        return 0.0, f"error: {e}"


def check_credential() -> tuple[float, str]:
    if not CREDENTIAL_STATE.exists():
        return 0.8, "no failures recorded (good)"
    try:
        reg = json.loads(CREDENTIAL_STATE.read_text())
        entries = reg.get("entries", {})
        if not entries:
            return 1.0, "all credentials healthy"
        failing = sum(1 for e in entries.values() if e.get("mode") not in ("rate_limited",))
        if failing == 0:
            return 1.0, "only transient failures"
        return max(0.0, 1.0 - failing * 0.3), f"{failing} credential(s) with persistent failures"
    except Exception:
        return 0.5, "could not read state"


def check_gateway() -> tuple[float, str]:
    import subprocess
    try:
        r = subprocess.run(["pgrep", "-f", "drewgent.*gateway"], capture_output=True, timeout=5)
        pids = [p for p in r.stdout.decode().strip().split("\n") if p]
        if pids:
            return 1.0, f"running (PID {pids[0]})"
        return 0.0, "not running"
    except Exception:
        return 0.0, "could not check"


def main() -> str:
    checks = {
        "cron": (0.30, check_cron()),
        "knowledge": (0.25, check_knowledge()),
        "credential": (0.20, check_credential()),
        "gateway": (0.25, check_gateway()),
    }
    H = sum(w * score for w, (score, _) in checks.values())

    now = datetime.now(timezone.utc)

    # Persist to state file for trend tracking
    state_path = DREW_HOME / ".agent" / "memory" / "health_history.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    history = {"checks": {}}
    if state_path.exists():
        try:
            history = json.loads(state_path.read_text())
        except Exception:
            pass
    history.setdefault("checks", {})
    for name, (_, (score, detail)) in checks.items():
        history["checks"][f"{now.isoformat()}:{name}"] = {"score": score, "detail": detail}
    # Keep only last 100 entries
    while len(history["checks"]) > 100:
        oldest = min(history["checks"].keys())
        del history["checks"][oldest]
    history["latest"] = {"H": round(H, 3), "at": now.isoformat()}
    state_path.write_text(json.dumps(history, indent=2))

    if H >= 0.8:
        return "[SILENT]"

    lines = ["# System Health Report"]
    lines.append(f"**Health score H={H:.2f}** (threshold=0.8)\n")
    for name, (weight, (score, detail)) in sorted(checks.items()):
        icon = "✅" if score >= 0.8 else "⚠️" if score >= 0.4 else "❌"
        lines.append(f"- {icon} **{name}**: score={score:.2f} (weight={weight}) — {detail}")
    lines.append("")
    lines.append(f"Run at: {now.isoformat()}")

    if H < 0.4:
        lines.append("")
        lines.append("**Action required**: Multiple subsystems degraded.")

    return "\n".join(lines)


if __name__ == "__main__":
    output = main()
    if output != "[SILENT]":
        print(output)
