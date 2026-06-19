#!/usr/bin/env python3
"""
brain_signal_report.py — Daily brain signal analysis report

Reads ~/.drewgent/state/brain_signal_log.jsonl and prints a formatted
awareness report to stdout. Designed to run as a cron job or on-demand.

Usage:
    python3 brain_signal_report.py                # last 24h, summary
    python3 brain_signal_report.py --hours 168     # last week
    python3 brain_signal_report.py --format json   # raw JSON output
    python3 brain_signal_report.py --format slack  # Slack block format
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add drewgent source to path for imports
SOURCE_PATH = Path.home() / ".drewgent" / "source" / "drewgent-agent"
if SOURCE_PATH.exists():
    sys.path.insert(0, str(SOURCE_PATH))

from agent.awareness_reporter import AwarenessReporter


def main():
    parser = argparse.ArgumentParser(description="Brain Signal Awareness Report")
    parser.add_argument("--hours", type=int, default=24, help="Hours to look back (default: 24)")
    parser.add_argument(
        "--log-path",
        default="~/.drewgent/state/brain_signal_log.jsonl",
        help="Path to brain_signal_log.jsonl",
    )
    parser.add_argument(
        "--severity",
        default="medium",
        choices=["low", "medium", "high", "critical"],
        help="Minimum severity to report",
    )
    parser.add_argument(
        "--format",
        default="text",
        choices=["text", "json", "slack"],
        help="Output format",
    )
    args = parser.parse_args()

    reporter = AwarenessReporter(
        log_path=args.log_path,
        severity_threshold=args.severity,
    )

    report = reporter.generate_awareness_report(since_hours=args.hours)

    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return

    if args.format == "slack":
        print(reporter.format_slack_message(report))
        return

    # Text format
    print(f"=== Brain Signal Awareness Report ===")
    print(f"Generated: {report.get('generated_at', 'N/A')}")
    print(f"Period: last {report.get('period_hours', args.hours)} hours")
    print(f"Sessions analyzed: {report.get('sessions_analyzed', 0)}")
    print()

    if report["status"] != "ok":
        print(f"⚠️  {report.get('message', 'unknown error')}")
        return

    print(f"📊 Summary")
    print(f"  Dangerous operations: {report['dangerous_ops_count']}")
    print(f"  Rule violations:      {report['violations_count']}")
    print(f"  Incomplete workflows: {report['incomplete_workflows_count']}")
    print()

    if report["violations"]:
        print(f"🚨 Rule Violations (top {min(10, len(report['violations']))}):")
        for v in report["violations"][:10]:
            sev = v.get("severity", "?").upper()
            rule = v.get("rule", "unknown")
            detail = (v.get("detail") or "")[:100]
            ts = (v.get("timestamp") or "")[11:16]
            print(f"  [{sev:8}] [{ts}] {rule}")
            if detail:
                print(f"            {detail}")
        print()

    if report["dangerous_ops"]:
        print(f"⚡ Dangerous Operations ({len(report['dangerous_ops'])} total):")
        seen = {}
        for op in report["dangerous_ops"]:
            key = op.get("operation", "unknown")
            if key not in seen:
                seen[key] = 0
            seen[key] += 1
        for op, count in sorted(seen.items(), key=lambda x: -x[1])[:10]:
            print(f"  {count:3}x  {op}")
        print()

    if report["incomplete_workflows"]:
        print(f"🔗 Incomplete Workflows:")
        for wf in report["incomplete_workflows"]:
            print(f"  {wf.get('integration_type', 'unknown')}: {wf.get('target_name', '?')} — {wf.get('status', '?')}")
        print()


if __name__ == "__main__":
    main()