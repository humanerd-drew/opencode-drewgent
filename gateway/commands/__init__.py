"""
Gateway Commands - Command handlers extracted from run.py

This module contains command handlers for the Drewgent Gateway.
Each command handler is a separate module for maintainability.

Base Classes:
    - CommandHandler: Abstract base for all command handlers

Extracted Commands:
    - admin: stop, status, help, commands
    - session: reset, resume, branch, title
    - config: model, provider, personality, voice
    - memory: brain, compress
    - rollback: checkpoint rollback
    - background: background, btw

Watchers (background tasks):
    - watchers: SessionExpiryWatcher, PlatformReconnectWatcher, etc.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

# Re-export MessageEvent for convenience
from gateway.platforms.base import MessageEvent


class CommandHandler(ABC):
    """Abstract base class for gateway command handlers.

    All command handlers should inherit from this class and implement
    the handle() method.
    """

    # Command name (e.g., "stop", "model", "reset")
    command_name: str = ""

    # Short help text shown in /help
    help_text: str = ""

    @abstractmethod
    async def handle(self, event: MessageEvent, runner: Any) -> Optional[str]:
        """Handle a command event.

        Args:
            event: The message event containing the command
            runner: Reference to GatewayRunner for state access

        Returns:
            Response string to send back, or None for no response
        """
        pass

    def can_handle(self, event: MessageEvent) -> bool:
        """Check if this handler can handle the given event."""
        command = event.get_command_name().lower()
        return command == self.command_name.lower()


# Convenience re-exports for external use
__all__ = [
    "CommandHandler",
    # Admin commands
    "HelpCommand",
    "StatusCommand",
    "StopCommand",
    "CommandsListCommand",
    # Session commands
    "ResetCommand",
    "ResumeCommand",
    "BranchCommand",
    "TitleCommand",
    # Config commands
    "ModelCommand",
    "ProviderCommand",
    "PersonalityCommand",
    "VoiceCommand",
    # Memory commands
    "BrainCommand",
    "CompressCommand",
    # Rollback
    "RollbackCommand",
    # Background
    "BackgroundCommand",
    "BtwCommand",
    # Watchers
    "SessionExpiryWatcher",
    "PlatformReconnectWatcher",
    "PendingWatcherDrain",
    "ProcessWatcher",
]

# Import all handlers for convenience
from gateway.commands.admin import (
    HelpCommand,
    StatusCommand,
    StopCommand,
    CommandsListCommand,
)
from gateway.commands.session import (
    ResetCommand,
    ResumeCommand,
    BranchCommand,
    TitleCommand,
)
from gateway.commands.config import (
    ModelCommand,
    ProviderCommand,
    PersonalityCommand,
    VoiceCommand,
)
from gateway.commands.memory import BrainCommand, CompressCommand
from gateway.commands.rollback import RollbackCommand
from gateway.commands.background import BackgroundCommand, BtwCommand
from gateway.commands.watchers import (
    SessionExpiryWatcher,
    PlatformReconnectWatcher,
    PendingWatcherDrain,
    ProcessWatcher,
)
