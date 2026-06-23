"""Brain Event Bus — signal-driven communication layer for Drewgent.

이벤트 버스는 module 간 loosely-coupled 통신을 위한 central hub이다.
"모든 것이 신호" architecture의 핵심이다.

Usage:
    from agent.event_bus import event_bus

    # Subscribe to events
    def on_tool_added(event):
        print(f"Tool added: {event.payload}")

    event_bus.subscribe("tool.integration.complete", on_tool_added)

    # Emit events
    event_bus.emit("tool.integration.complete", {
        "tool_name": "my_tool",
        "method": "registry.register"
    })
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from drewgent_constants import get_drewgent_home

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Event Dataclass
# ---------------------------------------------------------------------------

@dataclass
class BrainEvent:
    """A single signal/event in the brain event system."""

    event_type: str          # e.g., "tool.integration.complete"
    payload: Dict[str, Any]  # event data
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = ""         # which module emitted this
    correlation_id: str = ""  # for tracing related events

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "source": self.source,
            "correlation_id": self.correlation_id,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


# ---------------------------------------------------------------------------
# Event Bus
# ---------------------------------------------------------------------------

class EventBus:
    """Central event bus for brain signal-driven architecture.

    Thread-safe singleton event bus that handles:
    - Publishing (emit) signals
    - Subscribing (subscribe) to specific event types
    - Unsubscribing (unsubscribe) handlers
    - Synchronous dispatch to all subscribers
    """

    _instance: Optional["EventBus"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "EventBus":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # subscribers[event_type] = list of handler callbacks
        self._subscribers: Dict[str, List[Callable[[BrainEvent], None]]] = {}
        self._subscriber_lock = threading.RLock()

        # Event history for debugging and replay
        self._history: List[BrainEvent] = []
        self._history_max = 1000  # keep last 1000 events
        self._history_lock = threading.RLock()

        # Module identity
        self._module_name = "event_bus"

        logger.info("Brain EventBus initialized")

    # -------------------------------------------------------------------------
    # Publishing
    # -------------------------------------------------------------------------

    def emit(
        self,
        event_type: str,
        payload: Optional[Dict[str, Any]] = None,
        source: str = "",
        correlation_id: str = "",
    ) -> None:
        """Publish a signal/event to all subscribers.

        Args:
            event_type: Event identifier (e.g., "tool.integration.complete")
            payload: Event data dictionary
            source: Module that emitted this event
            correlation_id: Optional ID to group related events
        """
        if payload is None:
            payload = {}

        event = BrainEvent(
            event_type=event_type,
            payload=payload,
            source=source or self._module_name,
            correlation_id=correlation_id or self._generate_corr_id(),
        )

        # Store in history
        self._store_event(event)

        # Log the event
        logger.debug(
            f"[EventBus] emit: {event_type} (source={source}, corr_id={correlation_id})"
        )

        # Dispatch to subscribers synchronously
        self._dispatch(event)

    def _generate_corr_id(self) -> str:
        """Generate a unique correlation ID for event grouping."""
        import uuid
        return uuid.uuid4().hex[:12]

    def _store_event(self, event: BrainEvent) -> None:
        """Store event in history with size limit."""
        with self._history_lock:
            self._history.append(event)
            if len(self._history) > self._history_max:
                self._history = self._history[-self._history_max:]

    # -------------------------------------------------------------------------
    # Subscribing
    # -------------------------------------------------------------------------

    def subscribe(
        self,
        event_type: str,
        handler: Callable[[BrainEvent], None],
    ) -> None:
        """Subscribe a handler to a specific event type.

        Args:
            event_type: Event type to subscribe to (supports * wildcard)
            handler: Callback function that receives BrainEvent
        """
        with self._subscriber_lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []

            # Avoid duplicate handlers
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)
                logger.debug(f"[EventBus] subscribed: {event_type} -> {handler.__name__}")

    def unsubscribe(
        self,
        event_type: str,
        handler: Callable[[BrainEvent], None],
    ) -> None:
        """Unsubscribe a handler from an event type."""
        with self._subscriber_lock:
            if event_type in self._subscribers:
                try:
                    self._subscribers[event_type].remove(handler)
                    logger.debug(f"[EventBus] unsubscribed: {event_type} -> {handler.__name__}")
                except ValueError:
                    pass

    def unsubscribe_all(self, event_type: str) -> None:
        """Unsubscribe all handlers from an event type."""
        with self._subscriber_lock:
            if event_type in self._subscribers:
                self._subscribers[event_type].clear()
                logger.debug(f"[EventBus] unsubscribed all: {event_type}")

    # -------------------------------------------------------------------------
    # Dispatching
    # -------------------------------------------------------------------------

    def _dispatch(self, event: BrainEvent) -> None:
        """Dispatch event to all matching subscribers.

        Handles:
        - Exact match (e.g., "tool.integration.complete")
        - Wildcard match (e.g., "tool.*" matches "tool.integration.start")
        """
        with self._subscriber_lock:
            # Collect all handlers that should receive this event
            handlers: List[Callable[[BrainEvent], None]] = []

            # Exact match
            if event.event_type in self._subscribers:
                handlers.extend(self._subscribers[event.event_type])

            # Wildcard matching (e.g., "tool.*" matches "tool.integration.start")
            for pattern, pattern_handlers in self._subscribers.items():
                if "*" in pattern:
                    if self._match_wildcard(event.event_type, pattern):
                        for h in pattern_handlers:
                            if h not in handlers:
                                handlers.append(h)

        # Execute handlers outside the lock to avoid deadlocks
        errors = []
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.warning(
                    f"[EventBus] handler {handler.__name__} failed for {event.event_type}: {e}"
                )
                errors.append((handler.__name__, str(e)))

        if errors:
            event.payload["_dispatch_errors"] = errors

    def _match_wildcard(self, event_type: str, pattern: str) -> bool:
        """Match event type against wildcard pattern."""
        import fnmatch
        return fnmatch.fnmatch(event_type, pattern)

    # -------------------------------------------------------------------------
    # History & Debugging
    # -------------------------------------------------------------------------

    def get_history(
        self,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get recent events, optionally filtered by type."""
        with self._history_lock:
            events = list(reversed(self._history))

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        return [e.to_dict() for e in events[:limit]]

    def get_subscribers(self) -> Dict[str, int]:
        """Get count of subscribers per event type."""
        with self._subscriber_lock:
            return {et: len(handlers) for et, handlers in self._subscribers.items()}

    def clear_history(self) -> None:
        """Clear event history."""
        with self._history_lock:
            self._history.clear()
        logger.info("[EventBus] history cleared")

    # -------------------------------------------------------------------------
    # Persistence (optional - for event replay on restart)
    # -------------------------------------------------------------------------

    def persist_events(self, path: Optional[Path] = None) -> None:
        """Persist recent events to disk for event replay."""
        if path is None:
            path = Path(get_drewgent_home()) / "brain" / "event_history.jsonl"

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with self._history_lock:
                events = list(reversed(self._history))

            with open(path, "w", encoding="utf-8") as f:
                for event in events:
                    f.write(event.to_json() + "\n")

            logger.info(f"[EventBus] persisted {len(events)} events to {path}")
        except Exception as e:
            logger.warning(f"[EventBus] persist failed: {e}")


# ---------------------------------------------------------------------------
# Module-level convenience functions (use these instead of EventBus directly)
# ---------------------------------------------------------------------------

# Global singleton instance
_event_bus: Optional[EventBus] = None
_event_bus_lock = threading.Lock()


def get_event_bus() -> EventBus:
    """Get the global EventBus singleton."""
    global _event_bus
    if _event_bus is None:
        with _event_bus_lock:
            if _event_bus is None:
                _event_bus = EventBus()
    return _event_bus


def emit(
    event_type: str,
    payload: Optional[Dict[str, Any]] = None,
    source: str = "",
    correlation_id: str = "",
) -> None:
    """Convenience function to emit an event."""
    get_event_bus().emit(event_type, payload, source, correlation_id)


def subscribe(
    event_type: str,
    handler: Callable[[BrainEvent], None],
) -> None:
    """Convenience function to subscribe to an event type."""
    get_event_bus().subscribe(event_type, handler)


def unsubscribe(
    event_type: str,
    handler: Callable[[BrainEvent], None],
) -> None:
    """Convenience function to unsubscribe from an event type."""
    get_event_bus().unsubscribe(event_type, handler)