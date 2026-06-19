"""Lightweight CronAgent factory — minimal-overhead AIAgent for cron jobs.

Skips brain signals, session persistence, and monitor setup that are
unnecessary for automated scheduled tasks. Reduces per-job init cost
and eliminates ~1.2 MB of session log + request dump files per run.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def create_cron_agent(
    model: str = "",
    api_key: str = None,
    base_url: str = None,
    provider: str = None,
    api_mode: str = None,
    max_iterations: int = 90,
    reasoning_config: Optional[Dict[str, Any]] = None,
    prefill_messages: Optional[List[Dict[str, Any]]] = None,
    providers_allowed: Optional[List[str]] = None,
    providers_ignored: Optional[List[str]] = None,
    providers_order: Optional[List[str]] = None,
    provider_sort: str = None,
    session_id: str = "",
    session_db=None,
    **kwargs,
):
    """Create an AIAgent configured for cron job execution.

    Compared to a default AIAgent, this:
    - Skips brain signal processor + awareness reporter init
    - Skips brain monitor (no Discord delivery attempts)
    - Skips session JSON log file creation
    - Skips SQLite session persistence
    - Skips checkpoint manager
    - Disables interactive toolsets (cronjob, messaging, clarify)
    - Enables quiet mode and skips memory

    Returns:
        AIAgent instance ready for run_conversation() / chat()
    """
    from run_agent import AIAgent

    return AIAgent(
        model=model,
        api_key=api_key,
        base_url=base_url,
        provider=provider,
        api_mode=api_mode,
        max_iterations=max_iterations,
        reasoning_config=reasoning_config,
        prefill_messages=prefill_messages,
        providers_allowed=providers_allowed,
        providers_ignored=providers_ignored,
        providers_order=providers_order,
        provider_sort=provider_sort,
        disabled_toolsets=["cronjob", "messaging", "clarify"],
        quiet_mode=True,
        skip_memory=True,
        skip_brain_signals=True,
        skip_session=True,
        platform="cron",
        session_id=session_id,
        session_db=session_db,
        **kwargs,
    )
