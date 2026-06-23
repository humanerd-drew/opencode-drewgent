"""
Nous Portal provider for auxiliary client.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

from openai import OpenAI

from .base import BaseProvider, ProviderResult

logger = logging.getLogger(__name__)

_NOUS_MODEL = "google/gemini-3-flash-preview"
_NOUS_DEFAULT_BASE_URL = "https://inference-api.nousresearch.com/v1"
_AUTH_JSON_PATH = None  # Initialized lazily


def _get_auth_json_path():
    global _AUTH_JSON_PATH
    if _AUTH_JSON_PATH is None:
        from drewgent_constants import get_drewgent_home
        _AUTH_JSON_PATH = get_drewgent_home() / "auth.json"
    return _AUTH_JSON_PATH


def _read_nous_auth() -> Optional[dict]:
    """Read and validate ~/.drewgent/auth.json for an active Nous provider."""
    pool_present, entry = _select_pool_entry("nous")
    if pool_present:
        if entry is None:
            return None
        return {
            "access_token": getattr(entry, "access_token", ""),
            "refresh_token": getattr(entry, "refresh_token", None),
            "agent_key": getattr(entry, "agent_key", None),
            "inference_base_url": _pool_runtime_base_url(entry, _NOUS_DEFAULT_BASE_URL),
            "portal_base_url": getattr(entry, "portal_base_url", None),
            "client_id": getattr(entry, "client_id", None),
            "scope": getattr(entry, "scope", None),
            "token_type": getattr(entry, "token_type", "Bearer"),
            "source": "pool",
        }

    try:
        auth_path = _get_auth_json_path()
        if not auth_path.is_file():
            return None
        data = json.loads(auth_path.read_text())
        if data.get("active_provider") != "nous":
            return None
        provider = data.get("providers", {}).get("nous", {})
        if not provider.get("agent_key") and not provider.get("access_token"):
            return None
        return provider
    except Exception as exc:
        logger.debug("Could not read Nous auth: %s", exc)
        return None


def _select_pool_entry(provider: str) -> tuple:
    try:
        from agent.credential_pool import load_pool
        pool = load_pool(provider)
    except Exception:
        return False, None
    if not pool or not pool.has_credentials():
        return False, None
    try:
        return True, pool.select()
    except Exception:
        return True, None


def _pool_runtime_api_key(entry: Any) -> str:
    if entry is None:
        return ""
    return str(getattr(entry, "runtime_api_key", None) or getattr(entry, "access_token", "") or "").strip()


def _pool_runtime_base_url(entry: Any, fallback: str = "") -> str:
    if entry is None:
        return str(fallback or "").strip().rstrip("/")
    url = (
        getattr(entry, "runtime_base_url", None)
        or getattr(entry, "inference_base_url", None)
        or getattr(entry, "base_url", None)
        or fallback
    )
    return str(url or "").strip().rstrip("/")


def _nous_api_key(provider: dict) -> str:
    return provider.get("agent_key") or provider.get("access_token", "")


def _nous_base_url() -> str:
    return os.getenv("NOUS_INFERENCE_BASE_URL", _NOUS_DEFAULT_BASE_URL)


class NousProvider(BaseProvider):
    """Nous Portal provider."""

    name = "nous"
    label = "Nous Portal"

    def try_create(self) -> ProviderResult:
        from openai import OpenAI as OAI

        nous = _read_nous_auth()
        if not nous:
            return ProviderResult(client=None, model=None, available=False)

        logger.debug("Auxiliary client: Nous Portal")
        model = "gemini-3-flash" if nous.get("source") == "pool" else _NOUS_MODEL
        return ProviderResult(
            client=OAI(
                api_key=_nous_api_key(nous),
                base_url=str(nous.get("inference_base_url") or _nous_base_url()).rstrip("/"),
            ),
            model=model,
            available=True,
        )
