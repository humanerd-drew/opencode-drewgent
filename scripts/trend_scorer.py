#!/usr/bin/env python3
"""
Trend Scorer — heuristic scoring for newly collected trend items.

Reads collected/ items, runs heuristic_score (LLM-free), routes to
analyzed/keep/ (score >= threshold) or analyzed/graveyard/ (score < threshold).

Usage:
    python3 trend_scorer.py              # full run
    python3 trend_scorer.py --dry-run    # preview only
    python3 trend_scorer.py --keep       # override keep threshold (default 5.0)
"""
import json, shutil, sys, time
from datetime import datetime
from pathlib import Path
from collections import Counter

DREW_HOME = Path.home() / ".drewgent"
TREND_DIR = DREW_HOME / "@memory" / "growth" / "trend-harvester"
COLLECTED = TREND_DIR / "collected"
KEEP = TREND_DIR / "analyzed" / "keep"
GRAVEYARD = TREND_DIR / "analyzed" / "graveyard"
KEEP_THRESHOLD = 5.0

DRY_RUN = "--dry-run" in sys.argv
if "--keep" in sys.argv:
    idx = sys.argv.index("--keep")
    if idx + 1 < len(sys.argv):
        KEEP_THRESHOLD = float(sys.argv[idx + 1])
WIKI_PATH = DREW_HOME / "P5-ego" / "wiki" / "trend-harvester-keep.md"


def log(msg):
    prefix = "[DRY-RUN]" if DRY_RUN else "[scorer]"
    print(f"{prefix} {msg}")


def heuristic_score(item: dict) -> float:
    """Heuristic score 0-10 based on today_stars, language, keywords."""
    score = 3.0
    name = item.get("name", "") or ""
    desc = item.get("description", "") or ""
    full_name = item.get("full_name", "") or ""
    today_stars = item.get("today_stars", 0) or 0
    lang = item.get("language", "") or ""
    source = item.get("source", "") or ""
    combined = (name + " " + desc + " " + full_name).lower()

    if source == "github":
        score += min(3, today_stars / 100)
        if today_stars >= 50:
            score += 1
        if today_stars >= 200:
            score += 1
        hot_langs = {"python", "typescript", "rust", "go", "swift", "kotlin"}
        if lang.lower() in hot_langs:
            score += 0.5
        keywords = {"agent", "mcp", "llm", "ai", "model", "fine-tun", "rag",
                    "embedding", "vector", "workflow", "automation", "code",
                    "devops", "deploy", "sdk", "api", "framework", "compiler"}
        if any(k in combined for k in keywords):
            score += 0.5
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

    collected = item.get("collected_at", "")
    if collected:
        try:
            ts = datetime.fromisoformat(collected).timestamp()
            days_old = (time.time() - ts) / 86400
            score -= min(1.5, days_old / 14)
        except:
            pass
    return max(0, min(10, score))


def load_wiki_keeps() -> list[dict]:
    """Load existing keep items from analyzed/keep/."""
    items = []
    for f in sorted(KEEP.glob("*.json")):
        try:
            items.append(json.loads(f.read_text()))
        except:
            pass
    return items


def write_keep_item(item: dict, score: float, file_id: str) -> None:
    """Write a scored keep item to analyzed/keep/."""
    target = item.get("full_name") or item.get("name", "?")
    out = {
        "item": {
            "name": item.get("name", ""),
            "full_name": item.get("full_name", ""),
            "description": (item.get("description") or "")[:200],
            "url": item.get("url") or item.get("original_url", ""),
            "source": item.get("source", ""),
            "language": item.get("language", ""),
            "today_stars": item.get("today_stars", 0),
            "collected_at": item.get("collected_at", ""),
        },
        "scores": {
            "heuristic_score": round(score, 2),
            "_method": "heuristic",
        },
        "total_score": round(score, 2),
        "decision": "keep",
        "scored_at": datetime.now().isoformat(),
    }
    if not DRY_RUN:
        KEEP.mkdir(parents=True, exist_ok=True)
        (KEEP / file_id).write_text(json.dumps(out, indent=2))
        log(f"  KEEP {target[:60]:60s} score={score:.1f}")


