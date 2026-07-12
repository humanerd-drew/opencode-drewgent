#!/usr/bin/env python3
"""Ontology inference engine — transitive closure, backtrace, contradictions.

Usage:
  python3 scripts/inference.py transitive --entity launchd --type depends_on
  python3 scripts/inference.py backtrace --entity "incident-42"
  python3 scripts/inference.py contradictions
  python3 scripts/inference.py all
"""
import argparse, json, sqlite3
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
DB = PROJECT / ".opencode" / "knowledge.db"


def get_db():
    return sqlite3.connect(str(DB))


def transitive_closure(db, start_entity_id, relation_type="depends_on", direction="out", max_depth=10):
    """Follow typed relation chains with cycle detection."""
    if direction == "out":
        sql = """
            WITH RECURSIVE chain AS (
                SELECT r.target_id AS next_id, 1 AS lvl,
                       r.type AS rel_type, r.id AS rel_id,
                       '|' || CAST(r.source_id AS TEXT) || '|' || CAST(r.target_id AS TEXT) || '|' AS path
                FROM relations r
                WHERE r.source_id = ? AND r.type = ?
                  AND r.source_id != r.target_id
                UNION ALL
                SELECT r.target_id, c.lvl + 1,
                       r.type, r.id,
                       c.path || CAST(r.target_id AS TEXT) || '|'
                FROM chain c
                JOIN relations r ON r.source_id = c.next_id AND r.type = ?
                WHERE c.lvl < ? AND r.source_id != r.target_id
                  AND instr(c.path, '|' || CAST(r.target_id AS TEXT) || '|') = 0
            )
            SELECT DISTINCT e.id, e.label, e.type, e.type_parent, c.lvl
            FROM chain c
            JOIN entities e ON e.id = c.next_id
            ORDER BY c.lvl
        """
        params = (start_entity_id, relation_type, relation_type, max_depth)
    else:
        sql = """
            WITH RECURSIVE chain AS (
                SELECT r.source_id AS next_id, 1 AS lvl,
                       r.type AS rel_type, r.id AS rel_id,
                       '|' || CAST(r.target_id AS TEXT) || '|' || CAST(r.source_id AS TEXT) || '|' AS path
                FROM relations r
                WHERE r.target_id = ? AND r.type = ?
                  AND r.source_id != r.target_id
                UNION ALL
                SELECT r.source_id, c.lvl + 1,
                       r.type, r.id,
                       c.path || CAST(r.source_id AS TEXT) || '|'
                FROM chain c
                JOIN relations r ON r.target_id = c.next_id AND r.type = ?
                WHERE c.lvl < ? AND r.source_id != r.target_id
                  AND instr(c.path, '|' || CAST(r.source_id AS TEXT) || '|') = 0
            )
            SELECT DISTINCT e.id, e.label, e.type, e.type_parent, c.lvl
            FROM chain c
            JOIN entities e ON e.id = c.next_id
            ORDER BY c.lvl
        """
        params = (start_entity_id, relation_type, relation_type, max_depth)

    rows = db.execute(sql, params).fetchall()
    return [{"id": r[0], "label": r[1], "type": r[2], "parent": r[3], "level": r[4]} for r in rows]


def fix_backtrace(db, entity_id, max_depth=8):
    """Trace fixed_by → depends_on chain."""
    fixed_by = db.execute("""
        SELECT r.target_id, e.label, e.type
        FROM relations r
        JOIN entities e ON e.id = r.target_id
        WHERE r.source_id = ? AND r.type = 'fixed_by'
    """, (entity_id,)).fetchall()
    results = []
    for fix_id, fix_label, fix_type in fixed_by:
        results.append({"source": "fixed_by", "label": fix_label, "type": fix_type, "level": 0})
        deps = transitive_closure(db, fix_id, "depends_on", "out", max_depth)
        for d in deps:
            d["source"] = "depends_on"
            results.append(d)
    return results


def detect_contradictions(db):
    """Find entities connected by contradicts AND another relation type."""
    contradictions = []
    rows = db.execute("""
        SELECT c.source_id, c.target_id,
               e1.label, e1.type, e2.label, e2.type,
               r.type AS other_rel
        FROM relations c
        JOIN relations r ON r.source_id = c.source_id AND r.target_id = c.target_id
        JOIN entities e1 ON e1.id = c.source_id
        JOIN entities e2 ON e2.id = c.target_id
        WHERE c.type = 'contradicts' AND r.type != 'contradicts'
    """).fetchall()
    for r in rows:
        contradictions.append({
            "type": "direct_conflict",
            "entity_a": f"{r[2]}({r[3]})",
            "entity_b": f"{r[4]}({r[5]})",
            "detail": f"{r[2]} --{r[6]}--> {r[4]}, but also contradicts"
        })
    return contradictions


def cmd_all(args):
    db = get_db()
    print("=" * 50)
    print("ONTOLOGY INFERENCE REPORT")
    print("=" * 50)
    print(f"\nEntities: {db.execute('SELECT COUNT(*) FROM entities').fetchone()[0]}")
    print(f"Relations: {db.execute('SELECT COUNT(*) FROM relations').fetchone()[0]}")
    print(f"\n--- Relation distribution ---")
    for r in db.execute("SELECT type, COUNT(*) FROM relations GROUP BY type ORDER BY COUNT(*) DESC").fetchall():
        print(f"  {r[0]}: {r[1]}")
    contradictions = detect_contradictions(db)
    print(f"\n--- Contradictions: {len(contradictions)} ---")
    for c in contradictions:
        print(f"  ⚠️ {c['detail']}")
    db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ontology inference engine")
    sub = parser.add_subparsers(dest="command")
    p_t = sub.add_parser("transitive")
    p_t.add_argument("--entity", required=True)
    p_t.add_argument("--type", default="depends_on")
    p_t.add_argument("--direction", choices=["out", "in"], default="out")
    p_t.add_argument("--depth", type=int, default=10)
    p_b = sub.add_parser("backtrace")
    p_b.add_argument("--entity", required=True)
    p_b.add_argument("--depth", type=int, default=8)
    sub.add_parser("contradictions")
    sub.add_parser("all")
    args = parser.parse_args()
    db = get_db()

    if args.command == "transitive":
        entity = db.execute("SELECT id, label, type FROM entities WHERE label = ? OR id = ?",
            (args.entity, int(args.entity) if args.entity.isdigit() else -1)).fetchone()
        if not entity:
            print(f"entity not found: {args.entity}")
            raise SystemExit(1)
        rows = transitive_closure(db, entity[0], args.type, args.direction, args.depth)
        arrow = "←" if args.direction == "in" else "→"
        for r in rows:
            print(f"  [{r['level']}] {arrow} {r['label']}({r['type']})")
        print(f"\n  {len(rows)} hops")
    elif args.command == "backtrace":
        entity = db.execute("SELECT id, label, type FROM entities WHERE label = ? OR id = ?",
            (args.entity, int(args.entity) if args.entity.isdigit() else -1)).fetchone()
        if not entity:
            print(f"entity not found: {args.entity}")
            raise SystemExit(1)
        rows = fix_backtrace(db, entity[0], args.depth)
        for r in rows:
            tag = "🛠" if r["source"] == "fixed_by" else "📦"
            print(f"  {tag} [{r['level']}] {r['label']}({r['type']})")
    elif args.command == "contradictions":
        rows = detect_contradictions(db)
        for r in rows:
            print(f"  ⚠️ {r['detail']}")
        if not rows:
            print("  none")
    elif args.command == "all":
        cmd_all(args)
    db.close()
