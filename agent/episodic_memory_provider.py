"""Episodic RAG Memory Provider.

Saves compacted conversation turns to SQLite VectorStore, and performs
semantic retrieval on prefetched turns to maintain context continuity.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.memory_provider import MemoryProvider
from agent.auto_learn import VectorStore, get_embedding, cosine_similarity
from agent.context_compressor import ContextCompressor

logger = logging.getLogger(__name__)

class EpisodicMemoryProvider(MemoryProvider):
    """Memory provider that performs semantic retrieval on conversation history compacted by ContextCompressor."""

    def __init__(self, enabled: bool = True):
        self._enabled = enabled
        self.session_id: str = ""
        self.drewgent_home: Optional[Path] = None
        self.db_path: Optional[Path] = None
        self._vector_store: Optional[VectorStore] = None

    @property
    def name(self) -> str:
        return "episodic"

    def is_available(self) -> bool:
        return self._enabled

    def initialize(self, session_id: str, **kwargs) -> None:
        self.session_id = session_id
        
        home_str = kwargs.get("drewgent_home")
        if home_str:
            self.drewgent_home = Path(home_str)
        else:
            from drewgent_constants import get_drewgent_home
            self.drewgent_home = get_drewgent_home()
            
        self.db_path = self.drewgent_home / "memories" / "vectors.db"
        self._vector_store = VectorStore(self.db_path)
        
        logger.info(
            "EpisodicMemoryProvider initialized. session_id=%s, db_path=%s",
            self.session_id,
            self.db_path
        )

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """Query semantic history for matching past turns."""
        if not self._enabled or not query or not query.strip() or not self.db_path or not self.db_path.exists():
            return ""
            
        sid = session_id or self.session_id
        if not sid:
            return ""

        try:
            # 1. Get embedding for user query
            embeddings = get_embedding([query])
            if not embeddings or not embeddings[0]:
                return ""
            query_emb = embeddings[0]

            # 2. Query DB and compute similarities for target session
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.execute(
                "SELECT id, content, embedding FROM vectors WHERE itype = 'episodic' AND target = ?",
                (sid,)
            )
            rows = cursor.fetchall()
            conn.close()

            results = []
            for row in rows:
                try:
                    stored_embedding = json.loads(row[2])
                    score = cosine_similarity(query_emb, stored_embedding)
                    # Use threshold of 0.8
                    if score >= 0.8:
                        results.append({
                            "content": row[1],
                            "score": score
                        })
                except Exception:
                    continue

            if not results:
                return ""

            # Sort by score descending
            results.sort(key=lambda x: x["score"], reverse=True)
            
            # Take top 3 relevant matching turns
            top_results = results[:3]
            
            parts = []
            for res in top_results:
                parts.append(
                    f"--- Recalled Past Turn (Score: {res['score']:.2f}) ---\n"
                    f"{res['content']}"
                )
            
            recalled_text = "\n\n".join(parts)
            logger.info("Episodic memory prefetch found %d matches", len(top_results))
            return recalled_text

        except Exception as e:
            logger.debug("Episodic prefetch failed: %s", e)
            return ""

    def on_pre_compress(self, messages: List[Dict[str, Any]], compressor: Optional[ContextCompressor] = None) -> str:
        """Identify middle turns to be pruned, embed and store them in VectorStore."""
        if not self._enabled or not self._vector_store:
            return ""

        n_messages = len(messages)
        
        if compressor is not None:
            compress_start, compress_end = compressor.get_compression_boundaries(messages)
            if compress_start == 0 and compress_end == 0:
                return ""
        else:
            # Replicating ContextCompressor boundary check to identify exactly the pruned turns
            # We need protect_first_n and protect_last_n
            # These default to 3 and 20 in ContextCompressor.
            protect_first_n = 3
            protect_last_n = 20
            
            if n_messages <= protect_first_n + protect_last_n + 1:
                return ""

            # Slide forward to align start boundary
            compress_start = protect_first_n
            while compress_start < n_messages and messages[compress_start].get("role") == "tool":
                compress_start += 1

            # Walk backward to find tail budget boundary
            # Since we don't have easy access to the compressor's runtime budgets,
            # we can recreate a robust check based on the default tail budget or fallback protect_last_n.
            # Compressor default: threshold_tokens = context_length * 0.5, tail_token_budget = threshold_tokens * 0.20
            # If context_length = 200,000, tail_token_budget = 20,000 tokens (approx 80,000 characters).
            # We will walk backward and accumulate chars.
            accumulated_chars = 0
            cut_idx = n_messages
            char_budget = 80000  # ~20,000 tokens
            
            for i in range(n_messages - 1, compress_start - 1, -1):
                msg = messages[i]
                content = msg.get("content") or ""
                accumulated_chars += len(str(content))
                for tc in msg.get("tool_calls") or []:
                    if isinstance(tc, dict):
                        accumulated_chars += len(str(tc.get("function", {}).get("arguments", "")))
                if accumulated_chars > char_budget and (n_messages - i) >= protect_last_n:
                    break
                cut_idx = i

            # Fallback to protect_last_n
            fallback_cut = n_messages - protect_last_n
            if cut_idx > fallback_cut:
                cut_idx = fallback_cut
            if cut_idx <= compress_start:
                cut_idx = fallback_cut

            # Align backward
            if cut_idx > 0 and cut_idx < n_messages:
                check = cut_idx - 1
                while check >= 0 and messages[check].get("role") == "tool":
                    check -= 1
                if check >= 0 and messages[check].get("role") == "assistant" and messages[check].get("tool_calls"):
                    cut_idx = check

            compress_end = max(cut_idx, compress_start + 1)
            
        if compress_start >= compress_end:
            return ""

        turns_to_save = messages[compress_start:compress_end]
        if not turns_to_save:
            return ""

        # Chunk the turns to save into contextually coherent chunks (e.g. user-to-user exchanges)
        chunks = []
        current_chunk = []
        for msg in turns_to_save:
            role = msg.get("role", "unknown")
            content = msg.get("content") or ""
            
            # Skip existing summary/compaction blocks
            if role == "user" and isinstance(content, str):
                from agent.context_compressor import SUMMARY_PREFIX, LEGACY_SUMMARY_PREFIX
                if content.startswith(SUMMARY_PREFIX) or content.startswith(LEGACY_SUMMARY_PREFIX):
                    continue

            if role == "user" and current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []

            if role == "user":
                current_chunk.append(f"User: {content}")
            elif role == "assistant":
                tc_info = ""
                tool_calls = msg.get("tool_calls") or []
                if tool_calls:
                    tcs = []
                    for tc in tool_calls:
                        if isinstance(tc, dict):
                            fn_name = tc.get("function", {}).get("name", "?")
                            fn_args = tc.get("function", {}).get("arguments", "")
                            tcs.append(f"{fn_name}({fn_args})")
                        else:
                            fn_name = getattr(getattr(tc, "function", None), "name", "?")
                            tcs.append(f"{fn_name}(...)")
                    tc_info = f" [Tool Calls: {', '.join(tcs)}]"
                current_chunk.append(f"Assistant: {content}{tc_info}")
            elif role == "tool":
                if len(content) > 1200:
                    content = content[:1000] + "\n...[truncated]...\n" + content[-200:]
                current_chunk.append(f"Tool Result: {content}")
            else:
                current_chunk.append(f"{role.upper()}: {content}")

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        # Embed and save each chunk to SQLite VectorStore
        stored_count = 0
        for chunk in chunks:
            if not chunk.strip():
                continue
            try:
                embeddings = get_embedding([chunk])
                if embeddings and embeddings[0]:
                    chunk_id = f"episodic_{self.session_id}_{uuid.uuid4().hex[:12]}"
                    success = self._vector_store.add(
                        id=chunk_id,
                        content=chunk,
                        embedding=embeddings[0],
                        itype="episodic",
                        target=self.session_id
                    )
                    if success:
                        stored_count += 1
            except Exception as e:
                logger.debug("Failed to store episodic memory chunk: %s", e)

        logger.info("EpisodicMemoryProvider: Embedded and stored %d / %d chunks in database", stored_count, len(chunks))
        return ""

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return []

    def shutdown(self) -> None:
        pass
