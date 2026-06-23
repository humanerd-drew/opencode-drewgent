"""AutoLearning Module - Automatic Pattern Extraction to Obsidian Wiki

This module provides automatic learning capabilities that extract:
- User preferences and communication style
- Environmental facts and tool preferences
- Interaction patterns and corrections

Output is in Karpathy's LLM Wiki / Obsidian-compatible Markdown format:
- Individual markdown files with YAML frontmatter
- Wikilinks for cross-references
- Tags for Dataview queries
- Daily log for chronological tracking
- Semantic search via MiniMax embeddings (or local fallback)
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Set, List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, field

from agent.obsidian_graph import (
    ensure_backlink,
    links_frontmatter_lines,
    wiki_link,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Obsidian Wiki Structure
# ---------------------------------------------------------------------------

WIKI_STRUCTURE = {
    "entities": "entities",
    "concepts": "concepts",
    "insights_log": "insights",
    "retired": "retired",
}


# ---------------------------------------------------------------------------
# Insight Types -> Wiki Categories
# ---------------------------------------------------------------------------

INSIGHT_CATEGORIES = {
    "preference": ("entities", "preferences"),
    "name": ("entities", "user-profile"),
    "role": ("entities", "user-profile"),
    "field": ("entities", "user-profile"),
    "timezone": ("entities", "user-profile"),
    "style_concise": ("entities", "communication-style"),
    "style_detailed": ("entities", "communication-style"),
    "correction": ("entities", "corrections"),
    "anti_preference": ("entities", "preferences"),
    "os": ("entities", "environment"),
    "tool": ("entities", "environment"),
    "project": ("entities", "environment"),
    "concept": ("concepts", "recurring-topics"),
}

INSIGHT_TAGS = {
    "preference": ["user", "preference"],
    "name": ["user", "identity"],
    "role": ["user", "identity"],
    "field": ["user", "identity"],
    "timezone": ["user", "identity"],
    "style_concise": ["user", "communication"],
    "style_detailed": ["user", "communication"],
    "correction": ["user", "correction"],
    "anti_preference": ["user", "preference"],
    "os": ["environment", "os"],
    "tool": ["environment", "tool"],
    "project": ["environment", "project"],
    "concept": ["concept", "insight"],
}

# =============================================================================
# SESSION WORKFLOW PATTERNS (P4-Cortex integration)
# =============================================================================

# Path to where session workflow JSON files are stored
_P4_CORTEX_PATTERNS_DIR = Path.home() / ".drewgent" / "P4-cortex" / "growth" / "patterns"


# ---------------------------------------------------------------------------
# Embeddings Provider (MiniMax API → Ollama fallback)
# ---------------------------------------------------------------------------

# Priority: MiniMax API (if key + working) → Ollama (local) → None


def get_minimax_embedding(texts: list[str]) -> Optional[list[list[float]]]:
    """Get embeddings from MiniMax API.

    Requires MINIMAX_API_KEY environment variable.
    Uses the emb-01 model with "texts" parameter.

    Returns list of embedding vectors or None if API unavailable.
    """
    api_key = os.getenv("MINIMAX_API_KEY")
    if not api_key:
        logger.debug("MINIMAX_API_KEY not set")
        return None

    try:
        import urllib.request

        url = "https://api.minimax.io/v1/embeddings"
        payload = json.dumps(
            {
                "model": "embo-01",
                "texts": texts,  # MiniMax uses "texts" not "input"
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            # MiniMax returns {"vectors": [...]} not {"data": [...]}
            if result.get("vectors"):
                return result["vectors"]
            logger.debug(f"MiniMax returned no vectors: {result}")
            return None

    except Exception as e:
        logger.debug(f"MiniMax embeddings API failed: {e}")
        return None


def get_ollama_embedding(
    texts: list[str], model: str = "nomic-embed-text"
) -> Optional[list[list[float]]]:
    """Get embeddings from local Ollama server.

    Requires Ollama server running (localhost:11434).
    Falls back to qwen2.5:latest if nomic-embed-text not available.

    Returns list of embedding vectors or None if Ollama unavailable.
    """
    try:
        import urllib.request

        url = "http://localhost:11434/api/embeddings"

        # Try nomic-embed-text first, fallback to qwen2.5:latest
        for model_name in [model, "qwen2.5:latest"]:
            try:
                payload = json.dumps(
                    {
                        "model": model_name,
                        "prompt": texts[0] if texts else "",
                    }
                ).encode("utf-8")

                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )

                with urllib.request.urlopen(req, timeout=30) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    if "embedding" in result:
                        return [result["embedding"]]
                    # Ollama returns {"embedding": [...]} for single text
                    if "embeddings" in result:
                        return result["embeddings"]

            except Exception:
                continue

        logger.debug("Ollama: no working embedding model found")
        return None

    except Exception as e:
        logger.debug(f"Ollama embeddings failed: {e}")
        return None


def get_embedding(texts: list[str]) -> Optional[list[list[float]]]:
    """Get embeddings with automatic provider selection.

    Priority: MiniMax API → Ollama (local) → None

    Returns list of embedding vectors or None if all providers fail.
    """
    # Try MiniMax first
    result = get_minimax_embedding(texts)
    if result:
        logger.debug(f"Using MiniMax embeddings ({len(result)} vectors)")
        return result

    # Fall back to Ollama
    result = get_ollama_embedding(texts)
    if result:
        logger.debug(f"Using Ollama embeddings ({len(result)} vectors)")
        return result

    logger.debug("No embedding provider available")
    return None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ---------------------------------------------------------------------------
# Vector Store (SQLite-based)
# ---------------------------------------------------------------------------


class VectorStore:
    """Lightweight vector store using SQLite + JSON embeddings."""

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._ensure_db()

    def _ensure_db(self) -> None:
        """Create tables if not exist."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vectors (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                embedding TEXT NOT NULL,
                itype TEXT,
                target TEXT,
                created_at TEXT,
                last_accessed TEXT DEFAULT '',
                access_count INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()

    def add(
        self,
        id: str,
        content: str,
        embedding: list[float],
        itype: str = "",
        target: str = "",
    ) -> bool:
        """Add an embedding to the store."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            conn.execute(
                """
                INSERT OR REPLACE INTO vectors (id, content, embedding, itype, target, created_at, last_accessed, access_count)
                VALUES (?, ?, ?, ?, ?, ?, '', 0)
            """,
                (
                    id,
                    content,
                    json.dumps(embedding),
                    itype,
                    target,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.debug(f"VectorStore add failed: {e}")
            return False

    def search(self, query_embedding: list[float], limit: int = 5) -> list[dict]:
        """Search for most similar vectors."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            cursor = conn.execute(
                "SELECT id, content, embedding, itype, target, access_count FROM vectors"
            )
            rows = cursor.fetchall()

            results = []
            for row in rows:
                stored_embedding = json.loads(row[2])
                score = cosine_similarity(query_embedding, stored_embedding)
                results.append(
                    {
                        "id": row[0],
                        "content": row[1],
                        "score": score,
                        "itype": row[3],
                        "target": row[4],
                        "access_count": row[5],
                    }
                )

            # Touch IDs for access tracking
            for r in results:
                if r.get("id"):
                    self._vector_store.touch(r["id"]) if self._vector_store else None

            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:limit]

        except Exception as e:
            logger.debug(f"VectorStore search failed: {e}")
            return []

    def count(self) -> int:
        """Return total number of stored embeddings."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            cursor = conn.execute("SELECT COUNT(*) FROM vectors")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0

    def touch(self, id: str) -> None:
        """Record that vector id was accessed (increment count, update timestamp)."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            conn.execute(
                """
                UPDATE vectors
                SET last_accessed = ?, access_count = access_count + 1
                WHERE id = ?
                """,
                (datetime.now().isoformat(), id),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    def get_access_stats(self) -> dict:
        """Return overall access statistics."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            cursor = conn.execute(
                """
                SELECT COUNT(*), SUM(access_count), MAX(last_accessed)
                FROM vectors
                WHERE last_accessed != ''
                """
            )
            row = cursor.fetchone()
            conn.close()
            return {
                "total_accessed": row[0] or 0,
                "total_access_count": row[1] or 0,
                "last_accessed": row[2] or "",
            }
        except Exception:
            return {"total_accessed": 0, "total_access_count": 0, "last_accessed": ""}


# ---------------------------------------------------------------------------
# Insight Dataclass
# ---------------------------------------------------------------------------


@dataclass
class Insight:
    """A single insight extracted from conversation."""

    target: str  # "user" or "memory"
    itype: str  # insight type
    content: str
    context: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    last_accessed: str = ""  # ISO timestamp of last query_wiki hit
    access_count: int = 0  # how many times this entry was returned by query_wiki
    lifetime_days: int = 90  # retire after this many days of no access (0=never)
    retired: bool = False  # true = moved to retired/ folder

    def get_wiki_category(self) -> Tuple[str, str]:
        """Get (folder, filename) for wiki storage."""
        cats = INSIGHT_CATEGORIES.get(self.itype, ("entities", "general"))
        return cats[0], cats[1]

    def get_tags(self) -> List[str]:
        """Get Obsidian tags for this insight."""
        return INSIGHT_TAGS.get(self.itype, ["insight", "general"])

    def touch(self) -> None:
        """Mark this entry as accessed right now."""
        self.last_accessed = datetime.now().isoformat()
        self.access_count += 1

    def should_retire(self, now: datetime) -> bool:
        """Check if this entry should be retired based on access patterns.

        Retirement criteria:
        - Never accessed and 180+ days old: hard retire
        - Never accessed and 90+ days with no insights: cold retire
        - Low engagement (120+ days with <=1 insight): low engagement retire
        """
        age_days = (now - datetime.fromisoformat(self.timestamp)).days
        if age_days >= 180:
            return True
        if age_days >= 90 and self.access_count == 0:
            return True
        if age_days >= 120 and self.access_count <= 1:
            return True
        return False


# ---------------------------------------------------------------------------
# Pattern Definitions
# ---------------------------------------------------------------------------

# User preference patterns
_USER_PATTERNS = [
    (
        r"(?:I prefer|I like|I love|I hate|I'm a|my favorite|my favourite)[:\s]+([^.!?]+)",
        "preference",
    ),
    (r"(?:call me|named?)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", "name"),
    (r"(?:I work as|I'm a|my role is|my job is)[:\s]+([^.!?]+)", "role"),
    (r"(?:I'm in|I'm working in)[:\s]+([^.!?]+)", "field"),
    (r"(?:my timezone is|I'm in timezone)[:\s]+([^.!?]+)", "timezone"),
]

# Implicit preference patterns — learn from short/command inputs
# These recognize user signals without explicit "I prefer X" phrasing
_SENTIMENT_POSITIVE = frozenset({
    "thanks", "nice", "great", "perfect", "ok", "okay",
    "yep", "yeah", "yes", "good", "good job", "cool",
})
_SENTIMENT_NEGATIVE = frozenset({"no", "nah", "nope", "wait", "actually", "no,"})
_SHORT_TOOL_COMMANDS = frozenset({
    "grep", "find", "ls", "ps", "cat", "head", "tail",
    "sed", "awk", "ssh", "scp", "rsync", "git", "docker", "python",
    "curl", "wget", "tar", "zip", "unzip", "chmod", "chown",
    "kill", "pkill", "pgrep", "top", "htop",
})


def _detect_implicit_style(text: str) -> tuple[str, str] | None:
    """Detect implicit style preference from short user input.

    Returns:
        (itype, content) tuple if matched, None otherwise.
    """
    t = text.lower().strip().rstrip(",.!?")

    # Single command word → command-style preference
    if t in ("agent", "agi", "autonomous", "single"):
        return "style_command", f"from short input: {text.strip()[:60]}"

    # Positive sentiment → concise confirmation style
    if t in _SENTIMENT_POSITIVE:
        return "style_concise", f"from short input: {text.strip()[:60]}"

    # Compound positive: "nice thanks" / "great job" / "ok sure" / "nice, thanks" etc.
    words = t.split()
    if len(words) == 2:
        w0 = words[0].rstrip(",.!?")
        w1 = words[1].rstrip(",.!?")
        if w0 in _SENTIMENT_POSITIVE and w1 in _SENTIMENT_POSITIVE:
            return "style_concise", f"from short input: {text.strip()[:60]}"

    # Negative sentiment → cautious style
    if t in _SENTIMENT_NEGATIVE:
        return "style_cautious", f"from short input: {text.strip()[:60]}"

    # Tool command prefix (grep, git, docker, etc.) → tool preference
    first_word = t.split()[0] if t.split() else ""
    if first_word in _SHORT_TOOL_COMMANDS:
        return "tool", f"from short input: {text.strip()[:60]}"

    # Long detailed input → prefer detailed responses
    if len(text) >= 80:
        return "style_detailed", f"from short input: {text.strip()[:60]}"

    return None

# Communication style patterns
_STYLE_PATTERNS = [
    (r"be\s+(?:brief|short|concise|to the point)", "style_concise"),
    (
        r"(?:keep it short|don't overexplain|just the facts|don't repeat)",
        "style_concise",
    ),
    (
        r"(?:explain|dig deeper|tell me more|give me details|in detail|step by step)",
        "style_detailed",
    ),
]

# Correction patterns
_CORRECTION_PATTERNS = [
    (r"(?:no[, ]|actually[,]|not quite)[:\s]+([^.!?]+)", "correction"),
    (r"(?:that's wrong|incorrect|I meant)[:\s]+([^.!?]+)", "correction"),
]

# Environment/technical facts
_ENV_PATTERNS = [
    (
        r"(?:on|using|running)[:\s]*(?:my |the )?(Mac|Linux|Windows|Ubuntu|Debian|CentOS|macOS|iOS|Android)",
        "os",
    ),
    (r"(?:using|with)[:\s]+([A-Za-z][^.\s]+?)(?:\s|$|\.|\,)", "tool"),
]

# Anti-preference patterns
_ANTI_PATTERNS = [
    (r"(?:don't|not)[:\s]+([A-Za-z][^.!?]+)", "anti_preference"),
]


# ---------------------------------------------------------------------------
# Obsidian Wiki Writer
# ---------------------------------------------------------------------------


class ObsidianWriter:
    """Writes insights to Obsidian wiki format."""

    def __init__(self, wiki_path: Path):
        self._wiki_path = wiki_path
        self._ensure_structure()

    def _ensure_structure(self) -> None:
        """Create wiki directory structure if it doesn't exist."""
        self._wiki_path.mkdir(parents=True, exist_ok=True)
        for folder in WIKI_STRUCTURE.values():
            (self._wiki_path / folder).mkdir(parents=True, exist_ok=True)

        # Create SCHEMA.md if not exists
        schema_path = self._wiki_path / "SCHEMA.md"
        if not schema_path.exists():
            self._write_schema(schema_path)

        # Create index.md if not exists
        index_path = self._wiki_path / "index.md"
        if not index_path.exists():
            self._write_index(index_path)

        for folder in ("entities", "concepts", "insights"):
            category_index = self._wiki_path / folder / "index.md"
            if not category_index.exists():
                self._write_category_index(category_index, folder)

        for folder, filename in sorted(set(INSIGHT_CATEGORIES.values())):
            page_path = self._wiki_path / folder / f"{filename}.md"
            if not page_path.exists():
                tags = ["auto", folder, filename]
                page_path.write_text(
                    self._create_new_page(filename, tags, folder),
                    encoding="utf-8",
                )
                self._ensure_parent_links(page_path, folder)

    def _write_schema(self, path: Path) -> None:
        """Write SCHEMA.md with wiki conventions."""
        content = """---
title: SCHEMA
tags: [meta, wiki]
links:
  - "[[index]]"
---

# Wiki Schema

This is a Karpathy-style LLM Wiki - a persistent, compounding knowledge base.

## Structure

- [[entities/index]] - Entity pages (people, preferences, environment)
- [[concepts/index]] - Concept pages (ideas, patterns)
- [[insights/index]] - Daily insight logs

## Conventions

### Tags
- `#user` - User-related facts
- `#preference` - User preferences
- `#identity` - User identity
- `#communication` - Communication style
- `#correction` - Corrections made
- `#environment` - Technical environment
- `#insight` - Automatically extracted insights

### Wikilinks
- Use wikilinks for real notes, for example entities/environment
- Escape syntax examples when they are not real notes

### Frontmatter
Every page should have:
```yaml
---
tags: [...]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

## Updating Pages

1. Add new content to relevant entity page
2. Update the Log section with timestamp
3. Index is auto-updated; verify monthly

---
*Auto-generated by Drewgent Auto-Learning*
"""
        path.write_text(content, encoding="utf-8")

    def _write_index(self, path: Path) -> None:
        """Write index.md."""
        content = """---
title: Index
tags: [meta, wiki]
links:
  - "[[SCHEMA]]"
---

# Wiki Index

Auto-generated table of contents for the knowledge base.

## Entities
- [[entities/preferences]] - User preferences
- [[entities/user-profile]] - User identity
- [[entities/environment]] - Technical environment
- [[entities/communication-style]] - Communication preferences
- [[entities/corrections]] - Past corrections

## Concepts
- (Add concept pages here as they emerge)

## Daily Logs
- [[insights/YYYY-MM]] - Monthly insight logs
"""
        content = content.replace("YYYY-MM", datetime.now().strftime("%Y-%m"))
        path.write_text(content, encoding="utf-8")

    def _write_category_index(self, path: Path, folder: str) -> None:
        """Write a category index so generated pages have a parent node."""
        title = folder.replace("-", " ").title()
        today = datetime.now().strftime("%Y-%m-%d")
        content = f"""---
title: {title} Index
tags: [meta, wiki, {folder}]
created: {today}
updated: {today}
links:
  - "[[index]]"
  - "[[SCHEMA]]"
---

# {title} Index

Auto-generated category index.
"""
        path.write_text(content, encoding="utf-8")

    def write_insight(self, insight: Insight) -> bool:
        """Write an insight to the appropriate wiki page."""
        try:
            folder, filename = insight.get_wiki_category()
            page_path = self._wiki_path / folder / f"{filename}.md"

            # Read existing content or create new
            if page_path.exists():
                content = page_path.read_text(encoding="utf-8")
            else:
                content = self._create_new_page(filename, insight.get_tags(), folder)

            # Add insight to page
            updated_content = self._add_insight_to_page(content, insight)
            page_path.write_text(updated_content, encoding="utf-8")
            self._ensure_parent_links(page_path, folder)

            # Also append to daily log
            self._append_to_daily_log(insight)

            return True
        except Exception as e:
            logger.debug("ObsidianWriter: failed to write insight: %s", e)
            return False

    def _create_new_page(self, filename: str, tags: List[str], folder: str) -> str:
        """Create a new wiki page with frontmatter."""
        title = filename.replace("-", " ").title()
        today = datetime.now().strftime("%Y-%m-%d")
        tag_str = ", ".join(f'"{t}"' for t in tags)
        links = [
            wiki_link("index"),
            wiki_link("SCHEMA"),
            wiki_link(f"{folder}/index"),
        ]
        link_lines = "\n".join(links_frontmatter_lines(links))

        return f"""---
title: {title}
tags: [{tag_str}]
created: {today}
updated: {today}
{link_lines}
---

# {title}

## Known Facts



## Log

- {today}: Initial entry created
---

*Auto-generated by Drewgent Auto-Learning*
"""

    def _ensure_parent_links(self, page_path: Path, folder: str) -> None:
        """Make category/root indexes point back to a generated page."""
        for parent in (
            self._wiki_path / "index.md",
            self._wiki_path / folder / "index.md",
        ):
            ensure_backlink(parent, page_path, self._wiki_path)

    def _add_insight_to_page(self, content: str, insight: Insight) -> str:
        """Add an insight to an existing page."""
        today = datetime.now().strftime("%Y-%m-%d")
        tags = insight.get_tags()
        tag_str = ", ".join(f"#{t}" for t in tags)

        # Format the insight entry
        insight_entry = self._format_insight_entry(insight, today, tag_str)

        # Find insertion point - before the footer or at end
        footer_marker = "\n---\n*Auto-generated"
        if footer_marker in content:
            parts = content.split(footer_marker)
            # Insert before footer, after "Log" section
            log_marker = "## Log"
            if log_marker in parts[0]:
                log_parts = parts[0].split(log_marker)
                if len(log_parts) > 1:
                    # Insert at end of log section
                    log_content = log_parts[1]
                    lines = log_content.strip().split("\n")
                    # Find where log entries end
                    insert_idx = len(lines)
                    for i, line in enumerate(lines):
                        if line.startswith("---") or line.startswith("*Auto"):
                            insert_idx = i
                            break
                    new_log_lines = (
                        lines[:insert_idx] + [insight_entry] + lines[insert_idx:]
                    )
                    parts[0] = log_marker.join([log_parts[0], "\n".join(new_log_lines)])
                else:
                    parts[0] += "\n\n## Log\n\n" + insight_entry
            else:
                parts[0] += f"\n\n## Log\n\n{insight_entry}\n"
            content = footer_marker.join(parts)
        else:
            # No footer, just append
            content += f"\n\n{insight_entry}\n"

        # Update the "updated" frontmatter
        content = re.sub(
            r"^updated: .+$", f"updated: {today}", content, flags=re.MULTILINE
        )

        return content

    def _format_insight_entry(self, insight: Insight, today: str, tag_str: str) -> str:
        """Format an insight as a wiki entry."""
        content = insight.content.strip()
        itype = insight.itype.replace("_", "-")

        # Context if available
        context_str = ""
        if insight.context:
            context_str = f" *(context: {insight.context[:50]}...)*"

        return f"- {today}: {tag_str} {content}{context_str} ^{itype}-{today.replace('-', '')}"

    def _append_to_daily_log(self, insight: Insight) -> None:
        """Append insight to daily log file."""
        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")
        tags = insight.get_tags()
        tag_str = ", ".join(f"#{t}" for t in tags)

        log_dir = self._wiki_path / WIKI_STRUCTURE["insights_log"]
        log_dir.mkdir(parents=True, exist_ok=True)

        log_path = log_dir / f"{month}.md"

        if log_path.exists():
            content = log_path.read_text(encoding="utf-8")
            # Check if already logged today
            if f"## {today}" in content:
                # Find today's section boundaries
                marker = f"## {today}"
                idx = content.find(marker)
                next_marker = content.find("\n## ", idx + 1)
                section_end = next_marker if next_marker > 0 else len(content)

                # Check if this insight is already in today's section
                today_section = content[idx:section_end]
                if insight.content not in today_section:
                    # Append to today's section
                    entry = f"- {tag_str} {insight.content}\n"
                    content = content[:section_end] + entry + content[section_end:]
            else:
                # Add new day section
                content += f"\n## {today}\n\n- {tag_str} {insight.content}\n"
        else:
            # Create monthly log
            content = f"""---
title: Insights {month}
tags: [insights, log]
created: {month}-01
updated: {today}
links:
  - "[[index]]"
  - "[[insights/index]]"
---

# Insights Log: {month}

## {today}

- {tag_str} {insight.content}
"""
        log_path.write_text(content, encoding="utf-8")
        self._ensure_parent_links(log_path, WIKI_STRUCTURE["insights_log"])

    def update_index(self) -> None:
        """Update index.md with current state."""
        index_path = self._wiki_path / "index.md"
        entities_path = self._wiki_path / "entities"
        concepts_path = self._wiki_path / "concepts"

        # Find all entity files
        entities = []
        if entities_path.exists():
            for f in sorted(entities_path.glob("*.md")):
                name = f.stem.replace("-", " ").title()
                link = f"[[entities/{f.stem}]]"
                entities.append(f"- {link} - {name}")

        entity_list = "\n".join(entities) if entities else "- (none yet)"

        concepts = []
        if concepts_path.exists():
            for f in sorted(concepts_path.glob("*.md")):
                if f.stem == "index":
                    continue
                name = f.stem.replace("-", " ").title()
                link = f"[[concepts/{f.stem}]]"
                concepts.append(f"- {link} - {name}")
        concept_list = "\n".join(concepts) if concepts else "- (none yet)"

        content = f"""---
title: Index
tags: [meta, wiki]
updated: {datetime.now().strftime("%Y-%m-%d")}
links:
  - "[[SCHEMA]]"
  - "[[entities/index]]"
  - "[[concepts/index]]"
  - "[[insights/index]]"
---

# Wiki Index

Auto-generated table of contents for the knowledge base.

## Entities
{entity_list}

## Concepts
{concept_list}

## Daily Logs
- [[insights/{datetime.now().strftime("%Y-%m")}]] - Current month

---
*Auto-updated by Drewgent Auto-Learning*
"""
        index_path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Maintenance: stale retirement, deduplication, autonomous growth
