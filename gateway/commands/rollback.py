"""
Rollback Command - checkpoint rollback

Extracted from gateway/run.py for maintainability.

Handler:
    - RollbackCommand: /rollback
"""

from typing import Optional, TYPE_CHECKING

from gateway.commands import CommandHandler

if TYPE_CHECKING:
    from gateway.run import GatewayRunner


class RollbackCommand(CommandHandler):
    """Handle /rollback command - list or restore filesystem checkpoints.

    Features:
        - /rollback - list available checkpoints
        - /rollback <number> - restore by number
        - /rollback <hash> - restore by commit hash
    """

    command_name = "rollback"
    help_text = "Rollback to checkpoint"

    async def handle(self, event, runner: "GatewayRunner") -> Optional[str]:
        """Handle /rollback command."""
        return await runner._handle_rollback_command(event)


__all__ = [
    "RollbackCommand",
]
