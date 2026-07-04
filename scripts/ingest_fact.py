#!/usr/bin/env python3
"""Store a single fact into knowledge.db with embedding.
Used by the remember() opencode tool.
Input: JSON from stdin with {"fact": "...", "type": "..."}
"""
import json, sqlite3, sys, urllib.request, numpy as np
from pathlib import Path

DREW = Path(__file__).resolve().parent.parent
DB = DREW / ".opencode" / "knowledge.db"
EMBED_MODEL = "nomic-embed-text"
OLLAMA_HOST = "http://localhost:11434"

data = json.loads(sys.stdin.read())
fact = data["fact"]
ftype = data.get("type", "fact")

text = fact[:2000]
payload = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode()
req = urllib.request.Request(
    f"{OLLAMA_HOST}/api/embeddings",
    data=payload,
    headers={"Content-Type": "application/json"},
)
resp = urllib.request.urlopen(req, timeout=15)
vec = np.array(json.loads(resp.read())["embedding"], dtype=np.float32)

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
""")
cur = db.execute(
    "INSERT INTO knowledge (type, content, source) VALUES (?, ?, ?)",
    (ftype, fact, "remember_tool"),
)
kid = cur.lastrowid
db.execute(
    "INSERT OR IGNORE INTO embeddings (knowledge_id, embedding, model, dimensions) VALUES (?, ?, ?, ?)",
    (kid, vec.tobytes(), EMBED_MODEL, 768),
)
db.commit()
db.close()
print(f"stored id={kid} type={ftype}")
