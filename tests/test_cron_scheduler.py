"""
Tests for CronScheduler - background job scheduling.

These tests verify that CronScheduler correctly manages cron
ticker, pending watchers, and cache cleanup.
"""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch


class TestCronSchedulerCreation(unittest.TestCase):
    """Test CronScheduler instantiation."""

    def test_cron_scheduler_creatable(self):
        from gateway.cron_scheduler import CronScheduler

        scheduler = CronScheduler(
            running_ref=MagicMock(return_value=True),
            create_watcher_task_fn=MagicMock(),
        )
        self.assertIsNotNone(scheduler)
        self.assertEqual(len(scheduler.watcher_tasks), 0)


class TestCronStartStop(unittest.TestCase):
    """Test cron ticker start/stop."""

    def test_start_cron_creates_thread(self):
        from gateway.cron_scheduler import CronScheduler

        scheduler = CronScheduler(
            running_ref=MagicMock(return_value=True),
            create_watcher_task_fn=MagicMock(),
        )

        with patch.object(scheduler, "_cron_ticker_loop"):
            scheduler.start_cron()

            self.assertIsNotNone(scheduler._cron_thread)
            self.assertIsNotNone(scheduler._cron_stop_event)

    def test_stop_cron_sets_event(self):
        from gateway.cron_scheduler import CronScheduler

        scheduler = CronScheduler(
            running_ref=MagicMock(return_value=True),
            create_watcher_task_fn=MagicMock(),
        )

        stop_event_mock = MagicMock()
        scheduler._cron_stop_event = stop_event_mock
        scheduler._cron_thread = MagicMock()

        scheduler.stop_cron()

        stop_event_mock.set.assert_called_once()


class TestWatcherTaskManagement(unittest.TestCase):
    """Test watcher task management."""

    def test_add_watcher_task(self):
        from gateway.cron_scheduler import CronScheduler

        scheduler = CronScheduler(
            running_ref=MagicMock(return_value=True),
            create_watcher_task_fn=MagicMock(),
        )

        scheduler._watcher_tasks["session1"] = True
        self.assertIn("session1", scheduler.watcher_tasks)

    def test_cleanup_watcher_task(self):
        from gateway.cron_scheduler import CronScheduler

        scheduler = CronScheduler(
            running_ref=MagicMock(return_value=True),
            create_watcher_task_fn=MagicMock(),
        )

        scheduler._watcher_tasks["session1"] = True
        scheduler.cleanup_watcher_task("session1")
        self.assertNotIn("session1", scheduler.watcher_tasks)


class TestPendingWatcherDrain(unittest.TestCase):
    """Test pending watcher draining."""

    def test_drain_returns_early_when_no_pending(self):
        from gateway.cron_scheduler import CronScheduler

        scheduler = CronScheduler(
            running_ref=MagicMock(return_value=False),
            create_watcher_task_fn=MagicMock(),
        )

        async def run_drain():
            await scheduler.pending_watcher_drain(interval=1)

        import asyncio
        asyncio.run(run_drain())

        self.assertEqual(scheduler._create_watcher_task.call_count, 0)


if __name__ == "__main__":
    unittest.main()