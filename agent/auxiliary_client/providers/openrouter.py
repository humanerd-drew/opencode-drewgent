"""
OpenRouter provider for auxiliary client.
"""

import logging
import os
from typing import Optional, Tuple, Any

from openai import OpenAI

from .base import BaseProvider, ProviderResult
from ..constants import OPENROUTER_BASE_URL, _OR_HEADERS, _OPENROUTER_MODEL

logger = logging.getLogger(__name__)


def _select_pool_entry(provider: str) -> Tuple[bool, Optional[Any]]:
    """Return (pool_exists_for_provider, selected_entry)."""
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
    key = getattr(entry, "runtime_api_key", None) or getattr(entry, "access_token", "")
    return str(key or "").strip()


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


class OpenRouterProvider(BaseProvider):
    """OpenRouter provider."""

    name = "openrouter"
    label = "OpenRouter"

    def try_create(self) -> ProviderResult:
        pool_present, entry = _select_pool_entry("openrouter")
        if pool_present:
            or_key = _pool_runtime_api_key(entry)
            if not or_key:
                return ProviderResult(client=None, model=None, available=False)
            base_url = _pool_runtime_base_url(entry, OPENROUTER_BASE_URL) or OPENROUTER_BASE_URL
            logger.debug("Auxiliary client: OpenRouter via pool")
            return ProviderResult(
                client=OpenAI(api_key=or_key, base_url=base_url, default_headers=_OR_HEADERS),
                model=_OPENROUTER_MODEL,
                available=True,
            )

        or_key = os.getenv("OPENROUTER_API_KEY")
        if not or_key:
            return ProviderResult(client=None, model=None, available=False)

        logger.debug("Auxiliary client: OpenRouter")
        return ProviderResult(
            client=OpenAI(api_key=or_key, base_url=OPENROUTER_BASE_URL, default_headers=_OR_HEADERS),
            model=_OPENROUTER_MODEL,
            available=True,
        )
