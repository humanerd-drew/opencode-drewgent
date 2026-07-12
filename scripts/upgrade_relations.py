#!/usr/bin/env python3
"""Upgrade flat 'references' to typed relations via co-occurrence inference.

Run after you have accumulated knowledge entries:
  python3 scripts/upgrade_relations.py

This scans entity co-occurrence in knowledge entries and creates
semantic relations (depends_on, led_to, fixed_by, etc.).
"""
import json, sqlite3
from pathlib import Path
from collections import defaultdict

PROJECT = Path(__file__).resolve().parent.parent
DB = PROJECT / ".opencode" / "knowledge.db"

CO_OCCUR_RULES = [
    ("incident", "pattern", "fixed_by"),
    ("incident", "decision", "fixed_by"),
    ("incident", "tool", "depends_on"),
    ("incident", "script", "depends_on"),
    ("decision", "tool", "depends_on"),
    ("decision", "script", "depends_on"),
    ("decision", "skill", "depends_on"),
    ("pattern", "tool", "depends_on"),
    ("pattern", "script", "depends_on"),
    ("decision", "decision", "led_to"),
    ("decision", "pattern", "led_to"),
    ("pattern", "decision", "led_to"),
]


def main():
    db = sqlite3.connect(str(DB))
    db.execute("PRAGMA journal_mode=WAL")

    # Group entity references by knowledge entry
    by_entry = defaultdict(list)
    for kid, eid, label, etype in db.execute("""
        SELECT r.source_id, r.target_id, e.label, e.type
        FROM relations r
        JOIN entities e ON r.target_id = e.id
        WHERE r.type = 'references'
    """).fetchall():
        by_entry[kid].append((eid, label, etype))

    # Load existing entity→entity relations for dedup
    existing = set()
    for r in db.execute("""
        SELECT DISTINCT r.source_id, r.target_id, r.type
        FROM relations r
        JOIN entities e1 ON r.source_id = e1.id
        JOIN entities e2 ON r.target_id = e2.id
    """).fetchall():
        existing.add((r[0], r[1], r[2]))

    created = 0
    for kid, entities in by_entry.items():
        for i in range(len(entities)):
            for j in range(len(entities)):
                if i == j:
                    continue
                src_id, _, src_type = entities[i]
                tgt_id, _, tgt_type = entities[j]
                for rule_src, rule_tgt, new_rel in CO_OCCUR_RULES:
                    if src_type == rule_src and tgt_type == rule_tgt:
                        if (src_id, tgt_id, new_rel) not in existing:
                            db.execute(
                                "INSERT INTO relations (source_id, target_id, type, properties) VALUES (?, ?, ?, ?)",
                                (src_id, tgt_id, new_rel,
                                 json.dumps({"source": "co_occur_inference", "knowledge_id": kid})),
                            )
                            created += 1
                            existing.add((src_id, tgt_id, new_rel))
                        break

    db.commit()
    dist = {r[0]: r[1] for r in db.execute(
        "SELECT type, COUNT(*) FROM relations GROUP BY type ORDER BY COUNT(*) DESC"
    ).fetchall()}
    print(json.dumps({"created": created, "distribution": dist}, indent=2))
    db.close()


if __name__ == "__main__":
    raise SystemExit(main())
