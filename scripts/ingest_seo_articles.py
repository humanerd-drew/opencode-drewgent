#!/usr/bin/env python3
"""Ingest SEO article markdown files into knowledge.db with embeddings.

Makes collected SEO articles searchable via recall() — agents can discover
relevant SEO insights and past analyses.

Usage:
    python3 scripts/ingest_seo_articles.py               # bulk import
    python3 scripts/ingest_seo_articles.py --watch       # incremental (cron)
"""
import json, os, re, sqlite3, sys, time, urllib.request
from pathlib import Path

import numpy as np

DREW = Path(os.environ.get("DREW_HOME", str(Path.home() / ".drewgent")))
ARTICLES_DIR = DREW / "P2-hippocampus" / "knowledge" / "seo-articles"
DB = DREW / ".opencode" / "knowledge.db"
STATE = DREW / "logs" / "seo_ingest_state.json"
EMBED_MODEL = "nomic-embed-text"
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
PROVENANCE_PREFIX = "seo-article"


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


def extract_title(content, filename):
    title = ""
    m = re.search(r"^#\s+(.+)", content)
    if m:
        title = m.group(1).strip()
    else:
        title = filename.replace("_", " ").rsplit(".", 1)[0]
    return title


def find_md_files():
    files = []
    for year_dir in sorted(ARTICLES_DIR.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        for f in sorted(year_dir.glob("*.md")):
            files.append((f, f"{PROVENANCE_PREFIX}:{year_dir.name}/{f.stem}"))
    return files


def main():
    watch_mode = "--watch" in sys.argv

    state = {"imported": set(), "last_run": None}
    if STATE.exists():
        try:
            s = json.loads(STATE.read_text())
            state["imported"] = set(s.get("imported", []))
            state["last_run"] = s.get("last_run")
        except:
            pass

    db = get_db()
    ok = fail = skip = 0

    files = find_md_files()

    if not files:
        print("[seo-ingest] no articles found")
        return

    pending = [(f, sid) for f, sid in files if sid not in state["imported"]]

    if not pending:
        print(f"[seo-ingest] 0 new (total {len(state['imported'])})")
        return
    if watch_mode:
        pending = pending[:100]

    for fpath, source_id in pending:
        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
            if len(content) < 50:
                skip += 1
                state["imported"].add(source_id)
                continue

            title = extract_title(content, fpath.stem)
            body = f"# SEO: {title}\n\n{content[:100000]}"

            cur = db.execute(
                "INSERT INTO knowledge (type, content, source, created_at) VALUES (?, ?, ?, datetime('now'))",
                ("seo", body[:10000], source_id),
            )
            kid = cur.lastrowid

            try:
                vec = get_embedding(body[:2000])
                db.execute(
                    "INSERT OR IGNORE INTO embeddings (knowledge_id, embedding, model, dimensions) VALUES (?, ?, ?, ?)",
                    (kid, vec.tobytes(), EMBED_MODEL, 768),
                )
            except Exception as e:
                print(f"  [embed] {title[:40]}: {e}", file=sys.stderr)

            db.commit()
            ok += 1
            state["imported"].add(source_id)

        except Exception as e:
            print(f"  [fail] {fpath.name}: {e}", file=sys.stderr)
            fail += 1

    state["imported"] = sorted(state["imported"])
    state["last_run"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2))

    print(f"[seo-ingest] {ok} ingested, {skip} skipped, {fail} failed ({len(pending)} pending)")


if __name__ == "__main__":
    main()
