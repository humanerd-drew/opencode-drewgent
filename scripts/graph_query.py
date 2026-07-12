#!/usr/bin/env python3
"""Graph-reason query engine: explore, trace, and RCA modes.

Usage:
  python3 scripts/graph_query.py --mode explore "query"
  python3 scripts/graph_query.py --mode trace "entity"
  python3 scripts/graph_query.py --mode rca "incident"
  python3 scripts/graph_query.py --json --mode explore "query"
  python3 scripts/graph_query.py --mode explore "launchd" --infer
"""
import argparse, json, re, sqlite3, sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
DB = PROJECT / ".opencode" / "knowledge.db"


def connect():
    db = sqlite3.connect(str(DB))
    db.row_factory = sqlite3.Row
    return db


def fuzzy_find_entities(db, query):
    rows = db.execute(
        "SELECT id, label, type, properties FROM entities WHERE label LIKE ? ORDER BY id DESC LIMIT 10",
        (f"%{query}%",),
    ).fetchall()
    return [dict(r) for r in rows]


def traverse_relations(db, entity_id, direction="both", depth=3, rel_type=None):
    if direction == "out":
        dir_clause = "r.source_id = ?"
        next_col = "r.target_id"
    elif direction == "in":
        dir_clause = "r.target_id = ?"
        next_col = "r.source_id"
    else:
        dir_clause = "(r.source_id = ? OR r.target_id = ?)"
        next_col = "CASE WHEN r.source_id = ? THEN r.target_id ELSE r.source_id END"

    type_filter = ""
    if rel_type:
        type_filter = "AND r.type = ?"

    params = [entity_id]
    if direction == "both":
        params.append(entity_id)
    params.append(entity_id)
    if rel_type:
        params.append(rel_type)

    sql = f"""
        WITH RECURSIVE path AS (
            SELECT r.id AS rel_id, r.type AS rel_type,
                   {next_col} AS next_id, 1 AS lvl
            FROM relations r
            WHERE {dir_clause} {type_filter}
            UNION ALL
            SELECT r.id, r.type,
                   {next_col}, p.lvl + 1
            FROM path p
            JOIN relations r ON {'r.source_id' if direction in ('out', 'both') else 'r.target_id'} = p.next_id
            WHERE p.lvl < ? {type_filter}
        )
        SELECT DISTINCT p.rel_id, p.rel_type, e.id, e.label, e.type, p.lvl
        FROM path p
        JOIN entities e ON e.id = p.next_id
        ORDER BY p.lvl
    """
    params.append(depth)
    if rel_type:
        params.append(rel_type)

    rows = db.execute(sql, params).fetchall()
    return [{"rel_id": r[0], "rel_type": r[1], "entity_id": r[2],
             "entity_label": r[3], "entity_type": r[4], "level": r[5]} for r in rows]


def format_explore(db, query, entities, depth=3):
    out = {"query": query, "entities": []}
    for ent in entities:
        node = {"id": ent["id"], "label": ent["label"], "type": ent["type"],
                "neighbors": []}
        rels = traverse_relations(db, ent["id"], "out", depth)
        seen_labels = set()
        for r in rels:
            if r["entity_label"] not in seen_labels:
                node["neighbors"].append({
                    "relation": r["rel_type"], "label": r["entity_label"],
                    "type": r["entity_type"], "level": r["level"],
                })
                seen_labels.add(r["entity_label"])
        out["entities"].append(node)
    return out


def format_trace(db, query, entities, depth=4):
    out = {"query": query, "trace": []}
    for ent in entities:
        node = {"entity": ent["label"], "type": ent["type"],
                "inbound": [], "outbound": []}
        for r in traverse_relations(db, ent["id"], "in", depth):
            node["inbound"].append({"relation": r["rel_type"],
                "entity": r["entity_label"], "level": r["level"]})
        for r in traverse_relations(db, ent["id"], "out", depth):
            node["outbound"].append({"relation": r["rel_type"],
                "entity": r["entity_label"], "level": r["level"]})
        out["trace"].append(node)
    return out


