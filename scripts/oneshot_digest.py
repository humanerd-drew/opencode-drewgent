#!/usr/bin/env python3
"""One-shot cleanup: digest accumulated raw data, then prune.

Usage:
  python3 oneshot_digest.py              # dry-run (no destructive ops)
  python3 oneshot_digest.py --apply      # actually run

Sections (independent, skippable):
  1. state.db — session rows ≥30일 DELETE + VACUUM
  2. @memory/sessions/ — raw files ≥30일 DELETE
  3. QA evidence — aggregate → wiki → raw DELETE
  4. Trend collected — heuristic scoring → gbrain → collected DELETE
  5. Stale/empty DB files — DELETE
"""
import json, os, sqlite3, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

DREW_HOME = Path.home() / ".drewgent"
DRY_RUN = "--apply" not in sys.argv

def log(msg):
    tag = "DRY-RUN" if DRY_RUN else "EXECUTE"
    print(f"[{tag}] {msg}")

def fmt(n):
    if n >= 1_000_000_000:
        return f"{n/1_000_000_000:.1f}GB"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}MB"
    if n >= 1_000:
        return f"{n/1_000:.1f}KB"
    return f"{n}B"

# ═══════════════════════════════════════════════════════════════════
# 1. state.db — session TTL
# ═══════════════════════════════════════════════════════════════════
def prune_state_db():
    db_path = DREW_HOME / "state.db"
    if not db_path.exists():
        log("state.db not found, skipping")
        return 0
    before = db_path.stat().st_size
    conn = sqlite3.connect(str(db_path))
    cut = int(time.time()) - 30 * 86400
    # sessions table
    cur = conn.execute("SELECT COUNT(*) FROM sessions WHERE started_at < ?", (cut * 1000,))
    old_sessions = cur.fetchone()[0]
    cur = conn.execute("SELECT COUNT(*) FROM sessions")
    total_sessions = cur.fetchone()[0]
    log(f"state.db sessions: {old_sessions}/{total_sessions} rows ≥30일 old")

    if not DRY_RUN and old_sessions:
        conn.execute("DELETE FROM sessions WHERE started_at < ?", (cut * 1000,))
        conn.commit()
        # also prune orphaned messages
        conn.execute("""
            DELETE FROM messages WHERE session_id NOT IN (
                SELECT id FROM sessions
            )
        """)
        conn.commit()
        conn.execute("PRAGMA optimize")
        conn.commit()
        conn.execute("VACUUM")
        conn.commit()
        after = db_path.stat().st_size
        log(f"state.db: {fmt(before)} → {fmt(after)} (reclaimed {fmt(before - after)})")
    elif not DRY_RUN:
        log(f"state.db: no old sessions to delete")
    else:
        log(f"state.db: would delete {old_sessions} sessions + orphaned messages, then VACUUM")

    conn.close()
    return before

# ═══════════════════════════════════════════════════════════════════
# 2. @memory/sessions/ — raw files ≥30일
# ═══════════════════════════════════════════════════════════════════
def prune_sessions_files():
    sess_dir = DREW_HOME / "@memory" / "sessions"
    if not sess_dir.exists():
        log("@memory/sessions/ not found, skipping")
        return 0
    cut = time.time() - 30 * 86400
    total = 0
    size = 0
    for f in sess_dir.iterdir():
        if f.is_file() and f.stat().st_mtime < cut:
            total += 1
            size += f.stat().st_size
            if not DRY_RUN:
                f.unlink()
    log(f"@memory/sessions/: {total} files ({fmt(size)}) ≥30일 old" +
        (" (dry-run, would delete)" if DRY_RUN else " deleted"))
    return size

