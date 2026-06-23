from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "P5-ego" / "config"
SCRIPT_PATH = ROOT / "P4-cortex" / "scripts" / "diagnose_runtime_roots.py"
BOOTSTRAP_PATH = ROOT / "P3-sensors" / "gateway" / "config_bootstrap.py"

if str(CONFIG_DIR) not in sys.path:
    sys.path.insert(0, str(CONFIG_DIR))

from paths import candidate_runtime_roots, get_paths  # noqa: E402


def _load_diagnostic_module():
    spec = importlib.util.spec_from_file_location("diagnose_runtime_roots", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _load_bootstrap_module():
    spec = importlib.util.spec_from_file_location("config_bootstrap", BOOTSTRAP_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class PathsTest(unittest.TestCase):
    def test_get_paths_uses_7_layer_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = get_paths(root)

            self.assertEqual(paths.home, root.resolve())
            self.assertEqual(paths.brain, root.resolve() / "P0-brainstem" / "brain")
            self.assertEqual(
                paths.config,
                root.resolve() / "P5-ego" / "config" / "config.yaml",
            )
            self.assertEqual(paths.sessions, root.resolve() / "P2-hippocampus" / "sessions")
            self.assertEqual(paths.logs, root.resolve() / "P6-prefrontal" / "logs")

    def test_candidate_runtime_roots_include_home_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidates = candidate_runtime_roots(root)

            self.assertGreaterEqual(len(candidates), 1)
            self.assertEqual(candidates[0], root.resolve())


class RuntimeDiagnosticsTest(unittest.TestCase):
    def test_discover_repo_root_handles_scripts_symlink(self):
        module = _load_diagnostic_module()

        self.assertEqual(module.ROOT, ROOT)

    def test_build_report_contains_expected_sections(self):
        module = _load_diagnostic_module()
        report = module.build_report(log_limit=1)

        self.assertIn("drewgent_home", report)
        self.assertIn("canonical_paths", report)
        self.assertIn("runtime_root_candidates", report)
        self.assertIn("active_process_hints", report)
        self.assertIn("recent_log_path_references", report)


class GatewayBootstrapTest(unittest.TestCase):
    def test_bridge_config_to_env_maps_selected_values(self):
        bootstrap = _load_bootstrap_module()
        parent = types.ModuleType("drewgent_cli")
        config = types.ModuleType("drewgent_cli.config")
        config._expand_env_vars = lambda data: data
        old_parent = sys.modules.get("drewgent_cli")
        old_config = sys.modules.get("drewgent_cli.config")
        sys.modules["drewgent_cli"] = parent
        sys.modules["drewgent_cli.config"] = config

        keys = [
            "TERMINAL_ENV",
            "TERMINAL_TIMEOUT",
            "AUXILIARY_VISION_PROVIDER",
            "DREW_MAX_ITERATIONS",
            "HERMES_AGENT_TIMEOUT",
            "DREW_TIMEZONE",
            "DREW_REDACT_SECRETS",
        ]
        old_env = {key: os.environ.get(key) for key in keys}
        for key in keys:
            os.environ.pop(key, None)

        try:
            with tempfile.TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "config.yaml"
                config_path.write_text(
                    "\n".join(
                        [
                            "terminal:",
                            "  backend: local",
                            "  timeout: 42",
                            "auxiliary:",
                            "  vision:",
                            "    provider: test-provider",
                            "agent:",
                            "  max_turns: 9",
                            "  gateway_timeout: 123",
                            "timezone: Asia/Seoul",
                            "security:",
                            "  redact_secrets: true",
                        ]
                    ),
                    encoding="utf-8",
                )

                bootstrap.bridge_config_to_env(config_path)

                self.assertEqual(os.environ["TERMINAL_ENV"], "local")
                self.assertEqual(os.environ["TERMINAL_TIMEOUT"], "42")
                self.assertEqual(os.environ["AUXILIARY_VISION_PROVIDER"], "test-provider")
                self.assertEqual(os.environ["DREW_MAX_ITERATIONS"], "9")
                self.assertEqual(os.environ["HERMES_AGENT_TIMEOUT"], "123")
                self.assertEqual(os.environ["DREW_TIMEZONE"], "Asia/Seoul")
                self.assertEqual(os.environ["DREW_REDACT_SECRETS"], "true")
        finally:
            for key, value in old_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            if old_parent is None:
                sys.modules.pop("drewgent_cli", None)
            else:
                sys.modules["drewgent_cli"] = old_parent
            if old_config is None:
                sys.modules.pop("drewgent_cli.config", None)
            else:
                sys.modules["drewgent_cli.config"] = old_config


if __name__ == "__main__":
    unittest.main()
