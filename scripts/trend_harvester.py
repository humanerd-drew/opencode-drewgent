#!/usr/bin/env python3
"""
Trend Harvester — P4-cortex AI Trend Collection & 5-Axis Filtering

Collects AI tools/techniques from GitHub trending and GeekNews RSS,
scores through Drewgent's 5-axis philosophy filter.
Only trends that pass the filter get to analyzed/keep.

Usage:
    python3 trend_harvester.py --dry-run    # collect & score, no file writes
    python3 trend_harvester.py              # full run
    python3 trend_harvester.py --source geeknews  # GeekNews only
    python3 trend_harvester.py --source github   # GitHub trending only
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

# ---- config ----
_DREWGENT_HOME = Path.home() / ".drewgent"
_P4_TREND = _DREWGENT_HOME / "P4-cortex" / "growth" / "trend-harvester"
_STATE_FILE = _P4_TREND / ".harvester_state.json"
_PID_FILE = _P4_TREND / ".harvester.lock"
_DRY_RUN = False
_SOURCE = "all"  # "all", "github", "geeknews"

# GitHub trending languages to scan
LANGUAGES = ["python", "javascript", "typescript", "go", "rust", "java", "shell"]

# GitHub API rate limit handling
GH_RATE_LIMIT_DELAY = 1.0  # seconds between requests (avoid rate limit)

# GeekNews
GEONEWS_RSS_URL = "https://news.hada.io/rss/news"
GEONEWS_RATELIMIT_DELAY = 2.0

# ---- helpers ----

def log(msg: str) -> None:
    print(f"[harvester] {msg}", flush=True)


def load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text())
        except Exception:
            pass
    return {"synced_hashes": [], "last_run": None, "runs": 0}


def save_state(state: dict) -> None:
    if _DRY_RUN:
        return
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def content_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:12]


def acquire_lock() -> bool:
    """PID lock to prevent concurrent runs."""
    if _PID_FILE.exists():
        try:
            pid = int(_PID_FILE.read_text().strip())
            # Check if process still alive
            os.kill(pid, 0)
            log(f"Already running (PID {pid}), exiting.")
            return False
        except (ValueError, ProcessLookupError, PermissionError):
            log(f"Stale lock file (PID unknown or no permission), overwriting.")
    if not _DRY_RUN:
        _PID_FILE.write_text(str(os.getpid()))
    return True


def release_lock() -> None:
    if not _DRY_RUN and _PID_FILE.exists():
        _PID_FILE.unlink()


def _fetch_url(url: str, timeout: int = 15) -> str | None:
    """Generic URL fetch with error handling."""
    import urllib.request
    headers = {"User-Agent": "Mozilla/5.0 (compatible; Drewgent-Harvester/1.0)"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        log(f"  Failed to fetch {url}: {e}")
        return None


# ---- GitHub trending ----

def fetch_github_trending(lang: str) -> list[dict]:
    """Fetch GitHub trending repos for a language via HTML scraping."""
    url = f"https://github.com/trending/{lang}?since=daily"
    html = _fetch_url(url)
    if not html:
        return []

    repos = []
    articles = re.findall(r'<article class="Box-row">(.*?)</article>', html, re.DOTALL)

    for article in articles:
        # Find repo path - look for /owner/repo pattern, skip login links
        hrefs = re.findall(r'href="(/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)"', article)
        repo_path = None
        for href in hrefs:
            if not href.startswith('/login') and href.count('/') >= 1 and len(href) > 1:
                repo_path = href[1:]  # remove leading /
                break
        if not repo_path:
            continue

        # Repo name is the second part after /
        repo_name = repo_path.split('/')[-1]

        # Description
        desc_match = re.search(r'<p[^>]*>([^<]+)</p>', article)
        description = desc_match.group(1).strip() if desc_match else ""
        description = re.sub(r'\s+', ' ', description)
        description = description.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'")

        # Stars and today's stars
        article_text = re.sub(r'<[^>]+>', ' ', article)
        article_text = re.sub(r'\s+', ' ', article_text)

        stars_match = re.search(r'([\d,]+)\s{1,4}stars(?! today)', article_text)
        stars = int(stars_match.group(1).replace(',', '')) if stars_match else 0

        today_match = re.search(r'([\d,]+)\s+stars today', article_text)
        today_stars = int(today_match.group(1).replace(',', '')) if today_match else 0

        # Programming language
        lang_match = re.search(r'<span itemprop="programmingLanguage">([^<]+)</span>', article)
        language = lang_match.group(1) if lang_match else lang

        if not description:
            description = f"{repo_name} — {language} project on GitHub"

        repos.append({
            "name": repo_name,
            "full_name": repo_path,
            "description": description[:500],
            "language": language,
            "stars": stars,
            "today_stars": today_stars,
            "url": f"https://github.com/{repo_path}",
            "source": "github",
            "collected_at": datetime.now(timezone.utc).isoformat(),
        })

        time.sleep(GH_RATE_LIMIT_DELAY)

    return repos


# ---- GeekNews RSS ----

def fetch_geeknews_rss() -> list[dict]:
    """Fetch latest entries from GeekNews RSS (Atom feed)."""
    import xml.etree.ElementTree as ET

    xml_str = _fetch_url(GEONEWS_RSS_URL, timeout=20)
    if not xml_str:
        return []

    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError as e:
        log(f"  Failed to parse GeekNews RSS: {e}")
        return []

    # Atom namespace — use direct namespace URI string (not dict) for findall
    NS = "http://www.w3.org/2005/Atom"

    entries = []
    for entry in root.findall(f"{{{NS}}}entry"):
        title_el = entry.find(f"{{{NS}}}title")
        link_el = None
        for link in entry.findall(f"{{{NS}}}link"):
            if link.get("rel") == "alternate":
                link_el = link
                break
        id_el = entry.find(f"{{{NS}}}id")
        published_el = entry.find(f"{{{NS}}}published")
        updated_el = entry.find(f"{{{NS}}}updated")

        # Extract topic_id from link URL: news.hada.io/topic?id=XXX
        original_url = ""
        topic_id = ""
        link_url = ""
        if link_el is not None:
            link_url = link_el.get("href", "")
            match = re.search(r"topic\?id=(\d+)", link_url)
            if match:
                topic_id = match.group(1)

        # Extract content from atom:content (summary is None in this feed)
        geeknews_content = ""
        content_el = entry.find(f"{{{NS}}}content")
        if content_el is not None and content_el.text:
            geeknews_content = content_el.text

        title = title_el.text if title_el is not None and title_el.text else ""
        published = (published_el.text or updated_el.text or "") if published_el is not None or updated_el is not None else ""

        if not title or not topic_id:
            continue

        entries.append({
            "name": title.strip(),
            "topic_id": topic_id,
            "geeknews_url": link_url,
            "original_url": "",  # filled by fetch_topic_page()
            "description": geeknews_content[:500] if geeknews_content else title,
            "geeknews_content": geeknews_content,
            "source": "geeknews",
            "published": published,
            "collected_at": datetime.now(timezone.utc).isoformat(),
        })

        time.sleep(GEONEWS_RATELIMIT_DELAY)

    log(f"  Parsed {len(entries)} GeekNews entries")
    return entries


# ---- GeekNews topic page ----

def fetch_topic_page(entry: dict) -> dict:
    """Fetch a GeekNews topic page to extract original_url and curated content."""
    topic_url = f"https://news.hada.io/topic?id={entry['topic_id']}"
    html = _fetch_url(topic_url, timeout=15)
    if not html:
        entry["original_url"] = ""
        entry["geeknews_content"] = entry.get("geeknews_content", "")
        return entry

    # Extract original URL from <a class="bold ud"> inside .topictitle
    original_url = ""
    url_match = re.search(r'<a\s+href="(https?://[^"]+)"\s+class="bold\s+ud">', html)
    if url_match:
        original_url = url_match.group(1)
    else:
        # Fallback: try to find any external URL in topic title area
        url_match2 = re.search(r'class="topicurl">\s*\([^)]+\)</span>', html)
        if url_match2:
            pass  # just shows the domain, not the full URL

    # Extract curated content from #topic_contents
    content_match = re.search(r'<div\s+id="topic_contents">(.*?)</div>\s*</div>', html, re.DOTALL)
    if content_match:
        raw_html = content_match.group(1)
        # Strip HTML tags but preserve structure
        text = re.sub(r'<li>', '\n• ', raw_html)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\n\s*\n', '\n', text)
        text = text.strip()
        if text:
            entry["geeknews_content"] = text

    entry["original_url"] = original_url
    return entry


# ---- Original URL content fetch (with agent-style judgment) ----

def fetch_original_content(entry: dict) -> dict:
    """
    Attempt to fetch content from the original URL.
    Applies judgment logic for paywall/login detection.
    Falls back to geeknews_content on failure.
    """
    if not entry.get("original_url"):
        entry["content_status"] = "no_original_url"
        entry["content"] = entry.get("geeknews_content", "")
        return entry

    html = _fetch_url(entry["original_url"], timeout=15)
    if not html:
        entry["content_status"] = "fetch_failed"
        entry["content"] = entry.get("geeknews_content", "")
        return entry

    # ---- Content extraction heuristics ----
    extracted = _extract_main_content(html, entry["original_url"])

    # ---- Judgment: paywall / login / thin content detection ----
    status = "extracted"
    text = extracted

    # Check: very short content (likely paywall or restricted)
    if len(text) < 300:
        status = "likely_paywall"
        text = entry.get("geeknews_content", "")

    # Check: login/paywall indicators
    paywall_signals = [
        "로그인", "로그인 필요", "login required", "sign in", "subscription",
        "premium only", "paid content", "付费", "订阅", "paywall",
        "access denied", "403 forbidden", "unauthorized",
    ]
    for signal in paywall_signals:
        if signal.lower() in text.lower()[:1000]:
            status = "likely_paywall"
            text = entry.get("geeknews_content", "")
            break

    # Check: meta robots noindex
    if re.search(r'<meta[^>]+robots[^>]+noindex', html, re.I):
        status = "likely_paywall"
        text = entry.get("geeknews_content", "")

    # Check: redirect or thin content
    if re.search(r'<meta[^>]+refresh[^>]+url=', html, re.I):
        status = "likely_redirect"
        text = entry.get("geeknews_content", "")

    entry["content_status"] = status
    entry["content"] = text if text else entry.get("geeknews_content", "")
    return entry


def _extract_main_content(html: str, url: str) -> str:
    """Extract main text content from HTML page."""
    parsed = urlparse(url)
    domain = parsed.netloc

    # Remove noise
    for noise_pat in [
        r'<script[^>]*>.*?</script>',
        r'<style[^>]*>.*?</style>',
        r'<nav[^>]*>.*?</nav>',
        r'<footer[^>]*>.*?</footer>',
        r'<header[^>]*>.*?</header>',
        r'<aside[^>]*>.*?</aside>',
        r'<!--.*?-->',
    ]:
        html = re.sub(noise_pat, '', html, flags=re.DOTALL | re.I)

    text = html

    # Try article/main tags first
    for tag in ["article", "main", 'div class="content"', 'div id="content"']:
        m = re.search(rf'<{tag}[^>]*>(.*?)</{tag}>', html, re.DOTALL | re.I)
        if m and len(m.group(1)) > 200:
            text = m.group(1)
            break

    # Extract paragraphs
    paras = re.findall(r'<p[^>]*>(.*?)</p>', text, re.DOTALL)
    if paras:
        text = ' '.join(re.sub(r'<[^>]+>', '', p).strip() for p in paras if len(p) > 20)

    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    return text[:3000]  # cap at 3000 chars


# ---- 5-axis scoring ----

# ---- Knowledge-base scoring axes ----
# Purpose: "Is this worth Drewgent recording in its wiki knowledge base?"
# Drewgent reads analyzed/keep and records to wiki to stay current.
#
# Source-specific behavior:
#   GitHub  — scored on stars + keywords (tool-technique quality signal)
#   GeekNews — scored on content depth + topic relevance (knowledge worth reading)

KB_AXES = {
    "relevance": {
        # Does this relate to AI / developer tooling / software?
        # HARD BLOCK: irrelevant content should never reach review/keep
        "weight": 1.5,
        "hard_block": True,
        "keywords_boost": [
            # AI / LLM / agent space
            "ai", "llm", "model", "agent", "claude", "openai", "anthropic",
            "gemini", "mistral", "grok", "llama", "gpt", "rag",
            # Developer tooling
            "cli", "terminal", "tool", "api", "sdk", "framework", "library",
            "github", "open-source", "oss", "repo", "commit", "pull request",
            "coding", "programming", "developer", "devtools", "ide",
            # AI coding agents (directly relevant to Drewgent)
            "claude code", "/goal", "/memory", "/skill",
            "copilot", "cursor", "windsurf", "continue",
            "code agent", "coding agent", "auto coding",
            # AI infrastructure
            "vector", "embedding", "fine-tuning", "prompt", "inference",
            "deployment", "edge ai", "local model", "supply chain",
        ],
        "keywords_penalize": [
            # Non-software / niche hobby
            "게임", "게임 리뷰", "핀볼", "게임플레이",
            "카메라 수집", "포토", "사진촬영", "여-tube",
            "음식", "맛집", "요리", "맛집추천",
            "부동산", "주식", "투자",
            "정치", "선거",
        ],
        "keywords_reject": [
            # Completely off-topic
            "어머니의 날", "어머니께 전화", " Mothers Day ",
            "게임 리뷰", "영화 리뷰", "음악 추천",
            "부동산 계약", "주식 추천",
        ],
    },
    "direct_impact": {
        # Does this affect Drewgent's own capabilities or development?
        "weight": 1.5,
        "keywords_boost": [
            "claude code", "/goal", "/memory", "/skill",
            "hermes-agent", "drewgent",
            "ai agent", "coding agent", "terminal agent",
            "agent protocol", "mcp", "model context protocol",
            "claude api", "anthropic api",
        ],
        "keywords_penalize": [
            # Hardware / biology / physics / non-software
            "hardware", "chip", "cpu", "gpu", "内存", "benchmarks",
            "biology", "protein", "crispr",
        ],
        "keywords_reject": [],
    },
    "actionability": {
        # Does this contain a specific project, technique, or insight?
        # vs. pure opinion/discussion
        "weight": 1.0,
        "keywords_boost": [
            # Specific deliverables
            "open-source", "github.com", "repo", "npm", "pypi", "crate",
            "library", "framework", "tool", "plugin", "extension",
            "script", "cli", "tui", "gui",
            # Show HN / Project posts
            "show hn", "show gn", "launch", "release", "announcement",
            # Technical depth
            "how to", "tutorial", "guide", "implementation", "architecture",
            "benchmark", "comparison", "vs.",
        ],
        "keywords_penalize": [
            # Discussion / opinion / meta
            "ask hn", "ask gn", "discussion", "opinion", "thoughts?",
            "what do you think", "who else", "anyone else",
            "reminder", "meta post", "off-topic",
            # Generic/low-specificity posts
            "오늘은", " gratuler", "축하", "선물",  # reminder/celebration type
            "dc-in-text", "디시", "아카이브",  # community-specific not globally relevant
            "bank email", "이메일 파싱",  # too niche a tool
            "pinball", "space cadet", "linpack",  # retro/hardware curiosity
        ],
        "keywords_reject": [],
    },
    "novelty": {
        # Is this depthful content vs. a brief link/post?
        "weight": 1.0,
        "keywords_boost": [
            "analysis", "deep dive", "how we built", "post-mortem",
            "retrospective", "lessons learned", "architecture",
            "technical deep", "research paper", "paper",
        ],
        "keywords_penalize": [
            # Generic short-form / niche-specific projects
            "show gn:", "ask gn:", "remind hn:",
            # Niche: single platform / single community tool
            "unity", "unreal", "blender",  # 3D/game engine specific
            "dc-inside", "디시", "레딧", "인스타그램", "트위터",
            "bank email", "이메일 파싱", "은행",
            "카메라", "사진", "gimbal", "드론",
            "macos only", "ios only", "android only",
        ],
        "keywords_reject": [],
    },
    "credibility": {
        # Source quality + content specificity
        "weight": 0.5,
        "keywords_boost": [
            # GitHub stars are a credibility proxy
            # Actual specific topic names (not generic "AI")
            "nvidia", "google", "anthropic", "microsoft", "meta",
            "tanstack", "vercel", "railway", "supabase",
            "bun", "deno", "rust", "zig", "go",
        ],
        "keywords_penalize": [
            # Generic/reminder/low-effort
            "reminder", "meta post", "who else",
        ],
        "keywords_reject": [],
    },
}

KB_AXIS_ORDER = ["relevance", "direct_impact", "actionability", "novelty", "credibility"]


def score_trend(item: dict) -> dict:
    """
    Score a trend item for knowledge-base worthiness.
    Purpose: Is this worth Drewgent recording in its wiki knowledge base?
    """
    source = item.get("source", "unknown")
    is_geeknews = source == "geeknews"
    is_github = source == "github"

    # Full text for keyword matching
    score_text = " ".join([
        item.get("name", ""),
        item.get("description", ""),
        item.get("content", "")[:500],
        item.get("geeknews_content", "")[:500],
        item.get("language", ""),
    ]).lower()

    scores = {}
    details = {}

    has_stars = item.get("stars", 0) > 0

    for axis_name in KB_AXIS_ORDER:
        axis = KB_AXES[axis_name]

        # Keyword matching
        boost_kw = axis.get("keywords_boost", [])
        penalize_kw = axis.get("keywords_penalize", [])
        reject_kw = axis.get("keywords_reject", [])

        boost_count = sum(1 for kw in boost_kw if kw in score_text)
        penalize_count = sum(1 for kw in penalize_kw if kw in score_text)
        reject_count = sum(1 for kw in reject_kw if kw in score_text)

        keyword_score = (boost_count * 0.15) - (penalize_count * 0.1)
        keyword_score = max(0.0, min(1.0, 0.5 + keyword_score))  # 0.5 base

        # Source-specific base adjustments
        base_adjustment = 0.0
        if axis_name == "credibility" and is_github and has_stars:
            stars = item.get("stars", 0)
            base_adjustment = min(stars / 5000, 1.0) * 0.3  # GitHub stars → credibility
        elif axis_name == "novelty" and is_geeknews:
            # Content length → novelty signal for GeekNews
            gc_len = len(item.get("geeknews_content", ""))
            content_len = len(item.get("content", ""))
            max_len = max(gc_len, content_len)
            base_adjustment = min(max_len / 1000, 1.0) * 0.25
            # Penalize generic prefixes
            name = item.get("name", "").lower()
            if name.startswith("show gn:") or name.startswith("ask gn:"):
                base_adjustment -= 0.15
            if name.startswith("remind hn:") or "어머니의 날" in name:
                base_adjustment -= 0.2

        axis_score = max(0.0, min(1.0, keyword_score + base_adjustment))

        # Hard block: reject keywords found
        hard_blocked = reject_count > 0

        scores[axis_name] = round(axis_score, 3)
        details[axis_name] = {
            "keyword_score": round(keyword_score, 3),
            "base_adjustment": round(base_adjustment, 3),
            "boost_kw": boost_count,
            "penalize_kw": penalize_count,
            "reject_kw": reject_count,
            "hard_blocked": hard_blocked,
        }

    # Calculate weighted total score (0-10 scale)
    weighted_sum = sum(scores[axis] * KB_AXES[axis]["weight"] for axis in KB_AXIS_ORDER)
    total_weight = sum(KB_AXES[axis]["weight"] for axis in KB_AXIS_ORDER)
    total_score = round(weighted_sum / total_weight * 10, 2)

    # Decision logic
    relevance = scores["relevance"]
    direct_impact = scores["direct_impact"]

    # Hard blocks
    if relevance < 0.45:
        decision = "graveyard"
        reason = f"hard_block: relevance={relevance} < 0.45"
    elif total_score < 4.5:
        decision = "graveyard"
        reason = f"graveyard: score={total_score} < 4.5"
    elif total_score >= 6.5 and (direct_impact >= 0.6 or relevance >= 0.7):
        decision = "keep"
        reason = f"keep: score={total_score}, direct_impact={direct_impact}, relevance={relevance}"
    else:
        decision = "review"
        reason = f"review: 4.5 <= score={total_score} < 6.5"

    return {
        "item": item,
        "scores": scores,
        "details": details,
        "total_score": total_score,
        "decision": decision,
        "reason": reason,
        "scored_at": datetime.now(timezone.utc).isoformat(),
    }


# ---- output ----

def write_trend(result: dict, base_dir: Path) -> None:
    """Write a scored trend to the appropriate analyzed/ subdirectory."""
    decision = result["decision"]
    subdir = base_dir / "analyzed" / decision
    subdir.mkdir(parents=True, exist_ok=True)

    # Use hashed name for uniqueness
    h = content_hash(result["item"].get("url", result["item"].get("geeknews_url", result["item"].get("name", ""))))
    filename = f"{h}.json"
    filepath = subdir / filename

    if not _DRY_RUN:
        filepath.write_text(json.dumps(result, indent=2, ensure_ascii=False))
        log(f"  [{decision.upper()}] {result['item']['name']} (score={result['total_score']})")
    else:
        log(f"  [DRY-RUN {decision.upper()}] {result['item']['name']} (score={result['total_score']})")


def write_report_json(keep_count: int, review_count: int, graveyard_count: int,
                      top_keeps: list, base_dir: Path) -> None:
    """Write a machine-readable summary report for the cron agent to read."""
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "harvester_version": "1.1",
        "total_collected": keep_count + review_count + graveyard_count,
        "keep": keep_count,
        "review": review_count,
        "graveyard": graveyard_count,
        "top_keeps": top_keeps,
    }
    report_file = base_dir / "report.json"
    if not _DRY_RUN:
        report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        log(f"Report written: {report_file.name}")
    else:
        log(f"[DRY-RUN] Report would be written: {report_file.name}")


def write_collected(item: dict, base_dir: Path) -> None:
    """Write raw collected item to collected/ directory."""
    collected_dir = base_dir / "collected"
    collected_dir.mkdir(parents=True, exist_ok=True)

    h = content_hash(item.get("url", item.get("geeknews_url", item.get("name", ""))))
    filepath = collected_dir / f"{h}.json"

    if not _DRY_RUN:
        filepath.write_text(json.dumps(item, indent=2, ensure_ascii=False))


# ---- main ----

def main() -> int:
    global _DRY_RUN, _SOURCE

    parser = argparse.ArgumentParser(description="Drewgent Trend Harvester")
    parser.add_argument("--dry-run", action="store_true", help="Collect and score, don't write files")
    parser.add_argument("--source", choices=["all", "github", "geeknews"], default="all",
                        help="Source to collect from (default: all)")
    args = parser.parse_args()
    _DRY_RUN = args.dry_run
    _SOURCE = args.source

    log(f"Trend Harvester starting (dry_run={_DRY_RUN}, source={_SOURCE})")

    if not acquire_lock():
        return 1

    try:
        state = load_state()
        all_items = []

        # ---- GitHub Trending ----
        if _SOURCE in ("all", "github"):
            for lang in LANGUAGES:
                log(f"Fetching GitHub trending/{lang}...")
                repos = fetch_github_trending(lang)
                log(f"  Found {len(repos)} repos")
                all_items.extend(repos)

        # ---- GeekNews RSS ----
        if _SOURCE in ("all", "geeknews"):
            log(f"Fetching GeekNews RSS...")
            entries = fetch_geeknews_rss()
            log(f"  Found {len(entries)} entries from RSS")

            # For each entry, fetch topic page to get original_url + geeknews_content
            for entry in entries:
                entry_filled = fetch_topic_page(entry)
                # Apply original content fetch with judgment
                entry_filled = fetch_original_content(entry_filled)
                all_items.append(entry_filled)

        log(f"Total collected: {len(all_items)} items")

        if not all_items:
            log("No items collected, exiting.")
            return 0

        # Score each item
        keep_count = review_count = graveyard_count = 0

        for item in all_items:
            result = score_trend(item)

            # Write to collected/
            write_collected(item, _P4_TREND)

            # Write to analyzed/ subdir based on decision
            write_trend(result, _P4_TREND)

            if result["decision"] == "keep":
                keep_count += 1
            elif result["decision"] == "review":
                review_count += 1
            else:
                graveyard_count += 1

        log(f"Results: keep={keep_count}, review={review_count}, graveyard={graveyard_count}")

        # Build top_keeps for the report JSON
        keep_dir = _P4_TREND / "analyzed" / "keep"
        top_keeps = []
        if keep_dir.exists() and not _DRY_RUN:
            keep_files = sorted(keep_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)[:10]
            for f in keep_files:
                try:
                    d = json.loads(f.read_text())
                    item = d.get("item", {})
                    top_keeps.append({
                        "name": item.get("name", "")[:80],
                        "source": item.get("source", "unknown"),
                        "url": item.get("url") or item.get("geeknews_url", ""),
                        "score": d.get("total_score", 0),
                    })
                except Exception:
                    continue

        if not _DRY_RUN:
            write_report_json(keep_count, review_count, graveyard_count, top_keeps, _P4_TREND)

        # Update state
        if not _DRY_RUN:
            state["last_run"] = datetime.now(timezone.utc).isoformat()
            state["runs"] += 1
            save_state(state)
            log(f"State saved (runs={state['runs']})")

        return 0

    finally:
        release_lock()


if __name__ == "__main__":
    sys.exit(main())