# --------------------------------------------------------------------------


def _parse_frontmatter_date(content: str, key: str = "updated") -> Optional[str]:
    """Extract a date from frontmatter, or None if not found."""
    m = re.search(rf"^{key}: (\d{{4}}-\d{{2}}-\d{{2}})", content, re.MULTILINE)
    return m.group(1) if m else None


def _parse_daily_entry_date(line: str) -> Optional[str]:
    """Extract YYYY-MM-DD from a daily log entry line like '- 2026-05-08: ...'."""
    m = re.match(r"- (\d{4}-\d{2}-\d{2}):", line)
    return m.group(1) if m else None


def _normalize_content(text: str) -> str:
    """Strip wiki formatting for dedup comparison."""
    # Remove Obsidian block anchors ^foo-bar
    text = re.sub(r"\s*\^[a-zA-Z0-9_-]+", "", text)
    # Remove date prefix '- 2026-05-08:'
    text = re.sub(r"- \d{4}-\d{2}-\d{2}:\s*", "", text)
    # Remove tags #foo, #bar
    text = re.sub(r"\s*(?:^|\s)#[a-zA-Z0-9_-]+", "", text)
    # Remove context parentheticals
    text = re.sub(r"\s*\*\(context: [^)]+\)\*", "", text)
    # Collapse whitespace
    return re.sub(r"\s+", " ", text).strip().lower()


