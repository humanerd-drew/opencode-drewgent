"""
Session Commands - reset, resume, branch, title

Extracted from gateway/run.py for maintainability.

NOTE: These handlers are tightly coupled to GatewayRunner (self references).
Full extraction requires significant refactoring of command dispatch.
This module documents the handler structure.

Handlers:
    - ResetCommand: /reset, /new
    - ResumeCommand: /resume
    - BranchCommand: /branch
    - TitleCommand: /title
"""

from typing import Optional, TYPE_CHECKING

from gateway.commands import CommandHandler

if TYPE_CHECKING:
    from gateway.run import GatewayRunner


class ResetCommand(CommandHandler):
    """Handle /reset or /new command - reset conversation context."""

    command_name = "reset"
    aliases = ["new"]
    help_text = "Reset conversation context"

    async def handle(self, event, runner: "GatewayRunner") -> Optional[str]:
        """Handle /reset command.

        Dependencies:
            - runner.session_store
            - runner._evict_cached_agent()
            - runner._async_flush_memories()
            - runner._session_key_for_source()
            - runner._session_model_overrides
            - runner.hooks.emit()
            - runner._background_tasks
        """
        # TODO: Full extraction requires:
        # 1. Moving session_store management to separate SessionManager
        # 2. Moving hooks to separate HookManager
        # 3. Creating command context object to pass dependencies

        # For now, delegate to runner
        return await runner._handle_reset_command(event)


class ResumeCommand(CommandHandler):
    """Handle /resume command - resume a previous session."""

    command_name = "resume"
    help_text = "Resume a previous session"

    async def handle(self, event, runner: "GatewayRunner") -> Optional[str]:
        """Handle /resume command."""
        return await runner._handle_resume_command(event)


class BranchCommand(CommandHandler):
    """Handle /branch command - create a branch of conversation."""

    command_name = "branch"
    help_text = "Create a branch of current conversation"

    async def handle(self, event, runner: "GatewayRunner") -> Optional[str]:
        """Handle /branch command."""
        return await runner._handle_branch_command(event)


class TitleCommand(CommandHandler):
    """Handle /title command - set session title."""

    command_name = "title"
    help_text = "Set session title"

    async def handle(self, event, runner: "GatewayRunner") -> Optional[str]:
        """Handle /title command."""
        return await runner._handle_title_command(event)


__all__ = [
    "ResetCommand",
    "ResumeCommand",
    "BranchCommand",
    "TitleCommand",
]
