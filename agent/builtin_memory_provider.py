"""BuiltinMemoryProvider — wraps MEMORY.md / USER.md as a MemoryProvider.

Always registered as the first provider. Cannot be disabled or removed.
This is the existing Drewgent memory system exposed through the provider
interface for compatibility with the MemoryManager.

The actual storage logic lives in tools/memory_tool.py (MemoryStore).
This provider is a thin adapter that delegates to MemoryStore and
exposes the memory tool schema.

Auto-Learning Extension:
  When auto_learn=True, this provider automatically extracts insights from
  conversation turns and saves them to MEMORY.md / USER.md without requiring
  manual memory tool calls. This enables the agent to learn user preferences,
  communication patterns, and environmental facts proactively.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from agent.memory_provider import MemoryProvider

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Auto-Learning: Pattern Definitions
# ---------------------------------------------------------------------------

# User preference patterns (explicit statements about likes/dislikes)
_PREFERENCE_PATTERNS = [
    (
        r"(?:I prefer|I like|I love|I hate|I'm a|my favorite|my favourite)[:\s]+([^.!?]+)",
        "preference",
    ),
    (r"(?:call me|named?|I'm)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", "name"),
    (r"(?:I work as|I'm a|my role is|my job is)[:\s]+([^.!?]+)", "role"),
    (r"(?:I'm in|I'm working in)[:\s]+([^.!?]+)", "field"),
    (r"(?:my timezone is|I'm in timezone)[:\s]+([^.!?]+)", "timezone"),
]

# Communication style patterns
_STYLE_PATTERNS = [
    (r"be\s+(?:brief|short|concise|to the point)", "style_concise"),
    (r"(?:keep it short|don't overexplain|just the facts)", "style_concise"),
    (r"(?:explain|dig deeper|tell me more|give me details)", "style_detailed"),
    (r"(?:step by step|walk me through|in detail)", "style_detailed"),
]

# User correction patterns (user correcting the agent)
_CORRECTION_PATTERNS = [
    (r"(?:no[, ]|actually[,]|not quite|remember)[:\s]+([^.!?]+)", "correction"),
    (r"(?:that's wrong|incorrect)[:\s]+([^.!?]+)", "correction"),
]

# Environment/technical facts
_ENV_PATTERNS = [
    (
        r"(?:on|using|running)[:\s]*(?:my |the )?(Mac|Linux|Windows|Ubuntu|Debian|CentOS|macOS|iOS|Android)",
        "os",
    ),
    (r"(?:using|with)[:\s]+([A-Za-z][^.\s]+)(?:\s|$)", "tool"),
]

# Success/failure signals in assistant response
_SUCCESS_PATTERNS = [
    r"(?:perfect|great|thanks|that works|exactly|yes[, ]|got it|resolved|awesome)",
    r"(?:finally|found it|worked)",
]

_FAILURE_PATTERNS = [
    r"(?:doesn't work|failed|error|broken|wrong result)",
    r"(?:try again|different approach|not what I wanted)",
]


class AutoLearner:
    """Extracts insights from conversation turns automatically."""

    def __init__(self):
        self._learned_user: Set[str] = set()  # Track what's already learned
        self._learned_memory: Set[str] = set()

    def load_existing(self, memories_dir: Path) -> None:
        """Load existing entries to avoid duplicates."""
        user_file = memories_dir / "USER.md"
        mem_file = memories_dir / "MEMORY.md"

        if user_file.exists():
            content = user_file.read_text()
            for entry in content.split("§"):
                entry = entry.strip()
                if entry:
                    self._learned_user.add(entry.lower()[:60])

        if mem_file.exists():
            content = mem_file.read_text()
            for entry in content.split("§"):
                entry = entry.strip()
                if entry:
                    self._learned_memory.add(entry.lower()[:60])

    def extract_insights(
        self, user_text: str, assistant_text: str
    ) -> tuple[List[str], List[str]]:
        """Extract user profile and memory insights from a conversation turn.

        Returns (user_insights, memory_insights) lists.
        """
        user_insights = []
        memory_insights = []

        # Skip very short messages
        if len(user_text) < 3:
            return [], []

        # Extract user preferences and profile info
        for pattern, ptype in _PREFERENCE_PATTERNS:
            for match in re.finditer(pattern, user_text, re.IGNORECASE):
                content = match.group(1).strip()
                if self._is_meaningful(content):
                    insight = self._format_user_insight(ptype, content)
                    key = insight.lower()[:60]
                    if key not in self._learned_user:
                        user_insights.append(insight)
                        self._learned_user.add(key)

        # Extract communication style
        for pattern, style in _STYLE_PATTERNS:
            if re.search(pattern, user_text, re.IGNORECASE):
                insight = self._format_user_insight(
                    "style", style.replace("style_", "")
                )
                key = insight.lower()[:60]
                if key not in self._learned_user:
                    user_insights.append(insight)
                    self._learned_user.add(key)

        # Extract corrections
        for pattern, ptype in _CORRECTION_PATTERNS:
            for match in re.finditer(pattern, user_text, re.IGNORECASE):
                content = match.group(1).strip()
                if self._is_meaningful(content):
                    insight = self._format_user_insight("correction", content)
                    key = insight.lower()[:60]
                    if key not in self._learned_user:
                        user_insights.append(insight)
                        self._learned_user.add(key)

        # Extract environmental facts from user text
        for pattern, etype in _ENV_PATTERNS:
            for match in re.finditer(pattern, user_text, re.IGNORECASE):
                content = match.group(1).strip()
                if self._is_meaningful(content):
                    insight = self._format_memory_insight(etype, content)
                    key = insight.lower()[:60]
                    if key not in self._learned_memory:
                        memory_insights.append(insight)
                        self._learned_memory.add(key)

        return user_insights, memory_insights

    def _is_meaningful(self, text: str) -> bool:
        """Check if extracted text is meaningful enough to save."""
        text = text.strip().lower()
        # Skip generic responses
        generic = {
            "yes",
            "no",
            "okay",
            "ok",
            "sure",
            "thanks",
            "yeah",
            "nope",
            "please",
            "ok",
        }
        if text in generic:
            return False
        if len(text) < 2:
            return False
        if len(text) > 150:
            return False
        return True

    def _format_user_insight(self, itype: str, content: str) -> str:
        """Format user insight for USER.md."""
        labels = {
            "preference": "Preference",
            "name": "Name",
            "role": "Role",
            "field": "Field",
            "timezone": "Timezone",
            "style_concise": "Communication preference",
            "style_detailed": "Communication preference",
            "correction": "Corrected approach",
        }
        label = labels.get(itype, "Known")
        return f"{label}: {content}"

    def _format_memory_insight(self, etype: str, content: str) -> str:
        """Format memory insight for MEMORY.md."""
        labels = {
            "os": "Environment",
            "tool": "Using tool",
        }
        label = labels.get(etype, "Fact")
        return f"{label}: {content}"


# ---------------------------------------------------------------------------
# BuiltinMemoryProvider
# ---------------------------------------------------------------------------


class BuiltinMemoryProvider(MemoryProvider):
    """Built-in file-backed memory (MEMORY.md + USER.md).

    Always active, never disabled by other providers. The `memory` tool
    is handled by run_agent.py's agent-level tool interception (not through
    the normal registry), so get_tool_schemas() returns an empty list —
    the memory tool is already wired separately.

    When auto_learn=True, this provider also automatically extracts insights
    from conversation turns and saves them to the memory files.
    """

    def __init__(
        self,
        memory_store=None,
        memory_enabled: bool = False,
        user_profile_enabled: bool = False,
        auto_learn: bool = False,
        auto_learn_max_per_turn: int = 2,
    ):
        self._store = memory_store
        self._memory_enabled = memory_enabled
        self._user_profile_enabled = user_profile_enabled
        self._auto_learn = auto_learn
        self._auto_learn_max = auto_learn_max_per_turn

        self._learner = AutoLearner()
        self._memories_dir: Optional[Path] = None
        self._session_count = 0  # Track turns for logging

    @property
    def name(self) -> str:
        return "builtin"

    def is_available(self) -> bool:
        """Built-in memory is always available."""
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
        """Load memory from disk if not already loaded."""
        if self._store is not None:
            self._store.load_from_disk()

        # Setup auto-learner directories
        if self._auto_learn:
            drewgent_home = kwargs.get("drewgent_home")
            if drewgent_home:
                self._memories_dir = Path(drewgent_home) / "memories"
                self._memories_dir.mkdir(parents=True, exist_ok=True)
                self._learner.load_existing(self._memories_dir)

    def system_prompt_block(self) -> str:
        """Return MEMORY.md and USER.md content for the system prompt.

        Uses the frozen snapshot captured at load time. This ensures the
        system prompt stays stable throughout a session (preserving the
        prompt cache), even though the live entries may change via tool calls.
        """
        if not self._store:
            return ""

        parts = []
        if self._memory_enabled:
            mem_block = self._store.format_for_system_prompt("memory")
            if mem_block:
                parts.append(mem_block)
        if self._user_profile_enabled:
            user_block = self._store.format_for_system_prompt("user")
            if user_block:
                parts.append(user_block)

        return "\n\n".join(parts)

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """Built-in memory doesn't do query-based recall — it's injected via system_prompt_block."""
        return ""

    def sync_turn(
        self, user_content: str, assistant_content: str, *, session_id: str = ""
    ) -> None:
        """No-op — all auto-learning goes through agent/auto_learn.py only.

        The BuiltinMemoryProvider handles system-prompt block delivery.
        Obsidian wiki learning is the single source of truth, managed by
        the AutoLearner in run_agent.py. No file writes here.
        """
        # Delegated entirely to agent/auto_learn.py via
        # self._agent._auto_learner.learn_from_turn() in run_agent.py

    def _save_insights(self, target: str, insights: List[str]) -> None:
        """Save insights to memory store using add()."""
        if not self._store or not insights:
            return

        for insight in insights:
            # Use the store's add method for proper deduplication and char limits
            result = self._store.add(target, insight)
            if not result.get("success") and result.get("error"):
                # Char limit reached or duplicate — that's okay
                pass

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Return empty list.

        The `memory` tool is an agent-level intercepted tool, handled
        specially in run_agent.py before normal tool dispatch. It's not
        part of the standard tool registry. We don't duplicate it here.
        """
        return []

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        """Not used — the memory tool is intercepted in run_agent.py."""
        return json.dumps(
            {"error": "Built-in memory tool is handled by the agent loop"}
        )

    def shutdown(self) -> None:
        """No cleanup needed — files are saved on every write."""

    # -- Property access for backward compatibility --------------------------

    @property
    def store(self):
        """Access the underlying MemoryStore for legacy code paths."""
        return self._store

    @property
    def memory_enabled(self) -> bool:
        return self._memory_enabled

    @property
    def user_profile_enabled(self) -> bool:
        return self._user_profile_enabled