# ═══════════════════════════════════════════════════════════════════
# 3. QA evidence — aggregate → wiki → DELETE
# ═══════════════════════════════════════════════════════════════════
def digest_qa_evidence():
    qa_dir = DREW_HOME / "P2-hippocampus" / "qa-evidence"
    if not qa_dir.exists():
        log("qa-evidence/ not found, skipping")
        return
    # UUID-named directories each containing contract.json
    entries = sorted(qa_dir.iterdir())
    schema_file = qa_dir / "SCHEMA.json"
    uuid_dirs = [d for d in entries if d.is_dir() and len(d.name) == 36 and d.name.count("-") == 4]
    others = [e for e in entries if e not in uuid_dirs and e.name != "__init__.py"]
    log(f"qa-evidence/: {len(uuid_dirs)} UUID directories, {len(others)} other entries")

    # Aggregate: scan a sample to understand shape
    results = Counter()
    sample_contract = None
    for d in uuid_dirs[:10]:
        contract = d / "contract.json"
        if contract.exists():
            try:
                data = json.loads(contract.read_text())
                results["parsed_ok"] += 1
                if not sample_contract:
                    sample_contract = list(data.keys())[:10] if isinstance(data, dict) else type(data).__name__
            except:
                results["parse_fail"] += 1

    # Write summary to wiki
    wiki_dir = DREW_HOME / "P5-ego" / "wiki"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    wiki_path = wiki_dir / "qa-evidence-summary.md"
    wiki_content = f"""---
title: QA Evidence Summary
type: index
space: meta
created: {datetime.now().strftime('%Y-%m-%d')}
---

# QA Evidence Archive

Aggregated from {len(uuid_dirs)} auto-generated evidence directories.

| Metric | Value |
|--------|-------|
| UUID directories | {len(uuid_dirs)} |
| Other entries | {len(others)} |
| Sampled keys | {json.dumps(sample_contract) if sample_contract else 'N/A'} |
| Sampled parsed | {results.get('parsed_ok', 0)} / 10 |
| Date range | {time.ctime(min(d.stat().st_mtime for d in uuid_dirs)) if uuid_dirs else 'N/A'} ~ {time.ctime(max(d.stat().st_mtime for d in uuid_dirs)) if uuid_dirs else 'N/A'} |

This replaces the raw UUID-named directories in `P2-hippocampus/qa-evidence/`.
Signal preserved; raw files pruned.
"""
    if not DRY_RUN:
        wiki_path.write_text(wiki_content)
        import shutil
        for d in uuid_dirs:
            shutil.rmtree(d)
        log(f"qa-evidence/: aggregate written to {wiki_path}, {len(uuid_dirs)} UUID directories deleted")
    else:
        log(f"qa-evidence/: would aggregate {len(uuid_dirs)} dirs → {wiki_path}, then delete")

# ═══════════════════════════════════════════════════════════════════
# 4. Trend collected — heuristic scoring → gbrain → DELETE
# ═══════════════════════════════════════════════════════════════════
def heuristic_score(item: dict) -> float:
    """Score 0-10: 0=noise, 10=must-keep."""
    score = 3.0
    name = item.get("name", "") or ""
    desc = item.get("description", "") or ""
    full_name = item.get("full_name", "") or ""
    today_stars = item.get("today_stars", 0) or 0
    lang = item.get("language", "") or ""
    source = item.get("source", "") or ""
    combined = (name + " " + desc + " " + full_name).lower()

    # GitHub repos
    if source == "github":
        # today_stars = daily trending velocity (most accurate signal)
        score += min(3, today_stars / 100)
        if today_stars >= 50:
            score += 1
        if today_stars >= 200:
            score += 1

        # Language bonus
        hot_langs = {"python", "typescript", "rust", "go", "swift", "kotlin"}
        if lang.lower() in hot_langs:
            score += 0.5

        # AI/tool keywords
        keywords = {"agent", "mcp", "llm", "ai", "model", "fine-tun", "rag",
                    "embedding", "vector", "workflow", "automation", "code",
                    "devops", "deploy", "sdk", "api", "framework", "compiler"}
        if any(k in combined for k in keywords):
            score += 0.5

    # GeekNews — human-curated, score by content richness
    elif source == "geeknews":
        score += 1.5
        content = item.get("geeknews_content", item.get("content", ""))
        if isinstance(content, str) and len(content) > 500:
            score += 0.5

        korean_keywords = {"ai", "인공지능", "llm", "에이전트", "agent", "mcp",
                          "모델", "오픈소스", "개발", "코드", "자동화",
                          "cloud", "클라우드", "보안", "데이터", "gpu"}
        if any(k in combined for k in korean_keywords):
            score += 0.5

    # Recency: newer = better (half-life ~14 days)
    collected = item.get("collected_at", "")
    if collected:
        try:
            ts = datetime.fromisoformat(collected).timestamp()
            days_old = (time.time() - ts) / 86400
            score -= min(1.5, days_old / 14)
        except:
            pass

    return max(0, min(10, score))


