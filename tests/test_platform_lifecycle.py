"""
Tests for PlatformLifecycle - platform connection/reconnection management.

These tests verify that PlatformLifecycle correctly manages platform
connection state and reconnection logic.
"""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch


class TestPlatformLifecycleCreation(unittest.TestCase):
    """Test PlatformLifecycle instantiation."""

    def test_platform_lifecycle_creatable(self):
        from gateway.platform_lifecycle import PlatformLifecycle

        mock_config = MagicMock()
        mock_fn = MagicMock()
        mock_running = MagicMock(return_value=True)

        lifecycle = PlatformLifecycle(
            config=mock_config,
            create_adapter_fn=mock_fn,
            running_ref=mock_running,
        )
        self.assertIsNotNone(lifecycle)
        self.assertEqual(lifecycle.failed_count, 0)

    def test_failed_platforms_empty_on_init(self):
        from gateway.platform_lifecycle import PlatformLifecycle

        mock_config = MagicMock()
        lifecycle = PlatformLifecycle(
            config=mock_config,
            create_adapter_fn=MagicMock(),
            running_ref=MagicMock(return_value=True),
        )
        self.assertEqual(len(lifecycle.failed_platforms), 0)


class TestQueueReconnect(unittest.TestCase):
    """Test queueing platforms for reconnection."""

    def test_queue_reconnect_adds_platform(self):
        from gateway.platform_lifecycle import PlatformLifecycle
        from gateway.config import Platform

        mock_config = MagicMock()
        lifecycle = PlatformLifecycle(
            config=mock_config,
            create_adapter_fn=MagicMock(),
            running_ref=MagicMock(return_value=True),
        )

        mock_platform_config = MagicMock()
        lifecycle.queue_reconnect(Platform.DISCORD, mock_platform_config)

        self.assertEqual(lifecycle.failed_count, 1)
        self.assertIn(Platform.DISCORD, lifecycle.failed_platforms)

    def test_queue_reconnect_with_retryable_false(self):
        from gateway.platform_lifecycle import PlatformLifecycle
        from gateway.config import Platform

        mock_config = MagicMock()
        lifecycle = PlatformLifecycle(
            config=mock_config,
            create_adapter_fn=MagicMock(),
            running_ref=MagicMock(return_value=True),
        )

        lifecycle.queue_reconnect(Platform.DISCORD, MagicMock(), retryable=False)

        self.assertEqual(lifecycle.failed_count, 0)


class TestRemoveFailed(unittest.TestCase):
    """Test removing platforms from failed queue."""

    def test_remove_failed_removes_platform(self):
        from gateway.platform_lifecycle import PlatformLifecycle
        from gateway.config import Platform

        mock_config = MagicMock()
        lifecycle = PlatformLifecycle(
            config=mock_config,
            create_adapter_fn=MagicMock(),
            running_ref=MagicMock(return_value=True),
        )

        lifecycle.queue_reconnect(Platform.DISCORD, MagicMock())
        self.assertEqual(lifecycle.failed_count, 1)

        lifecycle.remove_failed(Platform.DISCORD)
        self.assertEqual(lifecycle.failed_count, 0)

    def test_remove_failed_nonexistent_is_noop(self):
        from gateway.platform_lifecycle import PlatformLifecycle
        from gateway.config import Platform

        mock_config = MagicMock()
        lifecycle = PlatformLifecycle(
            config=mock_config,
            create_adapter_fn=MagicMock(),
            running_ref=MagicMock(return_value=True),
        )

        lifecycle.remove_failed(Platform.DISCORD)
        self.assertEqual(lifecycle.failed_count, 0)


class TestSyncVoiceMode(unittest.TestCase):
    """Test voice mode synchronization to adapters."""

    def test_sync_voice_mode_sets_mode(self):
        from gateway.platform_lifecycle import PlatformLifecycle

        mock_config = MagicMock()
        lifecycle = PlatformLifecycle(
            config=mock_config,
            create_adapter_fn=MagicMock(),
            running_ref=MagicMock(return_value=True),
        )

        mock_adapter = MagicMock()
        mock_adapter.session_key = "test_session"
        mock_adapter.set_voice_mode = MagicMock()

        voice_modes = {"test_session": "voice_only"}
        lifecycle.sync_voice_mode_to_adapter(mock_adapter, voice_modes)

        mock_adapter.set_voice_mode.assert_called_once_with("voice_only")

    def test_sync_voice_mode_skips_unknown_session(self):
        from gateway.platform_lifecycle import PlatformLifecycle

        mock_config = MagicMock()
        lifecycle = PlatformLifecycle(
            config=mock_config,
            create_adapter_fn=MagicMock(),
            running_ref=MagicMock(return_value=True),
        )

        mock_adapter = MagicMock()
        mock_adapter.session_key = "unknown_session"
        mock_adapter.set_voice_mode = MagicMock()

        voice_modes = {"test_session": "voice_only"}
        lifecycle.sync_voice_mode_to_adapter(mock_adapter, voice_modes)

        mock_adapter.set_voice_mode.assert_not_called()


if __name__ == "__main__":
    unittest.main()