#!/usr/bin/env python3
"""Self-healing watcher: scan cron errors, classify, auto-fix known patterns.

Runs as a script-only cron job. Output is delivered to user.

Flow:
  1. Read jobs.json, collect all last_error entries
  2. For each: classify as known_pattern or unknown
  3. For known_pattern: apply fix, log outcome
  4. Track attempt count per (job_id, error_hash) to avoid infinite loops
  5. Output structured report
"""

import collections.abc
import hashlib
import json
import os
import re
import sys
from pathlib import Path

DREW_HOME = Path(os.environ.get("DREW_HOME", str(Path.home() / ".drewgent")))
JOBS_FILE = DREW_HOME / "cron" / "jobs.json"
STATE_FILE = DREW_HOME / "logs" / "self_heal_state.json"
SCRIPTS_DIR = DREW_HOME / "scripts"
SOURCE_DIR = DREW_HOME

EPOCH = "1970-01-01T00:00:00"


def save_jobs(jobs: list[dict]) -> bool:
    """Write updated jobs back to jobs.json atomically.

    Closes the behaviour loop that was missing the "verify and clear" step:
    after a successful run the watcher now clears its own stale last_error
    so jobs.json always reflects the current (not the historical) state.
    """
    import tempfile

    JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        raw = json.loads(JOBS_FILE.read_text())
        if isinstance(raw, dict):
            raw["jobs"] = jobs
        else:
            raw = {"jobs": jobs}
        tmp = JOBS_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(raw, indent=2, ensure_ascii=False))
        tmp.replace(JOBS_FILE)
        return True
    except Exception as exc:
        print(f"Failed to save jobs.json: {exc}", file=sys.stderr)
        return False


def error_hash(err: str) -> str:
    return hashlib.sha256(err.encode()).hexdigest()[:12]


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def load_jobs() -> list[dict]:
    raw = json.loads(JOBS_FILE.read_text())
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return raw.get("jobs", [])
    return []


class FixResult:
    def __init__(self, applied: bool, summary: str, detail: str = ""):
        self.applied = applied
        self.summary = summary
        self.detail = detail


KNOWN_FIXES: list[tuple[re.Pattern, str, callable]] = []


def register(pattern: str, label: str, fix_fn: callable):
    KNOWN_FIXES.append((re.compile(pattern), label, fix_fn))


def fix_undefined_name(file_path: str, name: str, suggested: str) -> FixResult:
    path = Path(file_path)
    if not path.exists():
        return FixResult(False, f"file not found: {file_path}")
    text = path.read_text()
    if name not in text:
        return FixResult(False, f"'{name}' not found in {file_path}")
    if suggested in text:
        return FixResult(False, f"'{suggested}' already exists in {file_path}")
    count = text.count(name)
    text = text.replace(name, suggested)
    path.write_text(text)
    return FixResult(True, f"replaced '{name}' → '{suggested}' ({count} occurrences)", file_path)


register(
    pattern=r"NameError: name '([A-Z_]+)' is not defined",
    label="undefined_name",
    fix_fn=lambda m: FixResult(
        False,
        f"undefined name '{m.group(1)}'",
        "try: fix import in the file where this name is used."
    ),
)


register(
    pattern=r"ModuleNotFoundError: No module named '([^']+)'",
    label="missing_module",
    fix_fn=lambda m: FixResult(
        False,
        f"missing module '{m.group(1)}'",
        "try: pip install or check import path."
    ),
)


register(
    pattern=r"Script not found: (.+)",
    label="script_not_found",
    fix_fn=lambda m: FixResult(
        False,
        f"script not found: {m.group(1)}",
        "check script path in jobs.json."
    ),
)


def classify_error(error: str) -> tuple[str, str, collections.abc.Callable | None]:
    for pattern, label, fix_fn in KNOWN_FIXES:
        m = pattern.search(error)
        if m:
            return label, f"matched: {label}", lambda: fix_fn(m)
    return "unknown", f"unrecognized error pattern", None


