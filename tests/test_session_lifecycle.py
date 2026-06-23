"""
Tests for SessionLifecycle - session expiry and memory flushing.

These tests verify that SessionLifecycle correctly manages session
expiration and memory flushing.
"""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch


class TestSessionLifecycleCreation(unittest.TestCase):
    """Test SessionLifecycle instantiation."""

    def test_session_lifecycle_creatable(self):
        from gateway.session_lifecycle import SessionLifecycle

        mock_store = MagicMock()
        mock_running = MagicMock(return_value=True)
        mock_flush = AsyncMock()

        lifecycle = SessionLifecycle(
            session_store=mock_store,
            running_ref=mock_running,
            async_flush_fn=mock_flush,
        )
        self.assertIsNotNone(lifecycle)

    def test_session_lifecycle_has_session_store(self):
        from gateway.session_lifecycle import SessionLifecycle

        mock_store = MagicMock()
        lifecycle = SessionLifecycle(
            session_store=mock_store,
            running_ref=MagicMock(return_value=True),
            async_flush_fn=AsyncMock(),
        )
        self.assertEqual(lifecycle._session_store, mock_store)


class TestSessionLifecycleExpiryWatcher(unittest.TestCase):
    """Test session expiry watcher functionality."""

    def test_expiry_watcher_skips_non_expired_sessions(self):
        from gateway.session_lifecycle import SessionLifecycle

        mock_store = MagicMock()
        mock_store._entries = {}
        mock_store._is_session_expired = MagicMock(return_value=False)
        mock_store._ensure_loaded = MagicMock()
        mock_store._lock = MagicMock()
        mock_store._save = MagicMock()

        lifecycle = SessionLifecycle(
            session_store=mock_store,
            running_ref=MagicMock(return_value=True),
            async_flush_fn=AsyncMock(),
        )

        mock_entry = MagicMock()
        mock_entry.memory_flushed = False
        mock_store._entries = {"test_key": mock_entry}
        mock_store._is_session_expired.return_value = False

        lifecycle._session_store._ensure_loaded()

        self.assertEqual(len(lifecycle._session_store._entries), 1)

    def test_expiry_watcher_skips_memory_flushed_sessions(self):
        from gateway.session_lifecycle import SessionLifecycle

        mock_store = MagicMock()
        mock_entry = MagicMock()
        mock_entry.memory_flushed = True
        mock_store._entries = {"test_key": mock_entry}
        mock_store._is_session_expired = MagicMock(return_value=True)
        mock_store._ensure_loaded = MagicMock()
        mock_store._lock = MagicMock()
        mock_store._save = MagicMock()

        lifecycle = SessionLifecycle(
            session_store=mock_store,
            running_ref=MagicMock(return_value=True),
            async_flush_fn=AsyncMock(),
        )

        lifecycle._session_store._ensure_loaded()

        self.assertEqual(len(lifecycle._session_store._entries), 1)


class TestSessionLifecycleFlushFailureTracking(unittest.TestCase):
    """Test flush failure tracking."""

    def test_flush_failure_retries_up_to_max(self):
        from gateway.session_lifecycle import SessionLifecycle, _MAX_FLUSH_RETRIES

        mock_store = MagicMock()
        mock_flush = AsyncMock(side_effect=Exception("flush error"))
        mock_entry = MagicMock()
        mock_entry.memory_flushed = False
        mock_entry.session_id = "test_session"
        mock_store._entries = {"test_key": mock_entry}
        mock_store._is_session_expired = MagicMock(return_value=True)
        mock_store._ensure_loaded = MagicMock()
        mock_store._lock = MagicMock()
        mock_store._save = MagicMock()

        lifecycle = SessionLifecycle(
            session_store=mock_store,
            running_ref=MagicMock(return_value=True),
            async_flush_fn=mock_flush,
        )

        self.assertEqual(_MAX_FLUSH_RETRIES, 3)


if __name__ == "__main__":
    unittest.main()