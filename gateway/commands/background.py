"""
Background Commands - background, btw

Extracted from gateway/run.py for maintainability.

Handlers:
    - BackgroundCommand: /background
    - BtwCommand: /btw
"""

from typing import Optional, TYPE_CHECKING

from gateway.commands import CommandHandler

if TYPE_CHECKING:
    from gateway.run import GatewayRunner


class BackgroundCommand(CommandHandler):
    """Handle /background command - run a task in background.

    Spawns a new AIAgent in a background thread with its own session.
    When it completes, sends the result back to the same chat.
    """

    command_name = "background"
    help_text = "Run a task in background"

    async def handle(self, event, runner: "GatewayRunner") -> Optional[str]:
        """Handle /background command."""
        return await runner._handle_background_command(event)


class BtwCommand(CommandHandler):
    """Handle /btw command - run 'by the way' thought.

    Runs a prompt in the background without disrupting the current session.
    """

    command_name = "btw"
    help_text = "Run 'by the way' thought"

    async def handle(self, event, runner: "GatewayRunner") -> Optional[str]:
        """Handle /btw command."""
        return await runner._handle_btw_command(event)


__all__ = [
    "BackgroundCommand",
    "BtwCommand",
]
