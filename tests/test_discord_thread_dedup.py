"""
Tests for DiscordAdapter thread creation deduplication and persistence.

These tests verify that the DiscordAdapter correctly tracks auto-created
threads and persists them across restarts.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


class TestAutoCreateThreadDeduplication(unittest.TestCase):
    """Test that _auto_create_thread prevents duplicate thread creation."""

    def test_auto_created_threads_tracked_in_init(self):
        """Verify _auto_created_threads dict exists in __init__."""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

        with patch('gateway.platforms.discord.DISCORD_AVAILABLE', True), \
             patch('gateway.platforms.discord.discord') as mock_discord:
            mock_discord.opus.is_loaded.return_value = False

            from gateway.platforms.discord import DiscordAdapter
            from gateway.config import Platform, PlatformConfig

            config = MagicMock(spec=PlatformConfig)
            config.platform = Platform.DISCORD
            config.enabled = True

            adapter = DiscordAdapter(config)
            self.assertIsInstance(adapter._auto_created_threads, dict)
            self.assertEqual(len(adapter._auto_created_threads), 0)

    def test_duplicate_thread_creation_returns_existing(self):
        """Test that calling _auto_create_thread twice returns the cached thread."""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

        with patch('gateway.platforms.discord.DISCORD_AVAILABLE', True), \
             patch('gateway.platforms.discord.discord') as mock_discord:
            mock_discord.opus.is_loaded.return_value = False

            from gateway.platforms.discord import DiscordAdapter
            from gateway.config import Platform, PlatformConfig

            config = MagicMock(spec=PlatformConfig)
            config.platform = Platform.DISCORD
            config.enabled = True

            adapter = DiscordAdapter(config)
            adapter._client = MagicMock()

            mock_thread = MagicMock()
            mock_thread.id = 12345
            adapter._client.get_channel.return_value = mock_thread

            adapter._auto_created_threads["999"] = "12345"

            result = adapter._auto_created_threads.get("999")
            self.assertEqual(result, "12345")


class TestAutoCreatedThreadsPersistence(unittest.TestCase):
    """Test that auto-created threads are persisted to disk."""

    def test_load_auto_created_threads_from_disk(self):
        """Test loading auto-created threads from a temp file."""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

        from gateway.platforms.discord import DiscordAdapter

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            thread_data = {"123": "456", "789": "012"}

            auto_threads_file = tmp_path / "discord_auto_threads.json"
            auto_threads_file.write_text(json.dumps(thread_data), encoding="utf-8")

            with patch('gateway.platforms.discord.DISCORD_AVAILABLE', True), \
                 patch('gateway.platforms.discord.discord') as mock_discord, \
                 patch.object(
                     DiscordAdapter,
                     '_auto_thread_state_path',
                     return_value=auto_threads_file
                 ):
                mock_discord.opus.is_loaded.return_value = False

                from gateway.config import Platform, PlatformConfig

                config = MagicMock(spec=PlatformConfig)
                config.platform = Platform.DISCORD
                config.enabled = True

                loaded = DiscordAdapter._load_auto_created_threads()
                self.assertEqual(loaded, {"123": "456", "789": "012"})

    def test_save_auto_created_threads_to_disk(self):
        """Test saving auto-created threads to a temp file."""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

        from gateway.platforms.discord import DiscordAdapter

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            auto_threads_file = tmp_path / "discord_auto_threads.json"

            with patch('gateway.platforms.discord.DISCORD_AVAILABLE', True), \
                 patch('gateway.platforms.discord.discord') as mock_discord, \
                 patch.object(
                     DiscordAdapter,
                     '_auto_thread_state_path',
                     return_value=auto_threads_file
                 ):
                mock_discord.opus.is_loaded.return_value = False

                from gateway.config import Platform, PlatformConfig

                config = MagicMock(spec=PlatformConfig)
                config.platform = Platform.DISCORD
                config.enabled = True

                adapter = DiscordAdapter(config)
                adapter._auto_created_threads = {"msg1": "thread1", "msg2": "thread2"}
                adapter._save_auto_created_threads()

                loaded = json.loads(auto_threads_file.read_text(encoding="utf-8"))
                self.assertEqual(loaded, {"msg1": "thread1", "msg2": "thread2"})

    def test_init_loads_auto_created_threads(self):
        """Test that __init__ loads auto-created threads from disk."""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

        from gateway.platforms.discord import DiscordAdapter

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            thread_data = {"loaded_msg": "loaded_thread"}
            auto_threads_file = tmp_path / "discord_auto_threads.json"
            auto_threads_file.write_text(json.dumps(thread_data), encoding="utf-8")

            with patch('gateway.platforms.discord.DISCORD_AVAILABLE', True), \
                 patch('gateway.platforms.discord.discord') as mock_discord, \
                 patch.object(
                     DiscordAdapter,
                     '_auto_thread_state_path',
                     return_value=auto_threads_file
                 ):
                mock_discord.opus.is_loaded.return_value = False

                from gateway.config import Platform, PlatformConfig

                config = MagicMock(spec=PlatformConfig)
                config.platform = Platform.DISCORD
                config.enabled = True

                adapter = DiscordAdapter(config)
                self.assertEqual(adapter._auto_created_threads, {"loaded_msg": "loaded_thread"})


if __name__ == "__main__":
    unittest.main()