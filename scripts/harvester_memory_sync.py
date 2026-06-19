#!/usr/bin/env python3
"""
Harvester Memory Sync — P4-cortex trend-harvester output → P2-hippocampus memories

Closes the P4→P2 downstream pipeline:
  trend-harvester/analyzed/ → P2-hippocampus/memories/insights/
  trend-harvester/pending/  → P2-hippocampus/memories/concepts/
  trend-harvester/applied/  → P2-hippocampus/memories/concepts/

Usage:
  python3 harvester_memory_sync.py         # full sync
  python3 harvester_memory_sync.py --dry-run   # show what would be synced
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

_DREWGENT_HOME = Path.home() / ".drewgent"
sys.path.insert(0, str(_DREWGENT_HOME))

from agent.obsidian_graph import ensure_backlink, ensure_related_section, wiki_link

_P4_TREND_HARVESTER = _DREWGENT_HOME / "P4-cortex" / "growth" / "trend-harvester"
_P2_INSIGHTS = _DREWGENT_HOME / "P2-hippocampus" / "memories" / "insights"
_P2_CONCEPTS = _DREWGENT_HOME / "P2-hippocampus" / "memories" / "concepts"
_P2_MEMORIES = _DREWGENT_HOME / "P2-hippocampus" / "memories"
_P4_KNOWLEDGE = _DREWGENT_HOME / "P4-cortex" / "knowledge"
_STATE_FILE = _P4_KNOWLEDGE / "harvester_sync_state.json"
_DRY_RUN = False


def ensure_trend_index() -> Path:
    """Create an Obsidian anchor for the trend-harvester corpus."""
    index_file = _P4_TREND_HARVESTER / "index.md"
    if _DRY_RUN or index_file.exists():
        return index_file
    _P4_TREND_HARVESTER.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    index_file.write_text(
        "\n".join(
            [
                "---",
                "title: Trend Harvester",
                "tags: [P4, growth, trend, harvester, cron]",
                f"created: {today}",
                f"updated: {today}",
                "links:",
                f'  - "{wiki_link("P2-hippocampus/memories/index")}"',
                f'  - "{wiki_link("P2-hippocampus/memories/insights/index")}"',
                f'  - "{wiki_link("P2-hippocampus/memories/concepts/index")}"',
                "---",
                "",
                "# Trend Harvester",
                "",
                "Cron-collected trend corpus and downstream P2 memory sync anchor.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return index_file


def ensure_graph_links(path: Path, links: list[str]) -> None:
    """Keep synced trend markdown connected in the Obsidian graph."""
    if _DRY_RUN or not path.exists():
        return
    trend_index = ensure_trend_index()
    content = path.read_text(encoding="utf-8", errors="ignore")
    updated = ensure_related_section(content, links)
    if updated != content:
        path.write_text(updated, encoding="utf-8")
    for parent in (
        _P2_MEMORIES / "index.md",
        _P2_MEMORIES / "SCHEMA.md",
        _P2_CONCEPTS / "index.md",
        _P2_INSIGHTS / "index.md",
        trend_index,
    ):
        ensure_backlink(parent, path, _DREWGENT_HOME)


def insight_log_header(month: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    return "\n".join(
        [
            "---",
            f"title: Trend Insights {month}",
            "tags: [insights, trends, cron]",
            f"created: {today}",
            f"updated: {today}",
            "links:",
            f'  - "{wiki_link("P2-hippocampus/memories/index")}"',
            f'  - "{wiki_link("P2-hippocampus/memories/insights/index")}"',
            f'  - "{wiki_link("P4-cortex/growth/trend-harvester/index")}"',
            "---",
            "",
            f"# Trend Insights {month}",
            "",
        ]
    )


def trend_frontmatter(title: str, tags: list[str]) -> list[str]:
    today = datetime.now().strftime("%Y-%m-%d")
    tag_str = ", ".join(tags)
    return [
        "---",
        f"title: {title}",
        f"created: {today}",
        f"updated: {today}",
        f"tags: [{tag_str}]",
        "links:",
        f'  - "{wiki_link("P2-hippocampus/memories/index")}"',
        f'  - "{wiki_link("P2-hippocampus/memories/concepts/index")}"',
        f'  - "{wiki_link("P4-cortex/growth/trend-harvester/index")}"',
        "---",
        "",
    ]


def load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text())
        except Exception:
            pass
    return {"synced_hashes": [], "last_sync_at": None, "synced_count": 0}


def save_state(state: dict) -> None:
    if _DRY_RUN:
        return
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def content_hash(content: str) -> str:
    return hashlib.md5(content.encode()).hexdigest()[:16]


def already_synced(state: dict, h: str) -> bool:
    return h in state.get("synced_hashes", [])


def mark_synced(state: dict, h: str) -> None:
    if h not in state["synced_hashes"]:
        state["synced_hashes"].append(h)
    state["synced_count"] += 1


def sync_analyzed_keep(state: dict) -> list:
    """Copy analyzed/keep/*.json → insights/YYYY-MM.md (appended)"""
    results = []
    keep_dir = _P4_TREND_HARVESTER / "analyzed" / "keep"
    if not keep_dir.exists():
        return results

    for f in keep_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue

        item = data.get("item", {})
        h = content_hash(item.get("url", "") or item.get("description", ""))
        if already_synced(state, h):
            continue

        month = datetime.now().strftime("%Y-%m")
        insight_file = _P2_INSIGHTS / f"{month}.md"
        insight_file.parent.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [
            f"## [{ts}] Trend: {item.get('name', data.get('name', '?')) or data.get('description', '?')[:60]}",
            f"- **Source**: {item.get('url', data.get('url', 'unknown'))}",
            f"- **Score**: {data.get('total_score', data.get('score', '?'))} | **Axes**: {data.get('scores', {})}",
            f"- **Reason**: {data.get('reason', 'see source')}",
            "",
        ]
        content = "\n".join(lines)
        marker = f"<!-- trend:{h} -->"

        existing = insight_file.read_text() if insight_file.exists() else ""
        if marker not in existing:
            mode = "a" if not _DRY_RUN else None
            if mode:
                if not existing:
                    insight_file.write_text(insight_log_header(month), encoding="utf-8")
                    mode = "a"
                with open(insight_file, mode, encoding="utf-8") as fh:
                    fh.write(content + "\n" + marker + "\n\n")
                ensure_graph_links(
                    insight_file,
                    [
                        wiki_link("P2-hippocampus/memories/index"),
                        wiki_link("P2-hippocampus/memories/insights/index"),
                        wiki_link("P4-cortex/growth/trend-harvester/index"),
                    ],
                )
            results.append(f"{'[DRY-RUN] ' if _DRY_RUN else ''}keep → {insight_file.name}: {item.get('name', '?')[:50]}")
        mark_synced(state, h)

    return results


def sync_analyzed_review(state: dict) -> list:
    """Copy analyzed/review/*.json → insights/pending/"""
    results = []
    review_dir = _P4_TREND_HARVESTER / "analyzed" / "review"
    pending_dir = _P2_INSIGHTS / "pending"
    if not review_dir.exists():
        return results
    pending_dir.mkdir(parents=True, exist_ok=True)

    for f in review_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue

        item = data.get("item", {})
        h = content_hash(item.get("url", "") or item.get("description", ""))
        if already_synced(state, h):
            continue

        slug = item.get("name", f.stem).replace("/", "_").replace(" ", "-")[:40]
        dest = pending_dir / f"{slug}.json"
        if not _DRY_RUN:
            dest.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        results.append(f"{'[DRY-RUN] ' if _DRY_RUN else ''}review → {dest.name}: {item.get('name', '?')[:50]}")
        mark_synced(state, h)

    return results


def sync_pending(state: dict) -> list:
    """Copy pending/*.json → concepts/"""
    results = []
    pending_dir = _P4_TREND_HARVESTER / "pending"
    if not pending_dir.exists():
        return results
    _P2_CONCEPTS.mkdir(parents=True, exist_ok=True)

    for f in pending_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue

        h = content_hash(data.get("item", {}).get("url", "") or data.get("item", {}).get("description", ""))
        if already_synced(state, h):
            continue

        slug = data.get("name", f.stem).replace("/", "_").replace(" ", "-")[:40]
        dest = _P2_CONCEPTS / f"trend-{slug}.md"

        # Write as markdown
        title = f"Trend: {data.get('name', '?')}"
        md = trend_frontmatter(title, ["concept", "trend", "cron"]) + [
            f"# Trend: {data.get('name', '?')}",
            f"",
            f"**Source**: {data.get('url', 'unknown')}",
            f"**Score**: {data.get('score', '?')}",
            f"**Axes**: {json.dumps(data.get('axes', {}), ensure_ascii=False)}",
            f"**Applied at**: {datetime.now().isoformat()}",
            f"",
            f"## Summary",
            f"{data.get('description', '?')}",
            "",
        ]
        content = "\n".join(md)
        if not _DRY_RUN:
            dest.write_text(content)
            ensure_graph_links(
                dest,
                [
                    wiki_link("P2-hippocampus/memories/index"),
                    wiki_link("P2-hippocampus/memories/concepts/index"),
                    wiki_link("P4-cortex/growth/trend-harvester/index"),
                ],
            )
        results.append(f"{'[DRY-RUN] ' if _DRY_RUN else ''}pending → {dest.name}: {data.get('name', '?')[:50]}")
        mark_synced(state, h)

    return results


def sync_applied(state: dict) -> list:
    """Copy applied/*.json → concepts/ + tag trend-applied"""
    results = []
    applied_dir = _P4_TREND_HARVESTER / "applied"
    if not applied_dir.exists():
        return results
    _P2_CONCEPTS.mkdir(parents=True, exist_ok=True)

    for f in applied_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue

        h = content_hash(data.get("item", {}).get("url", "") or data.get("item", {}).get("description", ""))
        if already_synced(state, h):
            continue

        slug = data.get("name", f.stem).replace("/", "_").replace(" ", "-")[:40]
        dest = _P2_CONCEPTS / f"trend-applied-{slug}.md"

        title = f"Trend Applied: {data.get('name', '?')}"
        md = trend_frontmatter(title, ["concept", "trend-applied", "cron"]) + [
            f"# Trend Applied: {data.get('name', '?')}",
            f"",
            f"**Source**: {data.get('url', 'unknown')}",
            f"**Score**: {data.get('score', '?')}",
            f"**Applied at**: {datetime.now().isoformat()}",
            f"**Tags**: `trend-applied`",
            f"",
            f"## Summary",
            f"{data.get('description', '?')}",
            f"",
            f"## Application Notes",
            f"{data.get('application_notes', 'Applied via trend-harvester pipeline')}",
            "",
        ]
        if not _DRY_RUN:
            dest.write_text("\n".join(md))
            ensure_graph_links(
                dest,
                [
                    wiki_link("P2-hippocampus/memories/index"),
                    wiki_link("P2-hippocampus/memories/concepts/index"),
                    wiki_link("P4-cortex/growth/trend-harvester/index"),
                ],
            )
        results.append(f"{'[DRY-RUN] ' if _DRY_RUN else ''}applied → {dest.name}: {data.get('name', '?')[:50]}")
        mark_synced(state, h)

    return results


def main() -> int:
    global _DRY_RUN

    parser = argparse.ArgumentParser(description="Harvester Memory Sync — P4→P2 bridge")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    _DRY_RUN = args.dry_run

    state = load_state()
    all_results = []

    print(f"Harvester Memory Sync {'(DRY-RUN)' if _DRY_RUN else ''}")
    print(f"  Source: {_P4_TREND_HARVESTER}")
    print(f"  Dest:   {_DREWGENT_HOME}/P2-hippocampus/memories/")
    print()

    r1 = sync_analyzed_keep(state)
    r2 = sync_analyzed_review(state)
    r3 = sync_pending(state)
    r4 = sync_applied(state)

    all_results = r1 + r2 + r3 + r4

    if not all_results:
        print("No new trends to sync (all hashes already synced or no output yet).")
        return 2

    print(f"Synced {len(all_results)} trend(s):")
    for r in all_results:
        print(f"  {r}")

    if not _DRY_RUN:
        state["last_sync_at"] = datetime.now().isoformat()
        state["last_sync_job"] = "trend-harvester-001"
        save_state(state)
        print(f"\nState saved: {state['synced_count']} total synced, last at {state['last_sync_at']}")

    return 0 if all_results else 2


if __name__ == "__main__":
    sys.exit(main())
