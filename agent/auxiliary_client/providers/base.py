"""
Base provider interface for auxiliary client providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Tuple, Any
from openai import OpenAI


@dataclass
class ProviderResult:
    """Result from a provider resolution attempt."""
    client: Optional[Any]  # OpenAI-compatible client
    model: Optional[str]  # Model identifier
    available: bool  # Whether this provider has valid credentials


class BaseProvider(ABC):
    """
    Abstract base class for LLM providers.

    Each provider implements:
    - `try_create()`: Attempt to create a client with this provider's credentials
    - `name`: Provider identifier
    - `label`: Human-readable label for logging
    """

    name: str = "base"
    label: str = "Base Provider"

    @abstractmethod
    def try_create(self) -> ProviderResult:
        """
        Attempt to create a client using this provider's credentials.

        Returns:
            ProviderResult with client/model if credentials are valid,
            ProviderResult with available=False if not configured.
        """
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name}>"
