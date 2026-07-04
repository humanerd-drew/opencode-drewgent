#!/usr/bin/env python3
"""Ingest P2 session logs into knowledge.db (SQLite + FTS5 + embeddings).
Replaces session_to_gbrain.py and gbrain entirely.

Uses Ollama for local embeddings ($0, nomic-embed-text:768).
"""
import json, gzip, os, sqlite3, sys, time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import urllib.request, urllib.error

DREW = Path(os.environ.get("DREW_HOME", str(Path.home() / ".drewgent")))
SESSIONS_DIR = DREW / "P2-hippocampus" / "sessions"
DB = DREW / ".opencode" / "knowledge.db"
STATE = DREW / "logs" / "session_ingest_state.json"
MAX_TIME = int(os.environ.get("MAX_TIME", "300"))
MAX_FILES = int(os.environ.get("MAX_FILES", "2000"))
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")
EMBED_DIMS = int(os.environ.get("EMBED_DIMS", "768"))
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


def get_db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(DB))
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL DEFAULT 'fact',
            content TEXT NOT NULL,
            source TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            message_count INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            knowledge_id INTEGER NOT NULL REFERENCES knowledge(id) ON DELETE CASCADE,
            embedding BLOB NOT NULL,
            model TEXT NOT NULL,
            dimensions INTEGER NOT NULL,
            UNIQUE(knowledge_id, model)
        );
        CREATE INDEX IF NOT EXISTS idx_knowledge_type ON knowledge(type);
        CREATE INDEX IF NOT EXISTS idx_knowledge_created ON knowledge(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_embeddings_model ON embeddings(model);
        CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
            content, type,
            content=knowledge, content_rowid=id
        );
        CREATE TRIGGER IF NOT EXISTS knowledge_ai AFTER INSERT ON knowledge BEGIN
            INSERT INTO knowledge_fts(rowid, content, type) VALUES (new.id, new.content, new.type);
        END;
        CREATE TRIGGER IF NOT EXISTS knowledge_ad AFTER DELETE ON knowledge BEGIN
            INSERT INTO knowledge_fts(knowledge_fts, rowid, content, type) VALUES('delete', old.id, old.content, old.type);
        END;
    """)
    return db


def get_embedding(text):
    data = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/embeddings",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=30)
    return np.array(json.loads(resp.read())["embedding"], dtype=np.float32)


def embed_batch(texts):
    results = []
    for t in texts:
        try:
            vec = get_embedding(t)
            results.append(vec)
        except Exception as e:
            print(f"  [embed] fail: {e}", file=sys.stderr)
            results.append(None)
    return results


def read_session(filepath):
    ext = filepath.suffix
    if ext == ".jsonl":
        text = filepath.read_text()
        messages = []
        slug = filepath.stem
        ts = None
        for line in text.strip().split("\n"):
            try:
                obj = json.loads(line)
                if obj.get("role") == "session_meta":
                    continue
                messages.append((obj.get("role", "?"), obj.get("content", "")))
                if not ts and obj.get("timestamp"):
                    ts = obj["timestamp"]
            except json.JSONDecodeError:
                continue
        return slug, ts, messages

    if ext == ".gz":
        try:
            data = json.loads(gzip.decompress(filepath.read_bytes()))
        except Exception:
            return None, None, []
        slug = data.get("session_id", filepath.stem.replace("session_", ""))
        ts = data.get("session_start")
        messages = [(m.get("role", "?"), m.get("content", "")) for m in data.get("messages", [])]
        return slug, ts, messages

    return None, None, []


def format_content(slug, ts, messages):
    parts = [f"# Session: {slug}"]
    if ts:
        parts.append(f"**Started:** {ts}")
        parts.append(f"**Messages:** {len(messages)}")
    parts.append("")
    for role, content in messages:
        h = "User" if role == "user" else ("Assistant" if role == "assistant" else role)
        parts.extend([f"## {h}", "", content, ""])
    return "\n".join(parts)


def store_embedding(db, knowledge_id, vec):
    blob = vec.tobytes()
    db.execute(
        "INSERT OR IGNORE INTO embeddings (knowledge_id, embedding, model, dimensions) VALUES (?, ?, ?, ?)",
        (knowledge_id, blob, EMBED_MODEL, EMBED_DIMS),
    )


def needs_embedding(db):
    rows = db.execute(
        "SELECT k.id, k.content FROM knowledge k "
        "LEFT JOIN embeddings e ON e.knowledge_id = k.id AND e.model = ? "
        "WHERE e.id IS NULL AND k.type = 'session' LIMIT 50",
        (EMBED_MODEL,)
    ).fetchall()
    return rows


def backfill_embeddings(db):
    total = 0
    fail = 0
    pending = needs_embedding(db)
    while pending:
        for kid, content in pending:
            try:
                vec = get_embedding(content[:4000])
                store_embedding(db, kid, vec)
                total += 1
            except Exception as e:
                fail += 1
        db.commit()
        print(f"  [embed] {total} ok, {fail} fail")
        pending = needs_embedding(db)
    return total, fail


def main():
    state = {"processed": [], "last_run": None}
    if STATE.exists():
        try:
            state = json.loads(STATE.read_text())
        except:
            pass

    processed = set(state.get("processed", []))
    files = sorted(SESSIONS_DIR.iterdir(), key=lambda f: f.stat().st_mtime)
    new_files = [f for f in files if f.name not in processed and f.suffix in (".jsonl", ".gz")]

    db = get_db()

    if new_files:
        batch = new_files[:MAX_FILES]
        deadline = time.time() + MAX_TIME
        ok = fail = 0

        for f in batch:
            if time.time() > deadline:
                break
            slug, ts, messages = read_session(f)
            if not slug or not messages:
                processed.add(f.name)
                fail += 1
                continue
            content = format_content(slug, ts, messages)
            date_str = ts[:10] if ts else slug[:8]
            table_date = date_str + "T00:00:00"
            existing = db.execute("SELECT id FROM sessions WHERE id = ?", (slug,)).fetchone()
            if existing:
                processed.add(f.name)
                ok += 1
                continue
            cur = db.execute(
                "INSERT INTO knowledge (type, content, source, created_at) VALUES (?, ?, ?, ?)",
                ("session", content[:100000], slug, table_date),
            )
            kid = cur.lastrowid
            db.execute(
                "INSERT OR REPLACE INTO sessions (id, title, message_count, created_at) VALUES (?, ?, ?, ?)",
                (slug, f"Session {slug}", len(messages), table_date),
            )
            db.commit()
            try:
                vec = get_embedding(content[:2000])
                store_embedding(db, kid, vec)
                db.commit()
            except Exception as e:
                print(f"  [embed] {slug}: {e}", file=sys.stderr)
            ok += 1
            processed.add(f.name)

        state["processed"] = sorted(processed)
        state["last_run"] = datetime.now(timezone.utc).isoformat()
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(state, indent=2))

        total_new = len(new_files)
        done = len(batch[:max(1, batch.index(f)+1)]) if batch else 0
        print(f"[ingest] {ok} ingested, {fail} failed ({total_new - done} remaining of {total_new})")

    backfilled = backfill_embeddings(db)
    if backfilled is None:
        print("[ingest] 0 new sessions, embedding complete")
    else:
        remaining = needs_embedding(db)
        if remaining:
            print(f"[ingest] {len(remaining)} sessions still need embedding (next run)")
        else:
            print("[ingest] all embeddings up to date")

    db.close()


if __name__ == "__main__":
    main()
