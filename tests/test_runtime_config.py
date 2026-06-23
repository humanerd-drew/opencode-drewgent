"""
Tests for RuntimeConfig - Gateway configuration extraction.

These tests validate that RuntimeConfig correctly loads and caches
configuration from config.yaml and environment variables.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
GATEWAY_DIR = ROOT / "P3-sensors" / "gateway"

sys.path.insert(0, str(GATEWAY_DIR))


class TestRuntimeConfigDefaults(unittest.TestCase):
    """Test RuntimeConfig with default/dummy values."""

    def test_runtime_config_creatable(self):
        from runtime_config import RuntimeConfig
        config = RuntimeConfig(drew_home=Path(tempfile.gettempdir()))
        self.assertIsNotNone(config)

    def test_prefill_messages_default_empty(self):
        from runtime_config import RuntimeConfig
        config = RuntimeConfig(drew_home=Path(tempfile.gettempdir()))
        self.assertEqual(config.prefill_messages, [])

    def test_ephemeral_system_prompt_default_empty(self):
        from runtime_config import RuntimeConfig
        config = RuntimeConfig(drew_home=Path(tempfile.gettempdir()))
        self.assertEqual(config.ephemeral_system_prompt, "")

    def test_show_reasoning_default_false(self):
        from runtime_config import RuntimeConfig
        config = RuntimeConfig(drew_home=Path(tempfile.gettempdir()))
        self.assertFalse(config.show_reasoning)

    def test_background_notifications_mode_default_all(self):
        from runtime_config import RuntimeConfig
        config = RuntimeConfig(drew_home=Path(tempfile.gettempdir()))
        self.assertEqual(config.background_notifications_mode, "all")

    def test_provider_routing_default_empty(self):
        from runtime_config import RuntimeConfig
        config = RuntimeConfig(drew_home=Path(tempfile.gettempdir()))
        self.assertEqual(config.provider_routing, {})

    def test_fallback_model_default_none(self):
        from runtime_config import RuntimeConfig
        config = RuntimeConfig(drew_home=Path(tempfile.gettempdir()))
        self.assertIsNone(config.fallback_model)

    def test_smart_model_routing_default_empty(self):
        from runtime_config import RuntimeConfig
        config = RuntimeConfig(drew_home=Path(tempfile.gettempdir()))
        self.assertEqual(config.smart_model_routing, {})


class TestRuntimeConfigFromYaml(unittest.TestCase):
    """Test RuntimeConfig loading from config.yaml."""

    def test_load_show_reasoning_from_yaml(self):
        from runtime_config import RuntimeConfig
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            config_yaml = home / "config.yaml"
            config_yaml.write_text(
                "display:\n  show_reasoning: true\n",
                encoding="utf-8",
            )
            config = RuntimeConfig(drew_home=home)
            self.assertTrue(config.show_reasoning)

    def test_load_reasoning_effort_from_yaml(self):
        from runtime_config import RuntimeConfig
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            config_yaml = home / "config.yaml"
            config_yaml.write_text(
                "agent:\n  reasoning_effort: high\n",
                encoding="utf-8",
            )
            config = RuntimeConfig(drew_home=home)
            self.assertEqual(config.reasoning_config, {"enabled": True, "effort": "high"})

    def test_load_provider_routing_from_yaml(self):
        from runtime_config import RuntimeConfig
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            config_yaml = home / "config.yaml"
            config_yaml.write_text(
                "provider_routing:\n  preferred: openai\n",
                encoding="utf-8",
            )
            config = RuntimeConfig(drew_home=home)
            self.assertEqual(config.provider_routing, {"preferred": "openai"})

    def test_load_fallback_model_from_yaml(self):
        from runtime_config import RuntimeConfig
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            config_yaml = home / "config.yaml"
            config_yaml.write_text(
                "fallback_providers:\n  - provider: anthropic\n",
                encoding="utf-8",
            )
            config = RuntimeConfig(drew_home=home)
            self.assertEqual(config.fallback_model, [{"provider": "anthropic"}])

    def test_load_smart_model_routing_from_yaml(self):
        from runtime_config import RuntimeConfig
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            config_yaml = home / "config.yaml"
            config_yaml.write_text(
                "smart_model_routing:\n  enabled: true\n",
                encoding="utf-8",
            )
            config = RuntimeConfig(drew_home=home)
            self.assertEqual(config.smart_model_routing, {"enabled": True})


class TestRuntimeConfigBackgroundNotifications(unittest.TestCase):
    """Test background notifications mode loading."""

    def test_default_mode_all(self):
        from runtime_config import RuntimeConfig
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            config = RuntimeConfig(drew_home=home)
            self.assertEqual(config.background_notifications_mode, "all")

    def test_mode_off_from_yaml(self):
        from runtime_config import RuntimeConfig
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            config_yaml = home / "config.yaml"
            config_yaml.write_text(
                "display:\n  background_process_notifications: false\n",
                encoding="utf-8",
            )
            config = RuntimeConfig(drew_home=home)
            self.assertEqual(config.background_notifications_mode, "off")

    def test_mode_result_from_yaml(self):
        from runtime_config import RuntimeConfig
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            config_yaml = home / "config.yaml"
            config_yaml.write_text(
                "display:\n  background_process_notifications: result\n",
                encoding="utf-8",
            )
            config = RuntimeConfig(drew_home=home)
            self.assertEqual(config.background_notifications_mode, "result")

    def test_invalid_mode_defaults_to_all(self):
        from runtime_config import RuntimeConfig
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            config_yaml = home / "config.yaml"
            config_yaml.write_text(
                "display:\n  background_process_notifications: invalid_mode\n",
                encoding="utf-8",
            )
            config = RuntimeConfig(drew_home=home)
            self.assertEqual(config.background_notifications_mode, "all")


class TestRuntimeConfigPrefillMessages(unittest.TestCase):
    """Test prefill messages loading."""

    def test_prefill_messages_from_file(self):
        from runtime_config import RuntimeConfig
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            prefills_file = home / "prefills.json"
            prefills_file.write_text(
                '[{"role": "user", "content": "hello"}]',
                encoding="utf-8",
            )
            config_yaml = home / "config.yaml"
            config_yaml.write_text(
                f"prefill_messages_file: {prefills_file}\n",
                encoding="utf-8",
            )
            config = RuntimeConfig(drew_home=home)
            self.assertEqual(config.prefill_messages, [{"role": "user", "content": "hello"}])

    def test_prefill_messages_invalid_file(self):
        from runtime_config import RuntimeConfig
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            prefills_file = home / "prefills.json"
            prefills_file.write_text("not a list", encoding="utf-8")
            config_yaml = home / "config.yaml"
            config_yaml.write_text(
                f"prefill_messages_file: {prefills_file}\n",
                encoding="utf-8",
            )
            config = RuntimeConfig(drew_home=home)
            self.assertEqual(config.prefill_messages, [])


if __name__ == "__main__":
    unittest.main()