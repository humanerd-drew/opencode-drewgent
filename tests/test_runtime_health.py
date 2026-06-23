"""
Tests for runtime_health.py - Drewgent runtime health validation.

These tests validate the startup health check module that detects:
- Missing required modules
- Runtime root drift
- State storage issues
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
RUNTIME_HEALTH_PATH = GATEWAY_DIR / "runtime_health.py"

sys.path.insert(0, str(GATEWAY_DIR))


class TestRuntimeHealthModuleImports(unittest.TestCase):
    """Test that runtime_health module itself can be imported."""

    def test_runtime_health_module_importable(self):
        import runtime_health
        self.assertTrue(hasattr(runtime_health, "validate_runtime"))
        self.assertTrue(hasattr(runtime_health, "RuntimeHealth"))
        self.assertTrue(hasattr(runtime_health, "HealthIssue"))


class TestHealthIssueDataclass(unittest.TestCase):
    """Test HealthIssue dataclass."""

    def test_health_issue_creation(self):
        from runtime_health import HealthIssue
        issue = HealthIssue(
            severity="critical",
            code="TEST_CODE",
            message="Test message",
            hint="Test hint"
        )
        self.assertEqual(issue.severity, "critical")
        self.assertEqual(issue.code, "TEST_CODE")
        self.assertEqual(issue.message, "Test message")
        self.assertEqual(issue.hint, "Test hint")


class TestRuntimeHealthDataclass(unittest.TestCase):
    """Test RuntimeHealth dataclass."""

    def test_runtime_health_default_is_healthy(self):
        from runtime_health import RuntimeHealth
        health = RuntimeHealth(is_healthy=True)
        self.assertTrue(health.is_healthy)
        self.assertEqual(len(health.issues), 0)

    def test_runtime_health_add_issue_makes_unhealthy(self):
        from runtime_health import RuntimeHealth
        health = RuntimeHealth(is_healthy=True)
        health.add_issue("critical", "TEST", "Test issue")
        self.assertFalse(health.is_healthy)
        self.assertEqual(len(health.issues), 1)


class TestCheckModuleImportable(unittest.TestCase):
    """Test module import validation."""

    def test_stdlib_module_is_importable(self):
        from runtime_health import check_module_importable
        self.assertTrue(check_module_importable("pathlib"))

    def test_nonexistent_module_is_not_importable(self):
        from runtime_health import check_module_importable
        self.assertFalse(check_module_importable("this_module_definitely_does_not_exist_12345"))


class TestGetDrewgentHome(unittest.TestCase):
    """Test DREW_HOME resolution."""

    def test_default_home(self):
        from runtime_health import get_drewgent_home
        with patch.dict(os.environ, {}, clear=True):
            home = get_drewgent_home()
            self.assertEqual(home, Path.home() / ".drewgent")

    def test_drew_home_env_override(self):
        from runtime_health import get_drewgent_home
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"DREW_HOME": tmp}):
                home = get_drewgent_home()
                self.assertEqual(home.resolve(), Path(tmp).resolve())

    def test_drewgent_home_env_override(self):
        from runtime_health import get_drewgent_home
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"DREWGENT_HOME": tmp}):
                home = get_drewgent_home()
                self.assertEqual(home.resolve(), Path(tmp).resolve())


class TestValidateRuntime(unittest.TestCase):
    """Test the main validate_runtime function."""

    def test_validate_runtime_returns_runtime_health(self):
        from runtime_health import validate_runtime, RuntimeHealth
        health = validate_runtime()
        self.assertIsInstance(health, RuntimeHealth)
        self.assertIsInstance(health.issues, list)
        self.assertIsInstance(health.module_check_results, dict)
        self.assertIsNotNone(health.drewgent_home)

    def test_validate_runtime_has_required_modules_check(self):
        from runtime_health import validate_runtime, REQUIRED_MODULES
        health = validate_runtime()
        for module_name in REQUIRED_MODULES:
            self.assertIn(module_name, health.module_check_results)


class TestCheckPortAvailable(unittest.TestCase):
    """Test port availability checking."""

    def test_port_0_is_available(self):
        from runtime_health import check_port_available
        self.assertTrue(check_port_available(0))


class TestCheckDualStorage(unittest.TestCase):
    """Test dual storage detection."""

    def test_no_dual_storage_when_neither_exists(self):
        from runtime_health import check_dual_storage
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            has_dual, details = check_dual_storage(home)
            self.assertFalse(has_dual)
            self.assertIsNone(details)

    def test_no_dual_storage_when_only_db_exists(self):
        from runtime_health import check_dual_storage
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / "state.db").touch()
            has_dual, details = check_dual_storage(home)
            self.assertFalse(has_dual)
            self.assertIsNone(details)

    def test_no_dual_storage_when_only_json_exists(self):
        from runtime_health import check_dual_storage
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / "sessions.json").touch()
            has_dual, details = check_dual_storage(home)
            self.assertFalse(has_dual)
            self.assertIsNone(details)

    def test_dual_storage_detected_when_both_exist(self):
        from runtime_health import check_dual_storage
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / "state.db").touch()
            (home / "sessions.json").touch()
            has_dual, details = check_dual_storage(home)
            self.assertTrue(has_dual)
            self.assertIsNotNone(details)
            self.assertIn("dual storage", details)


class TestFormatHealthReport(unittest.TestCase):
    """Test health report formatting."""

    def test_format_empty_health_report(self):
        from runtime_health import RuntimeHealth, format_health_report
        health = RuntimeHealth(is_healthy=True)
        report = format_health_report(health)
        self.assertIn("DREW_HOME", report)
        self.assertIn("healthy", report)

    def test_format_unhealthy_report_shows_issues(self):
        from runtime_health import RuntimeHealth, format_health_report
        health = RuntimeHealth(is_healthy=True)
        health.add_issue("critical", "TEST_CODE", "Test issue message", "Test hint")
        report = format_health_report(health)
        self.assertIn("TEST_CODE", report)
        self.assertIn("Test issue message", report)
        self.assertIn("Test hint", report)


if __name__ == "__main__":
    unittest.main()