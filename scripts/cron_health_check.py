#!/usr/bin/env python3
"""
cron_health_check.py — Health check for Drewgent cron jobs.
Reads ~/.drewgent/cron/jobs.json and reports issues.
Exit 0 = all healthy, 1 = issues found.
"""
import json
import datetime
import sys
import pathlib
import re

HOME = pathlib.Path.home()
JOBS_PATH = HOME / ".drewgent" / "cron" / "jobs.json"
NOW = datetime.datetime.now(datetime.timezone.utc)

FMT_DISCORD = (
    "---\n"
    "**Cron Health Check** — {ts}\n\n"
    "{summary}\n\n"
    "{details}"
)

FMT_DETAIL = "**{status_icon} {name}** ({id_short})\n{reason}"

def parse_iso(dt_str):
    if not dt_str:
        return None
    if dt_str.endswith("Z"):
        dt_str = dt_str[:-1] + "+00:00"
    try:
        return datetime.datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        return None

def estimate_interval_minutes(schedule):
    kind = schedule.get("kind")
    if kind == "interval":
        return schedule.get("minutes", 0)
    if kind == "cron":
        return cron_to_minutes(schedule.get("expr", ""))
    return None

def cron_to_minutes(expr):
    if not expr:
        return None
    parts = expr.strip().split()
    if len(parts) < 5:
        return None
    minute_field, hour_field, dom_field, month_field, dow_field = parts[:5]

    # Every minute.
    if minute_field == "*":
        return 1

    # Minute-level step, e.g. "*/5 * * * *".
    if minute_field.startswith("*/"):
        val = _parse_star(minute_field)
        if val:
            return val

    # Hourly patterns: "0 * * * *", "0 */6 * * *".
    if minute_field == "0":
        if hour_field == "*":
            return 60
        if hour_field.startswith("*/"):
            val = _parse_star(hour_field)
            if val:
                return val * 60

    # Fixed minute, hour wildcard: "5 * * * *" -> hourly.
    if hour_field == "*":
        return 60

    # Fixed hour: distinguish daily / weekly / monthly.
    if re.match(r"^\d+$", hour_field):
        if dow_field != "*":
            # Day-of-week specified, e.g. "0 10 * * 1" -> weekly.
            return 7 * 24 * 60
        if dom_field.startswith("*/"):
            val = _parse_star(dom_field)
            if val:
                return val * 24 * 60
        if dom_field != "*":
            # Day-of-month specified, e.g. "0 10 1 * *" -> monthly.
            return 30 * 24 * 60
        return 24 * 60

    return 24 * 60

def _parse_star(field):
    if field.startswith("*/"):
        parts = field[2:].split(",")
        try:
            return int(parts[0])
        except ValueError:
            return None
    return None

def _parse_int(field):
    try:
        return int(field)
    except (ValueError, TypeError):
        return None

def compute_stale_threshold(interval_minutes):
    if interval_minutes is None or interval_minutes == 0:
        return datetime.timedelta(days=7)
    return datetime.timedelta(minutes=interval_minutes * 2)

def check_job(job):
    name = job.get("name", "unnamed")
    id_short = job.get("id", "?")[:8]
    enabled = job.get("enabled", False)
    state = job.get("state", "")
    last_run_at = job.get("last_run_at")
    last_status = job.get("last_status")
    schedule = job.get("schedule", {})
    issues = []

    if not enabled:
        return None

    if enabled and state not in ("scheduled",):
        issues.append(("anomalous-state", f"enabled but state={state}"))

    if last_run_at is None:
        created_at = job.get("created_at")
        created_dt = parse_iso(created_at)
        if created_dt is None or (NOW - created_dt) >= datetime.timedelta(hours=2):
            issues.append(("never-run", "enabled but never ran"))
    else:
        last_dt = parse_iso(last_run_at)
        if last_dt:
            age = NOW - last_dt
            interval_min = estimate_interval_minutes(schedule)
            threshold = compute_stale_threshold(interval_min)
            if age > threshold:
                age_h = age.total_seconds() / 3600
                issues.append(("stale", f"last run {age_h:.1f}h ago (>{threshold.total_seconds()/3600:.1f}h threshold)"))

    if last_status == "error":
        last_error = job.get("last_error", "")
        issues.append(("erroring", f"last_status=error: {last_error[:200]}"))

    return {"name": name, "id": id_short, "issues": issues}

def build_report(results):
    all_issues = [r for r in results if r and r["issues"]]
    total = len([r for r in results if r is not None])
    healthy = total - len(all_issues)

    lines = []
    for r in all_issues:
        for kind, reason in r["issues"]:
            icon = {"never-run": ":new:", "stale": ":warning:", "erroring": ":no_entry:", "anomalous-state": ":question:"}.get(kind, ":grey_question:")
            lines.append(FMT_DETAIL.format(
                status_icon=icon, name=r["name"], id_short=r["id"],
                reason=reason
            ))

    details = "\n".join(lines) if lines else "All jobs healthy."
    summary = f"{healthy}/{total} healthy"

    return FMT_DISCORD.format(
        ts=NOW.strftime("%Y-%m-%d %H:%M UTC"),
        summary=f"{healthy}/{total} healthy",
        details=details
    )

def main():
    if not JOBS_PATH.exists():
        print(f"Jobs file not found: {JOBS_PATH}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(JOBS_PATH) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in {JOBS_PATH}: {e}", file=sys.stderr)
        sys.exit(1)

    jobs = data.get("jobs", [])
    results = [check_job(j) for j in jobs]
    issues = [r for r in results if r and r["issues"]]

    report = build_report(results)
    print(report)
    print(f"\n---\nTotal enabled: {len([r for r in results if r])} | Issues: {len(issues)}")

    sys.exit(1 if issues else 0)

if __name__ == "__main__":
    main()
