#!/usr/bin/env python3
"""
SEO Article Analyzer
====================
Reads unprocessed articles from _new/, uses LLM to analyze (dedup, summarize, categorize),
updates frontmatter with results, adds wikilinks, moves to year directory.

Usage:
    python3 analyzer.py                       # 분석 실행 (최대 5개)
    python3 analyzer.py --dry-run             # 분석만 출력, 파일 변경 없음
    python3 analyzer.py --force FILE.md       # 특정 파일 강제 분석
"""

import os, re, json, sys, subprocess, shutil, time
from datetime import datetime
from pathlib import Path

DREW_HOME = Path(os.environ.get("DREW_HOME", os.path.expanduser("~/.drewgent")))
SEO_DIR = DREW_HOME / "P2-hippocampus" / "knowledge" / "seo-articles"
NEW_DIR = SEO_DIR / "_new"
STATE_FILE = DREW_HOME / "P4-cortex" / "growth" / "seo" / "seo_analysis_state.json"
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
ANALYZED_COUNT_FILE = DREW_HOME / "P4-cortex" / "growth" / "seo" / "analyzed_count.json"
MAX_PER_RUN = 5
YEAR = str(datetime.now().year)

ANALYSIS_PROMPT = """You are an SEO article analyst. Analyze the given article and respond with ONLY valid JSON (no markdown, no explanation).

Article title: {title}
Content preview: {content_preview}
Source URL: {source_url}

Return JSON with these fields:
- "category": one of ["technical-seo", "content-marketing", "google-update", "ai-search", "local-seo", "ecommerce-seo", "link-building", "analytics", "seo-general"]
- "summary": 2-3 sentence Korean summary
- "key_insights": array of 2-3 key points in Korean
- "relevance_score": 1-5 integer
- "is_duplicate": true/false (true if this is clearly a near-duplicate of another article on the same topic)
- "tags": array of 3-5 relevant tags
- "linked_wikilinks": array of Drewgent P-node wikilinks relevant to this article's topic (e.g. ["P4-cortex/growth/seo/technical-seo", "P2-hippocampus/knowledge/seo"])
- "duplicate_reason": string explaining why if is_duplicate=true, else null
"""


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"analyzed_urls": [], "analyzed_count": 0, "last_analyzed_at": None}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    ANALYZED_COUNT_FILE.write_text(json.dumps({
        "analyzed_count": state["analyzed_count"],
        "last_analyzed_at": state["last_analyzed_at"],
    }, ensure_ascii=False, indent=2))


def analyze_article(title: str, content_preview: str, source_url: str) -> dict:
    prompt = ANALYSIS_PROMPT.format(
        title=title[:200],
        content_preview=content_preview[:1500],
        source_url=source_url,
    )
    result = subprocess.run(
        ["opencode", "run", "--model", "opencode-go/deepseek-v4-flash"],
        input=prompt, capture_output=True, text=True, timeout=120,
    )
    stdout = result.stdout.strip()
    json_match = re.search(r"```(?:json)?\s*\n?(\{.*?\n?\})\s*```", stdout, re.DOTALL)
    if json_match:
        stdout_clean = json_match.group(1).strip()
    else:
        brace_start = stdout.find("{")
        brace_end = stdout.rfind("}")
        if brace_start >= 0 and brace_end > brace_start:
            stdout_clean = stdout[brace_start:brace_end + 1]
        else:
            stdout_clean = stdout
    try:
        parsed = json.loads(stdout_clean)
        required = ["category", "summary", "key_insights", "relevance_score", "is_duplicate", "tags"]
        for k in required:
            if k not in parsed:
                raise ValueError(f"Missing field: {k}")
        return parsed
    except (json.JSONDecodeError, ValueError) as e:
        print(f"  ⚠ LLM parse failed: {e}")
        print(f"  Raw output: {stdout[:300]}")
        return {
            "category": "seo-general",
            "summary": "",
            "key_insights": [],
            "relevance_score": 1,
            "is_duplicate": False,
            "duplicate_reason": None,
            "tags": ["seo"],
            "linked_wikilinks": ["P2-hippocampus/knowledge/seo-articles/index-by-topic"],
        }


def update_article(filepath: Path, analysis: dict) -> None:
    content = filepath.read_text(encoding="utf-8", errors="ignore")
    now = datetime.now()
    analysis_date = now.strftime("%Y-%m-%d %H:%M")

    new_links = [
        '"[[P2-hippocampus/knowledge/seo-articles/index-by-topic]]"',
        '"[[skills/seo-article-harvester/SKILL]]"',
    ]
    for wl in analysis.get("linked_wikilinks", []):
        link = f'"[[{wl}]]"'
        if link not in new_links:
            new_links.append(link)

    links_yaml = "\n".join(f"  - {l}" for l in new_links)
    tags = analysis.get("tags", ["seo"])
    tags_yaml = ", ".join(tags)
    key_insights = analysis.get("key_insights", [])
    insights_yaml = "\n".join(f'  - "{k}"' for k in key_insights)

    frontmatter = f"""---
title: {filepath.stem.split("_")[0].replace("-", " ").title()}
source: {extract_source_url(content)}
analyzed: true
analyzed_date: {analysis_date}
category: {analysis["category"]}
relevance_score: {analysis["relevance_score"]}
is_duplicate: {json.dumps(analysis["is_duplicate"])}
tags: [{tags_yaml}]
links:
{links_yaml}
---

# {analysis["summary"]}

**카테고리:** {analysis["category"]}
**관련도:** {'⭐' * analysis["relevance_score"]}

## 핵심 인사이트
{chr(10).join(f'- {k}' for k in key_insights)}

## 원문
{content_preview(content)}
"""

    filepath.write_text(frontmatter, encoding="utf-8")


