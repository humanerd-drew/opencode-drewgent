#!/usr/bin/env python3
"""notion-indexer — Build INDEX.md and _cache_meta.json from Notion search JSON.

Usage:
  1. Agent searches Notion via notion_API-post-search
  2. Agent pipes result JSON to this script:
     cat search_results.json | python3 notion-indexer.py pilates --categorize '{"11ba...":"theory","1aae...":"business"}'

Output:
  - Writes INDEX.md to P2-hippocampus/{domain}/
  - Writes _cache_meta.json with detected entries
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HIPPOCAMPUS = Path.home() / ".loragent" / "P2-hippocampus"
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s\-_가-힣]", "", text)
    return re.sub(r"\s+", "-", text.strip())[:80]


def parse_search(json_input: str) -> tuple[list, list]:
    data = json.loads(json_input)
    pages, dbs = [], []
    for item in data.get("results", []):
        obj_type = item.get("object")
        title = ""
        props = item.get("properties", {})
        title_field = props.get("title", props.get("이름", {}))
        for t in title_field.get("title", []):
            title += t.get("plain_text", "")
        entry = {
            "id": item["id"],
            "title": title.strip(),
            "object": obj_type,
            "last_edited": item.get("last_edited_time", ""),
            "url": item.get("url", ""),
            "parent_type": item.get("parent", {}).get("type", ""),
        }
        if obj_type == "data_source":
            entry["schema"] = list(item.get("properties", {}).keys())
            dbs.append(entry)
        else:
            pages.append(entry)
    return pages, dbs


def build_index_md(domain: str, pages: list, dbs: list, categories: dict) -> str:
    lines = []
    lines.append("---")
    lines.append(f"title: {domain.title()} Knowledge Index")
    lines.append("type: index")
    lines.append(f"domain: {domain}")
    lines.append(f"generated: {NOW}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {domain.title()} 지식 인덱스")
    lines.append("")
    lines.append(f"| 항목 | 값 |")
    lines.append(f"|------|-----|")
    lines.append(f"| 도메인 | {domain} |")
    lines.append(f"| Notion 검색어 | (기록 필요) |")
    lines.append(f"| 총 페이지 | {len(pages)} |")
    lines.append(f"| 총 DB | {len(dbs)} |")
    lines.append(f"| 마지막 갱신 | {NOW} |")
    lines.append("")
    lines.append("## Databases (API 전용)")
    lines.append("")
    lines.append("| DB명 | ID | 스키마 |")
    lines.append("|------|-----|-------|")
    for db in sorted(dbs, key=lambda x: x["title"]):
        schema_str = ", ".join(db.get("schema", [])[:5])
        lines.append(f"| {db['title']} | `{db['id']}` | {schema_str} |")
    lines.append("")
    lines.append("## Pages")
    lines.append("")
    grouped = {}
    for p in pages:
        cat = categories.get(p["id"], "uncategorized")
        grouped.setdefault(cat, []).append(p)
    for cat in sorted(grouped.keys()):
        lines.append(f"### {cat}")
        lines.append("")
        lines.append("| 제목 | ID | 최종수정 |")
        lines.append("|------|-----|---------|")
        for p in sorted(grouped[cat], key=lambda x: x["title"]):
            short_id = p["id"][:8] + "..."
            edited = p["last_edited"][:10] if p["last_edited"] else "-"
            lines.append(f"| {p['title']} | `{p['id']}` | {edited} |")
        lines.append("")
    lines.append("## 조회 방법")
    lines.append("")
    lines.append("```")
    lines.append("# Notion 페이지 내용 조회")
    lines.append('notion_API-retrieve-page-markdown(page_id="...")')
    lines.append("")
    lines.append("# Notion DB 전체 조회")
    lines.append('notion_API-query-data-source(data_source_id="...", page_size=100)')
    lines.append("")
    lines.append("# 로컬 캐시 확인")
    lines.append("cat P2-hippocampus/{domain}/{category}/{slug}.md")
    lines.append("```")
    return "\n".join(lines)


def build_cache_meta(domain: str, pages: list, categories: dict) -> dict:
    entries = []
    for p in pages:
        entries.append({
            "notion_id": p["id"],
            "title": p["title"],
            "last_edited_at": p["last_edited"],
            "last_synced_at": NOW,
            "category": categories.get(p["id"], "uncategorized"),
            "tags": [],
            "relations": [],
            "local_path": None,
            "archived": False,
        })
    return {
        "$schema": "loragent:notion-knowledge-sync:cache-meta:v1",
        "domain": domain,
        "created_at": NOW,
        "entries": entries,
    }


def main():
    parser = argparse.ArgumentParser(description="Notion knowledge indexer")
    parser.add_argument("domain", help="Domain name (e.g. pilates)")
    parser.add_argument("--categorize", default="{}",
                        help='JSON map of notion_id→category, e.g. \'{"id1":"theory","id2":"business"}\'')
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--input", "-i", type=argparse.FileType("r"), default=sys.stdin,
                        help="Notion search JSON file/stdin")
    args = parser.parse_args()

    categories = json.loads(args.categorize)
    pages, dbs = parse_search(args.input.read())

    domain_dir = HIPPOCAMPUS / args.domain
    if not args.dry_run:
        (domain_dir).mkdir(parents=True, exist_ok=True)

    index_md = build_index_md(args.domain, pages, dbs, categories)
    cache_meta = build_cache_meta(args.domain, pages, categories)

    if args.dry_run:
        print("=== INDEX.md (preview) ===")
        print(index_md[:500])
        print("...")
        print("\n=== _cache_meta.json (preview) ===")
        print(json.dumps(cache_meta, indent=2, ensure_ascii=False)[:500])
        print("...")
        print(f"\nWould write {len(pages)} pages + {len(dbs)} DBs to {domain_dir}")
        return

    (domain_dir / "INDEX.md").write_text(index_md, encoding="utf-8")
    (domain_dir / "_cache_meta.json").write_text(
        json.dumps(cache_meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[ok] INDEX.md written ({len(index_md)} chars)")
    print(f"[ok] _cache_meta.json written ({len(cache_meta['entries'])} entries)")
    print(f"[ok] Domain: {args.domain} at {domain_dir}")
    print(f"[next] Fetch core pages: notion_API-retrieve-page-markdown(id)")


if __name__ == "__main__":
    main()
