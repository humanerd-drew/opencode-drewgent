"""Tests for EpisodicMemoryProvider."""

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agent.episodic_memory_provider import EpisodicMemoryProvider
from agent.memory_manager import MemoryManager
from agent.auto_learn import VectorStore

@pytest.fixture
def temp_home(tmp_path):
    """Fixture to create a temporary DREW_HOME directory."""
    home_dir = tmp_path / "drewgent"
    home_dir.mkdir()
    (home_dir / "memories").mkdir()
    return home_dir

@pytest.fixture
def provider(temp_home):
    """Fixture to instantiate and initialize EpisodicMemoryProvider."""
    emp = EpisodicMemoryProvider(enabled=True)
    emp.initialize(
        session_id="test_session_123",
        drewgent_home=str(temp_home),
        platform="cli"
    )
    return emp

class TestEpisodicMemoryProvider:
    def test_name_and_availability(self):
        emp = EpisodicMemoryProvider(enabled=True)
        assert emp.name == "episodic"
        assert emp.is_available() is True

        emp_disabled = EpisodicMemoryProvider(enabled=False)
        assert emp_disabled.is_available() is False

    @patch("agent.episodic_memory_provider.get_embedding")
    def test_on_pre_compress_stores_turns(self, mock_get_embedding, provider, temp_home):
        # We need a dummy embedding of length e.g. 3
        mock_get_embedding.return_value = [[0.1, 0.2, 0.3]]

        # Prepare messages list. Needs to be > protect_first_n + protect_last_n + 1 (3 + 20 + 1 = 24)
        messages = []
        # Head (3 messages)
        messages.append({"role": "system", "content": "System prompt"})
        messages.append({"role": "user", "content": "Head user"})
        messages.append({"role": "assistant", "content": "Head assistant"})

        # Middle (to be compressed - 5 messages)
        messages.append({"role": "user", "content": "Middle user 1"})
        messages.append({"role": "assistant", "content": "Middle assistant 1", "tool_calls": [{"id": "call1", "type": "function", "function": {"name": "test_tool"}}]})
        messages.append({"role": "tool", "content": "Tool output 1", "tool_call_id": "call1"})
        messages.append({"role": "user", "content": "Middle user 2"})
        messages.append({"role": "assistant", "content": "Middle assistant 2"})

        # Tail (20 messages to protect)
        for i in range(20):
            messages.append({"role": "user" if i % 2 == 0 else "assistant", "content": f"Tail content {i}"})

        # Run compression hook
        provider.on_pre_compress(messages)

        # Check that mock embedding was called for middle turns chunked together
        assert mock_get_embedding.called

        # Connect to sqlite db directly and verify records
        conn = sqlite3.connect(str(provider.db_path))
        cursor = conn.execute("SELECT id, content, itype, target FROM vectors WHERE itype = 'episodic'")
        rows = cursor.fetchall()
        conn.close()

        # Check database records
        assert len(rows) > 0
        for row in rows:
            assert row[2] == "episodic"
            assert row[3] == "test_session_123"
            # It should have saved user-to-user exchanges
            assert "Middle user 1" in row[1] or "Middle user 2" in row[1]

    @patch("agent.episodic_memory_provider.get_embedding")
    def test_prefetch_recalls_relevant_turns(self, mock_get_embedding, provider):
        # Setup vector store records directly
        db = VectorStore(provider.db_path)
        # Vector A: user query closely related
        db.add(
            id="episodic_test_a",
            content="User: How do I compile the rust project?\nAssistant: Use cargo build.",
            embedding=[1.0, 0.0, 0.0],
            itype="episodic",
            target="test_session_123"
        )
        # Vector B: unrelated
        db.add(
            id="episodic_test_b",
            content="User: What is the capital of France?\nAssistant: Paris.",
            embedding=[0.0, 1.0, 0.0],
            itype="episodic",
            target="test_session_123"
        )
        # Vector C: different session
        db.add(
            id="episodic_test_c",
            content="User: How do I compile rust?\nAssistant: cargo build.",
            embedding=[1.0, 0.0, 0.0],
            itype="episodic",
            target="other_session"
        )

        # Mock user query closely matches Vector A (close to [1.0, 0.0, 0.0])
        mock_get_embedding.return_value = [[0.95, 0.05, 0.0]]

        # Run prefetch
        recalled = provider.prefetch("compile rust")

        # Verify recalled content
        assert recalled != ""
        assert "cargo build" in recalled
        assert "capital of France" not in recalled
        assert "Score:" in recalled

    def test_integration_coexistence_in_memory_manager(self, provider):
        """Verify that EpisodicMemoryProvider can coexist with another external memory provider."""
        mgr = MemoryManager()
        
        # 1. Add episodic memory provider (treated as builtin/internal RAG)
        mgr.add_provider(provider)

        # 2. Add custom external memory provider (should not be blocked)
        from tests.agent.test_memory_provider import FakeMemoryProvider
        ext_provider = FakeMemoryProvider("honcho")
        
        mgr.add_provider(ext_provider)

        # Both should be registered successfully
        assert "episodic" in mgr.provider_names
        assert "honcho" in mgr.provider_names
        assert len(mgr.providers) == 2

    @patch("agent.episodic_memory_provider.get_embedding")
    def test_on_pre_compress_with_compressor_stores_turns(self, mock_get_embedding, provider, temp_home):
        mock_get_embedding.return_value = [[0.1, 0.2, 0.3]]

        # Prepare messages
        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "Head user"},
            {"role": "assistant", "content": "Head assistant"},
            # Middle (turns 3-5 to summarize)
            {"role": "user", "content": "Target Middle user 1"},
            {"role": "assistant", "content": "Target Middle assistant 1"},
            # Tail
            {"role": "user", "content": "Tail user 1"},
            {"role": "assistant", "content": "Tail assistant 1"},
        ]

        # Mock ContextCompressor
        mock_compressor = MagicMock()
        # Instruct mock to return compress_start=3, compress_end=5
        mock_compressor.get_compression_boundaries.return_value = (3, 5)

        # Run compression hook passing the mock compressor
        provider.on_pre_compress(messages, compressor=mock_compressor)

        # Check that mock_compressor.get_compression_boundaries was called with messages
        mock_compressor.get_compression_boundaries.assert_called_once_with(messages)

        # Connect to sqlite db directly and verify records
        conn = sqlite3.connect(str(provider.db_path))
        cursor = conn.execute("SELECT id, content, itype, target FROM vectors WHERE itype = 'episodic'")
        rows = cursor.fetchall()
        conn.close()

        # Should have saved turns 3-5
        assert len(rows) > 0
        found_target = False
        for row in rows:
            if "Target Middle user 1" in row[1]:
                found_target = True
        assert found_target is True
