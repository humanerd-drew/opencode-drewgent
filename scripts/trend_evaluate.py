#!/usr/bin/env python3
"""
Trend Evaluate — find unevaluated keep items and create kanban tasks.
Replaces the n8n_trigger_runner.py path (n8n removed 2026-06-18).

Flow:
  1. trend-collect → trend-scorer → keep/
  2. This script: find keep items not marked in evaluated/
  3. Top N by composite score → kanban INSERT
  4. Mark processed: evaluated/YYYY-MM-DD-queue-{hash}.json

Usage:
  python3 trend_evaluate.py              # process top 5
  python3 trend_evaluate.py --limit 10   # process top 10
  python3 trend_evaluate.py --dry-run    # preview only
"""
import json, os, sys, time, uuid
from pathlib import Path
from datetime import date

HOME = Path.home()
KEEP = HOME / ".drewgent" / "@memory" / "growth" / "trend-harvester" / "analyzed" / "keep"
EVALUATED = HOME / ".drewgent" / "@memory" / "growth" / "trend-harvester" / "evaluated"
KANBAN_DB = HOME / ".drewgent" / "kanban.db"
LIMIT = 5
THRESHOLD = 0.65
DRY_RUN = "--dry-run" in sys.argv
if "--limit" in sys.argv:
    idx = sys.argv.index("--limit")
    if idx + 1 < len(sys.argv):
        LIMIT = int(sys.argv[idx + 1])

TODAY = date.today().isoformat()


def log(msg):
    prefix = "[DRY-RUN]" if DRY_RUN else "[evaluate]"
    print(f"{prefix} {msg}")


def get_evaluated_set():
    """Return set of keep base names that have been evaluated."""
    if not EVALUATED.exists():
        return set()
    evaluated = set()
    for f in os.listdir(str(EVALUATED)):
        # filenames: YYYY-MM-DD-queue-{hash}.json or YYYY-MM-DD-apply-{hash}.json or YYYY-MM-DD-discard-{hash}.json
        parts = f.replace(".json", "").split("-")
        if len(parts) >= 4:
            evaluated.add(parts[-1])  # last segment = hash
    return evaluated


def composite_score(scores: dict) -> float:
    axes = [scores.get(k, 0) for k in ("relevance", "direct_impact", "actionability", "novelty", "credibility")]
    return sum(axes) / max(len(axes), 1)


def main():
    if not KEEP.exists():
        log(f"keep dir not found: {KEEP}")
        return
    if not KANBAN_DB.exists():
        log(f"kanban db not found: {KANBAN_DB}")
        return

    evaluated_set = get_evaluated_set()
    log(f"evaluated items: {len(evaluated_set)}")

    candidates = []
    for fname in sorted(os.listdir(str(KEEP))):
        if not fname.endswith(".json"):
            continue
        base = fname.replace(".json", "")
        if base in evaluated_set:
            continue
        try:
            d = json.loads((KEEP / fname).read_text())
        except Exception as e:
            log(f"  skip {fname}: {e}")
            continue
        item = d.get("item", {})
        scores = d.get("scores", {})
        comp = composite_score(scores)
        if comp < THRESHOLD:
            continue
        name = item.get("name", base)[:60]
        url = item.get("url", "")
        desc = (item.get("description", "") or "")[:200]
        candidates.append((comp, name, url, desc, base, fname))

    candidates.sort(key=lambda x: -x[0])
    log(f"unevaluated above threshold ({THRESHOLD}): {len(candidates)}")

    if not candidates:
        print("silent")
        return

    batch = candidates[:LIMIT]
    log(f"processing top {len(batch)}:")

    now_ts = int(time.time())
    created = 0
    for comp, name, url, desc, base, fname in batch:
        task_id = f"trend-evaluate-{TODAY}-{base}"
        title = f"trend-evaluate: {name}"
        body = f"""## Trend Evaluate: {name}

**Source**: {url}
**Composite score**: {comp:.2f}
**Description**: {desc}

### Task
1. Review this tool/project
2. Determine relevance to Drewgent
3. If applicable → create implementation plan
4. If not applicable → mark as discarded

### Score Breakdown
See keep file: {fname}
"""
        log(f"  → {title} (score={comp:.2f})")

        if not DRY_RUN:
            import sqlite3
            try:
                conn = sqlite3.connect(str(KANBAN_DB))
                conn.execute(
                    "INSERT OR IGNORE INTO tasks (id, title, body, status, priority, created_at, skills) "
                    "VALUES (?, ?, ?, 'pending', 1, ?, '[\"kanban-orchestrator\"]')",
                    (task_id, title, body, now_ts),
                )
                conn.commit()
                conn.close()
                created += 1
            except Exception as e:
                log(f"  DB error: {e}")
                continue

        # Mark evaluated
        if not DRY_RUN:
            marker = EVALUATED / f"{TODAY}-queue-{base}.json"
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text(json.dumps({
                "keep_file": fname,
                "name": name,
                "score": comp,
                "kanban_id": task_id,
                "created_at": TODAY,
            }, ensure_ascii=False, indent=2))

    if created > 0 and not DRY_RUN:
        log(f"created {created} kanban tasks")
        print(f"{created}")
    elif DRY_RUN:
        log(f"[DRY-RUN] would create {len(batch)} tasks")
        print(f"dry-run: {len(batch)} tasks")


if __name__ == "__main__":
    main()
