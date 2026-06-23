"""
Admin Commands - stop, status, help, commands

Extracted from gateway/run.py for maintainability.
"""

from typing import Optional, TYPE_CHECKING

from gateway.commands import CommandHandler

if TYPE_CHECKING:
    from gateway.run import GatewayRunner


class HelpCommand(CommandHandler):
    """Handle /help command - show available commands."""

    command_name = "help"
    help_text = "Show this help message"

    async def handle(self, event, runner: "GatewayRunner") -> Optional[str]:
        """Handle /help command."""
        # Build help text
        lines = [
            "**Drewgent Gateway Commands**",
            "",
            "**Session Management**",
            "  /reset — Reset conversation context",
            "  /resume — Resume a previous session",
            "  /branch — Create a branch of current conversation",
            "  /title — Set session title",
            "",
            "**Configuration**",
            "  /model — Switch AI model",
            "  /provider — Switch AI provider",
            "  /personality — Change agent personality",
            "  /voice — Configure voice mode",
            "",
            "**Memory & Context**",
            "  /brain — Manage brain/memory settings",
            "  /compress — Compress conversation context",
            "  /rollback — Rollback to checkpoint",
            "",
            "**Background Tasks**",
            "  /background — Run task in background",
            "  /btw — Run 'by the way' thought",
            "",
            "**Admin**",
            "  /status — Show gateway status",
            "  /stop — Stop the gateway",
            "",
        ]

        # Add reasoning commands if enabled
        if hasattr(runner, "_show_reasoning") and runner._show_reasoning:
            lines.extend(
                [
                    "**Reasoning**",
                    "  /reasoning — Toggle reasoning display",
                    "  /yolo — Run without safety checks",
                    "",
                ]
            )

        lines.extend(
            [
                "**Utilities**",
                "  /usage — Show API usage stats",
                "  /insights — Show conversation insights",
                "  /profile — Manage profiles",
                "  /retry — Retry last message",
                "  /undo — Undo last agent action",
                "  /verbose — Toggle verbose output",
                "  /approve — Approve pending action",
                "  /deny — Deny pending action",
                "  /update — Check for updates",
                "  /reload-mcp — Reload MCP servers",
            ]
        )

        return "\n".join(lines)


class StatusCommand(CommandHandler):
    """Handle /status command - show gateway status."""

    command_name = "status"
    help_text = "Show gateway status"

    async def handle(self, event, runner: "GatewayRunner") -> Optional[str]:
        """Handle /status command."""
        from datetime import datetime

        status_parts = [
            "**Gateway Status**",
            f"  Running: {runner._running}",
            f"  Adapters: {len(runner.adapters)}",
        ]

        if runner._running:
            uptime_seconds = (datetime.now() - runner._start_time).total_seconds()
            hours, remainder = divmod(int(uptime_seconds), 3600)
            minutes, seconds = divmod(remainder, 60)
            status_parts.append(f"  Uptime: {hours}h {minutes}m {seconds}s")

        status_parts.append(f"  Active sessions: {len(runner.session_store._sessions)}")

        # Add platform info
        if runner.adapters:
            status_parts.append("  Platforms:")
            for platform in runner.adapters:
                status_parts.append(f"    - {platform.value}")

        return "\n".join(status_parts)


class StopCommand(CommandHandler):
    """Handle /stop command - stop the gateway."""

    command_name = "stop"
    help_text = "Stop the gateway"

    async def handle(self, event, runner: "GatewayRunner") -> Optional[str]:
        """Handle /stop command."""
        if runner._running:
            runner._exit_cleanly = True
            # Schedule shutdown
            import asyncio

            asyncio.create_task(runner.stop())
            return "🛑 Gateway shutdown initiated..."
        return "Gateway is not running"


class CommandsListCommand(CommandHandler):
    """Handle /commands command - list all commands."""

    command_name = "commands"
    help_text = "List all available commands"

    async def handle(self, event, runner: "GatewayRunner") -> Optional[str]:
        """Handle /commands command."""
        # This is similar to /help but more concise
        commands = [
            "reset",
            "resume",
            "branch",
            "title",
            "model",
            "provider",
            "personality",
            "voice",
            "brain",
            "compress",
            "rollback",
            "background",
            "btw",
            "status",
            "stop",
            "help",
            "commands",
            "reasoning",
            "yolo",
            "verbose",
            "retry",
            "undo",
            "usage",
            "insights",
            "profile",
            "approve",
            "deny",
            "update",
            "reload-mcp",
        ]

        return "Available commands: " + ", ".join(f"/{cmd}" for cmd in sorted(commands))


__all__ = [
    "HelpCommand",
    "StatusCommand",
    "StopCommand",
    "CommandsListCommand",
]
