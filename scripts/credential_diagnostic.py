#!/usr/bin/env python3
"""Credential state diagnostic — probe, classify, report.

Mathematical model:
  Each credential c has a true state s ∈ S unknown to the agent.
  The agent receives an observation o ∈ O that is a many-to-one
  function of s: o = f(s).  This diagnostic adds:
    1. A PROBE (cheap validation call) → separates auth failure from
       provider/model unavailability.
    2. A CLASSIFIER that maps (o, source, type, history) → failure
       mode m ∈ M (refinement of S).
    3. A REGISTRY (JSON) that persists classified failure modes so
       the agent can query credential health WITHOUT trial and error.

  After this fix the agent can answer "what keys work?" from the
  registry instead of discovering expired keys mid-conversation.
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DREW_HOME = Path(os.environ.get("DREW_HOME", str(Path.home() / ".drewgent")))
REGISTRY_PATH = DREW_HOME / ".agent" / "memory" / "credential_state.json"
AUTH_PATH = DREW_HOME / "auth.json"
CONFIG_PATH = DREW_HOME / "config.yaml"

# ── Failure mode classification ───────────────────────────────────────
# Maps (status_code, error_body_hints, credential_source, type) → mode

FAILURE_MODES = {
    "expired_oauth": {
        "description": "OAuth token expired, refreshable",
        "action": "Run credential refresh (auto)",
        "retryable": True,
    },
    "expired_api_key": {
        "description": "API key expired, needs manual renewal",
        "action": "Replace the key in config",
        "retryable": False,
    },
    "wrong_key": {
        "description": "Key rejected — not the right key for this provider/model",
        "action": "Check which key the provider expects",
        "retryable": False,
    },
    "rate_limited": {
        "description": "Rate limited — too many requests",
        "action": "Wait and retry (auto)",
        "retryable": True,
    },
    "quota_exhausted": {
        "description": "Daily/monthly quota exhausted",
        "action": "Upgrade plan or wait for reset",
        "retryable": False,
    },
    "model_access": {
        "description": "API key valid but no access to this model",
        "action": "Check model availability for this key",
        "retryable": False,
    },
    "provider_down": {
        "description": "Provider returned 5xx or connection timeout",
        "action": "Retry with different provider (auto)",
        "retryable": True,
    },
    "no_credential": {
        "description": "No credential found for this provider",
        "action": "Add a credential (config, env, or auth)",
        "retryable": False,
    },
    "unknown": {
        "description": "Unclassified failure",
        "action": "Check logs for details",
        "retryable": False,
    },
}


def classify_failure(
    status_code: int | None,
    error_message: str,
    credential_source: str,
    credential_type: str,
) -> tuple[str, str]:
    """Classify a credential failure into a failure mode.

    Args:
        status_code: HTTP status code (None if connection error)
        error_message: Full error text from the API response
        credential_source: where the key came from
        credential_type: "api_key" / "oauth" / "pat"

    Returns:
        (mode_key, confidence_reason)
    """
    msg_lower = error_message.lower()

    if status_code is None:
        if "timeout" in msg_lower or "timed out" in msg_lower:
            return ("provider_down", "connection timeout")
        if "refused" in msg_lower or "reset" in msg_lower:
            return ("provider_down", "connection refused/reset")
        return ("unknown", f"no status code: {error_message[:60]}")

    if status_code == 401:
        body = error_message[:500].lower()
        # OAuth-specific hints
        if "token expired" in body or "expired token" in body:
            return ("expired_oauth", "response body says 'token expired'")
        if "invalid token" in body or "invalid access token" in body:
            return ("expired_oauth", "response body says 'invalid token'")
        if "refresh token" in body:
            return ("expired_oauth", "response body mentions refresh token")
        if credential_type == "oauth":
            return ("expired_oauth", "OAuth token returned 401, no specific body hint")
        # API key
        if "invalid" in body or "incorrect" in body:
            return ("wrong_key", "response body says 'invalid' or 'incorrect'")
        if "not found" in body:
            return ("wrong_key", "response body says 'not found'")
        return ("unknown", "401 with no classifier hints. Type: {credential_type}")

    if status_code == 403:
        body = error_message[:500].lower()
        if "no access" in body or "not authorized" in body or "permission" in body:
            return ("model_access", "403: no access to this model")
        if "billing" in body or "payment" in body:
            return ("quota_exhausted", "403: billing/payment issue")
        return ("model_access", "403 generic (likely model access)")

    if status_code == 429:
        body = error_message[:500].lower()
        if "quota" in body or "limit" in body:
            return ("quota_exhausted", "429: quota/limit exhaustion")
        return ("rate_limited", "429 generic rate limit")

    if status_code == 402:
        return ("quota_exhausted", "402: payment required")

    if 500 <= status_code < 600:
        return ("provider_down", f"{status_code} server error")

    return ("unknown", f"unhandled status code {status_code}")


# ── Credential sources scanner ────────────────────────────────────────


def scan_auth_json() -> list[dict]:
    """Read credential pool entries from auth.json."""
    entries = []
    if not AUTH_PATH.exists():
        return entries
    try:
        raw = json.loads(AUTH_PATH.read_text())
        pool = raw.get("credential_pool", {})
        if isinstance(pool, dict):
            for provider, creds in pool.items():
                if not isinstance(creds, list):
                    continue
                for entry in creds:
                    if not isinstance(entry, dict):
                        continue
                    expiry = entry.get("expiry")
                    status = entry.get("last_status", "unknown")
                    cooldown_until = entry.get("cooldown_until")
                    source = entry.get("source", "auth.json")
                    ctype = "oauth" if entry.get("refresh_token") else "api_key"
                    entries.append({
                        "provider": provider,
                        "source": source,
                        "type": ctype,
                        "status": status,
                        "expiry": expiry,
                        "cooldown_until": cooldown_until,
                        "has_refresh_token": bool(entry.get("refresh_token")),
                    })
        elif isinstance(pool, list):
            for entry in pool:
                if not isinstance(entry, dict):
                    continue
                provider = entry.get("provider", "unknown")
                expiry = entry.get("expiry")
                status = entry.get("last_status", "unknown")
                cooldown_until = entry.get("cooldown_until")
                source = entry.get("source", "auth.json")
                ctype = "oauth" if entry.get("refresh_token") else "api_key"
                entries.append({
                    "provider": provider,
                    "source": source,
                    "type": ctype,
                    "status": status,
                    "expiry": expiry,
                    "cooldown_until": cooldown_until,
                    "has_refresh_token": bool(entry.get("refresh_token")),
                })
    except Exception as exc:
        entries.append({"error": f"Failed to read auth.json: {exc}"})
    return entries


def scan_env_vars() -> list[dict]:
    """Find credential-related env vars."""
    patterns = [
        re.compile(r"^(.+)_API_KEY$"),
        re.compile(r"^(.+)_TOKEN$"),
        re.compile(r"^(.+)_ACCESS_TOKEN$"),
        re.compile(r"^(.+)_SECRET$"),
    ]
    entries = []
    for key, val in sorted(os.environ.items()):
        for pat in patterns:
            m = pat.match(key)
            if m:
                provider = m.group(1).lower()
                val_preview = val[:8] + "..." if len(val) > 12 else val
                entries.append({
                    "provider": provider,
                    "source": f"env:{key}",
                    "type": "api_key",
                    "value_preview": val_preview,
                    "value_length": len(val),
                })
                break
    return entries


def scan_oauth_files() -> list[dict]:
    """Scan OAuth credential files for Claude Code and Drewgent-native."""
    entries = []
    oauth_files = {
        "claude_code": DREW_HOME.parent / ".claude" / ".credentials.json",
        "drewgent_oauth": DREW_HOME / ".anthropic_oauth.json",
    }
    for name, path in oauth_files.items():
        if path.exists():
            try:
                data = json.loads(path.read_text())
                expiry = data.get("expiresAt") or data.get("expiry")
                entries.append({
                    "provider": "anthropic",
                    "source": name,
                    "type": "oauth",
                    "has_access_token": bool(data.get("accessToken")),
                    "has_refresh_token": bool(data.get("refreshToken")),
                    "expiry": expiry,
                })
            except Exception:
                pass
    return entries


def read_registry() -> dict:
    """Read the credential state registry."""
    if REGISTRY_PATH.exists():
        try:
            return json.loads(REGISTRY_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"entries": {}, "last_updated": None}


def write_registry(registry: dict):
    """Write the credential state registry atomically."""
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    registry["last_updated"] = datetime.now(timezone.utc).isoformat()
    tmp = REGISTRY_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(registry, indent=2, ensure_ascii=False))
    tmp.replace(REGISTRY_PATH)


def update_registry(failure_key: str, mode: str, evidence: str):
    """Record a credential failure in the persistent registry."""
    registry = read_registry()
    registry.setdefault("entries", {})
    now = datetime.now(timezone.utc).isoformat()
    if failure_key not in registry["entries"]:
        registry["entries"][failure_key] = {
            "first_seen": now,
            "last_seen": now,
            "count": 0,
        }
    entry = registry["entries"][failure_key]
    entry["last_seen"] = now
    entry["count"] = entry.get("count", 0) + 1
    entry["mode"] = mode
    entry["evidence"] = evidence
    entry["mode_info"] = FAILURE_MODES.get(mode, FAILURE_MODES["unknown"])
    write_registry(registry)


# ── Report generation ─────────────────────────────────────────────────


def generate_report() -> str:
    """Generate a structured credential health report."""
    registry = read_registry()
    now = datetime.now(timezone.utc)

    sections = []
    sections.append("# Credential Health Report")
    sections.append("")

    # 1. Current credentials
    sections.append("## Available Credentials")
    sources = scan_auth_json() + scan_env_vars() + scan_oauth_files()
    if not sources:
        sections.append("_No credentials found_")
    else:
        for s in sources:
            if "error" in s:
                sections.append(f"- ⚠️ {s['error']}")
                continue
            provider = s.get("provider", "?")
            source = s.get("source", "?")
            ctype = s.get("type", "?")
            status = s.get("status", "available")
            icon = "✅" if status == "ok" else "⚠️" if status == "error" else "❓"
            parts = [f"  Source: {source}", f"  Type: {ctype}"]
            if s.get("expiry"):
                parts.append(f"  Expiry: {s['expiry']}")
            if s.get("value_preview"):
                parts.append(f"  Key: {s['value_preview']}")
            if s.get("cooldown_until"):
                parts.append(f"  Cooldown until: {s['cooldown_until']}")
            sections.append(f"- {icon} **{provider}** ({status})")
            for p in parts:
                sections.append(f"  {p}")

    sections.append("")

    # 2. Registry: known failure states
    entries = registry.get("entries", {})
    sections.append(f"## Credential State Registry ({len(entries)} entries)")
    if entries:
        for key, entry in sorted(entries.items()):
            mode = entry.get("mode", "unknown")
            info = FAILURE_MODES.get(mode, FAILURE_MODES["unknown"])
            count = entry.get("count", 0)
            last = entry.get("last_seen", "?")[:19]
            sections.append(f"- ❌ **{key}**: {info['description']}")
            sections.append(f"  Action: {info['action']}")
            sections.append(f"  Seen: {last} | Count: {count}")
    else:
        sections.append("_No credential failures recorded_")

    sections.append("")
    sections.append(f"Last updated: {registry.get('last_updated', 'never')}")
    sections.append("")
    sections.append("---")
    sections.append("*Use `credential-diagnostic` to refresh this report. Run this script before starting a conversation to verify credential health.*")

    return "\n".join(sections)


def seed_registry_from_pool():
    """Seed credential registry with known failures from auth.json pool.

    Exhausted/expired pool entries are registered so the agent's per-turn
    credential-state injection shows which providers to avoid.
    """
    now = datetime.now(timezone.utc)
    for entry in scan_auth_json():
        if "error" in entry:
            continue
        provider = entry.get("provider", "?")
        status = entry.get("status", "unknown")
        expiry = entry.get("expiry")

        if status in ("error", "exhausted"):
            update_registry(f"pool:{provider}", "expired_api_key", f"pool status={status}")
        elif expiry:
            try:
                exp = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
                if exp < now:
                    update_registry(f"pool:{provider}", "expired_api_key", f"expired at {expiry}")
            except (ValueError, AttributeError):
                pass


def main():
    seed_registry_from_pool()
    report = generate_report()
    print(report)


if __name__ == "__main__":
    main()
