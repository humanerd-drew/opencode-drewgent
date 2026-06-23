"""
Memory Commands - brain, compress

Extracted from gateway/run.py for maintainability.

Handlers:
    - BrainCommand: /brain
    - CompressCommand: /compress
"""

from typing import Optional, TYPE_CHECKING

from gateway.commands import CommandHandler

if TYPE_CHECKING:
    from gateway.run import GatewayRunner


class BrainCommand(CommandHandler):
    """Handle /brain command - manage brain/memory settings."""

    command_name = "brain"
    help_text = "Manage brain/memory settings"

    async def handle(self, event, runner: "GatewayRunner") -> Optional[str]:
        """Handle /brain command."""
        return await runner._handle_brain_command(event)


class CompressCommand(CommandHandler):
    """Handle /compress command - compress conversation context."""

    command_name = "compress"
    help_text = "Compress conversation context"

    async def handle(self, event, runner: "GatewayRunner") -> Optional[str]:
        """Handle /compress command."""
        return await runner._handle_compress_command(event)


__all__ = [
    "BrainCommand",
    "CompressCommand",
]
