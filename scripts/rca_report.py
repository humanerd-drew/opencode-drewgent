#!/usr/bin/env python3
"""RCA report generator — graph path → NL analysis.

Usage:
  python3 scripts/rca_report.py "cron stuck"
  python3 scripts/rca_report.py --json "parse_schedule"
"""
import argparse, json, sqlite3, subprocess, sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
DB = PROJECT / ".opencode" / "knowledge.db"
GRAPH_QUERY = PROJECT / "scripts" / "graph_query.py"


def run_graph_query(query, mode="rca", depth=3):
    proc = subprocess.run(
        [sys.executable, str(GRAPH_QUERY), "--mode", mode,
         "--depth", str(depth), "--json", query],
        capture_output=True, text=True, timeout=30,
    )
    if proc.returncode != 0:
        return None, proc.stderr
    try:
        return json.loads(proc.stdout), None
    except json.JSONDecodeError as e:
        return None, str(e)


def get_knowledge_for_entity(db, entity_id, limit=5):
    rows = db.execute("""
        SELECT k.content, k.type, k.source FROM knowledge k
        JOIN relations r ON r.source_id = k.id
        WHERE r.target_id = ? AND r.type = 'references'
        LIMIT ?
    """, (entity_id, limit)).fetchall()
    return rows


def generate_report(result, db):
    lines = [f"# RCA Report", ""]
    for rca in result.get("root_causes", []):
        inc = rca.get("incident", {})
        lines.append(f"## Incident: {inc.get('label', 'unknown')}")
        timeline = rca.get("timeline", [])
        if not timeline:
            lines.append("  No causal chain found.")
            continue
        for t in timeline:
            marker = "🛠 Fix" if t["type"] == "fix" else "🔍 Cause"
            lines.append(f"  {marker} [{t['level']}] {t['entity']} ({t['entity_type']})")
            # Look for knowledge entries
            if db:
                for kid, in db.execute(
                    "SELECT id FROM entities WHERE label = ?", (t['entity'],)
                ).fetchall():
                    for kc, kt, ks in get_knowledge_for_entity(db, kid):
                        lines.append(f"    → {kc[:120]}...")
                        break
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="RCA report generator")
    parser.add_argument("query", help="Incident or pattern query")
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result, err = run_graph_query(args.query, "rca", args.depth)
    if not result:
        print(f"RCA failed: {err}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    db = sqlite3.connect(str(DB))
    report = generate_report(result, db)
    db.close()
    print(report)


if __name__ == "__main__":
    main()
