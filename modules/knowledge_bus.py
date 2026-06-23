"""
Knowledge Bus - Drewgent's Central Knowledge Store

Provides a shared knowledge base that connects all Drewgent modules:
- NeuronFS (memory/brain)
- VerificationEngine (quality gate)
- GrowthEngine (pattern discovery)
- RevisionLoop (revision logic)

Knowledge Flow:
    Module produces knowledge
        ↓
    Knowledge Bus stores it
        ↓
    Other modules query it
        ↓
    Better decisions

Usage:
    from modules.knowledge_bus import KnowledgeBus, Knowledge

    kb = KnowledgeBus.get_instance()

    # Store knowledge
    kb.store(Knowledge(
        source="revision_loop",
        type="pattern",
        content="completeness fails for research tasks",
        confidence=0.8,
        tags=["verification", "completeness"],
    ))

    # Query knowledge
    results = kb.query(tags=["verification"])
"""

import json
import os
import threading
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, List


@dataclass
class Knowledge:
    """A unit of knowledge in the Drewgent knowledge base."""

    source: str  # Module that created this knowledge
    type: str  # Type: pattern, insight, check_result, revision_insight, etc.
    content: str  # The knowledge content
    confidence: float  # 0.0 - 1.0
    tags: List[str]  # Tags for querying
    timestamp: str = ""  # Auto-set on creation
    id: str = ""  # Auto-generated

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"
        if not self.id:
            self.id = f"{self.source}_{self.timestamp}_{hash(self.content) % 10000}"


class KnowledgeBus:
    """
    Central knowledge store connecting all Drewgent modules.

    Singleton - single source of truth for knowledge.
    Persists to JSON file.

    Thread-safe: All operations are protected by a reentrant lock.
    """

    _instance = None
    _lock = threading.RLock()  # Class-level lock for thread safety

    def __init__(self):
        """Initialize Knowledge Bus."""
        self.knowledge_store: List[Knowledge] = []
        self._load_knowledge()

    @classmethod
    def get_instance(cls):
        """Get singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def store(self, knowledge: Knowledge) -> None:
        """
        Store a knowledge fragment.

        Args:
            knowledge: Knowledge object to store
        """
        with self._lock:
            self.knowledge_store.append(knowledge)
            self._save_knowledge()

    def store_from_module(
        self,
        module: str,
        content: str,
        knowledge_type: str = "insight",
        confidence: float = 0.5,
        tags: List[str] = None,
    ) -> None:
        """
        Convenience method to store knowledge from a module.

        Args:
            module: Source module name
            content: Knowledge content
            knowledge_type: Type of knowledge
            confidence: Confidence level (0.0 - 1.0)
            tags: Tags for this knowledge
        """
        if tags is None:
            tags = [module]

        knowledge = Knowledge(
            source=module,
            type=knowledge_type,
            content=content,
            confidence=confidence,
            tags=tags,
        )
        self.store(knowledge)

    def query(
        self,
        tags: List[str] = None,
        source: str = None,
        knowledge_type: str = None,
        min_confidence: float = 0.0,
        limit: int = 10,
    ) -> List[Knowledge]:
        """
        Query knowledge by tags, source, type, or confidence.

        Args:
            tags: Match any of these tags
            source: Match this source module
            knowledge_type: Match this type
            min_confidence: Minimum confidence level
            limit: Maximum results to return

        Returns:
            List of matching Knowledge objects
        """
        with self._lock:
            results = []

            for k in self.knowledge_store:
                # Filter by tags (any match)
                if tags:
                    if not any(tag in k.tags for tag in tags):
                        continue

                # Filter by source
                if source and k.source != source:
                    continue

                # Filter by type
                if knowledge_type and k.type != knowledge_type:
                    continue

                # Filter by confidence
                if k.confidence < min_confidence:
                    continue

                results.append(k)

            # Sort by confidence (highest first) and timestamp (newest first)
            results.sort(
                key=lambda x: (
                    -x.confidence,
                    -datetime.fromisoformat(x.timestamp.replace("Z", "+00:00")).timestamp(),
                )
            )

            return results[:limit]

    def get_recent(self, limit: int = 10) -> List[Knowledge]:
        """Get most recent knowledge fragments."""
        with self._lock:
            sorted_knowledge = sorted(
                self.knowledge_store,
                key=lambda x: datetime.fromisoformat(
                    x.timestamp.replace("Z", "+00:00")
                ).timestamp(),
                reverse=True,
            )
            return sorted_knowledge[:limit]

    def get_by_source(self, source: str) -> List[Knowledge]:
        """Get all knowledge from a specific source."""
        with self._lock:
            return [k for k in self.knowledge_store if k.source == source]

    def get_stats(self) -> dict:
        """Get statistics about the knowledge base."""
        with self._lock:
            total = len(self.knowledge_store)
            by_source = {}
            by_type = {}
            avg_confidence = 0.0

            for k in self.knowledge_store:
                by_source[k.source] = by_source.get(k.source, 0) + 1
                by_type[k.type] = by_type.get(k.type, 0) + 1
                avg_confidence += k.confidence

            avg_confidence = avg_confidence / total if total > 0 else 0.0

            return {
                "total_knowledge": total,
                "by_source": by_source,
                "by_type": by_type,
                "avg_confidence": round(avg_confidence, 3),
            }

    def reset(self) -> None:
        """Clear all knowledge (use with caution!)."""
        with self._lock:
            self.knowledge_store.clear()
            self._save_knowledge()

    def _get_knowledge_path(self) -> Path:
        """Get path to knowledge store file."""
        hermes_home = os.environ.get("HERMES_HOME")
        if hermes_home:
            hermes_path = Path(hermes_home)
        else:
            hermes_path = Path.home() / ".drewgent"
        return hermes_path / "drewgent_knowledge.json"

    def _load_knowledge(self) -> None:
        """Load knowledge from file."""
        path = self._get_knowledge_path()
        if not path.exists():
            return

        try:
            with open(path, "r") as f:
                data = json.load(f)

            for k_data in data.get("knowledge_store", []):
                self.knowledge_store.append(Knowledge(**k_data))
        except Exception as e:
            print(f"[Knowledge Bus] Failed to load: {e}")

    def _save_knowledge(self) -> None:
        """Save knowledge to file."""
        path = self._get_knowledge_path()
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "knowledge_store": [asdict(k) for k in self.knowledge_store],
            "last_updated": datetime.utcnow().isoformat() + "Z",
        }

        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[Knowledge Bus] Failed to save: {e}")


def get_knowledge_bus() -> KnowledgeBus:
    """Convenience function to get Knowledge Bus instance."""
    return KnowledgeBus.get_instance()
