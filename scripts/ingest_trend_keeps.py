#!/usr/bin/env python3
"""Ingest trend-harvester keep items into knowledge.db with embeddings.

Makes keep items searchable via recall() — agents can discover relevant
trends and past evaluation decisions.

Usage:
    python3 scripts/ingest_trend_keeps.py              # bulk import all
    python3 scripts/ingest_trend_keeps.py --watch      # incremental (for cron)
"""
import json, os, sqlite3, sys, time, urllib.request
from pathlib import Path

import numpy as np

DREW = Path(os.environ.get("DREW_HOME", str(Path.home() / ".drewgent")))
KEEP_DIR = DREW / "@memory" / "growth" / "trend-harvester" / "analyzed" / "keep"
DB = DREW / ".opencode" / "knowledge.db"
STATE = DREW / "logs" / "trend_ingest_state.json"
EMBED_MODEL = "nomic-embed-text"
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
PROVENANCE_PREFIX = "trend-harvester-keep"


def get_db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(DB))
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL DEFAULT 'fact',
            content TEXT NOT NULL,
            source TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            knowledge_id INTEGER NOT NULL REFERENCES knowledge(id) ON DELETE CASCADE,
            embedding BLOB NOT NULL,
            model TEXT NOT NULL,
            dimensions INTEGER NOT NULL,
            UNIQUE(knowledge_id, model)
        );
        CREATE INDEX IF NOT EXISTS idx_knowledge_source ON knowledge(source);
    """)
    return db


def get_embedding(text):
    data = json.dumps({"model": EMBED_MODEL, "prompt": text[:2000]}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/embeddings",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=30)
    return np.array(json.loads(resp.read())["embedding"], dtype=np.float32)


def format_keep(item, scores):
    name = item.get("name", "?")
    desc = item.get("description", "")
    content = item.get("content", "")
    source = item.get("source", "?")
    published = item.get("published", item.get("collected_at", ""))[:10]
    total = sum(scores.values()) / max(len(scores), 1)

    # Strip HTML for embedding text
    import re
    plain = re.sub(r"<[^>]+>", "", desc or content or name)

    body = (
        f"# Trend: {name}\n"
        f"**Source:** {source} | **Date:** {published}\n"
        f"**Score:** {total:.2f} (relevance={scores.get('relevance',0):.1f}, "
        f"impact={scores.get('direct_impact',0):.1f}, "
        f"novelty={scores.get('novelty',0):.1f})\n\n"
        f"{plain[:5000]}"
    )
    return body, total


def main():
    watch_mode = "--watch" in sys.argv

    state = {"imported": [], "last_run": None}
    if STATE.exists():
        try:
            state = json.loads(STATE.read_text())
        except:
            pass

    imported = set(state.get("imported", []))
    files = sorted(KEEP_DIR.glob("*.json"))
    pending = [f for f in files if f.stem not in imported]

    if not pending and not watch_mode:
        print(f"[trend-ingest] 0 new (total {len(imported)})")
        return
    if not pending and watch_mode:
        return

    db = get_db()
    ok = fail = 0

    for f in pending:
        try:
            data = json.loads(f.read_text())
            item = data.get("item", {})
            scores = data.get("scores", {})
            name = item.get("name", f.stem)
            source_id = f"{PROVENANCE_PREFIX}:{name[:80]}"

            body, total = format_keep(item, scores)

            cur = db.execute(
                "INSERT INTO knowledge (type, content, source, created_at) VALUES (?, ?, ?, datetime('now'))",
                ("trend", body[:100000], source_id),
            )
            kid = cur.lastrowid

            try:
                vec = get_embedding(body[:2000])
                db.execute(
                    "INSERT OR IGNORE INTO embeddings (knowledge_id, embedding, model, dimensions) VALUES (?, ?, ?, ?)",
                    (kid, vec.tobytes(), EMBED_MODEL, 768),
                )
            except Exception as e:
                print(f"  [embed] {name[:50]}: {e}", file=sys.stderr)

            db.commit()
            ok += 1
            imported.add(f.stem)

        except Exception as e:
            print(f"  [fail] {f.name}: {e}", file=sys.stderr)
            fail += 1

    state["imported"] = sorted(imported)
    state["last_run"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2))

    print(f"[trend-ingest] {ok} ingested, {fail} failed ({len(pending)} total)")


if __name__ == "__main__":
    main()