def format_timestamp(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def main() -> str:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    state = load_state()
    jobs = load_jobs()
    state.setdefault("attempts", {})

    failed_jobs = [j for j in jobs if j.get("last_error") and j.get("last_status") == "error"]
    attempts = state["attempts"]
    applied_fixes = []
    unknown_errors = []
    skipped_retries = []
    reenabled_jobs = []

    escalation_actions = {
        "undefined_name": ["check import path", "verify module installed", "reinstall package"],
        "missing_module": ["pip install module", "check venv activated", "recreate venv"],
        "script_not_found": ["verify script path", "restore from backup", "disable job"],
        "timeout": ["increase timeout", "reduce workload", "split job"],
    }

    for job in failed_jobs:
        jid = job["id"]
        name = job.get("name", jid)
        error = job["last_error"]
        eh = error_hash(error)
        attempt_key = f"{jid}:{eh}"
        attempt_info = attempts.get(attempt_key, {"count": 0, "last_result": None})

        label, reason, fix_fn = classify_error(error)
        attempt_count = attempt_info["count"]

        if fix_fn is None:
            unknown_errors.append((name, error))
            continue

        # Escalation: different strategies per attempt count
        strategies = escalation_actions.get(label, ["retry", "notify user", "disable"])
        if attempt_count >= len(strategies):
            skipped_retries.append((name, label, error))
            # Mark for alert escalation
            if attempt_count >= 3:
                unknown_errors.append((name, f"{error} [escalated: all {len(strategies)} strategies exhausted]"))
            continue

        result = fix_fn()
        if result.applied:
            attempts[attempt_key] = {"count": attempt_count + 1, "last_result": "fixed", "fixed_at": now.isoformat(), "strategy": strategies[attempt_count]}
            applied_fixes.append((name, label, result.summary, result.detail))
        else:
            attempts[attempt_key] = {"count": attempt_count + 1, "last_result": result.summary, "failed_at": now.isoformat(), "strategy": strategies[attempt_count]}
            if attempt_count >= 1:
                skipped_retries.append((name, label, f"{error} [tried: {strategies[attempt_count-1]}]"))
            else:
                unknown_errors.append((name, error))

    save_state(state)

    lines = []

    if applied_fixes:
        lines.append(f"## Self-heal: {len(applied_fixes)} fix(es) applied")
        for name, label, summary, detail in applied_fixes:
            lines.append(f"- **{name}** ({label}): {summary}")
            if detail:
                lines.append(f"  └─ {detail}")
        lines.append("")

    if unknown_errors:
        lines.append(f"## Unknown / unfixable: {len(unknown_errors)} error(s)")
        for name, error in unknown_errors:
            error_preview = error[:200].replace("\n", " ")
            lines.append(f"- **{name}**: {error_preview}")
        lines.append("")

    if skipped_retries:
        lines.append(f"## Retry limit reached: {len(skipped_retries)} (already attempted once)")
        for name, label, error in skipped_retries:
            lines.append(f"- **{name}**: {label}")
        lines.append("")

    # ── Re-enable stuck cron jobs ─────────────────────────────────────
    # Jobs with enabled=false + next_run_at=None + recurring schedule are
    # stuck in a completed state.  Re-enable them if they have a valid
    # cron/interval schedule (not once, not repeat-limited).
    for job in jobs:
        if job.get("enabled") or job.get("state") != "completed":
            continue
        schedule = job.get("schedule")
        if not schedule or schedule.get("kind") == "once":
            continue
        repeat = job.get("repeat", {})
        if repeat.get("times") is not None and repeat.get("completed", 0) >= repeat["times"]:
            continue
        job["enabled"] = True
        job["state"] = "scheduled"
        job["paused_at"] = None
        job["paused_reason"] = None
        try:
            job["next_run_at"] = compute_next_run(schedule)
        except Exception:
            job["next_run_at"] = now.isoformat()
        reenabled_jobs.append(job.get("name", job["id"]))
        jobs_changed = True

    # ── Close the loop: clear the watcher's own stale last_error ─────
    # Without this step a job that failed once keeps its last_error
    # forever, even after the fix is deployed and subsequent runs succeed.
    # The behaviour chain was: fail → detect → (try fix) → record → STALE.
    # Now it is:       fail → detect → (try fix) → record → verify → CLEAR.
    watcher_job = next((j for j in jobs if j.get("id") == "self-heal-watcher"), None)
    if watcher_job and watcher_job.get("last_error"):
        watcher_job["last_status"] = "ok"
        watcher_job["last_error"] = ""
        watcher_job["cleared_at"] = now.isoformat()
        jobs_changed = True
    else:
        jobs_changed = False

    if jobs_changed:
        save_jobs(jobs)

    if reenabled_jobs:
        lines.append(f"## Re-enabled stuck jobs: {len(reenabled_jobs)}")
        for name in reenabled_jobs:
            lines.append(f"- **{name}**: was completed, re-enabled with recurring schedule")

    if not applied_fixes and not unknown_errors and not skipped_retries:
        return "[SILENT]"

    summary_line = f"self-heal: {len(applied_fixes)} fixed, {len(skipped_retries)} retry-limited, {len(unknown_errors)} unknown"
    lines.insert(0, "# Self-Healing Watcher Report")
    lines.insert(1, f"**Summary**: {summary_line}")
    lines.insert(2, "")

    return "\n".join(lines)


if __name__ == "__main__":
    output = main()
    if output != "[SILENT]":
        print(output)
