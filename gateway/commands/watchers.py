"""
Gateway Watchers - Background monitoring tasks

Extracted from gateway/run.py for maintainability.

This module contains background watcher tasks that monitor various aspects
of the gateway lifecycle.

Watchers:
    - SessionExpiryWatcher: Monitors session expiration
    - PlatformReconnectWatcher: Handles platform reconnection
    - PendingWatcherDrain: Drains pending background task watchers
    - ProcessWatcher: Monitors background process output
"""

from typing import Any, Dict, Optional, TYPE_CHECKING
import asyncio

if TYPE_CHECKING:
    from gateway.run import GatewayRunner


class SessionExpiryWatcher:
    """Monitor session expiration and handle cleanup.

    Periodically checks for expired sessions and:
    - Flushes memories
    - Cleans up checkpoint files
    - Emits session:expired hooks
    """

    @staticmethod
    async def run(runner: "GatewayRunner", interval: int = 300) -> None:
        """Run the session expiry watcher.

        Args:
            runner: GatewayRunner instance
            interval: Check interval in seconds (default 5 minutes)
        """
        await runner._session_expiry_watcher(interval)


class PlatformReconnectWatcher:
    """Monitor platform connections and handle reconnection.

    Periodically checks for failed platforms and attempts reconnection.
    """

    @staticmethod
    async def run(runner: "GatewayRunner", interval: int = 60) -> None:
        """Run the platform reconnect watcher.

        Args:
            runner: GatewayRunner instance
            interval: Check interval in seconds (default 1 minute)
        """
        await runner._platform_reconnect_watcher(interval)


class PendingWatcherDrain:
    """Drain pending watchers from process registry.

    Picks up new watchers registered by terminal(background=True) and
    starts process watcher tasks for them.
    """

    @staticmethod
    async def run(runner: "GatewayRunner", interval: int = 30) -> None:
        """Run the pending watcher drain.

        Args:
            runner: GatewayRunner instance
            interval: Check interval in seconds (default 30 seconds)
        """
        await runner._pending_watcher_drain(interval)


class ProcessWatcher:
    """Monitor background process output.

    Periodically checks a background process and pushes updates to the user.
    Supports notification modes: all, result, error, off.
    """

    @staticmethod
    async def run(runner: "GatewayRunner", watcher: Dict[str, Any]) -> None:
        """Run a process watcher.

        Args:
            runner: GatewayRunner instance
            watcher: Watcher configuration dict with keys:
                - session_id: Session identifier
                - check_interval: Polling interval
                - session_key: Gateway session key
                - platform: Platform name
                - chat_id: Chat identifier
                - thread_id: Thread identifier (optional)
                - notify_on_complete: Whether to notify on completion
        """
        await runner._run_process_watcher(watcher)


__all__ = [
    "SessionExpiryWatcher",
    "PlatformReconnectWatcher",
    "PendingWatcherDrain",
    "ProcessWatcher",
]