class WikiMaintenance:
    """Autonomous wiki maintenance operations."""

    def __init__(self, wiki_path: Path):
        self._wiki_path = wiki_path
        self._retired_path = wiki_path / WIKI_STRUCTURE["retired"]
        self._retired_path.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1. retire_stale_entries
    # ------------------------------------------------------------------

    def retire_stale_entries(self, dry_run: bool = False) -> dict:
        """Move entries to retired/ based on access frequency signals.

        Retirement decision (in priority order):
        1. Never updated in 180+ days: hard retire
        2. No new insights in 90+ days AND 0 insight blocks: cold retire
        3. 120+ days old with no activity: low engagement retire

        Returns dict with counts of examined / retired / errors.
        """
        now = datetime.now()
        examined = 0
        retired = 0
        errors = 0

        for folder in ("entities", "concepts", "insights"):
            folder_path = self._wiki_path / WIKI_STRUCTURE.get(folder, folder)
            if not folder_path.exists():
                continue

            for md_file in folder_path.glob("*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")
                    updated = _parse_frontmatter_date(content, "updated")
                    if not updated:
                        continue

                    try:
                        updated_dt = datetime.strptime(updated, "%Y-%m-%d")
                    except ValueError:
                        continue

                    days_since_update = (now - updated_dt).days

                    # Count insight log entries in this file
                    insight_blocks = re.findall(r'- \d{4}-\d{2}-\d{2}:', content)
                    insight_count = len(insight_blocks)
                    age_days = days_since_update

                    # Decision matrix
                    if age_days >= 180:
                        # Hard retire: never touched in 6+ months
                        should_retire = True
                        reason = "hard (180+ days)"
                    elif age_days >= 90 and insight_count == 0:
                        # Cold: old and completely empty of insights
                        should_retire = True
                        reason = "cold (90+ days, 0 insights)"
                    elif age_days >= 120 and insight_count <= 1:
                        # Low engagement: old with minimal activity
                        should_retire = True
                        reason = "low engagement (120+ days)"
                    else:
                        should_retire = False

                    if not should_retire:
                        continue

                    examined += 1

                    if dry_run:
                        logger.info(
                            "[WikiMaintenance] would retire (%s, updated %s, %d days ago, %d insights): %s",
                            reason, updated, days_since_update, insight_count, md_file.name,
                        )
                        continue

                    # Move to retired/
                    retired_name = f"retired-{md_file.name}"
                    retired_file = self._retired_path / retired_name
                    md_file.rename(retired_file)
                    logger.info(
                        "[WikiMaintenance] retired (%s, updated %s, %d days ago, %d insights): %s -> %s",
                        reason, updated, days_since_update, insight_count, md_file.name, retired_file.name,
                    )
                    retired += 1

                except Exception as e:
                    logger.debug("retire_stale_entries error on %s: %s", md_file.name, e)
                    errors += 1

        return {"examined": examined, "retired": retired, "errors": errors}

    # ------------------------------------------------------------------
    # 2. deduplicate_wiki
    # ------------------------------------------------------------------

    def deduplicate_wiki(self, dry_run: bool = False) -> dict:
        """Merge visually duplicate daily log entries within the same monthly log.

        Entries are considered duplicates if their normalized content matches
        (ignoring date, tags, context). Only the most recent entry is kept.
        """
        log_dir = self._wiki_path / WIKI_STRUCTURE["insights_log"]
        if not log_dir.exists():
            return {"files_scanned": 0, "duplicates_found": 0, "duplicates_removed": 0}

        files_scanned = 0
        duplicates_found = 0
        duplicates_removed = 0

        for log_file in log_dir.glob("*.md"):
            try:
                content = log_file.read_text(encoding="utf-8")
                original_len = len(content)

                # Split into lines
                lines = content.split("\n")
                seen: dict[str, str] = {}  # normalized → full line (most recent wins)

                # Pass 1: identify duplicates
                for line in lines:
                    date_str = _parse_daily_entry_date(line)
                    if not date_str:
                        continue
                    normalized = _normalize_content(line)
                    if not normalized:
                        continue
                    if normalized in seen:
                        duplicates_found += 1
                        seen[normalized] = line  # update to newer entry
                    else:
                        seen[normalized] = line

                # Pass 2: collect lines to remove (older duplicates)
                to_remove: set[str] = set()
                for line in lines:
                    date_str = _parse_daily_entry_date(line)
                    if not date_str:
                        continue
                    normalized = _normalize_content(line)
                    if not normalized:
                        continue
                    if normalized in seen and seen[normalized] != line:
                        to_remove.add(line)
                        seen[normalized] = line  # keep the newer one

                if not to_remove:
                    files_scanned += 1
                    continue

                # Remove duplicate lines
                new_lines = [l for l in lines if l not in to_remove]
                new_content = "\n".join(new_lines)

                if dry_run:
                    logger.info(
                        "[WikiMaintenance] would dedup %s: remove %d duplicate lines",
                        log_file.name, len(to_remove),
                    )
                else:
                    log_file.write_text(new_content, encoding="utf-8")
                    logger.info(
                        "[WikiMaintenance] deduped %s: removed %d duplicate lines",
                        log_file.name, len(to_remove),
                    )

                duplicates_removed += len(to_remove)
                files_scanned += 1

            except Exception as e:
                logger.debug("deduplicate_wiki error on %s: %s", log_file.name, e)
                files_scanned += 1

        return {
            "files_scanned": files_scanned,
            "duplicates_found": duplicates_found,
            "duplicates_removed": duplicates_removed,
        }

    # ------------------------------------------------------------------
    # 3. autonomous_growth — gap detection + wiki augmentation
    # ------------------------------------------------------------------

    def detect_knowledge_gaps(self) -> List[str]:
        """Identify topics the user has asked about but lack wiki coverage."""
        gaps: List[str] = []

        # Check if any entity files exist for recent topics
        entities_path = self._wiki_path / "entities"
        existing = (
            {f.stem.replace("-", " ").lower() for f in entities_path.glob("*.md")}
            if entities_path.exists()
            else set()
        )

        # Common topic areas we track but may not have entries for
        tracked_topics = [
            "preferences", "communication-style", "environment",
            "corrections", "user-profile",
        ]
        for topic in tracked_topics:
            topic_key = topic.lower().replace("-", " ")
            if topic_key not in existing and topic_key.replace(" ", "-") not in existing:
                gaps.append(topic)

        return gaps

    def run_autonomous_maintenance(self, dry_run: bool = False) -> dict:
        """Run all maintenance operations and return a summary dict."""
        retire_result = self.retire_stale_entries(dry_run=dry_run)
        dedup_result = self.deduplicate_wiki(dry_run=dry_run)
        gaps = self.detect_knowledge_gaps()

        return {
            "retire": retire_result,
            "dedup": dedup_result,
            "gaps_detected": gaps,
            "dry_run": dry_run,
        }


