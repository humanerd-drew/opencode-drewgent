#!/usr/bin/env python3
"""Create and seed knowledge.db from wiki content.

knowledge.db is queried by AIAgent via _query_memory_db() on every turn
and injected as [Agent memories].  It did not exist → the agent always
got an empty block.  This script creates the DB, populates it from the
cleaned wiki files, and can be run periodically to sync new entries.

Idempotent: re-running upserts new content and skips duplicates.
"""

import hashlib
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DREW_HOME = Path(__file__).resolve().parent.parent
DB_PATH = DREW_HOME / ".agent" / "memory" / "knowledge.db"
WIKI_DIR = DREW_HOME / "memories"

ENTRY_PATTERN = re.compile(r"^-\s+(\d{4}-\d{2}-\d{2})[:\s]+(.+)$", re.MULTILINE)
TYPE_TAG = re.compile(r"#(\w+)")


def init_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(DB_PATH))
    db.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5("
        "  fact, \"type\", content_hash UNINDEXED,"
        "  tokenize='porter unicode61'"
        ")"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS source_meta ("
        "  content_hash TEXT PRIMARY KEY,"
        "  source_file TEXT,"
        "  synced_at TEXT"
        ")"
    )
    db.commit()
    return db


def extract_entries(file_path: Path) -> list[dict]:
    """Extract log entries from a wiki file as (fact, type, hash)."""
    text = file_path.read_text(encoding="utf-8")
    entries = []
    for match in ENTRY_PATTERN.finditer(text):
        date, content = match.group(1), match.group(2).strip()
        tags = TYPE_TAG.findall(content)
        entry_type = tags[0] if tags else "knowledge"
        fact = f"[{date}] {content}"
        content_hash = hashlib.sha256(fact.encode()).hexdigest()[:16]
        entries.append({
            "fact": fact,
            "type": entry_type,
            "content_hash": content_hash,
            "source": str(file_path.relative_to(DREW_HOME)),
        })
    return entries


def main() -> str:
    now = datetime.now(timezone.utc).isoformat()
    db = init_db()
    synced = 0
    skipped = 0

    existing = {row[0] for row in db.execute("SELECT content_hash FROM source_meta").fetchall()}

    for folder in ("entities", "concepts", "insights"):
        folder_path = WIKI_DIR / folder
        if not folder_path.exists():
            continue
        for md_file in sorted(folder_path.glob("*.md")):
            try:
                entries = extract_entries(md_file)
            except Exception as exc:
                print(f"  Error reading {md_file}: {exc}", file=sys.stderr)
                continue
            for entry in entries:
                if entry["content_hash"] in existing:
                    skipped += 1
                    continue
                db.execute(
                    'INSERT OR IGNORE INTO memory_fts (fact, "type", content_hash) VALUES (?, ?, ?)',
                    (entry["fact"], entry["type"], entry["content_hash"]),
                )
                db.execute(
                    "INSERT OR IGNORE INTO source_meta (content_hash, source_file, synced_at) VALUES (?, ?, ?)",
                    (entry["content_hash"], entry["source"], now),
                )
                synced += 1

    db.commit()
    total = db.execute("SELECT COUNT(*) FROM memory_fts").fetchone()[0]
    db.close()

    if synced == 0:
        return f"[SILENT] knowledge.db has {total} entries, no new entries to sync"

    return (
        f"# knowledge.db Seed Report\n"
        f"**Synced**: {synced} new entries\n"
        f"**Skipped**: {skipped} existing\n"
        f"**Total**: {total} entries in memory_fts\n"
        f"**DB path**: {DB_PATH}\n"
        f"Run at: {now}"
    )


if __name__ == "__main__":
    output = main()
    if output:
        print(output)
