"""Super Tool — a simple test tool that does nothing useful."""

import json
from tools.registry import registry


def check_requirements() -> bool:
    """Super tool has no external requirements -- always available."""
    return True


def super_tool(message: str = "Hello from super_tool!", task_id: str = None) -> str:
    """Echo back a message with a timestamp."""
    import datetime
    now = datetime.datetime.now().isoformat()
    return json.dumps({
        "success": True,
        "tool": "super_tool",
        "message": message,
        "timestamp": now,
    })


registry.register(
    name="super_tool",
    toolset="super",
    schema={
        "name": "super_tool",
        "description": "A simple test tool that echoes a message back with a timestamp.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The message to echo back.",
                    "default": "Hello from super_tool!",
                },
            },
            "required": [],
        },
    },
    handler=lambda args, **kw: super_tool(
        message=args.get("message", "Hello from super_tool!"),
        task_id=kw.get("task_id"),
    ),
    check_fn=check_requirements,
    requires_env=[],
    is_async=False,
    description="A simple test tool that echoes a message back with a timestamp.",
    emoji="⚡",
)