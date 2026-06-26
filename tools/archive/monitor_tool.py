#!/usr/bin/env python3
"""
Monitor Tool Module

Provides Claude Code-style pattern matching monitors for background processes.
When a regex pattern matches process output, an event is pushed to the
completion_queue to trigger agent wake-up.

Usage:
    from tools.monitor_tool import monitor_handler

    # Add a monitor
    result = monitor_handler({"action": "add", "session_id": "proc_xxx", "pattern": "error|Error"})

    # List monitors
    result = monitor_handler({"action": "list"})

    # Cancel a monitor
    result = monitor_handler({"action": "cancel", "monitor_id": "mon_xxx"})
"""

import json
import logging
from typing import Any, Dict

from tools.registry import registry
from tools.process_registry import process_registry

logger = logging.getLogger(__name__)


# Tool schema for OpenAI function calling
MONITOR_SCHEMA = {
    "name": "monitor",
    "description": (
        "Monitor background process output for regex patterns (Claude Code-style). "
        "Actions: 'add' (start monitoring stdout for a regex match), "
        "'list' (show active monitors), 'cancel' (stop a monitor). "
        "When a pattern matches, an event is pushed to wake up the agent."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "list", "cancel"],
                "description": "Monitor action to perform"
            },
            "session_id": {
                "type": "string",
                "description": "Process session ID to monitor (required for 'add' action)"
            },
            "pattern": {
                "type": "string",
                "description": "Regex pattern to match against process output (required for 'add' action)"
            },
            "once": {
                "type": "boolean",
                "description": "If true, stop monitoring after first match (default: false, keep monitoring)"
            },
            "monitor_id": {
                "type": "string",
                "description": "Monitor ID to cancel (required for 'cancel' action)"
            }
        },
        "required": ["action"]
    }
}


def monitor_handler(args: dict) -> str:
    """
    Handle monitor tool invocations.

    Args:
        args: dict with action and parameters

    Returns:
        JSON string with result
    """
    action = args.get("action", "")

    if action == "add":
        session_id = args.get("session_id", "")
        pattern = args.get("pattern", "")

        if not session_id:
            return json.dumps({"error": "session_id is required for add action"}, ensure_ascii=False)

        if not pattern:
            return json.dumps({"error": "pattern is required for add action"}, ensure_ascii=False)

        once = args.get("once", False)

        result = process_registry.add_monitor(session_id, pattern, once=once)
        return json.dumps(result, ensure_ascii=False)

    elif action == "list":
        session_id = args.get("session_id")
        monitors = process_registry.list_monitors(session_id=session_id)
        return json.dumps({"monitors": monitors}, ensure_ascii=False)

    elif action == "cancel":
        monitor_id = args.get("monitor_id", "")

        if not monitor_id:
            return json.dumps({"error": "monitor_id is required for cancel action"}, ensure_ascii=False)

        result = process_registry.cancel_monitor(monitor_id)
        return json.dumps(result, ensure_ascii=False)

    else:
        return json.dumps({
            "error": f"Unknown monitor action: {action}. Use: add, list, cancel"
        }, ensure_ascii=False)


# Register the tool at module level
registry.register(
    name="monitor",
    toolset="system",
    schema=MONITOR_SCHEMA,
    handler=monitor_handler,
    check_fn=None,
    requires_env=[],
    is_async=False,
    description="Monitor background process output for regex patterns",
    emoji="📊",
)
