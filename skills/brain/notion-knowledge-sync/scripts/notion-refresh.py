#!/usr/bin/env python3
"""notion-refresh — Check _cache_meta.json for stale entries.

Compares local last_edited_at with Notion's current last_edited_time.
Outputs stale entries for re-fetch. Can be called before any knowledge query.

Usage:
  python3 notion-refresh.py pilates  # Check domain, output stale list
  python3 notion-refresh.py pilates --check "id1,id2"  # Check specific IDs
  python3 notion-refresh.py pilates --update-meta  # Update _cache_meta after re-fetch
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HIPPOCAMPUS = Path.home() / ".loragent" / "P2-hippocampus"
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_meta(domain: str) -> dict:
    path = HIPPOCAMPUS / domain / "_cache_meta.json"
    if not path.exists():
        print(f"[notion-refresh] No _cache_meta.json for domain: {domain}", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def save_meta(domain: str, meta: dict):
    path = HIPPOCAMPUS / domain / "_cache_meta.json"
    path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def check_stale(entry: dict) -> bool:
    """Agent should check Notion API before calling this.

    This script expects the agent to provide current Notion last_edited_time
    via --check or stdin. Returns True if entry is stale.
    """
    return False  # Agent handles API call; this is a placeholder


def main():
    parser = argparse.ArgumentParser(description="Notion cache refresher")
    parser.add_argument("domain", help="Domain name")
    parser.add_argument("--check", default="",
                        help='Comma-separated notion_ids to check, or "all"')
    parser.add_argument("--update-meta", default="",
                        help='JSON: {"notion_id": {"last_edited_at": "...", "local_path": "..."}}')
    parser.add_argument("--mark-archived", default="",
                        help='Comma-separated notion_ids to mark archived')
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    meta = load_meta(args.domain)
    entries = {e["notion_id"]: e for e in meta["entries"]}

    if args.mark_archived:
        ids = [x.strip() for x in args.mark_archived.split(",")]
        for nid in ids:
            if nid in entries:
                entries[nid]["archived"] = True
                entries[nid]["last_synced_at"] = NOW
                print(f"[notion-refresh] Marked archived: {entries[nid]['title']}")
        if not args.dry_run:
            meta["entries"] = list(entries.values())
            save_meta(args.domain, meta)
        return

    if args.update_meta:
        updates = json.loads(args.update_meta)
        for nid, upd in updates.items():
            if nid in entries:
                entries[nid].update(upd)
                entries[nid]["last_synced_at"] = NOW
                print(f"[notion-refresh] Updated meta: {entries[nid]['title']}")
        if not args.dry_run:
            meta["entries"] = list(entries.values())
            save_meta(args.domain, meta)
        return

    if args.check:
        ids = [x.strip() for x in args.check.split(",")]
        if ids == ["all"]:
            ids = list(entries.keys())
        stale = []
        for nid in ids:
            e = entries.get(nid)
            if not e:
                continue
            if e.get("archived"):
                continue
            stale.append({
                "notion_id": nid,
                "title": e["title"],
                "local_path": e.get("local_path"),
                "last_edited_at": e["last_edited_at"],
                "last_synced_at": e["last_synced_at"],
                "category": e.get("category", "uncategorized"),
            })
        print(json.dumps({"stale": stale}, indent=2, ensure_ascii=False))
        print(f"\n[notion-refresh] {len(stale)} entries to check. Call Notion API for each, then --update-meta.")
        return

    # Default: show status
    total = len(entries)
    archived = sum(1 for e in entries.values() if e.get("archived"))
    cached = sum(1 for e in entries.values() if e.get("local_path"))
    print(f"[notion-refresh] Domain: {args.domain}")
    print(f"  Total entries: {total}")
    print(f"  Archived: {archived}")
    print(f"  Cached locally: {cached}")
    print(f"  Pending cache: {total - archived - cached}")
    print(f"[next] Run with --check all to verify staleness")


if __name__ == "__main__":
    main()
