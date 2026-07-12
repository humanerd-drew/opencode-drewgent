#!/usr/bin/env python3
"""Ingest .opencode/instructions/*.md into knowledge.db + entity graph.

Run after editing instruction files:
  python3 scripts/ingest_instructions.py
"""
import hashlib, json, re, sqlite3, sys, urllib.request
from pathlib import Path

import numpy as np

PROJECT = Path(__file__).resolve().parent.parent
DB = PROJECT / ".opencode" / "knowledge.db"
INSTR_DIR = PROJECT / ".opencode" / "instructions"

INSTR_FILES = {
    "00-architecture.md": "architecture",
    "10-conventions.md": "convention",
    "20-knowledge-system.md": "knowledge-system",
    "30-model-routing.md": "model-routing",
    "40-known-pitfalls.md": "pitfall",
}


def get_db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(DB))
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("""
        CREATE TABLE IF NOT EXISTS embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            knowledge_id INTEGER NOT NULL REFERENCES knowledge(id) ON DELETE CASCADE,
            embedding BLOB NOT NULL, model TEXT NOT NULL,
            dimensions INTEGER NOT NULL, UNIQUE(knowledge_id, model)
        );
    """)
    db.row_factory = sqlite3.Row
    return db


def get_embedding(text):
    data = json.dumps({"model": "nomic-embed-text", "prompt": text[:2000]}).encode()
    resp = urllib.request.urlopen(
        urllib.request.Request("http://localhost:11434/api/embeddings",
            data=data, headers={"Content-Type": "application/json"}), timeout=30)
    return np.array(json.loads(resp.read())["embedding"], dtype=np.float32)


def content_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def main():
    if not INSTR_DIR.exists():
        print("No instruction files found", file=sys.stderr)
        return 1

    db = get_db()
    ingested = linked = embeddings = 0

    for fname, topic in INSTR_FILES.items():
        fpath = INSTR_DIR / fname
        if not fpath.exists():
            continue

        content = fpath.read_text()
        slug = f".opencode/instructions/{fname}"
        new_hash = content_hash(content)

        existing = db.execute(
            "SELECT id, content FROM knowledge WHERE source = ? AND type = 'instruction'",
            (slug,),
        ).fetchone()

        needs_embed = False
        if existing:
            if content_hash(existing["content"]) != new_hash:
                db.execute("UPDATE knowledge SET content = ? WHERE id = ?", (content[:50000], existing["id"]))
                needs_embed = True
            kid = existing["id"]
            if not db.execute("SELECT id FROM embeddings WHERE knowledge_id = ?", (kid,)).fetchone():
                needs_embed = True
        else:
            db.execute("INSERT INTO knowledge (type, content, source) VALUES ('instruction', ?, ?)", (content[:50000], slug))
            kid = db.execute("SELECT id FROM knowledge WHERE source = ?", (slug,)).fetchone()["id"]
            ingested += 1
            needs_embed = True

        if needs_embed:
            try:
                vec = get_embedding(content)
                db.execute("INSERT OR REPLACE INTO embeddings (knowledge_id, embedding, model, dimensions) VALUES (?, ?, ?, ?)",
                    (kid, vec.tobytes(), "nomic-embed-text", 768))
                embeddings += 1
            except Exception as e:
                print(f"  embedding fail {fname}: {e}", file=sys.stderr)

    db.commit()
    print(json.dumps({"ingested": ingested, "embeddings": embeddings}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
