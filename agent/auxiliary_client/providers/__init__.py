"""
auxiliary_client.providers - Provider implementations for auxiliary LLM calls.

This subpackage contains provider-specific implementations for:
- OpenRouter
- Nous Portal
- Anthropic
- Codex
- Custom endpoints
- API key based providers

Each provider is responsible for:
1. Credential resolution
2. Client creation
3. Provider-specific adaptations
"""

from .base import BaseProvider, ProviderResult

# Re-export for convenience
__all__ = ["BaseProvider", "ProviderResult"]