def write_graveyard_item(item: dict, score: float, file_id: str) -> None:
    """Write a rejected item to analyzed/graveyard/."""
    target = item.get("full_name") or item.get("name", "?")
    out = {
        "item": {
            "name": item.get("name", ""),
            "full_name": item.get("full_name", ""),
            "description": (item.get("description") or "")[:200],
            "source": item.get("source", ""),
            "language": item.get("language", ""),
            "today_stars": item.get("today_stars", 0),
        },
        "scores": {
            "heuristic_score": round(score, 2),
            "_method": "heuristic",
        },
        "total_score": round(score, 2),
        "decision": "graveyard",
        "scored_at": datetime.now().isoformat(),
    }
    if not DRY_RUN:
        GRAVEYARD.mkdir(parents=True, exist_ok=True)
        (GRAVEYARD / file_id).write_text(json.dumps(out, indent=2))


def update_wiki_page(all_keeps: list[dict]) -> None:
    """Regenerate wiki page from all analyzed/keep/ items."""
    if DRY_RUN:
        return
    sorted_items = sorted(all_keeps, key=lambda x: -x.get("total_score", 0))
    lines = []
    for item in sorted_items:
        inner = item.get("item", {})
        name = inner.get("full_name") or inner.get("name", "?")
        url = inner.get("url", "")
        score = item.get("total_score", 0)
        lang = inner.get("language", "") or ""
        desc = (inner.get("description") or "")[:120]
        entry = f"- **{name}** (⭐{inner.get('today_stars', '?')}, {lang}) [{score}] — {desc}"
        if url:
            entry += f" [[link]({url})]"
        lines.append(entry)

    content = f"""---
title: Trend Harvester — Keep Items
type: index
space: growth
created: {datetime.now().strftime('%Y-%m-%d')}
---

# Trend Harvester Keep Items ({len(all_keeps)})

Auto-evaluated {datetime.now().strftime('%Y-%m-%d %H:%M')}.
Items with heuristic score ≥ {KEEP_THRESHOLD} preserved.

{chr(10).join(lines)}
"""
    WIKI_PATH.parent.mkdir(parents=True, exist_ok=True)
    WIKI_PATH.write_text(content)
    log(f"Wiki page updated: {WIKI_PATH} ({len(all_keeps)} keeps)")


def main():
    log(f"Trend scorer — threshold={KEEP_THRESHOLD}")

    if not COLLECTED.exists():
        log(f"collected/ not found: {COLLECTED}")
        return

    files = sorted(COLLECTED.glob("*.json"))
    if not files:
        log("No new items in collected/")
        return

    log(f"Scoring {len(files)} new items...")
    keep_count = 0
    retire_count = 0
    for f in files:
        try:
            item = json.loads(f.read_text())
        except:
            log(f"  SKIP (unparseable): {f.name}")
            continue

        score = heuristic_score(item)
        file_id = f.name

        if score >= KEEP_THRESHOLD:
            write_keep_item(item, score, file_id)
            keep_count += 1
        else:
            write_graveyard_item(item, score, file_id)
            retire_count += 1

        # Remove from collected/ after scoring
        if not DRY_RUN:
            f.unlink()

    log(f"Done: {keep_count} keep, {retire_count} retire")

    if keep_count > 0:
        all_keeps = []
        for f in sorted(KEEP.glob("*.json")):
            try:
                all_keeps.append(json.loads(f.read_text()))
            except:
                pass
        update_wiki_page(all_keeps)

    log(f"collected/ now has {len(list(COLLECTED.glob('*.json')))} remaining items")


if __name__ == "__main__":
    main()
