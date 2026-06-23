"""Brain Signal Monitor — tracks and reports data-flow through the brain pipeline.

Subscribes to all brain events and formats them as structured monitoring reports
delivered to configured channels (e.g., "status-monitoring").

Usage:
    monitor = BrainSignalMonitor(session_id="abc123")
    monitor.start()  # begin subscribing
    monitor.stop()   # unsubscribe and flush
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------
# Event categories and formatting
# -----------------------------------------------------------------------

# Which events to monitor and how to format them
_MONITORED_EVENTS = [
    # Integration lifecycle
    "tool.integration.start",
    "skill.integration.start",
    "gateway_platform.integration.start",
    "tool.integration.detected",
    "skill.integration.detected",
    "tool.integration.complete",
    "skill.integration.complete",
    # Workflow progress
    "brain.awareness.integration_progress",
    "brain.awareness.integration_started",
    "brain.awareness.integration_complete",
    "brain.awareness.guidance_requested",
    # Agent activity
    "user.prompt",
    "agent.exploring",
    "agent.modifying",
    "tool.start",
    "tool.complete",
    "session.end",
    # Awareness
    "brain.report.hint",
    "brain.awareness.initialized",
]

# Emojis per event type for quick visual scanning
_EVENT_EMOJI = {
    "tool.integration.start":        "🛠️",
    "skill.integration.start":        "⚙️",
    "gateway_platform.integration.start": "🌐",
    "tool.integration.detected":     "📝",
    "skill.integration.detected":    "📝",
    "tool.integration.complete":     "✅",
    "skill.integration.complete":     "✅",
    "brain.awareness.integration_progress": "📊",
    "brain.awareness.integration_started":  "🚀",
    "brain.awareness.integration_complete": "🏁",
    "brain.awareness.guidance_requested":  "❓",
    "user.prompt":                   "💬",
    "agent.exploring":               "🔍",
    "agent.modifying":               "✏️",
    "tool.start":                    "▶️",
    "tool.complete":                 "⏹️",
    "session.end":                   "🔚",
    "brain.report.hint":             "💡",
    "brain.awareness.initialized":   "🧠",
}


@dataclass
class MonitorEntry:
    """A single monitoring log entry."""
    timestamp: str
    event: str
    emoji: str
    summary: str
    payload: Dict[str, Any]
    correlation_id: str = ""

    def to_text(self) -> str:
        """One-line summary for terminal/logging."""
        return f"{self.emoji} [{self.timestamp}] {self.event}: {self.summary}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "event": self.event,
            "emoji": self.emoji,
            "summary": self.summary,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
        }


class BrainSignalMonitor:
    """Subscribes to brain event bus and formats entries for delivery.

    Thread-safe. Can be started/stopped multiple times.
    Buffer is flushed on stop or when max_size is reached.
    """

    def __init__(
        self,
        session_id: str = "",
        delivery_target: str = "local",
        buffer_size: int = 50,
        flush_interval: float = 10.0,
    ):
        """
        Args:
            session_id: Session identifier for correlation
            delivery_target: Delivery target string e.g. "local", "status-monitoring"
            buffer_size: Flush after this many entries (0 = never auto-flush)
            flush_interval: Flush every N seconds regardless of buffer size
        """
        self.session_id = session_id
        self.delivery_target = delivery_target
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval

        self._entries: List[MonitorEntry] = []
        self._lock = threading.Lock()
        self._running = False
        self._handler_ref: Optional[callable] = None
        self._last_flush = time.monotonic()
        self._flush_timer: Optional[threading.Timer] = None

    # ── Public API ────────────────────────────────────────────────────

    def start(self) -> None:
        """Subscribe to the event bus and start periodic flushing."""
        if self._running:
            return

        from agent.event_bus import get_event_bus

        bus = get_event_bus()
        handler = self._make_handler()

        for event_type in _MONITORED_EVENTS:
            bus.subscribe(event_type, handler)

        self._handler_ref = handler
        self._running = True
        self._last_flush = time.monotonic()
        self._schedule_flush()
        logger.info("BrainSignalMonitor started (session=%s, target=%s)", self.session_id, self.delivery_target)

    def stop(self) -> None:
        """Unsubscribe and flush remaining entries."""
        if not self._running:
            return

        self._running = False

        if self._flush_timer:
            self._flush_timer.cancel()
            self._flush_timer = None

        if self._handler_ref:
            from agent.event_bus import get_event_bus
            bus = get_event_bus()
            for event_type in _MONITORED_EVENTS:
                try:
                    bus.unsubscribe(event_type, self._handler_ref)
                except Exception:
                    pass
            self._handler_ref = None

        self._flush()
        logger.info("BrainSignalMonitor stopped (%d entries flushed)", len(self._entries))

    def get_entries(self) -> List[Dict[str, Any]]:
        """Return all buffered entries as dicts (for debugging)."""
        with self._lock:
            return [e.to_dict() for e in self._entries]

    # ── Internal ──────────────────────────────────────────────────────

    def _make_handler(self):
        """Create a handler closure that references self safely."""
        monitor = self

        def handler(event):
            monitor._on_event(event)

        return handler

    def _on_event(self, event) -> None:
        """Process a brain event, buffer it, flush if needed."""
        try:
            entry = self._format_entry(event)
        except Exception as e:
            logger.warning("BrainSignalMonitor: failed to format event %s: %s", getattr(event, "event_type", "?"), e)
            return

        with self._lock:
            self._entries.append(entry)
            entry_count = len(self._entries)

        # Check flush conditions (outside lock to avoid deadlock)
        should_flush = (
            (self.buffer_size > 0 and entry_count >= self.buffer_size)
            or (time.monotonic() - self._last_flush >= self.flush_interval)
        )

        if should_flush:
            self._flush()

    def _format_entry(self, event) -> MonitorEntry:
        """Convert a BrainEvent to a MonitorEntry with human-readable summary."""
        event_type = getattr(event, "event_type", "?")
        payload = getattr(event, "payload", {}) or {}
        correlation_id = getattr(event, "correlation_id", "") or ""

        emoji = _EVENT_EMOJI.get(event_type, "📌")
        summary = self._summarize(event_type, payload)
        ts = datetime.now().strftime("%H:%M:%S")

        return MonitorEntry(
            timestamp=ts,
            event=event_type,
            emoji=emoji,
            summary=summary,
            payload=payload,
            correlation_id=correlation_id,
        )

    def _summarize(self, event_type: str, payload: Dict[str, Any]) -> str:
        """Human-readable one-line summary of an event payload."""
        if event_type == "user.prompt":
            msg = payload.get("message", "")
            return msg[:60] + ("..." if len(msg) > 60 else "")

        if event_type == "tool.start":
            return payload.get("tool", "?")

        if event_type == "tool.complete":
            tool = payload.get("tool", "?")
            success = payload.get("success", True)
            return f"{tool} → {'OK' if success else 'FAIL'}"

        if event_type == "agent.modifying":
            op = payload.get("operation", "?")
            path = payload.get("path", "")
            filename = path.split("/")[-1] if path else "?"
            return f"{op} {filename}"

        if event_type == "brain.awareness.integration_progress":
            int_type = payload.get("integration_type", "?")
            progress = payload.get("progress", {})
            step = progress.get("step_name", "?")
            complete = progress.get("is_complete", False)
            files = payload.get("files_modified", [])
            file_count = len(files)
            status = "✓" if complete else "○"
            return f"{status} [{int_type}] step={step} files={file_count}"

        if event_type == "brain.awareness.integration_started":
            int_type = payload.get("integration_type", "?")
            target = payload.get("target_name", "")
            return f"[{int_type}] {target}"

        if event_type == "brain.awareness.integration_complete":
            int_type = payload.get("integration_type", "?")
            target = payload.get("target_name", "")
            return f"✓ [{int_type}] {target} complete"

        if event_type == "brain.awareness.guidance_requested":
            msg = payload.get("message", "")
            return msg[:50] + ("..." if len(msg) > 50 else "")

        if event_type == "brain.report.hint":
            hint = payload.get("hint", "") or payload.get("message", "")
            return hint[:60] + ("..." if len(hint) > 60 else "")

        if event_type == "brain.awareness.initialized":
            tool_count = payload.get("tool_count", 0)
            return f"tools={tool_count}"

        if event_type == "session.end":
            return payload.get("summary", "")

        # Fallback: print first few payload fields
        items = ", ".join(f"{k}={str(v)[:20]}" for k, v in list(payload.items())[:3])
        return items if items else "..."

    def _schedule_flush(self) -> None:
        """Schedule the next periodic flush."""
        if not self._running:
            return
        self._flush_timer = threading.Timer(self.flush_interval, self._do_flush_scheduled)
        self._flush_timer.daemon = True
        self._flush_timer.start()

    def _do_flush_scheduled(self) -> None:
        """Periodic flush callback (runs in timer thread)."""
        if self._running:
            self._flush()
            self._schedule_flush()

    def _flush(self) -> None:
        """Write buffered entries to delivery target."""
        with self._lock:
            if not self._entries:
                return
            entries_copy = self._entries
            self._entries = []

        self._last_flush = time.monotonic()

        try:
            self._deliver(entries_copy)
        except Exception as e:
            logger.error("BrainSignalMonitor: delivery failed: %s", e)

    def _is_cron_noise(self, entries: List[MonitorEntry]) -> bool:
        """Check if all entries are cron initialization noise — skip writing."""
        if not self.session_id or not self.session_id.startswith("cron_"):
            return False
        return all(e.event == "brain.awareness.initialized" for e in entries)

    def _deliver(self, entries: List[MonitorEntry]) -> None:
        """Send formatted entries to delivery target."""
        # Skip cron-only initialization noise
        if self._is_cron_noise(entries):
            logger.debug("Skipping cron noise (%d entries)", len(entries))
            return

        # Build the report
        lines = [
            f"## 🧠 Brain Signal Monitor — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Session: `{self.session_id or 'unknown'}` | Entries: {len(entries)}",
            ""
        ]

        for entry in entries:
            lines.append(f"{entry.emoji} `{entry.timestamp}` **{entry.event}**")
            lines.append(f"   → {entry.summary}")

        content = "\n".join(lines)

        # Deliver via DeliveryRouter (same system as cron jobs)
        try:
            from gateway.delivery import DeliveryRouter

            config = self._get_gateway_config()
            router = DeliveryRouter(config)

            targets = router.resolve_targets(self.delivery_target, origin=None)

            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                results = loop.run_until_complete(
                    router.deliver(content, targets, metadata={"monitor": "brain-signals"})
                )
            finally:
                loop.close()

            delivered = sum(1 for r in results.values() if r.get("success"))
            logger.debug("BrainSignalMonitor delivered %d/%d entries", delivered, len(results))

        except Exception as e:
            logger.debug("DeliveryRouter unavailable, appending to local log: %s", e)
            self._deliver_fallback(entries)

    def _deliver_fallback(self, entries: List[MonitorEntry]) -> None:
        """Append entries as JSONL to a single log file instead of creating individual files."""
        from drewgent_constants import get_drewgent_home
        monitor_dir = get_drewgent_home() / "monitor"
        monitor_dir.mkdir(parents=True, exist_ok=True)
        path = monitor_dir / "brain_signal_log.jsonl"

        import json as _json
        batch = []
        for entry in entries:
            batch.append(_json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")

        with open(path, "a", encoding="utf-8") as f:
            f.writelines(batch)

        logger.info("BrainSignalMonitor appended %d entries to %s", len(entries), path)

    def _get_gateway_config(self):
        """Load gateway config for DeliveryRouter."""
        try:
            from drewgent_cli.config import load_config
            cfg = load_config()
            gw = cfg.get("gateway", {})
            class _ConfigProxy:
                @property
                def always_log_local(self):
                    return gw.get("always_log_local", True)
                def get_home_channel(self, platform):
                    return None
            return _ConfigProxy()
        except Exception:
            # Minimal config fallback
            class _MinimalConfig:
                def get_home_channel(self, platform): return None
                @property
                def always_log_local(self): return True
            return _MinimalConfig()


# -----------------------------------------------------------------------
# Global monitor registry (one per session)
# -----------------------------------------------------------------------

_monitors: Dict[str, BrainSignalMonitor] = {}
_monitors_lock = threading.Lock()


def get_monitor(session_id: str, **kwargs) -> BrainSignalMonitor:
    """Get or create a monitor for a session."""
    with _monitors_lock:
        if session_id not in _monitors:
            _monitors[session_id] = BrainSignalMonitor(
                session_id=session_id,
                **kwargs
            )
        return _monitors[session_id]


def stop_monitor(session_id: str) -> None:
    """Stop and remove a session's monitor."""
    with _monitors_lock:
        if session_id in _monitors:
            _monitors[session_id].stop()
            del _monitors[session_id]