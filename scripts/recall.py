#!/usr/bin/env python3
"""Hybrid search over knowledge.db: semantic (Ollama) + FTS5 + query expansion + RRF fusion.

Usage:
  python3 scripts/recall.py "query"           # hybrid
  python3 scripts/recall.py "query" --json    # JSON output
  python3 scripts/recall.py "query" --fts     # FTS5 only
  python3 scripts/recall.py "query" --graph   # show entity neighbors
"""
import argparse, json, os, re, sqlite3, sys, time, urllib.request, urllib.error
from pathlib import Path

import numpy as np

PROJECT = Path(os.environ.get("PROJECT_HOME", str(Path(__file__).resolve().parent.parent)))
DB = PROJECT / ".opencode" / "knowledge.db"
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_LIMIT = 10
DEFAULT_THRESHOLD = 0.2
RRF_K = 10


def get_db():
    if not DB.exists():
        print("[recall] knowledge.db not found", file=sys.stderr)
        sys.exit(1)
    return sqlite3.connect(str(DB))


def get_embedding(text):
    data = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode()
    resp = urllib.request.urlopen(
        urllib.request.Request(f"{OLLAMA_HOST}/api/embeddings",
            data=data, headers={"Content-Type": "application/json"}), timeout=30)
    return np.array(json.loads(resp.read())["embedding"], dtype=np.float32)


def cosine_similarity(a, b):
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom else 0.0


def expand_query(query):
    expansions = [query]
    has_kr = bool(re.search(r"[가-힣]", query))
    has_en = bool(re.search(r"[a-zA-Z]", query))
    if has_kr or has_en:
        cleaned = re.sub(r"[^a-zA-Z가-힣0-9\s]", "", query).strip()
        if cleaned and cleaned != query:
            expansions.append(cleaned)
        short = " ".join(query.split()[:3])
        if short and short != query:
            expansions.append(short)
    return list(set(expansions))[:3]


def semantic_search(db, qvec, limit=30, threshold=0.2):
    rows = db.execute(
        "SELECT k.id, e.embedding, k.content, k.source, k.type FROM knowledge k "
        "JOIN embeddings e ON e.knowledge_id = k.id WHERE e.model = ?",
        (EMBED_MODEL,)
    ).fetchall()
    scored = []
    for kid, blob, content, source, ktype in rows:
        vec = np.frombuffer(blob, dtype=np.float32)
        sim = cosine_similarity(qvec, vec)
        if sim >= threshold:
            scored.append((sim, kid, content, source, ktype))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:limit]


def fts_search(db, query, limit=30):
    # Try direct FTS5 search, fall back to LIKE
    try:
        q = " OR ".join(w for w in query.split() if len(w) > 1)
        if db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_fts'").fetchone():
            rows = db.execute(
                "SELECT k.id, k.content, k.source, k.type FROM knowledge_fts f "
                "JOIN knowledge k ON k.id = f.rowid WHERE knowledge_fts MATCH ? ORDER BY rank LIMIT ?",
                (q, limit)
            ).fetchall()
            return rows
    except:
        pass
    # Fallback: LIKE search
    like = "%" + query.replace(" ", "%") + "%"
    return db.execute(
        "SELECT id, content, source, type FROM knowledge WHERE content LIKE ? LIMIT ?",
        (like, limit)
    ).fetchall()


def rrf_fusion(sem_results, fts_results, limit=20):
    ranks = {}
    for i, (score, kid, *_) in enumerate(sem_results):
        ranks.setdefault(kid, {})["sem_rank"] = i + 1
        ranks[kid]["sem_score"] = score
        ranks[kid]["data"] = (kid, sem_results[i][2], sem_results[i][3], sem_results[i][4])
    for i, row in enumerate(fts_results):
        kid = row[0]
        ranks.setdefault(kid, {})["fts_rank"] = i + 1
        if "data" not in ranks:
            ranks[kid]["data"] = (kid, row[1], row[2], row[3])
    fused = []
    for kid, info in ranks.items():
        sem_r = info.get("sem_rank")
        fts_r = info.get("fts_rank")
        rrf = 0
        if sem_r:
            rrf += 1 / (RRF_K + sem_r)
        if fts_r:
            rrf += 1 / (RRF_K + fts_r)
        fused.append((rrf, kid, info["data"], info.get("sem_score", 0), sem_r, fts_r))
    fused.sort(key=lambda x: x[0], reverse=True)
    return fused[:limit]


def diversify(results, limit):
    seen_types = {}
    final = []
    for score, kid, meta, sem_score, sem_r, fts_r in results:
        if isinstance(meta, tuple):
            mtype = meta[3]
        else:
            mtype = ""
        if mtype not in seen_types:
            seen_types[mtype] = 0
        if seen_types[mtype] < 2 and len(final) < limit:
            final.append((score, kid, {
                "rrf": score, "sem_score": sem_score, "sem_rank": sem_r, "fts_rank": fts_r,
                "content": meta[2] if isinstance(meta, tuple) else meta.get("content", ""),
                "source": meta[3] if isinstance(meta, tuple) else meta.get("source", ""),
                "type": meta[4] if isinstance(meta, tuple) else meta.get("type", ""),
            }))
            seen_types[mtype] += 1
    return final


