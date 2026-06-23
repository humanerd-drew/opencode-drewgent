"""
Session Manager - Facade for session-related operations in Gateway

Provides a centralized interface for session management, bridging:
  - SessionStore (persistent session data)
  - Running agents (active AIAgent instances per session)
  - Session lifecycle (create, switch, reset, expire)

Usage:
    session_mgr = SessionManager(runner)

    # Get or create session
    entry = session_mgr.get_session(source)

    # Load transcript
    history = session_mgr.load_history(session_id)

    # Append to transcript
    session_mgr.append_message(session_id, role, content)

    # Switch session
    session_mgr.switch_session(session_key, target_id)
"""

import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from gateway.run import GatewayRunner

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Facade for session management operations.

    This class provides a stable interface for session operations,
    delegating to GatewayRunner's internal state. This allows:
      - Gradual migration to separate SessionManager class
      - Clear API boundary for session operations
      - Future extraction without changing call sites
    """

    def __init__(self, runner: "GatewayRunner"):
        """
        Initialize SessionManager.

        Args:
            runner: GatewayRunner instance
        """
        self._runner = runner

        # Direct references to runner's state (for now)
        # These will be migrated to SessionManager's own state in future phases
        self._session_store = runner.session_store
        self._running_agents = runner._running_agents
        self._running_agents_ts = runner._running_agents_ts

    # -------------------------------------------------------------------------
    # Session Lifecycle
    # -------------------------------------------------------------------------

    def get_session(self, source: Any) -> Any:
        """
        Get or create a session for the given source.

        Delegates to SessionStore.get_or_create_session().
        """
        return self._session_store.get_or_create_session(source)

    def reset_session(self, session_key: str) -> Any:
        """Reset session and return new entry."""
        return self._session_store.reset_session(session_key)

    def switch_session(self, session_key: str, target_id: str) -> Any:
        """Switch to a different session."""
        return self._session_store.switch_session(session_key, target_id)

    # -------------------------------------------------------------------------
    # Transcript Management
    # -------------------------------------------------------------------------

    def load_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Load transcript for a session."""
        return self._session_store.load_transcript(session_id)

    def append_message(
        self, session_id: str, role: str, content: str, metadata: Optional[Dict] = None
    ) -> None:
        """Append a message to the session transcript."""
        self._session_store.append_to_transcript(session_id, role, content, metadata)

    def rewrite_transcript(self, session_id: str, truncated: List[Dict]) -> None:
        """Rewrite transcript with truncated version."""
        self._session_store.rewrite_transcript(session_id, truncated)

    # -------------------------------------------------------------------------
    # Agent Management
    # -------------------------------------------------------------------------

    def get_running_agent(self, session_key: str) -> Optional[Any]:
        """Get the running agent for a session, if any."""
        return self._running_agents.get(session_key)

    def set_running_agent(self, session_key: str, agent: Any) -> None:
        """Set the running agent for a session."""
        self._running_agents[session_key] = agent
        self._running_agents_ts[session_key] = time.time()

    def clear_running_agent(self, session_key: str) -> None:
        """Clear the running agent for a session."""
        self._running_agents.pop(session_key, None)
        self._running_agents_ts.pop(session_key, None)

    def has_running_agent(self, session_key: str) -> bool:
        """Check if session has a running agent."""
        return session_key in self._running_agents

    # -------------------------------------------------------------------------
    # Persistence
    # -------------------------------------------------------------------------

    def save(self) -> None:
        """Save session state to disk."""
        self._session_store._save()

    def has_any_sessions(self) -> bool:
        """Check if there are any sessions."""
        return self._session_store.has_any_sessions()

    # -------------------------------------------------------------------------
    # Properties (read-only access to internal state)
    # -------------------------------------------------------------------------

    @property
    def session_store(self) -> Any:
        """Direct access to SessionStore (for gradual migration)."""
        return self._session_store

    @property
    def entries(self) -> Dict[str, Any]:
        """Direct access to session entries (for gradual migration)."""
        return self._session_store._entries

    @property
    def config(self) -> Any:
        """Access to session config."""
        return self._session_store.config


__all__ = ["SessionManager"]
