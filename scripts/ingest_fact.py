#!/usr/bin/env python3
"""Store a single fact into knowledge.db with embedding + entity extraction.
Used by the remember() opencode tool.
Input: JSON from stdin with {"fact": "...", "type": "..."}
"""
import json, sqlite3, subprocess, sys, urllib.request, numpy as np
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
EXT_SCRIPT = PROJECT / "scripts" / "extract_entities_llm.py"
DB = PROJECT / ".opencode" / "knowledge.db"
EMBED_MODEL = "nomic-embed-text"
OLLAMA_HOST = "http://localhost:11434"

use_llm = "--llm" in sys.argv
no_extract = "--no-extract" in sys.argv
args = [a for a in sys.argv[1:] if not a.startswith("--")]

if len(sys.argv) > 1 and sys.argv[1] == "--json":
    data = json.loads(sys.argv[2])
else:
    data = json.loads(sys.stdin.read())
fact = data["fact"]
ftype = data.get("type", "fact")

text = fact[:2000]
payload = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode()
req = urllib.request.Request(
    f"{OLLAMA_HOST}/api/embeddings",
    data=payload, headers={"Content-Type": "application/json"},
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
        content TEXT NOT NULL, source TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS embeddings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        knowledge_id INTEGER NOT NULL REFERENCES knowledge(id) ON DELETE CASCADE,
        embedding BLOB NOT NULL, model TEXT NOT NULL,
        dimensions INTEGER NOT NULL, UNIQUE(knowledge_id, model)
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

out = {"id": kid, "type": ftype}

if not no_extract:
    mode = "--llm" if use_llm else "--fallback"
    try:
        proc = subprocess.run(
            [sys.executable, str(EXT_SCRIPT), mode, "--fact-id", str(kid), fact],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode == 0:
            ext_result = json.loads(proc.stdout.strip())
            out["entities_extracted"] = ext_result.get("new_entities", 0)
            out["relations_extracted"] = ext_result.get("new_relations", 0)
            if ext_result.get("entities"):
                out["entities"] = [e["label"] for e in ext_result["entities"]]
    except Exception as e:
        out["extraction_error"] = str(e)

print(json.dumps(out, ensure_ascii=False))
