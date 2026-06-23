"""
Configuration Commands - model, provider, personality, voice

Extracted from gateway/run.py for maintainability.

NOTE: These handlers are tightly coupled to GatewayRunner.
Full extraction requires significant refactoring.

Handlers:
    - ModelCommand: /model
    - ProviderCommand: /provider
    - PersonalityCommand: /personality
    - VoiceCommand: /voice
"""

from typing import Optional, TYPE_CHECKING

from gateway.commands import CommandHandler

if TYPE_CHECKING:
    from gateway.run import GatewayRunner


class ModelCommand(CommandHandler):
    """Handle /model command - switch AI model.

    Features:
        - /model - interactive picker (Telegram/Discord) or text list
        - /model <name> - switch for this session only
        - /model <name> --global - switch and persist to config.yaml
        - /model <name> --provider <provider> - switch provider + model
        - /model --provider <provider> - switch to provider, auto-detect model
    """

    command_name = "model"
    help_text = "Switch AI model"

    async def handle(self, event, runner: "GatewayRunner") -> Optional[str]:
        """Handle /model command."""
        return await runner._handle_model_command(event)


class ProviderCommand(CommandHandler):
    """Handle /provider command - switch AI provider."""

    command_name = "provider"
    help_text = "Switch AI provider"

    async def handle(self, event, runner: "GatewayRunner") -> Optional[str]:
        """Handle /provider command."""
        return await runner._handle_provider_command(event)


class PersonalityCommand(CommandHandler):
    """Handle /personality command - change agent personality."""

    command_name = "personality"
    help_text = "Change agent personality"

    async def handle(self, event, runner: "GatewayRunner") -> Optional[str]:
        """Handle /personality command."""
        return await runner._handle_personality_command(event)


class VoiceCommand(CommandHandler):
    """Handle /voice command - configure voice mode."""

    command_name = "voice"
    help_text = "Configure voice mode (off, voice_only, all)"

    async def handle(self, event, runner: "GatewayRunner") -> Optional[str]:
        """Handle /voice command."""
        return await runner._handle_voice_command(event)


__all__ = [
    "ModelCommand",
    "ProviderCommand",
    "PersonalityCommand",
    "VoiceCommand",
]
