"""Tests for gateway runtime status tracking."""

import json
import os

from gateway import status


class TestGatewayPidState:
    def test_write_pid_file_records_gateway_metadata(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DREW_HOME", str(tmp_path))

        status.write_pid_file()

        payload = json.loads((tmp_path / "gateway.pid").read_text())
        assert payload["pid"] == os.getpid()
        assert payload["kind"] == "drewgent-gateway"
        assert isinstance(payload["argv"], list)
        assert payload["argv"]

    def test_get_running_pid_rejects_live_non_gateway_pid(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DREW_HOME", str(tmp_path))
        pid_path = tmp_path / "gateway.pid"
        pid_path.write_text(str(os.getpid()))

        assert status.get_running_pid() is None
        assert not pid_path.exists()

    def test_get_running_pid_accepts_gateway_metadata_when_cmdline_unavailable(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DREW_HOME", str(tmp_path))
        pid_path = tmp_path / "gateway.pid"
        pid_path.write_text(json.dumps({
            "pid": os.getpid(),
            "kind": "drewgent-gateway",
            "argv": ["python", "-m", "drewgent_cli.main", "gateway"],
            "start_time": 123,
        }))

        monkeypatch.setattr(status.os, "kill", lambda pid, sig: None)
        monkeypatch.setattr(status, "_get_process_start_time", lambda pid: 123)
        monkeypatch.setattr(status, "_read_process_cmdline", lambda pid: None)

        assert status.get_running_pid() == os.getpid()

    def test_get_running_pid_accepts_script_style_gateway_cmdline(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DREW_HOME", str(tmp_path))
        pid_path = tmp_path / "gateway.pid"
        pid_path.write_text(json.dumps({
            "pid": os.getpid(),
            "kind": "drewgent-gateway",
            "argv": ["/venv/bin/python", "/repo/drewgent_cli/main.py", "gateway", "run", "--replace"],
            "start_time": 123,
        }))

        monkeypatch.setattr(status.os, "kill", lambda pid, sig: None)
        monkeypatch.setattr(status, "_get_process_start_time", lambda pid: 123)
        monkeypatch.setattr(
            status,
            "_read_process_cmdline",
            lambda pid: "/venv/bin/python /repo/drewgent_cli/main.py gateway run --replace",
        )

        assert status.get_running_pid() == os.getpid()


class TestGatewayLockDir:
    def test_default_lock_dir_lives_under_drew_home(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DREW_HOME", str(tmp_path))
        monkeypatch.delenv("DREW_GATEWAY_LOCK_DIR", raising=False)
        monkeypatch.delenv("XDG_STATE_HOME", raising=False)

        assert status._get_lock_dir() == tmp_path / "run" / "gateway-locks"

    def test_lock_dir_override_still_wins(self, tmp_path, monkeypatch):
        override = tmp_path / "custom-locks"
        monkeypatch.setenv("DREW_HOME", str(tmp_path / "home"))
        monkeypatch.setenv("DREW_GATEWAY_LOCK_DIR", str(override))

        assert status._get_lock_dir() == override


class TestGatewayRuntimeStatus:
    def test_write_runtime_status_overwrites_stale_pid_on_restart(self, tmp_path, monkeypatch):
        """Regression: setdefault() preserved stale PID from previous process (#1631)."""
        monkeypatch.setenv("DREW_HOME", str(tmp_path))

        # Simulate a previous gateway run that left a state file with a stale PID
        state_path = tmp_path / "gateway_state.json"
        state_path.write_text(json.dumps({
            "pid": 99999,
            "start_time": 1000.0,
            "kind": "drewgent-gateway",
            "platforms": {},
            "updated_at": "2025-01-01T00:00:00Z",
        }))

        status.write_runtime_status(gateway_state="running")

        payload = status.read_runtime_status()
        assert payload["pid"] == os.getpid(), "PID should be overwritten, not preserved via setdefault"
        assert payload["start_time"] != 1000.0, "start_time should be overwritten on restart"

    def test_write_runtime_status_overwrites_stale_argv_on_restart(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DREW_HOME", str(tmp_path))

        state_path = tmp_path / "gateway_state.json"
        state_path.write_text(json.dumps({
            "pid": 99999,
            "kind": "drewgent-gateway",
            "argv": ["/old/source/drewgent_cli/main.py", "gateway", "run"],
            "start_time": 1000.0,
            "platforms": {},
            "updated_at": "2025-01-01T00:00:00Z",
        }))

        monkeypatch.setattr(status.sys, "argv", ["/new/source/drewgent_cli/main.py", "gateway", "run"])

        status.write_runtime_status(gateway_state="running")

        payload = status.read_runtime_status()
        assert payload["argv"] == ["/new/source/drewgent_cli/main.py", "gateway", "run"]

    def test_write_runtime_status_records_platform_failure(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DREW_HOME", str(tmp_path))

        status.write_runtime_status(
            gateway_state="startup_failed",
            exit_reason="telegram conflict",
            platform="telegram",
            platform_state="fatal",
            error_code="telegram_polling_conflict",
            error_message="another poller is active",
        )

        payload = status.read_runtime_status()
        assert payload["gateway_state"] == "startup_failed"
        assert payload["exit_reason"] == "telegram conflict"
        assert payload["platforms"]["telegram"]["state"] == "fatal"
        assert payload["platforms"]["telegram"]["error_code"] == "telegram_polling_conflict"
        assert payload["platforms"]["telegram"]["error_message"] == "another poller is active"

    def test_write_runtime_status_clears_stale_platform_error_when_connected(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DREW_HOME", str(tmp_path))

        status.write_runtime_status(
            platform="feishu",
            platform_state="fatal",
            error_code="feishu_app_lock",
            error_message="stale lock",
        )
        status.write_runtime_status(
            platform="feishu",
            platform_state="connected",
        )

        payload = status.read_runtime_status()
        feishu = payload["platforms"]["feishu"]
        assert feishu["state"] == "connected"
        assert "error_code" not in feishu
        assert "error_message" not in feishu

    def test_write_runtime_status_starting_resets_stale_platforms(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DREW_HOME", str(tmp_path))

        status.write_runtime_status(
            platform="feishu",
            platform_state="fatal",
            error_code="feishu_app_lock",
            error_message="stale lock",
        )
        status.write_runtime_status(gateway_state="starting", exit_reason=None)

        payload = status.read_runtime_status()
        assert payload["gateway_state"] == "starting"
        assert payload["platforms"] == {}


class TestScopedLocks:
    def test_acquire_scoped_lock_rejects_live_other_process(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DREW_GATEWAY_LOCK_DIR", str(tmp_path / "locks"))
        lock_path = tmp_path / "locks" / "telegram-bot-token-2bb80d537b1da3e3.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text(json.dumps({
            "pid": 99999,
            "start_time": 123,
            "kind": "drewgent-gateway",
        }))

        monkeypatch.setattr(status.os, "kill", lambda pid, sig: None)
        monkeypatch.setattr(status, "_get_process_start_time", lambda pid: 123)

        acquired, existing = status.acquire_scoped_lock("telegram-bot-token", "secret", metadata={"platform": "telegram"})

        assert acquired is False
        assert existing["pid"] == 99999

    def test_acquire_scoped_lock_preserves_process_when_signal_permission_denied(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DREW_GATEWAY_LOCK_DIR", str(tmp_path / "locks"))
        lock_path = tmp_path / "locks" / "telegram-bot-token-2bb80d537b1da3e3.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text(json.dumps({
            "pid": 99999,
            "start_time": 123,
            "kind": "drewgent-gateway",
        }))

        def fake_kill(pid, sig):
            raise PermissionError

        monkeypatch.setattr(status.os, "kill", fake_kill)
        monkeypatch.setattr(status, "_get_process_start_time", lambda pid: 123)

        acquired, existing = status.acquire_scoped_lock("telegram-bot-token", "secret")

        assert acquired is False
        assert existing["pid"] == 99999

    def test_acquire_scoped_lock_replaces_stale_record(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DREW_GATEWAY_LOCK_DIR", str(tmp_path / "locks"))
        lock_path = tmp_path / "locks" / "telegram-bot-token-2bb80d537b1da3e3.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text(json.dumps({
            "pid": 99999,
            "start_time": 123,
            "kind": "drewgent-gateway",
        }))

        def fake_kill(pid, sig):
            raise ProcessLookupError

        monkeypatch.setattr(status.os, "kill", fake_kill)

        acquired, existing = status.acquire_scoped_lock("telegram-bot-token", "secret", metadata={"platform": "telegram"})

        assert acquired is True
        assert existing["pid"] == 99999
        payload = json.loads(lock_path.read_text())
        assert payload["pid"] == os.getpid()
        assert payload["metadata"]["platform"] == "telegram"

    def test_acquire_scoped_lock_writes_created_and_heartbeat_timestamps(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DREW_GATEWAY_LOCK_DIR", str(tmp_path / "locks"))

        acquired, _ = status.acquire_scoped_lock("telegram-bot-token", "secret")

        assert acquired is True
        lock_path = tmp_path / "locks" / "telegram-bot-token-2bb80d537b1da3e3.lock"
        payload = json.loads(lock_path.read_text())
        assert payload["created_at"]
        assert payload["heartbeat_at"]
        assert payload["created_at"] == payload["heartbeat_at"]

    def test_acquire_scoped_lock_refreshes_heartbeat_when_current_owner_reacquires(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DREW_GATEWAY_LOCK_DIR", str(tmp_path / "locks"))
        monkeypatch.setattr(status, "_get_process_start_time", lambda pid: 99999)

        assert status.acquire_scoped_lock("telegram-bot-token", "secret", metadata={"n": 1})[0]
        lock_path = tmp_path / "locks" / "telegram-bot-token-2bb80d537b1da3e3.lock"
        original_payload = json.loads(lock_path.read_text())

        ticks = iter([
            "2026-05-01T00:00:00+00:00",
            "2026-05-01T00:00:01+00:00",
        ])
        monkeypatch.setattr(status, "_utc_now_iso", lambda: next(ticks))

        acquired, existing = status.acquire_scoped_lock("telegram-bot-token", "secret", metadata={"n": 2})

        assert acquired is True
        assert existing["metadata"]["n"] == 1
        refreshed_payload = json.loads(lock_path.read_text())
        assert refreshed_payload["created_at"] == original_payload["created_at"]
        assert refreshed_payload["heartbeat_at"] == "2026-05-01T00:00:01+00:00"
        assert refreshed_payload["metadata"]["n"] == 2

    def test_acquire_scoped_lock_replaces_live_pid_with_mismatched_start_time(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DREW_GATEWAY_LOCK_DIR", str(tmp_path / "locks"))
        lock_path = tmp_path / "locks" / "telegram-bot-token-2bb80d537b1da3e3.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text(json.dumps({
            "pid": 99999,
            "start_time": 123,
            "kind": "drewgent-gateway",
        }))

        monkeypatch.setattr(status.os, "kill", lambda pid, sig: None)
        monkeypatch.setattr(status, "_get_process_start_time", lambda pid: 456 if pid == 99999 else 789)

        acquired, existing = status.acquire_scoped_lock("telegram-bot-token", "secret", metadata={"platform": "telegram"})

        assert acquired is True
        assert existing["pid"] == 99999
        payload = json.loads(lock_path.read_text())
        assert payload["pid"] == os.getpid()

    def test_release_scoped_lock_only_removes_current_owner(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DREW_GATEWAY_LOCK_DIR", str(tmp_path / "locks"))

        acquired, _ = status.acquire_scoped_lock("telegram-bot-token", "secret", metadata={"platform": "telegram"})
        assert acquired is True
        lock_path = tmp_path / "locks" / "telegram-bot-token-2bb80d537b1da3e3.lock"
        assert lock_path.exists()

        status.release_scoped_lock("telegram-bot-token", "secret")
        assert not lock_path.exists()

    def test_release_all_scoped_locks_preserves_live_other_gateway_lock(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DREW_GATEWAY_LOCK_DIR", str(tmp_path / "locks"))
        locks_dir = tmp_path / "locks"
        locks_dir.mkdir(parents=True)
        current_pid = os.getpid()
        other_pid = 88888
        stale_pid = 77777
        current_start_time = 111
        other_start_time = 222

        (locks_dir / "current.lock").write_text(json.dumps({
            "pid": current_pid,
            "start_time": current_start_time,
            "kind": "drewgent-gateway",
            "argv": ["python", "-m", "drewgent_cli.main", "gateway"],
        }))
        (locks_dir / "other.lock").write_text(json.dumps({
            "pid": other_pid,
            "start_time": other_start_time,
            "kind": "drewgent-gateway",
            "argv": ["python", "-m", "drewgent_cli.main", "gateway"],
        }))
        (locks_dir / "stale.lock").write_text(json.dumps({
            "pid": stale_pid,
            "start_time": 333,
            "kind": "drewgent-gateway",
        }))

        def fake_kill(pid, sig):
            if pid in {current_pid, other_pid}:
                return None
            raise ProcessLookupError

        def fake_start_time(pid):
            if pid == current_pid:
                return current_start_time
            if pid == other_pid:
                return other_start_time
            return None

        monkeypatch.setattr(status.os, "kill", fake_kill)
        monkeypatch.setattr(status, "_get_process_start_time", fake_start_time)
        monkeypatch.setattr(status, "_read_process_cmdline", lambda pid: None)

        removed = status.release_all_scoped_locks()

        remaining = {path.name for path in locks_dir.glob("*.lock")}
        assert removed == 2
        assert remaining == {"other.lock"}