def extract_source_url(content: str) -> str:
    m = re.search(r"source:\s*(https?://[^\s}]+)", content)
    if m:
        return m.group(1).rstrip()
    m = re.search(r"source_url:\s*(https?://[^\s}]+)", content)
    if m:
        return m.group(1).rstrip()
    return ""


def content_preview(content: str, max_chars: int = 2000) -> str:
    frontmatter_end = content.find("---", 3)
    if frontmatter_end > 0:
        body = content[frontmatter_end + 3:]
    else:
        body = content
    body = re.sub(r"\[\[.*?\]\]", "", body)
    body = re.sub(r"## Related\n.*", "", body, flags=re.DOTALL)
    body = body.strip()
    return body[:max_chars]


def find_backlog_files(limit: int = 20) -> list:
    """Find existing orphan articles (heritage but not analyzed) from year dirs."""
    files = []
    for year_dir in sorted(SEO_DIR.glob("2*/")):
        if year_dir.name.startswith("_"):
            continue
        for f in sorted(year_dir.glob("*.md")):
            if len(files) >= limit:
                break
            content = f.read_text(encoding="utf-8", errors="ignore")
            if "analyzed: true" in content:
                continue
            files.append(f)
        if len(files) >= limit:
            break
    return files


def main():
    import argparse
    parser = argparse.ArgumentParser(description="SEO Article Analyzer")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no changes")
    parser.add_argument("--force", type=str, help="Force-analyze a specific file")
    parser.add_argument("--backlog", type=int, default=0, help="Process N backlog articles from year dirs")
    args = parser.parse_args()

    state = load_state()
    analyzed_urls = set(state.get("analyzed_urls", []))
    analyzed_count = state.get("analyzed_count", 0)

    files_to_analyze = []
    if args.force:
        fpath = Path(args.force)
        if fpath.exists():
            files_to_analyze.append(fpath)
    elif args.backlog > 0:
        files_to_analyze = find_backlog_files(args.backlog)
        if files_to_analyze:
            print(f"[Analyzer] Processing {len(files_to_analyze)} backlog articles...")
    else:
        for f in sorted(NEW_DIR.glob("*.md"))[:MAX_PER_RUN]:
            content = f.read_text(encoding="utf-8", errors="ignore")
            url = extract_source_url(content)
            if url and url in analyzed_urls:
                continue
            files_to_analyze.append(f)

    if not files_to_analyze:
        print("[Analyzer] No new articles to analyze.")
        return

    print(f"[Analyzer] Analyzing {len(files_to_analyze)} articles...")

    results = []
    for i, f in enumerate(files_to_analyze, 1):
        content = f.read_text(encoding="utf-8", errors="ignore")
        url = extract_source_url(content)
        title = f.stem.replace("_", " ").replace("-", " ").title()
        preview = content_preview(content)
        print(f"  [{i}/{len(files_to_analyze)}] {title[:50]}...")

        if args.dry_run:
            print(f"    DRY-RUN: Would analyze {f.name}")
            results.append({"file": f.name, "status": "dry-run"})
            continue

        analysis = analyze_article(title, preview, url)

        if analysis.get("is_duplicate"):
            print(f"    ⏭️ Duplicate: {analysis.get('duplicate_reason', 'no reason')}")
            f.unlink()
            results.append({"file": f.name, "status": "duplicate-deleted"})
            continue

        if analysis.get("relevance_score", 0) < 2:
            print(f"    ⏭️ Low relevance (score={analysis['relevance_score']})")
            f.unlink()
            results.append({"file": f.name, "status": "low-relevance-deleted"})
            continue

        update_article(f, analysis)
        year_dir = SEO_DIR / YEAR
        year_dir.mkdir(parents=True, exist_ok=True)
        dest = year_dir / f.name
        shutil.move(str(f), str(dest))
        print(f"    ✅ Analyzed → {YEAR}/{f.name}")

        analyzed_urls.add(url)
        analyzed_count += 1
        results.append({"file": f.name, "status": "analyzed", "category": analysis["category"]})

        time.sleep(1)

    state["analyzed_urls"] = sorted(analyzed_urls)
    state["analyzed_count"] = analyzed_count
    state["last_analyzed_at"] = datetime.now().isoformat()
    if not args.dry_run:
        save_state(state)

    print(f"\n[Analyzer] Done: {len(results)} processed")
    for r in results:
        print(f"  {r['status']}: {r['file'][:60]}")


if __name__ == "__main__":
    main()
