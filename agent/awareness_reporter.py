"""
Brain Signal Awareness Reporter — agent/awareness_reporter.py

Posts-session 시그널을 분석해서 awareness_event를 생성하는 컴포넌트.
signal_processor가 disk에 쓴 brain_signal_log.jsonl을 읽고,
severity threshold之上的violation/dangerous op을 awareness channel로 전달한다.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class AwarenessReporter:
    """Reads brain_signal_log.jsonl and emits awareness events."""

    def __init__(
        self,
        log_path: str = "~/.drewgent/state/brain_signal_log.jsonl",
        severity_threshold: str = "medium",
    ):
        self.log_path = Path(log_path).expanduser()
        self.severity_threshold = severity_threshold
        self._severity_order = ["low", "medium", "high", "critical"]

    def _severity_score(self, severity: str) -> int:
        s = severity.lower().strip()
        if s not in self._severity_order:
            return self._severity_order.index("medium")
        return self._severity_order.index(s)

    def generate_awareness_report(
        self,
        since_hours: int = 24,
    ) -> dict:
        """Analyze brain signal log for the last N hours and generate a report."""
        if not self.log_path.exists():
            return {"status": "no_log", "message": f"Log file not found: {self.log_path}"}

        cutoff = datetime.now() - timedelta(hours=since_hours)
        threshold = self._severity_score(self.severity_threshold)

        violations: list[dict] = []
        dangerous_ops: list[dict] = []
        incomplete_workflows: list[dict] = []
        sessions_analyzed = 0

        try:
            with open(self.log_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    ts = record.get("timestamp", "")
                    try:
                        record_time = datetime.fromisoformat(ts)
                    except (ValueError, TypeError):
                        continue

                    if record_time < cutoff:
                        continue

                    sessions_analyzed += 1

                    # Violations above threshold
                    for v in record.get("violations", []):
                        severity_str = v.get("severity", "medium")
                        if self._severity_score(severity_str) >= threshold:
                            violations.append({**v, "session_id": record.get("session_id"), "timestamp": ts})

                    # Dangerous ops
                    dangerous_ops.extend([
                        {**op, "session_id": record.get("session_id"), "timestamp": ts}
                        for op in record.get("dangerous_ops", [])
                    ])

                    # Incomplete workflows
                    incomplete_workflows.extend([
                        {**wf, "session_id": record.get("session_id"), "timestamp": ts}
                        for wf in record.get("incomplete_workflows", [])
                    ])

        except Exception as e:
            logger.error("Failed to read brain_signal_log: %s", e)
            return {"status": "error", "message": str(e)}

        report = {
            "status": "ok",
            "sessions_analyzed": sessions_analyzed,
            "period_hours": since_hours,
            "violations_count": len(violations),
            "dangerous_ops_count": len(dangerous_ops),
            "incomplete_workflows_count": len(incomplete_workflows),
            "violations": violations,
            "dangerous_ops": dangerous_ops[:20],  # cap at 20 for display
            "incomplete_workflows": incomplete_workflows,
            "generated_at": datetime.now().isoformat(),
        }

        return report

    def format_slack_message(self, report: dict) -> str:
        """Format the awareness report as a Slack-friendly message."""
        if report["status"] != "ok":
            return f"⚠️ Brain Signal Report — {report.get('message', 'unknown error')}"

        lines = ["*Brain Signal Awareness Report*"]

        # Summary line
        summary = (
            f"Last {report['period_hours']}h | "
            f"{report['sessions_analyzed']} sessions | "
            f"⚡ {report['dangerous_ops_count']} dangerous ops | "
            f"🚨 {report['violations_count']} violations | "
            f"🔗 {report['incomplete_workflows_count']} incomplete workflows"
        )
        lines.append(summary)

        # Top violations
        if report["violations"]:
            lines.append("\n*Top Violations:*")
            for v in report["violations"][:5]:
                severity_icon = {
                    "critical": "🔴", "high": "🟠",
                    "medium": "🟡", "low": "⚪",
                }.get(v.get("severity", "medium"), "⚪")
                rule = v.get("rule", "unknown")
                detail = v.get("detail", "")[:80]
                ts = v.get("timestamp", "")[11:16]  # HH:MM only
                lines.append(f"  {severity_icon} [{ts}] {rule}: {detail}")

        # Dangerous ops summary
        if report["dangerous_ops"]:
            lines.append("\n*Dangerous Operations:*")
            seen = set()
            for op in report["dangerous_ops"][:5]:
                key = op.get("operation", "")
                if key not in seen:
                    seen.add(key)
                    lines.append(f"  ⚡ {key}")
            if len(report["dangerous_ops"]) > 5:
                lines.append(f"  ... and {len(report['dangerous_ops']) - 5} more")

        # Incomplete workflows
        if report["incomplete_workflows"]:
            lines.append("\n*Incomplete Workflows:*")
            for wf in report["incomplete_workflows"][:3]:
                lines.append(
                    f"  🔗 {wf.get('integration_type', 'unknown')}: "
                    f"{wf.get('target_name', 'unnamed')} — {wf.get('status', '?')}"
                )

        return "\n".join(lines)