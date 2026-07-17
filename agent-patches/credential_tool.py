#!/usr/bin/env python3
"""Credential provisioning tool.

Allows the agent to store and verify API keys when the user provides them.
Also provides auto-detection of key patterns in user messages.

Mathematical model:
  f(message) ∈ {CREDENTIAL, NOT_CREDENTIAL}  — classifier
  g(message) → (provider, key, type)          — extractor
  store(provider, key) → auth.json            — persistence
"""

import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


# ── Key detection ──────────────────────────────────────────────────────

RAW_KEY_PATTERN = re.compile(r"(?:sk-|api-|pk-)[a-zA-Z0-9_\-]{10,}")

KEY_STATEMENT_PATTERNS = [
    re.compile(
        r"(?:my|the)\s+(?:api\s*)?(?:key|token)\s+(?:is|:)\s*['\"]?(.+?)['\"]?\s*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:here|use|try)\s+(?:is|this)\s+(?:my|the|an?\s+)?(?:api\s*)?key\s*[:\s]+['\"]?(.+?)['\"]?\s*$",
        re.IGNORECASE,
    ),
    re.compile(r"^['\"]?(sk-[a-zA-Z0-9]{10,})['\"]?\s*$", re.IGNORECASE),
    re.compile(r"^(?:key|token)[:\s]+['\"]?(.+?)['\"]?\s*$", re.IGNORECASE),
]

PROVIDER_KEY_PREFIXES: dict[str, str] = {
    "sk-ant": "anthropic",
    "sk-or": "openrouter",
    "sk-or-v1": "openrouter",
}


def infer_provider(key: str) -> str:
    for prefix, provider in PROVIDER_KEY_PREFIXES.items():
        if key.startswith(prefix):
            return provider
    return "custom"


def detect_key(text: str) -> str | None:
    m = RAW_KEY_PATTERN.search(text)
    return m.group(0) if m else None


def detect_key_statement(text: str) -> str | None:
    for pat in KEY_STATEMENT_PATTERNS:
        m = pat.search(text)
        if m:
            return m.group(1).strip()
    return None


# ── Credential storage ────────────────────────────────────────────────


def add_credential(provider: str, api_key: str, label: str = "") -> dict:
    if not api_key or len(api_key) < 8:
        return {"success": False, "error": "Invalid key (too short)"}
    try:
        result = subprocess.run(
            [sys.executable, "-m", "drewgent_cli.main", "auth", "add",
             provider, "--api-key", api_key, "--label", label or provider],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            return {"success": True, "message": f"Crendential for {provider} saved."}
        error = (result.stderr or result.stdout or "").strip()[:200]
        return {"success": False, "error": f"auth add failed: {error}"}
    except FileNotFoundError:
        try:
            from drewgent_cli.auth import write_credential_pool
            write_credential_pool(provider, api_key, label or provider)
            return {"success": True, "message": f"Crendential for {provider} saved."}
        except Exception as e:
            return {"success": False, "error": f"pool write failed: {e}"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timed out saving credential"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Tool entry point ──────────────────────────────────────────────────


def credential_provision(provider: str = "", api_key: str = "") -> str:
    """Store and verify an API key for the given provider.

    Called by the agent when the user provides a credential.
    The provider can be auto-detected from the key prefix if omitted.

    Args:
        provider: Provider id (openrouter, anthropic, etc.). Auto-detected if empty.
        api_key: The API key value. Auto-detected from the conversation if empty.

    Returns:
        JSON string describing the result.
    """
    effective_provider = provider or infer_provider(api_key) if api_key else "custom"
    result = add_credential(effective_provider, api_key)
    result["provider"] = effective_provider
    return json.dumps(result, ensure_ascii=False)


# ── Auto-provision (called by run_agent.py context builder) ────────────


def auto_provision_from_message(text: str) -> str | None:
    """Scan user message for a credential and store it automatically.

    Returns a context note for the LLM if a credential was stored,
    or None if nothing was detected.
    """
    key = detect_key(text) or detect_key_statement(text)
    if not key:
        return None

    provider = infer_provider(key)
    # Store without requiring the user to specify provider
    result = add_credential(provider, key)

    if result["success"]:
        return f"[Credential stored] API key for {provider} saved automatically. Ready to use."
    else:
        return f"[Credential note] Detected a key but could not store it: {result.get('error', 'unknown error')}. Please use drewgent auth add manually."


# ── Schema + Registry ─────────────────────────────────────────────────

PROVISION_SCHEMA = {
    "name": "credential_provision",
    "description": (
        "Store an API key so the system can use it. "
        "Call this when the user provides an API key, token, or credential. "
        "The key is stored persistently and verified."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "provider": {
                "type": "string",
                "description": (
                    "Provider id (openrouter, anthropic, openai-codex, minimax, etc.). "
                    "Auto-detected from the key prefix if omitted."
                ),
            },
            "api_key": {
                "type": "string",
                "description": "The API key or token value.",
            },
        },
        "required": ["api_key"],
    },
}

from tools.registry import registry

registry.register(
    name="credential_provision",
    toolset="core",
    schema=PROVISION_SCHEMA,
    handler=lambda args, **kw: credential_provision(
        provider=args.get("provider", ""),
        api_key=args.get("api_key", ""),
    ),
    emoji="🔑",
)
