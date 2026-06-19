"""
Kanban Notify Hook — delivers kanban task notifications to platform subscribers.

On gateway:startup: stores adapter references in a global registry.
On agent:end: checks if the response contains kanban task results and sends
  notifications to the original platform+chat where the task was created.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger("hooks.kanban-notify")

# Global adapter registry — populated at gateway:startup
_kanban_adapters: dict = {}
_kanban_loop: Optional[asyncio.AbstractEventLoop] = None


def handle(event_type: str, context: dict) -> None:
    """
    Single entry point for all kanban-notify events.
    Routes to the appropriate handler based on event type.
    """
    if event_type == "gateway:startup":
        _handle_gateway_startup(event_type, context)
    elif event_type == "agent:end":
        _handle_agent_end(event_type, context)


# ---------------------------------------------------------------------------
# gateway:startup handler
# ---------------------------------------------------------------------------

def _handle_gateway_startup(event_type: str, context: dict) -> None:
    """
    Called at gateway:startup. Stores adapter references so we can use them
    in the agent:end handler (which fires in the async message-handling loop).

    Context keys:
      - adapters: dict mapping Platform → BasePlatformAdapter instance
      - loop: asyncio event loop
    """
    global _kanban_adapters, _kanban_loop

    adapters = context.get("adapters")
    loop = context.get("loop")

    if adapters:
        _kanban_adapters = adapters
        logger.info("kanban-notify: registered %d live adapters", len(adapters))
    if loop:
        _kanban_loop = loop
        logger.info("kanban-notify: registered event loop")

    if not adapters and not loop:
        logger.debug("kanban-notify: no adapters/loop in startup context")


# ---------------------------------------------------------------------------
# agent:end handler
# ---------------------------------------------------------------------------

def _handle_agent_end(event_type: str, context: dict) -> None:
    """
    Called at agent:end. Parses the agent response for kanban task results
    (completed/blocked/crashed) and sends notifications to subscribers.

    Context keys:
      - platform: platform name (e.g. "discord")
      - session_id: session identifier
      - response: the agent's final response text (first 500 chars)
    """
    global _kanban_adapters, _kanban_loop

    if not _kanban_adapters:
        logger.debug("kanban-notify: no adapters registered, skipping")
        return

    response = context.get("response", "")
    if not response:
        return

    # Parse task results from agent response
    task_results = _parse_task_results(response)
    if not task_results:
        return

    logger.info("kanban-notify: found %d task result(s) in agent response", len(task_results))

    for task_id, event_kind, result_text in task_results:
        _notify_async(task_id, event_kind, result_text, context)


# ---------------------------------------------------------------------------
# Parse agent response for kanban task results
# ---------------------------------------------------------------------------

def _parse_task_results(response: str) -> list[tuple[str, str, str]]:
    """
    Parse the agent response text for kanban task result indicators.

    Looks for patterns like:
      - ✅ Completed: t_abc123def456 — Summary of work
      - 🔴 Blocked: t_abc123def456 — reason for blocking
      - ❌ Crashed: t_abc123def456 — error summary

    Returns list of (task_id, event_kind, result_text).
    """
    results = []
    import re

    patterns = [
        (r"✅\s*Completed:\s*(t_[0-9a-f]{12})(?:\s*[-—]\s*(.+))?", "completed"),
        (r"🔴\s*Blocked:\s*(t_[0-9a-f]{12})(?:\s*[-—]\s*(.+))?", "blocked"),
        (r"❌\s*Crashed:\s*(t_[0-9a-f]{12})(?:\s*[-—]\s*(.+))?", "crashed"),
        (r"🔄\s*Unblocked:\s*(t_[0-9a-f]{12})(?:\s*[-—]\s*(.+))?", "unblocked"),
    ]

    for pattern, event_kind in patterns:
        for match in re.finditer(pattern, response, re.IGNORECASE):
            task_id = match.group(1).strip()
            result_text = match.group(2).strip() if match.group(2) else ""
            results.append((task_id, event_kind, result_text))

    return results


# ---------------------------------------------------------------------------
# Async notification via live adapters
# ---------------------------------------------------------------------------

def _notify_async(task_id: str, event_kind: str, result_text: str, context: dict) -> None:
    """
    Dispatch notification to subscribers via live adapters.
    Runs in the gateway's async loop to avoid blocking.
    """
    global _kanban_loop

    if not _kanban_loop:
        logger.debug("kanban-notify: no event loop, skipping notify")
        return

    loop = _kanban_loop
    asyncio.run_coroutine_threadsafe(
        _do_notify(task_id, event_kind, result_text, context),
        loop,
    )


async def _do_notify(task_id: str, event_kind: str, result_text: str, context: dict) -> None:
    """
    Async send to subscribers. Looks up their platform/chat_id and sends
    the notification message via the live adapter.
    """
    from tools.drewgent_kanban_db import notify_list

    platform_name = context.get("platform", "discord")
    subscribers = notify_list(task_id)

    if not subscribers:
        logger.debug("kanban-notify: no subscribers for task %s", task_id)
        return

    # Map platform name to Platform enum key
    platform_map = {
        "discord": "DISCORD",
        "telegram": "TELEGRAM",
        "slack": "SLACK",
        "whatsapp": "WHATSAPP",
        "signal": "SIGNAL",
        "matrix": "MATRIX",
    }
    platform_key = platform_map.get(platform_name.lower(), platform_name.upper())
    adapter = _kanban_adapters.get(platform_key)

    if not adapter:
        logger.warning("kanban-notify: no adapter for platform %s", platform_key)
        return

    # Build notification message
    event_icons = {
        "completed": "✅",
        "blocked": "🔴",
        "crashed": "❌",
        "unblocked": "🔄",
    }
    icon = event_icons.get(event_kind, "📋")
    title = f"{icon} Task {event_kind.capitalize()}: `{task_id}`"
    body = result_text[:200] if result_text else f"Kanban task {task_id} was marked as {event_kind}."
    message = f"{title}\n{body}"

    # Send to each subscriber
    for sub in subscribers:
        chat_id = sub.get("chat_id")
        thread_id = sub.get("thread_id")
        if not chat_id:
            continue

        metadata = {"thread_id": thread_id} if thread_id else None
        try:
            await adapter.send(chat_id, message, metadata=metadata)
            logger.info("kanban-notify: sent %s notification for %s to %s", event_kind, task_id, chat_id)
        except Exception as e:
            logger.warning("kanban-notify: failed to send %s notification for %s: %s", event_kind, task_id, e)