def digest_trends():
    col_dir = DREW_HOME / "@memory" / "growth" / "trend-harvester" / "collected"
    if not col_dir.exists():
        log("trend-harvester/collected/ not found, skipping")
        return
    files = sorted(col_dir.glob("*.json"))
    log(f"trend-harvester: {len(files)} items to score")

    scored = []
    for f in files:
        try:
            item = json.loads(f.read_text())
            s = heuristic_score(item)
            item["_score"] = round(s, 2)
            item["_file"] = f.name
            scored.append(item)
        except:
            pass

    keep = [x for x in scored if x["_score"] >= 6.0]
    retire = [x for x in scored if x["_score"] < 6.0]
    log(f"trend-harvester: {len(keep)} keep (score≥6), {len(retire)} retire (score<6)")

    # Write keep items to gbrain-compatible page
    wiki_dir = DREW_HOME / "P5-ego" / "wiki"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    keep_lines = []
    for item in sorted(keep, key=lambda x: -x["_score"]):
        name = item.get("full_name") or item.get("name", "?")
        url = item.get("url") or item.get("original_url", "")
        stars = item.get("stars", "?")
        lang = item.get("language", "")
        desc = (item.get("description") or "")[:120]
        keep_lines.append(f"- **{name}** (⭐{stars}, {lang}) [{item['_score']}] — {desc}")
        if url:
            keep_lines[-1] += f" [[link]({url})]"

    wiki_content = f"""---
title: Trend Harvester — Keep Items
type: index
space: growth
created: {datetime.now().strftime('%Y-%m-%d')}
---

# Trend Harvester Keep Items ({len(keep)})

Auto-evaluated {datetime.now().strftime('%Y-%m-%d %H:%M')} from {len(files)} collected items.
Items with heuristic score ≥ 6.0 preserved.

{chr(10).join(keep_lines)}
"""
    wiki_path = wiki_dir / "trend-harvester-keep.md"

    if not DRY_RUN:
        wiki_path.write_text(wiki_content)
        for f in files:
            f.unlink()
        log(f"trend-harvester: keep summary → {wiki_path}, {len(files)} collected files deleted")
    else:
        log(f"trend-harvester: would write {len(keep)} keep items → {wiki_path}, delete {len(files)} files")

    return keep, retire

# ═══════════════════════════════════════════════════════════════════
# 5. Stale/empty DB files
# ═══════════════════════════════════════════════════════════════════
STALE_DBS = [
    "sessions.db",
    "cron/jobs.db",
    "state/drewgent_cron.db",
    "state/scheduler.db",
    "state/state.db",
    "state/awareness_log.jsonl",
]

def clean_stale_dbs():
    reclaimed = 0
    for rel in STALE_DBS:
        p = DREW_HOME / rel
        if p.exists() and p.stat().st_size == 0:
            reclaimed += 1
            if not DRY_RUN:
                p.unlink()
            log(f"stale: {rel} (0 bytes)" + (" → deleted" if not DRY_RUN else " → would delete"))
        elif p.exists():
            log(f"stale: {rel} — {fmt(p.stat().st_size)}, NOT empty, skipping")
    total = sum(
        (DREW_HOME / rel).stat().st_size
        for rel in STALE_DBS
        if (DREW_HOME / rel).exists()
    )
    if total > 0 and not DRY_RUN:
        log(f"stale: would have skipped {fmt(total)} non-empty files")
    return reclaimed

# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════
def main():
    print(f"{'='*60}")
    print(f"  Drewgent One-Shot Digest")
    print(f"  Mode: {'DRY RUN' if DRY_RUN else 'LIVE'}")
    print(f"  Started: {datetime.now().isoformat()}")
    print(f"{'='*60}")
    print()

    print("─── 1. state.db session TTL ───")
    prune_state_db()
    print()

    print("─── 2. @memory/sessions/ file TTL ───")
    prune_sessions_files()
    print()

    print("─── 3. QA evidence ───")
    digest_qa_evidence()
    print()

    print("─── 4. Trend harvester ───")
    digest_trends()
    print()

    print("─── 5. Stale/empty DBs ───")
    clean_stale_dbs()
    print()

    print(f"{'='*60}")
    if DRY_RUN:
        print("  DRY RUN complete. Run with --apply to execute.")
    else:
        print("  DONE.")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