# ---------------------------------------------------------------------------
# AutoLearner (Obsidian Wiki Edition)
# ---------------------------------------------------------------------------
class AutoLearner:
    """
    Extracts insights from conversation turns and writes to Obsidian wiki.

    Tracks learned facts to avoid duplicates. Outputs to Karpathy's LLM Wiki
    format with proper Obsidian frontmatter, tags, and wikilinks.

    Supports semantic search via MiniMax embeddings (when MINIMAX_API_KEY is set).
    """

    def __init__(
        self,
        wiki_path: Optional[Path] = None,
        enabled: bool = False,
        max_per_turn: int = 2,
        semantic_search: bool = True,
    ):
        self._enabled = enabled
        self._max_per_turn = max_per_turn
        self._wiki_path = wiki_path
        self._writer: Optional[ObsidianWriter] = None
        self._vector_store: Optional[VectorStore] = None
        self._semantic_search_enabled = semantic_search

        # Track what's already learned to avoid duplicates
        self._learned: Set[str] = set()
        self._turn_count = 0

        # Gap-filling: topics detected as missing from wiki
        self._gap_insights: List[Insight] = []
        self._suggested_gap_topics: List[str] = []

    def enable(self, wiki_path: Path) -> None:
        """Enable auto-learning and initialize wiki writer."""
        self._enabled = True
        self._wiki_path = wiki_path
        self._writer = ObsidianWriter(wiki_path)

        # Initialize vector store for semantic search
        if self._semantic_search_enabled:
            db_path = wiki_path / "vectors.db"
            self._vector_store = VectorStore(db_path)
            logger.debug(
                f"VectorStore initialized at {db_path} ({self._vector_store.count()} vectors)"
            )

        self._load_existing(wiki_path)

    def _load_existing(self, wiki_path: Path) -> None:
        """Load existing entries to avoid duplicates."""
        entities_path = wiki_path / "entities"
        if not entities_path.exists():
            return

        for file_path in entities_path.glob("*.md"):
            content = file_path.read_text(encoding="utf-8")
            # Extract key phrases for deduplication
            for line in content.split("\n"):
                if line.strip().startswith("-"):
                    # Get the content after date and tags
                    match = re.search(r"[:\-]\s+.+?$", line)
                    if match:
                        key = match.group(0).lower()[:50]
                        self._learned.add(key)

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    @property
    def wiki_path(self) -> Optional[Path]:
        return self._wiki_path

    def learn_from_turn(self, user_text: str, assistant_text: str) -> Tuple[int, int]:
        """
        Analyze a conversation turn and extract insights.

        Returns (user_insights_count, memory_insights_count) saved.
        """
        if not self._enabled or not self._writer:
            return 0, 0

        self._turn_count += 1

        if not user_text and not assistant_text:
            return 0, 0

        insights = self._extract_insights(user_text, assistant_text)

        # Limit per turn
        insights = insights[: self._max_per_turn]

        user_saved = 0
        memory_saved = 0
        for insight in insights:
            if self._save_insight(insight):
                if insight.target == "user":
                    user_saved += 1
                else:
                    memory_saved += 1

        total_saved = user_saved + memory_saved
        if total_saved > 0:
            logger.debug(
                "AutoLearn turn %d: saved %d insights to Obsidian wiki",
                self._turn_count,
                total_saved,
            )
            # Update index after saving
            try:
                self._writer.update_index()
            except Exception:
                pass

        return user_saved, memory_saved

    def on_session_end(self, messages: List[Dict[str, Any]]) -> Optional[Dict[str, int]]:
        """Deep reflection at session end — analyze full conversation for patterns.

        Called when the agent session closes (CLI exit, gateway disconnect, etc).
        This is distinct from per-turn learn_from_turn which does lightweight
        regex extraction. Session-end reflection can do:
        - Full conversation summarization (via MiniMax)
        - Cross-turn pattern detection
        - Entity/concept linking to existing wiki entries
        - Vector embedding for semantic search

        Args:
            messages: Full conversation history [{role, content}, ...]

        Returns:
            Optional dict with insight counts: {user, memory, concepts}
            Returns None if disabled or no new insights found.
        """
        if not self._enabled or not self._writer or not messages:
            return None

        logger.debug("AutoLearn: session-end deep reflection on %d messages", len(messages))

        # Collect conversation text for analysis
        conversation_text = "\n".join(
            f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
            for msg in messages
            if msg.get("content")
        )

        if len(conversation_text) < 20:
            return None

        # Extract session-level insights (topics, recurring patterns, etc.)
        session_insights: List[Insight] = []

        # Topic extraction: find repeated words across conversation
        topic_pattern = re.compile(r'\b[a-z]{4,}\b', re.IGNORECASE)
        topic_counts: Dict[str, int] = {}
        for msg in messages:
            content = msg.get("content", "")
            for match in topic_pattern.finditer(content):
                topic = match.group(0).strip()
                if len(topic) > 3:
                    topic_counts[topic] = topic_counts.get(topic, 0) + 1

        # Save recurring topics as concept entries
        for topic, count in sorted(topic_counts.items(), key=lambda x: -x[1])[:5]:
            if count >= 2:
                key = f"concept:{topic.lower()[:40]}"
                if key not in self._learned:
                    session_insights.append(
                        Insight(
                            target="memory",
                            itype="concept",
                            content=f"recurring topic: {topic} ({count}x)",
                            context=f"Seen {count} times in conversation",
                        )
                    )
                    self._learned.add(key)

        # Save insights
        saved = {"user": 0, "memory": 0, "concepts": 0}
        for insight in session_insights:
            if self._save_insight(insight):
                if insight.target == "user":
                    saved["user"] += 1
                elif insight.itype == "concept":
                    saved["concepts"] += 1
                else:
                    saved["memory"] += 1

        if sum(saved.values()) > 0:
            logger.debug(
                "AutoLearn session-end: saved %s to Obsidian wiki",
                saved,
            )
            try:
                self._writer.update_index()
            except Exception:
                pass

        return saved if sum(saved.values()) > 0 else None

    # -----------------------------------------------------------------------
    # P4-Cortex: Session Workflow Pattern Recording (per-turn)
    # -----------------------------------------------------------------------

    def record_workflow_pattern(
        self,
        tool_sequence: list[str],
        task_type: str = "unknown",
        turn_number: int = 0,
        outcome: str = "success",
        session_id: str = "",
    ) -> bool:
        """Record a tool sequence as a workflow pattern for P4-cortex growth.

        Saves a JSON file to ~/.drewgent/P4-cortex/growth/patterns/ that is
        later consumed by GrowthEngine to detect recurring workflows.

        Args:
            tool_sequence: List of tool names called in this turn
            task_type: Classification of the task (e.g., "code_edit", "research")
            turn_number: Which turn this was in the session
            outcome: "success" or "failure"
            session_id: Optional session identifier for linking

        Returns:
            True if pattern was saved, False otherwise
        """
        if not tool_sequence or len(tool_sequence) < 2:
            return False

        # Ensure patterns directory exists
        _P4_CORTEX_PATTERNS_DIR.mkdir(parents=True, exist_ok=True)

        # Build a hash for deduplication and filename
        seq_str = "_".join(tool_sequence)
        seq_hash = hashlib.md5(seq_str.encode()).hexdigest[:8]
        import time as _time

        timestamp = _time.strftime("%Y%m%d%H%M%S")
        filename = f"turn_workflow_{seq_hash}_{timestamp}.json"
        filepath = _P4_CORTEX_PATTERNS_DIR / filename

        pattern_data = {
            "id": f"{seq_hash}-{timestamp}",
            "type": "turn_workflow",
            "description": f"Turn workflow: {' → '.join(tool_sequence)}",
            "severity": "info",
            "recommendation": f"Tool sequence used for {task_type} task",
            "affected_items": tool_sequence,
            "task_type": task_type,
            "turn_number": turn_number,
            "outcome": outcome,
            "session_id": session_id,
            "detected_at": _time.strftime("%Y-%m-%dT%H:%M:%S.%f"),
        }

        try:
            filepath.write_text(json.dumps(pattern_data, indent=2), encoding="utf-8")
            logger.debug(
                "Recorded workflow pattern: %s → %s (%s turn %d)",
                seq_str[:40],
                outcome,
                task_type,
                turn_number,
            )
            return True
        except Exception as e:
            logger.debug("Failed to record workflow pattern: %s", e)
            return False

    def run_maintenance(self, dry_run: bool = False) -> dict:
        """Run autonomous wiki maintenance: retire stale, dedup, detect gaps.

        Call this from on_session_end or a periodic timer to keep the wiki
        healthy without requiring user intervention.

        Args:
            dry_run: If True, only report what would be done (no file changes).

        Returns:
            Summary dict with retire/dedup/gaps results.
        """
        if not self._enabled or not self._wiki_path:
            return {"error": "not enabled"}

        maintenance = WikiMaintenance(self._wiki_path)
        result = maintenance.run_autonomous_maintenance(dry_run=dry_run)

        # Generate self-initiated growth suggestions from detected gaps
        if not dry_run:
            self._update_gap_insights(result.get("gaps_detected", []))

        return result

    def _update_gap_insights(self, gaps: List[str]) -> None:
        """Update suggested gap topics that agent can proactively fill."""
        if not gaps:
            self._suggested_gap_topics = []
            self._gap_insights = []
            return

        self._suggested_gap_topics = gaps

        # Generate suggested insight entries for each gap
        self._gap_insights = []
        gap_itype_map = {
            "preferences": "preference",
            "communication-style": "communication",
            "environment": "environment",
            "corrections": "correction",
            "user-profile": "identity",
        }

        for topic in gaps:
            itype = gap_itype_map.get(topic, "insight")
            self._gap_insights.append(
                Insight(
                    target="user",
                    itype=itype,
                    content=f"Consider exploring: {topic}",
                    context="knowledge gap detected — agent should investigate and fill",
                    lifetime_days=7,  # short-lived: fill or forget
                )
            )

    def get_growth_suggestions(self) -> List[Insight]:
        """Return suggested gap-filling insights for agent to pursue."""
        return self._gap_insights

    def get_suggested_topics(self) -> List[str]:
        """Return list of topic names that have gaps."""
        return list(self._suggested_gap_topics)

    def fill_gap(self, topic: str, content: str, itype: str = "insight") -> bool:
        """Record a self-initiated insight to fill a detected gap."""
        gap_itype_map = {
            "preferences": "preference",
            "communication-style": "communication",
            "environment": "environment",
            "corrections": "correction",
            "user-profile": "identity",
        }

        insight = Insight(
            target="user",
            itype=gap_itype_map.get(topic, itype),
            content=content,
            context=f"self-initiated fill for gap: {topic}",
            lifetime_days=90,
        )

        saved = self._save_insight(insight)
        if saved:
            if topic in self._suggested_gap_topics:
                self._suggested_gap_topics.remove(topic)
            self._gap_insights = [g for g in self._gap_insights if topic not in g.content]
            logger.info("[AutoLearner] filled gap '%s': %s", topic, content[:60])
        return saved

    def _extract_insights(self, user_text: str, assistant_text: str) -> List[Insight]:
        """Extract insights from conversation text."""
        insights: List[Insight] = []

        if not user_text or len(user_text) < 1:
            return insights

        # Also allow very short meaningful content through
        # (don't require 3+ chars since implicit patterns handle short inputs)

        # Extract user preferences
        for pattern, itype in _USER_PATTERNS:
            for match in re.finditer(pattern, user_text, re.IGNORECASE):
                content = match.group(1).strip()
                if self._is_meaningful(content):
                    key = f"{itype}:{content.lower()[:40]}"
                    if key not in self._learned:
                        insights.append(
                            Insight(
                                target="user",
                                itype=itype,
                                content=content,
                                context=user_text[:80],
                            )
                        )
                        self._learned.add(key)

        # Extract communication style
        for pattern, itype in _STYLE_PATTERNS:
            if re.search(pattern, user_text, re.IGNORECASE):
                content = itype.replace("style_", "")
                key = f"style:{content}"
                if key not in self._learned:
                    insights.append(
                        Insight(
                            target="user",
                            itype=itype,
                            content=f"prefers {content} responses",
                        )
                    )
                    self._learned.add(key)

        # Extract corrections
        for pattern, itype in _CORRECTION_PATTERNS:
            for match in re.finditer(pattern, user_text, re.IGNORECASE):
                content = match.group(1).strip()
                if self._is_meaningful(content):
                    key = f"correction:{content.lower()[:40]}"
                    if key not in self._learned:
                        insights.append(
                            Insight(
                                target="user",
                                itype="correction",
                                content=content,
                                context=f"Previously: {assistant_text[:50]}...",
                            )
                        )
                        self._learned.add(key)

        # Extract anti-preferences
        for pattern, itype in _ANTI_PATTERNS:
            for match in re.finditer(pattern, user_text, re.IGNORECASE):
                content = match.group(1).strip()
                if self._is_meaningful(content) and len(content) > 2:
                    key = f"anti:{content.lower()[:40]}"
                    if key not in self._learned:
                        insights.append(
                            Insight(
                                target="user",
                                itype="anti_preference",
                                content=content,
                            )
                        )
                        self._learned.add(key)

        # Extract environment facts
        for pattern, etype in _ENV_PATTERNS:
            for match in re.finditer(pattern, user_text, re.IGNORECASE):
                content = match.group(1).strip()
                if self._is_meaningful(content):
                    key = f"{etype}:{content.lower()[:40]}"
                    if key not in self._learned:
                        insights.append(
                            Insight(
                                target="memory",
                                itype=etype,
                                content=content,
                            )
                        )
                        self._learned.add(key)

        # Extract implicit preferences from short/command inputs
        implicit = _detect_implicit_style(user_text)
        if implicit:
            itype, content = implicit
            key = f"implicit:{itype}:{user_text.strip().lower()[:30]}"
            if key not in self._learned:
                insights.append(
                    Insight(
                        target="user",
                        itype=itype,
                        content=content,
                    )
                )
                self._learned.add(key)

        return insights

    def _is_meaningful(self, text: str) -> bool:
        """Check if text is meaningful enough to save."""
        text = text.strip().lower()
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
            "yes,",
            "no,",
            "ok,",
            "sure,",
            "i see",
            "understood",
            "good",
            "fine",
            "great",
            "cool",
            "nice",
            "yes.",
            "no.",
            "done",
        }
        if text in generic:
            return False
        if len(text) < 2 or len(text) > 150:
            return False
        return True

    def _save_insight(self, insight: Insight) -> bool:
        """Save insight to Obsidian wiki. Returns True if saved."""
        if not self._writer:
            return False

        try:
            # Write to Obsidian wiki
            success = self._writer.write_insight(insight)

            # Also store embedding for semantic search
            if success and self._vector_store:
                self._store_embedding(insight)

            return success
        except Exception as e:
            logger.debug("AutoLearn: failed to save insight: %s", e)
            return False

    def _store_embedding(self, insight: Insight) -> None:
        """Store embedding for semantic search."""
        embedding = get_embedding([insight.content])
        if embedding:
            # Generate unique ID
            insight_id = f"{insight.itype}_{insight.content[:30].replace(' ', '_')}"
            self._vector_store.add(
                id=insight_id,
                content=insight.content,
                embedding=embedding[0],
                itype=insight.itype,
                target=insight.target,
            )
            logger.debug(f"Stored embedding for: {insight.content[:50]}")

    def semantic_search(self, query: str, limit: int = 5) -> list[dict]:
        """Search memories semantically using embeddings.

        Uses MiniMax API (if available) or Ollama (local) automatically.

        Args:
            query: Search query text
            limit: Maximum number of results

        Returns:
            List of dicts with content, score, itype, target
        """
        if not self._vector_store:
            return []

        # Get query embedding
        embeddings = get_embedding([query])
        if not embeddings:
            logger.debug("Semantic search failed: could not get embeddings")
            return []

        # Search vector store
        results = self._vector_store.search(embeddings[0], limit=limit)

        # Format results
        return [
            {
                "content": r["content"],
                "score": r["score"],
                "type": r["itype"],
                "target": r["target"],
            }
            for r in results
        ]

    def read_wiki_for_context(self, max_entries: int = 10, max_chars: int = 4000) -> str:
        """Read wiki entries for context injection into system prompt.

        Reads recent entries from entities/, concepts/, and insights/ folders
        and formats them for context injection.

        Args:
            max_entries: Maximum number of entries per category
            max_chars: Maximum total characters

        Returns:
            Formatted wiki context string, or empty string if no wiki path
        """
        if not self._wiki_path:
            return ""

        context_parts = []
        total_chars = 0

        # Read from each wiki category
        for folder, label in [
            ("entities", "Entities"),
            ("concepts", "Concepts"),
            ("insights", "Insights"),
        ]:
            folder_path = self._wiki_path / folder
            if not folder_path.exists():
                continue

            entries = []
            for md_file in sorted(folder_path.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:max_entries]:
                try:
                    content = md_file.read_text(encoding="utf-8")
                    # Extract log entries (lines starting with - date:)
                    for line in content.split("\n"):
                        if line.strip().startswith("- 20"):
                            entries.append(line.strip())
                except Exception:
                    continue

            if entries:
                # Limit entries for this folder
                folder_entries = []
                for entry in entries[:max_entries]:
                    if total_chars + len(entry) + 50 > max_chars:
                        break
                    folder_entries.append(entry)
                    total_chars += len(entry) + 1

                if folder_entries:
                    context_parts.append(f"## {label}\n" + "\n".join(folder_entries))

        if not context_parts:
            return ""

        # Build wiki context with header
        wiki_context = """═══════════════════════════════════════════════
WIKI KNOWLEDGE BASE (Obsidian)
═══════════════════════════════════════════════
Reference these facts when answering. Wiki-links like [[entities/environment]] 
connect related concepts.

"""
        wiki_context += "\n\n".join(context_parts)
        wiki_context += "\n═══════════════════════════════════════════════"

        return wiki_context

    # --------------------------------------------------------------------------
    # Public API for brain_tool.py — active brain access
    # --------------------------------------------------------------------------

    def save_insight(self, insight: Insight) -> bool:
        """Public method to save an insight directly to the brain.

        Used by brain_tool.brain_record() for explicit agent recording.
        """
        return self._save_insight(insight)

    def query_wiki(
        self,
        query: str,
        context: str = "",
        max_results: int = 5,
        max_chars: int = 2000,
    ) -> str:
        """Query wiki for contextually relevant knowledge.

        Active querying method used by brain_tool.brain_query().
        Combines text search with semantic search for comprehensive results.

        Args:
            query: What to search for
            context: Current task context for relevance ranking
            max_results: Maximum entries to return
            max_chars: Maximum response size

        Returns:
            Formatted string of relevant wiki entries
        """
        if not self._wiki_path:
            return ""

        query_lower = query.lower().strip()
        context_lower = context.lower().strip()

        # Collect candidates from wiki folders
        candidates = []
        for folder in ("entities", "concepts", "insights"):
            folder_path = self._wiki_path / folder
            if not folder_path.exists():
                continue
            for md_file in folder_path.glob("*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")
                    self._extract_entries_from_file(
                        content, query_lower, context_lower, candidates, md_file
                    )
                except Exception:
                    continue

        if not candidates:
            # Fallback 1: semantic search
            if self._vector_store:
                sem_results = self.semantic_search(query, limit=max_results)
                if sem_results:
                    high_quality = [r for r in sem_results if r["score"] >= 0.5]
                    if high_quality:
                        self._touch_result_ids(high_quality)
                        return self._format_wiki_query_results(high_quality, max_chars)

            # Fallback 2: gap knowledge — if query relates to a known gap topic,
            # offer the gap insight so the agent can self-initiate filling it
            gap_suggestions = self.get_growth_suggestions()
            if gap_suggestions:
                query_lower = query.lower().strip()
                for gi in gap_suggestions:
                    if query_lower in gi.content.lower() or query_lower in gi.itype.lower():
                        lines = [
                            "## Brain Query Results",
                            f"[GAP DETECTED] {gi.content}",
                            f"Topic: {gi.itype}",
                            "(Use brain_record to fill this gap)",
                        ]
                        return "\n".join(lines)

            return ""

        # Sort by relevance: query match > context match > recency
        def relevance_score(item):
            score = 0
            # Query keyword match
            if query_lower in item["content"].lower():
                score += 10
            # Context keyword match
            if context_lower and context_lower in item["content"].lower():
                score += 5
            # Recent entries get slight boost
            if item.get("recency", 0) > 0:
                score += item["recency"] * 0.1
            # Prefer user preferences over general insights
            if item.get("target") == "user":
                score += 2
            return score

        candidates.sort(key=relevance_score, reverse=True)
        results = candidates[:max_results]

        # Track access for returned entries
        self._touch_result_ids(results)

        # Format results
        return self._format_wiki_query_results(results, max_chars)

    def _extract_entries_from_file(
        self, content: str, query_lower: str, context_lower: str,
        candidates: list, md_file: Path = None
    ) -> None:
        """Extract relevant entries from a wiki file."""
        for line in content.split("\n"):
            if not line.strip().startswith("- 20"):
                continue
            line_lower = line.lower()
            # Match if query appears anywhere in the line
            if query_lower and query_lower not in line_lower:
                # Try individual words for partial matching
                query_words = query_lower.split()
                if not any(w in line_lower for w in query_words if len(w) >= 3):
                    continue
            # Generate stable ID for access tracking
            entry_id = self._make_entry_id(line.strip(), md_file)
            candidates.append({
                "content": line.strip(),
                "line": line.strip(),
                "target": "user" if " #user" in line_lower else "memory",
                "recency": 0,
                "id": entry_id,
            })

    def _make_entry_id(self, line: str, md_file: Path = None) -> str:
        """Create a stable ID for a wiki entry matching VectorStore format."""
        # Derive insight ID from first 30 chars of content (same as _store_embedding)
        content_snippet = line[:30].replace(" ", "_").replace("\n", "")
        return f"general_{content_snippet}"

    def _touch_result_ids(self, results: list[dict]) -> None:
        """Record access for all result IDs that have vector entries."""
        if not self._vector_store:
            return
        for r in results:
            entry_id = r.get("id", "")
            if entry_id:
                self._vector_store.touch(entry_id)

    def _format_wiki_query_results(self, results: list[dict], max_chars: int) -> str:
        """Format wiki query results into readable string."""
        if not results:
            return ""

        lines = []
        total = 0
        for r in results:
            content = r.get("content", r.get("line", ""))
            if not content:
                continue
            lines.append(content)
            total += len(content) + 1
            if total > max_chars:
                break

        if not lines:
            return ""

        header = "## Brain Query Results\n"
        body = "\n".join(lines)
        return header + body
