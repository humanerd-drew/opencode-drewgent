#!/usr/bin/env python3
"""Semantic search over knowledge.db using Ollama embeddings + FTS5 fallback.

Usage:
  python3 scripts/recall.py "질문 내용"             # semantic search
  python3 scripts/recall.py "질문" --fts            # FTS5 only
  python3 scripts/recall.py "질문" --limit 5        # top 5
  python3 scripts/recall.py "질문" --threshold 0.3  # similarity cutoff
"""
import argparse, json, os, sqlite3, sys
from pathlib import Path

import numpy as np
import urllib.request, urllib.error

DREW = Path(os.environ.get("DREW_HOME", str(Path.home() / ".drewgent")))
DB = DREW / ".opencode" / "knowledge.db"
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_LIMIT = 10
DEFAULT_THRESHOLD = 0.25


def get_db():
    if not DB.exists():
        print("[recall] knowledge.db not found", file=sys.stderr)
        sys.exit(1)
    return sqlite3.connect(str(DB))


def get_embedding(text):
    data = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/embeddings",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=30)
    return np.array(json.loads(resp.read())["embedding"], dtype=np.float32)


def cosine_similarity(a, b):
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def semantic_search(db, query_vec, limit, threshold):
    rows = db.execute(
        "SELECT k.id, k.content, k.source, k.type, e.embedding, e.dimensions "
        "FROM knowledge k "
        "JOIN embeddings e ON e.knowledge_id = k.id AND e.model = ?",
        (EMBED_MODEL,)
    ).fetchall()

    scored = []
    for kid, content, source, ktype, blob, dims in rows:
        stored = np.frombuffer(blob, dtype=np.float32)
        if stored.shape[0] != dims:
            continue
        sim = cosine_similarity(query_vec, stored)
        if sim >= threshold:
            scored.append((sim, kid, content, source, ktype))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:limit]


def fts_search(db, query, limit):
    rows = db.execute(
        "SELECT k.id, k.content, k.source, k.type, rank "
        "FROM knowledge_fts f JOIN knowledge k ON f.rowid = k.id "
        "WHERE knowledge_fts MATCH ? "
        "ORDER BY rank LIMIT ?",
        (query, limit)
    ).fetchall()
    return [(1.0 - r[4], r[0], r[1], r[2], r[3]) for r in rows]


def main():
    parser = argparse.ArgumentParser(description="Semantic search over agent knowledge")
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--fts", action="store_true", help="FTS5 only (no semantic)")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help=f"Max results (default {DEFAULT_LIMIT})")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                        help=f"Similarity threshold (default {DEFAULT_THRESHOLD})")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if not args.query:
        query = input("> ")
    else:
        query = args.query

    db = get_db()

    if args.fts:
        results = fts_search(db, query, args.limit)
    else:
        query_vec = get_embedding(query)
        results = semantic_search(db, query_vec, args.limit, args.threshold)

        if not results:
            ft = fts_search(db, query, args.limit)
            if ft:
                if not args.json:
                    print("[recall] semantic: no match, FTS5 fallback:")
                results = ft

    if args.json:
        out = []
        for score, kid, content, source, ktype in results:
            preview = content[:500] if content else ""
            out.append({
                "score": round(score, 4),
                "id": kid,
                "source": source,
                "type": ktype,
                "preview": preview,
            })
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return

    if not results:
        print("[recall] no results")
        return

    for score, kid, content, source, ktype in results:
        preview = content[:200].replace("\n", " ").strip()
        print(f"  [{score:.3f}] ({source or kid}) {preview}")

    print(f"\n[recall] {len(results)} results")


if __name__ == "__main__":
    main()
