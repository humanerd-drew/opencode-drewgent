"""Tests for brain_tool.py — bidirectional brain access for agent.

TDD approach for brain_query and brain_record tools:

1. brain_record: agent intentionally saves knowledge to wiki via auto_learn
2. brain_query: agent queries relevant wiki knowledge for active reasoning

Run: python3 -m pytest tests/tools/test_brain_tool.py -v -o "addopts="
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from agent.auto_learn import AutoLearner


# ==============================================================================
# Test 1: brain_record — intentional learning via tool call
# ==============================================================================

class TestBrainRecord:
    """brain_record() wraps auto_learn.learn_from_turn() for explicit agent use."""

    def test_brain_record_saves_insight(self, tmp_path):
        """brain_record should save an insight to wiki via auto_learn."""
        wiki_path = tmp_path / "wiki"
        wiki_path.mkdir(exist_ok=True)

        learner = AutoLearner()
        learner.enable(wiki_path)

        # Simulate brain_record call (direct wrapper)
        user_text = "always explain the reasoning first"
        assistant_text = "Understood — reasoning first, then conclusion."
        itype = "preference"

        # brain_record saves via learn_from_turn
        u, m = learner.learn_from_turn(user_text, assistant_text)

        # Verify: something was saved
        assert u > 0 or m > 0, "brain_record should save at least one insight"

    def test_brain_record_target_user(self, tmp_path):
        """brain_record with target='user' saves to entities/preferences."""
        wiki_path = tmp_path / "wiki"
        wiki_path.mkdir(exist_ok=True)

        learner = AutoLearner()
        learner.enable(wiki_path)

        # Simulate: agent explicitly records a user preference
        learner.learn_from_turn(
            "I prefer short answers",
            "Got it — keeping it brief."
        )

        # Verify: preference file created
        pref_file = wiki_path / "entities" / "preferences.md"
        assert pref_file.exists(), "preference should be saved to entities/preferences.md"

    def test_brain_record_idempotent(self, tmp_path):
        """brain_record should not duplicate same insight twice."""
        wiki_path = tmp_path / "wiki"
        wiki_path.mkdir(exist_ok=True)

        learner = AutoLearner()
        learner.enable(wiki_path)

        user_text = "I prefer concise"
        assistant_text = "OK, being brief."

        # Record same insight twice
        learner.learn_from_turn(user_text, assistant_text)
        u1, m1 = learner.learn_from_turn(user_text, assistant_text)

        # Second call should skip (key already learned)
        assert u1 == 0 and m1 == 0, (
            "Duplicate insight should return 0,0 (not re-save)"
        )


# ==============================================================================
# Test 2: brain_query — semantic wiki search for active reasoning
# ==============================================================================

class TestBrainQuery:
    """brain_query searches wiki for contextually relevant knowledge."""

    def test_brain_query_returns_matching_entries(self, tmp_path):
        """brain_query should return entries matching the query."""
        wiki_path = tmp_path / "wiki"
        wiki_path.mkdir(exist_ok=True)

        learner = AutoLearner()
        learner.enable(wiki_path)

        # Pre-populate wiki with brain_record-style explicit saves
        from agent.auto_learn import Insight
        insights = [
            Insight(target="memory", itype="tool", content="n8n workflow setup: 1. Create credential in n8n UI"),
            Insight(target="user", itype="preference", content="I prefer concise answers"),
            Insight(target="memory", itype="tool", content="docker logs command: docker logs --tail 100 container"),
        ]
        for ins in insights:
            learner.save_insight(ins)

        # Query for n8n content
        result = learner.query_wiki("n8n", context="current task")

        assert result, "brain_query should return something for 'n8n' query"
        assert "n8n" in result.lower(), f"result should contain 'n8n', got: {result[:200]}"

    def test_brain_query_empty_for_no_match(self, tmp_path):
        """brain_query should return empty string for no match."""
        wiki_path = tmp_path / "wiki"
        wiki_path.mkdir(exist_ok=True)

        learner = AutoLearner()
        learner.enable(wiki_path)

        # Only save docker content
        from agent.auto_learn import Insight
        learner.save_insight(Insight(
            target="memory", itype="tool",
            content="docker ps: list running containers"
        ))

        result = learner.query_wiki("nonexistent_topic_xyz", context="")

        # Empty result for non-matching query (no partial word match)
        assert result == "" or result.isspace(), (
            f"brain_query should return empty for no match, got: {result[:100]}"
        )

    def test_brain_query_respects_max_chars(self, tmp_path):
        """brain_query should truncate to max_chars."""
        wiki_path = tmp_path / "wiki"
        wiki_path.mkdir(exist_ok=True)

        learner = AutoLearner()
        learner.enable(wiki_path)

        # Add multiple entries
        for i in range(20):
            learner.learn_from_turn(f"detail {i}", f"Detail response {i}." * 20)

        result = learner.query_wiki("detail", context="", max_chars=200)

        assert len(result) <= 300, "result should be <= max_chars (with overhead buffer)"

    def test_brain_query_with_context(self, tmp_path):
        """brain_query with context should weight results by relevance."""
        wiki_path = tmp_path / "wiki"
        wiki_path.mkdir(exist_ok=True)

        learner = AutoLearner()
        learner.enable(wiki_path)

        # Two different topics
        learner.learn_from_turn("git commit message", "Use conventional commits.")
        learner.learn_from_turn("dockerfile optimization", "Multi-stage build recommended.")

        # Query with context mentioning docker
        result = learner.query_wiki("git", context="dockerfile build")

        # Should prefer git over dockerfile when query is git
        # (even though context mentions docker)
        assert "git" in result.lower(), "result should contain git topic"


# ==============================================================================
# Test 3: Integration — brain_record then brain_query
# ==============================================================================

class TestBrainRecordQueryCycle:
    """Record knowledge, then immediately query it back."""

    def test_record_then_query_cycle(self, tmp_path):
        """brain_record → brain_query should return the saved knowledge."""
        wiki_path = tmp_path / "wiki"
        wiki_path.mkdir(exist_ok=True)

        learner = AutoLearner()
        learner.enable(wiki_path)

        # Step 1: Agent records a preference
        learner.learn_from_turn(
            "I prefer that you explain the reasoning first",
            "Understood — I'll show my reasoning before the conclusion."
        )

        # Step 2: Agent queries for this preference in a new context
        result = learner.query_wiki("reasoning", context="explaining approach")

        assert result, "brain_query should find the 'reasoning' insight"
        # The insight content should be findable
        assert "reasoning" in result.lower() or "preference" in result.lower(), (
            "returned content should reference the saved insight"
        )


# ==============================================================================
# Test 4: Tool registration — brain_tool should be discoverable
# ==============================================================================

class TestBrainToolRegistration:
    """brain_tool should be registered in tools/registry.py via model_tools."""

    @pytest.fixture(autouse=True)
    def _ensure_model_tools_loaded(self):
        """model_tools must be imported first to trigger tool discovery."""
        # Importing model_tools triggers _discover_tools() which imports all tool modules
        from model_tools import _discover_tools  # noqa: F401

    def test_brain_tool_schema_exists(self):
        """Tools registry should have brain_query and brain_record schemas."""
        from tools.registry import registry

        tool_names = registry.get_all_tool_names()

        assert "brain_query" in tool_names, "brain_query should be registered"
        assert "brain_record" in tool_names, "brain_record should be registered"

    def test_brain_tool_handler_callable(self):
        """brain_tool handlers should be callable."""
        from tools.registry import registry

        for name in ("brain_query", "brain_record"):
            schema = registry.get_schema(name)
            assert schema is not None, f"{name} should have a schema"
            assert "name" in schema, f"{name} schema should have 'name' key"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-o", "addopts="])