def get_entity_neighbors(db, kid, limit=5):
    rows = db.execute(
        "SELECT e.id, e.label, e.type FROM relations r "
        "JOIN entities e ON e.id = r.target_id "
        "WHERE r.source_id = ? AND r.type = 'references' AND e.type != '_task' LIMIT ?",
        (kid, limit),
    ).fetchall()
    return [{"id": r[0], "label": r[1], "type": r[2]} for r in rows]


def get_instruction_refs(db, kid):
    rows = db.execute("""
        SELECT DISTINCT e2.label FROM relations r
        JOIN entities e1 ON r.source_id = e1.id
        JOIN entities e2 ON r.target_id = e2.id
        WHERE e1.id IN (SELECT target_id FROM relations WHERE source_id = ?)
          AND r.type = 'references' AND e2.type = 'doc'
          AND e2.label LIKE 'instruction:%'
        LIMIT 3
    """, (kid,)).fetchall()
    return [r[0].replace("instruction:", "").replace(".md", "") for r in rows]


def auto_link(db, max_entries=100):
    cols = [r[1] for r in db.execute("PRAGMA table_info(knowledge)").fetchall()]
    if "graph_linked_at" not in cols:
        return 0
    rows = db.execute(
        "SELECT id, content FROM knowledge WHERE graph_linked_at IS NULL ORDER BY id DESC LIMIT ?",
        (max_entries,),
    ).fetchall()
    if not rows:
        return 0
    entity_cache = {}
    for eid, label, etype in db.execute(
        "SELECT id, label, type FROM entities WHERE type != '_task'"
    ).fetchall():
        for variant in [label.lower(), label.lower().replace("-", " "), label.lower().replace(" ", "")]:
            entity_cache[variant] = (eid, label, etype)
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    linked = 0
    for kid, content in rows:
        if not content:
            continue
        text_lower = content.lower()
        for norm_key, (eid, label, etype) in entity_cache.items():
            if len(norm_key) < 3:
                continue
            if norm_key in text_lower:
                if not db.execute(
                    "SELECT id FROM relations WHERE source_id = ? AND target_id = ? AND type = 'references'",
                    (kid, eid),
                ).fetchone():
                    db.execute(
                        "INSERT INTO relations (source_id, target_id, type, properties) VALUES (?, ?, ?, ?)",
                        (kid, eid, "references",
                         json.dumps({"source": "auto_link"}, ensure_ascii=False)),
                    )
                    linked += 1
        db.execute("UPDATE knowledge SET graph_linked_at = ? WHERE id = ?", (now, kid))
    db.commit()
    return linked


def main():
    parser = argparse.ArgumentParser(description="Hybrid search over agent knowledge")
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--semantic", action="store_true")
    parser.add_argument("--fts", action="store_true")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-expand", action="store_true")
    parser.add_argument("--graph", action="store_true", help="Show entity neighbors")
    parser.add_argument("--no-auto-link", action="store_true")
    args = parser.parse_args()

    if not args.query:
        query = input("> ")
    else:
        query = args.query

    db = get_db()

    if not args.no_auto_link:
        n = auto_link(db, 50)
        if n:
            print(f"[recall] auto-linked {n} new relations", file=sys.stderr) if not args.json else None

    if args.fts:
        results = fts_search(db, query, args.limit * 2)
        final = [(1.0, r[0], r) for r in results[:args.limit]] if results else []
    else:
        queries = [query]
        if not args.no_expand:
            queries = expand_query(query)
        all_sem = []
        seen_ids = set()
        for q in queries:
            try:
                qvec = get_embedding(q)
                for r in semantic_search(db, qvec, args.limit * 3, args.threshold):
                    if r[1] not in seen_ids:
                        all_sem.append(r)
                        seen_ids.add(r[1])
            except Exception:
                continue
        all_sem.sort(key=lambda x: x[0], reverse=True)
        all_sem = all_sem[:args.limit * 3]

        if args.semantic:
            final = [(s, kid, {"rrf": s, "sem_rank": i + 1, "fts_rank": None,
                "content": c, "source": src, "type": t, "sem_score": s})
                for i, (s, kid, c, src, t) in enumerate(all_sem[:args.limit])]
        else:
            fts_results = fts_search(db, query, args.limit * 3) if not args.semantic else []
            fused = rrf_fusion(all_sem, fts_results, args.limit * 2)
            final = diversify(fused, args.limit)

    if args.json:
        out = []
        for score, kid, meta in final:
            if isinstance(meta, dict):
                item = {"score": round(score, 4), "id": kid,
                    "source": meta["source"], "type": meta["type"],
                    "preview": meta["content"][:500]}
                if args.graph:
                    item["neighbors"] = get_entity_neighbors(db, kid)
                    item["instructions"] = get_instruction_refs(db, kid)
                out.append(item)
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return

    if not final:
        print("[recall] no results")
        return

    for score, kid, meta in final:
        content = meta["content"] if isinstance(meta, dict) else meta[2]
        stype = meta["type"] if isinstance(meta, dict) else meta[4]
        preview = content[:200].replace("\n", " ").strip()
        print(f"  [{score:.3f}] ({stype}) {preview}")
        if args.graph:
            neighbors = get_entity_neighbors(db, kid, limit=3)
            if neighbors:
                print(f"  └─ {', '.join(f'{n[\"label\"]}({n[\"type\"]})' for n in neighbors)}")
            instr_refs = get_instruction_refs(db, kid)
            if instr_refs:
                print(f"      📖 {', '.join(instr_refs)}")

    print(f"\n[recall] {len(final)} results")


if __name__ == "__main__":
    main()
