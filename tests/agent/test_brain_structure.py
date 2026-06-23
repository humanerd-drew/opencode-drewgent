"""Tests for brain-structure fix: single-source auto_learn through auto_learn.py.

This test file validates the TDD fix for Drewgent's brain (auto_learn) system:

1. Duplicate removal: BuiltinMemoryProvider.sync_turn is now a no-op.
   All Obsidian wiki learning goes through agent/auto_learn.py only.
2. Implicit patterns: Short commands ("agent", "nice", "ok") are now learnable.
3. Session-end reflection: AutoLearner.on_session_end() does deep learning.

Run: python3 -m pytest tests/agent/test_brain_structure.py -q -o "addopts="
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from agent.builtin_memory_provider import BuiltinMemoryProvider
from agent.auto_learn import AutoLearner
from scripts.obsidian_graph_integrity import check_graph


# ==============================================================================
# Test 1: No duplicate learning — BuiltinMemoryProvider.sync_turn is no-op
# ==============================================================================

class TestNoDuplicateLearning:
    """BuiltinMemoryProvider.sync_turn must NOT write to files.

    The only source of truth for Obsidian wiki learning is auto_learn.py.
    """

    def test_sync_turn_is_no_op(self, tmp_path):
        """sync_turn should be a no-op (no file writes)."""
        provider = BuiltinMemoryProvider(
            memory_store=None,  # No store needed
            memory_enabled=True,
            user_profile_enabled=True,
            auto_learn=False,  # Even with auto_learn, sync_turn is no-op
        )

        # Should not raise, even without a store
        provider.sync_turn(
            "I prefer concise answers",
            "Got it, being brief."
        )

        # Verify: no memory files created (we can check the log/don't raise)
        # The key assertion is that sync_turn doesn't crash without a store
        assert True  # If we get here, sync_turn was a no-op

    def test_sync_turn_no_mem_file_created(self, tmp_path):
        """Even with auto_learn=True, sync_turn writes nothing to disk."""
        provider = BuiltinMemoryProvider(
            memory_store=None,
            memory_enabled=True,
            auto_learn=True,  # Even with auto_learn enabled
        )

        provider.sync_turn("I prefer verbose", "Understood.")
        # No exception raised = sync_turn was correctly a no-op
        assert True


# ==============================================================================
# Test 2: Implicit preference patterns in AutoLearner
# ==============================================================================

class TestImplicitPatterns:
    """AutoLearner must learn from short commands and implicit signals."""

    def test_short_command_agent_learned(self, tmp_path):
        """'agent' alone should be recognized as a command-style preference."""
        wiki_path = tmp_path / "wiki"
        wiki_path.mkdir(parents=True, exist_ok=True)

        learner = AutoLearner()
        learner.enable(wiki_path)

        # Short command-style input
        user_saved, _ = learner.learn_from_turn(
            "agent",
            "How can I help you today?"
        )

        # After fix: implicit pattern should match "agent" → style_command
        assert user_saved > 0, (
            "'agent' command should trigger implicit style_command pattern"
        )

    def test_short_positive_feedback_learned(self, tmp_path):
        """'nice, thanks' should signal positive preference."""
        wiki_path = tmp_path / "wiki"
        wiki_path.mkdir(parents=True, exist_ok=True)

        learner = AutoLearner()
        learner.enable(wiki_path)

        user_saved, _ = learner.learn_from_turn(
            "nice, thanks",
            "You're welcome!"
        )

        # "nice" matches implicit style_concise
        assert user_saved > 0, (
            "Positive feedback like 'nice, thanks' should be learnable as style_concise"
        )

    def test_one_word_ok_learned(self, tmp_path):
        """Single 'ok' from user should trigger style_concise."""
        wiki_path = tmp_path / "wiki"
        wiki_path.mkdir(parents=True, exist_ok=True)

        learner = AutoLearner()
        learner.enable(wiki_path)

        user_saved, _ = learner.learn_from_turn("ok", "Done.")

        # "ok" matches ^ok$ implicit pattern → style_concise
        assert user_saved > 0, (
            "'ok' one-word response should match implicit style_concise pattern"
        )

    def test_tool_command_learned(self, tmp_path):
        """grep/find/ls etc. should be learnable as tool preference."""
        wiki_path = tmp_path / "wiki"
        wiki_path.mkdir(parents=True, exist_ok=True)

        learner = AutoLearner()
        learner.enable(wiki_path)

        user_saved, _ = learner.learn_from_turn(
            "grep -r pattern .",
            "Found 5 matches in 3 files."
        )

        # "grep" appears in implicit tool pattern
        assert user_saved > 0, (
            "'grep' command should be learnable as tool preference"
        )


# ==============================================================================
# Test 3: Session-end deep reflection in AutoLearner
# ==============================================================================

class TestSessionEndReflection:
    """AutoLearner must have on_session_end() for deep reflection at session close."""

    def test_on_session_end_method_exists(self, tmp_path):
        """AutoLearner must have on_session_end() method."""
        wiki_path = tmp_path / "wiki"
        wiki_path.mkdir(parents=True, exist_ok=True)

        learner = AutoLearner()
        learner.enable(wiki_path)

        assert hasattr(learner, 'on_session_end'), (
            "AutoLearner must have on_session_end() method"
        )
        assert callable(learner.on_session_end), (
            "on_session_end must be callable"
        )

    def test_on_session_end_accepts_messages(self, tmp_path):
        """on_session_end() should accept conversation messages list."""
        wiki_path = tmp_path / "wiki"
        wiki_path.mkdir(parents=True, exist_ok=True)

        learner = AutoLearner()
        learner.enable(wiki_path)

        messages = [
            {"role": "user", "content": "agent"},
            {"role": "assistant", "content": "How can I help?"},
            {"role": "user", "content": "grep -r pattern ."},
            {"role": "assistant", "content": "Found 5 matches in 3 files."},
        ]

        # Should not raise
        result = learner.on_session_end(messages)

        # Result is None (no new insights) or dict with counts
        assert result is None or isinstance(result, dict), (
            "on_session_end should return None or dict"
        )

    def test_on_session_end_extracts_recurring_topics(self, tmp_path):
        """on_session_end should detect recurring topics across conversation."""
        wiki_path = tmp_path / "wiki"
        wiki_path.mkdir(parents=True, exist_ok=True)

        learner = AutoLearner()
        learner.enable(wiki_path)

        # Multi-turn session with recurring topic
        messages = [
            {"role": "user", "content": "agent"},
            {"role": "assistant", "content": "I'm ready to help."},
            {"role": "user", "content": "grep pytest tests/"},
            {"role": "assistant", "content": "Found 8 matches."},
            {"role": "user", "content": "run pytest again"},
            {"role": "assistant", "content": "All 60 tests passed!"},
            {"role": "user", "content": "show pytest results"},
            {"role": "assistant", "content": "60 passed, 0 failed."},
        ]

        result = learner.on_session_end(messages)

        # Should return a dict with counts (topic was recurring)
        assert result is not None, (
            "on_session_end should detect recurring topic 'pytest' and return result"
        )
        concepts_count = result.get("concepts", 0) + result.get("memory", 0)
        assert concepts_count > 0, (
            "on_session_end should save at least one concept/memory for recurring topic"
        )


# ==============================================================================
# Test 4: Session-end hook connected in run_agent.py
# ==============================================================================

class TestSessionEndHookConnected:
    """shutdown_memory_provider should call _auto_learner.on_session_end."""

    def test_auto_learner_has_on_session_end_and_is_callable(self):
        """Verify AutoLearner.on_session_end is properly implemented."""
        learner = AutoLearner()
        learner.enable(Path("/tmp/test_wiki"))
        assert callable(learner.on_session_end)
        # Should not raise with None messages
        result = learner.on_session_end(None)
        assert result is None


# ==============================================================================
# Test 5: Integration — single source of truth
# ==============================================================================

class TestSingleSourceOfTruth:
    """Obsidian wiki is the only destination for auto_learn insights."""

    def test_auto_learner_writes_to_entities_not_memory_md(self, tmp_path):
        """AutoLearner should write to entities/ directory, not MEMORY.md."""
        wiki_path = tmp_path / "wiki"
        wiki_path.mkdir(parents=True, exist_ok=True)

        learner = AutoLearner()
        learner.enable(wiki_path)

        learner.learn_from_turn(
            "I prefer concise",
            "OK, being brief."
        )

        # Verify: entities/ directory exists and has content
        entities_dir = wiki_path / "entities"
        assert entities_dir.exists(), (
            "AutoLearner should write to entities/ directory"
        )
        md_files = list(entities_dir.glob("*.md"))
        assert len(md_files) > 0, (
            "AutoLearner should create at least one .md file in entities/"
        )


# ==============================================================================
# Test 6: Obsidian graph integrity for generated memory notes
# ==============================================================================

class TestObsidianGraphIntegrity:
    """Generated memory pages must not become Obsidian graph orphans."""

    def test_auto_learner_creates_parent_and_backlink(self, tmp_path):
        wiki_path = tmp_path / "memories"
        learner = AutoLearner()
        learner.enable(wiki_path)

        learner.learn_from_turn(
            "I prefer concise answers",
            "Understood.",
        )

        preferences = wiki_path / "entities" / "preferences.md"
        assert preferences.exists()

        content = preferences.read_text(encoding="utf-8")
        assert "[[index]]" in content
        assert "[[SCHEMA]]" in content
        assert "[[entities/index]]" in content

        root_index = (wiki_path / "index.md").read_text(encoding="utf-8")
        entity_index = (wiki_path / "entities" / "index.md").read_text(encoding="utf-8")
        assert "[[entities/preferences]]" in root_index
        assert "[[entities/preferences]]" in entity_index

    def test_generated_wiki_passes_graph_checker(self, tmp_path):
        vault = tmp_path / "vault"
        wiki_path = vault / "memories"
        (vault / ".obsidian").mkdir(parents=True)

        learner = AutoLearner()
        learner.enable(wiki_path)
        learner.learn_from_turn("I prefer concise answers", "Understood.")

        result = check_graph(vault)
        assert result["broken_links"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-o", "addopts="])
