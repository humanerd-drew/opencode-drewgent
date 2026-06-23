"""
Task Manager - Background task tracking for Gateway

Manages lifecycle of asyncio tasks created by the Gateway,
providing:
  - Automatic task tracking (add on create, remove on done)
  - Graceful shutdown (cancel all tasks)
  - BTW task management (special case for /btw command)
"""

import asyncio
import logging
from typing import Any, Callable, Coroutine, Dict, Optional

logger = logging.getLogger(__name__)


class TaskManager:
    """
    Centralized task management for Gateway background tasks.

    Automatically tracks tasks and provides cleanup on shutdown.

    Usage:
        task_manager = TaskManager(runner)

        # Create a tracked task
        task_manager.create_task(my_coro())

        # Create BTW task (special case)
        task_manager.create_btw_task(session_key, my_coro())

        # Cancel all tasks on shutdown
        await task_manager.cancel_all()
    """

    def __init__(self, runner: Any):
        """
        Initialize TaskManager.

        Args:
            runner: GatewayRunner instance (for accessing _running flag)
        """
        self._runner = runner
        # Set of all tracked background tasks
        self._background_tasks: set = set()
        # Dict of active /btw tasks: session_key -> task
        self._active_btw_tasks: Dict[str, asyncio.Task] = {}

    def create_task(self, coro: Coroutine) -> asyncio.Task:
        """
        Create an asyncio task and track it automatically.

        Task will be removed from tracking when done.

        Args:
            coro: Coroutine to run as a task

        Returns:
            The created asyncio.Task
        """
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return task

    def create_btw_task(
        self,
        session_key: str,
        coro: Coroutine,
    ) -> asyncio.Task:
        """
        Create a BTW (by-the-way) task and track it.

        BTW tasks are special because:
        - Only one per session_key
        - Need cleanup of _active_btw_tasks dict

        Args:
            session_key: Session identifier
            coro: Coroutine to run

        Returns:
            The created asyncio.Task
        """
        # Cancel existing BTW task for this session if any
        existing = self._active_btw_tasks.get(session_key)
        if existing and not existing.done():
            existing.cancel()

        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        self._active_btw_tasks[session_key] = task

        def cleanup(t: asyncio.Task) -> None:
            self._background_tasks.discard(t)
            if self._active_btw_tasks.get(session_key) is t:
                self._active_btw_tasks.pop(session_key, None)

        task.add_done_callback(cleanup)
        return task

    async def cancel_all(self) -> None:
        """
        Cancel all tracked tasks and wait for them to complete.

        Called during Gateway shutdown.
        """
        # Cancel all tracked tasks
        for task in list(self._background_tasks):
            if not task.done():
                task.cancel()

        # Wait for all tasks to acknowledge cancellation
        if self._background_tasks:
            await asyncio.gather(
                *self._background_tasks,
                return_exceptions=True,
            )

        self._background_tasks.clear()
        self._active_btw_tasks.clear()

    @property
    def background_tasks(self) -> set:
        """Return set of tracked background tasks (read-only view)."""
        return self._background_tasks.copy()

    @property
    def active_btw_tasks(self) -> Dict[str, asyncio.Task]:
        """Return dict of active BTW tasks (read-only view)."""
        return self._active_btw_tasks.copy()

    def get_btw_task(self, session_key: str) -> Optional[asyncio.Task]:
        """Get BTW task for a session, or None if not exists."""
        task = self._active_btw_tasks.get(session_key)
        if task and task.done():
            self._active_btw_tasks.pop(session_key, None)
            return None
        return task


__all__ = ["TaskManager"]