def format_rca(db, query, entities, depth=3):
    out = {"query": query, "root_causes": []}
    for ent in entities:
        if ent["type"] not in ("incident", "pattern"):
            continue
        rca = {"incident": {"id": ent["id"], "label": ent["label"]}, "timeline": []}
        for c in traverse_relations(db, ent["id"], "in", depth, rel_type="caused"):
            rca["timeline"].append({"type": "cause", "entity": c["entity_label"],
                "entity_type": c["entity_type"], "level": c["level"]})
        for f in traverse_relations(db, ent["id"], "out", depth, rel_type="fixed_by"):
            rca["timeline"].append({"type": "fix", "entity": f["entity_label"],
                "entity_type": f["entity_type"], "level": f["level"]})
        out["root_causes"].append(rca)
    return out


def main():
    parser = argparse.ArgumentParser(description="Graph-reason query engine")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--mode", choices=["explore", "trace", "rca"], default="explore")
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--entity-id", type=int, help="Direct entity ID (skip fuzzy search)")
    parser.add_argument("--infer", action="store_true", help="Run inference (transitive)")
    args = parser.parse_args()

    db = connect()

    if args.entity_id:
        entities = [dict(r) for r in db.execute(
            "SELECT id, label, type, properties FROM entities WHERE id = ?",
            (args.entity_id,)
        ).fetchall()]
    else:
        entities = fuzzy_find_entities(db, args.query)

    if not entities:
        print(f"[graph-query] no entities matched '{args.query}'")
        return

    if args.infer:
        try:
            from inference import transitive_closure
            for e in entities:
                deps = transitive_closure(db, e["id"], "depends_on", "out", args.depth)
                if deps:
                    print(f"  🔗 {e['label']} depends_on: {' → '.join(d['label'] for d in deps[:5])}")
                dep_by = transitive_closure(db, e["id"], "depends_on", "in", args.depth)
                if dep_by:
                    print(f"  🔙 {e['label']} depended by: {' ← '.join(d['label'] for d in dep_by[:5])}")
        except ImportError:
            print("  (inference engine not available)")

    if args.mode == "explore":
        result = format_explore(db, args.query, entities, depth=args.depth)
    elif args.mode == "trace":
        result = format_trace(db, args.query, entities, depth=args.depth)
    elif args.mode == "rca":
        result = format_rca(db, args.query, entities, depth=args.depth)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if args.mode == "explore":
        print(f"\n[graph-query] mode=explore depth={args.depth}")
        for e in result["entities"]:
            print(f"\n  ┌─ {e['label']} ({e['type']}) id={e['id']}")
            for n in e["neighbors"][:8]:
                print(f"  ├── {n['label']} --{n['relation']}--> {n['label']}")
            if len(e["neighbors"]) > 8:
                print(f"  └── ... and {len(e['neighbors']) - 8} more")
    elif args.mode == "trace":
        print(f"\n[graph-query] mode=trace depth={args.depth}")
        for t in result["trace"]:
            print(f"\n  ┌─ {t['entity']} ({t['type']})")
            for r in t["inbound"][:5]:
                print(f"  ← [{r['level']}] {r['entity']} --{r['relation']}-->")
            for r in t["outbound"][:5]:
                print(f"  → [{r['level']}] --{r['relation']}--> {r['entity']}")
    elif args.mode == "rca":
        print(f"\n[graph-query] mode=rca depth={args.depth}")
        for rca in result["root_causes"]:
            print(f"\n  ┌─ Incident: {rca['incident']['label']}")
            for t in rca["timeline"][:5]:
                print(f"  {'🛠' if t['type']=='fix' else '🔍'} [{t['level']}] {t['entity']} ({t['entity_type']})")

    db.close()


if __name__ == "__main__":
    main()
