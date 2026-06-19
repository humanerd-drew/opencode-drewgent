#!/usr/bin/env python3
"""
SEO Article Harvester
=====================
RSS 피드 모니터링 → 새 기사 크롤링 → Discord 전달

Usage:
    python3 harvester.py                  # 전체 수집
    python3 harvester.py --dry-run         # RSS 확인만
    python3 harvester.py --feed-url URL    # 특정 피드만
"""

import os
import re
import json
import hashlib
import sys
import textwrap
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Optional
import html

# ── 설정 ────────────────────────────────────────────
DREW_HOME = Path(os.environ.get("DREW_HOME", os.path.expanduser("~/.drewgent")))
sys.path.insert(0, str(DREW_HOME))

from agent.obsidian_graph import ensure_backlink, ensure_related_section, wiki_link

SEO_DIR = DREW_HOME / "P2-hippocampus" / "knowledge" / "seo-articles"

# ── Quality guards (2026-06-01: letspl.me junk article 차단) ──
# 본문이 너무 짧거나 title이 trivial하면 article로 저장하지 않음.
# letspl.me 같은 밋업 feed의 "안녕하세요" 같은 placeholder를 건너뛰기 위한 안전망.
MIN_TITLE_LENGTH = 10  # 한글 5자 / 영문 10자
MIN_BODY_LENGTH = 200   # 미만이면 placeholder 또는 crawl 실패로 간주
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_SEO")  # 환경변수에서 설정
DISCORD_CHANNEL_ID = "1504328297419640872"

# ── 주제 필터 (2026-06-05) ──
# SEO 전용 피드의 모든 글은 통과. 나머지는 제목 기반 키워드 필터 적용.
SEO_SPECIFIC_DOMAINS = {
    "ahrefs.com", "searchengineland.com", "semrush.com",
    "yoast.com", "seopress.org", "ascentkorea.com",
    "growthmk.com", "moz.com", "searchenginejournal.com",
    "copyblogger.com", "openschema.co.jp",
}
SEO_KEYWORDS = [
    "seo", "search engine", "google search", "google algorithm", "google update",
    "ranking", "keyword", "backlink", "link building", "serp", "organic traffic",
    "ppc", "google ads", "content marketing", "search marketing",
    "webmaster", "crawl", "index", "sitemap", "core web vital",
    "structured data", "schema markup", "rich snippet", "featured snippet",
    "ai overview", "search generative", "google analytics", "search console",
    "local seo", "ecommerce seo", "technical seo", "on-page", "off-page",
    "domain authority", "page authority", "domain rating",
    "content strategy", " editorial", "publisher", "google news",
    "search traffic", "click-through", "conversion rate",
    "aibo", "google discover", "google labs",
]

def is_seo_relevant(title: str, domain: str) -> bool:
    domain_clean = domain.removeprefix("www.").removeprefix("blog.")
    if domain_clean in SEO_SPECIFIC_DOMAINS:
        return True
    title_lower = title.lower()
    return any(kw in title_lower for kw in SEO_KEYWORDS)

RSS_FEEDS = [
    # ── SEO / 마케팅 (10개) ──
    "https://ahrefs.com/blog/feed",
    "https://searchengineland.com/feed",
    "https://www.semrush.com/blog/feed",
    "https://yoast.com/feed/",
    "https://www.seopress.org/feed",
    "https://www.ascentkorea.com/feed",
    "https://growthmk.com/feed",
    "https://moz.com/blog/feed",
    "https://www.searchenginejournal.com/feed",
    "https://copyblogger.com/feed",
    # ── 테크 / 개발 (11개) ──
    "https://blog.google/technology/ai/rss",
    "https://developers.googleblog.com/feed",
    "https://techcrunch.com/feed",
    "https://www.theverge.com/rss/index.xml",
    "https://www.wired.com/feed/rss",
    "https://www.zdnet.com/rss.xml",
    "https://feeds.arstechnica.com/arstechnica/index",
    "https://css-tricks.com/feed",
    "https://www.smashingmagazine.com/feed",
    "https://aws.amazon.com/blogs/aws/feed",
    "https://github.blog/feed",
    # ── 글로벌 / 커뮤니티 (7개) ──
    "https://developers.googleblog.com/feeds/posts/default",
    "https://blog.chromium.org/feeds/posts/default",
    "https://openschema.co.jp/feed",
    "https://hnrss.org/frontpage",
    "https://dev.to/feed",
    "https://news.ycombinator.com/rss",
    "https://www.techmeme.com/feed.xml",
]

# ── 색인: 이미 수집된 URL 캐시 ───────────────────────
def build_url_cache() -> set:
    """이미 수집된 article URL 집합을 생성 (중복 수집 방지)"""
    cache = set()
    index_file = SEO_DIR / "collected_urls.json"
    if index_file.exists():
        try:
            cache = set(json.loads(index_file.read_text()))
        except Exception:
            pass
    # _new/ 폴더의 파일에서도 URL 추출
    new_dir = SEO_DIR / "_new"
    if new_dir.exists():
        for f in new_dir.glob("*.md"):
            try:
                content = f.read_text()
                # frontmatter에서 source 추출
                m = re.search(r"source:\s*(https?://[^\s]+)", content)
                if m:
                    cache.add(m.group(1).rstrip())
            except Exception:
                pass
    return cache

def save_url_cache(cache: set):
    """URL 캐시를 저장"""
    index_file = SEO_DIR / "collected_urls.json"
    index_file.write_text(json.dumps(sorted(cache), ensure_ascii=False, indent=2))

# ── RSS 파싱 ────────────────────────────────────────
def fetch_rss(url: str, timeout: int = 20) -> Optional[ET.Element]:
    """RSS/Atom 피드를 가져와서 파싱"""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; SEO-Harvester/1.0; +https://drewgent.ai)",
                "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml",
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
        root = ET.fromstring(data)
        return root
    except Exception as e:
        print(f"  ⚠ RSS 실패: {url} — {e}")
        return None

def parse_feed_items(root: ET.Element) -> list:
    """RSS 또는 Atom 피드에서 item 목록 추출"""
    items = []
    # namespace 처리
    ns = {n.split(":")[1]: n.split(":")[0] + ":" for n in root.attrib.values() if ":" in n}
    
    # RSS 2.0
    for item in root.findall("channel/item"):
        title = _text(item, "title")
        link = _text(item, "link")
        pub_date = _text(item, "pubDate")
        guid = _text(item, "guid") or link
        if title and link:
            items.append({"title": html.unescape(title.strip()), "link": link.strip(), "pub_date": pub_date, "guid": guid})
    
    # Atom
    for entry in root.findall("entry"):
        title = _text(entry, "title")
        link_el = entry.find("link")
        link = link_el.get("href") if link_el is not None else _text(entry, "link")
        pub_date = _text(entry, "published") or _text(entry, "updated")
        guid = _text(entry, "id") or link
        if title and link:
            items.append({"title": html.unescape(title.strip()), "link": link.strip(), "pub_date": pub_date, "guid": guid})
    
    return items

def _text(el: ET.Element, tag: str) -> Optional[str]:
    found = el.find(tag)
    if found is not None and found.text:
        return found.text.strip()
    return None

# ── 크롤링 ──────────────────────────────────────────
def crawl_article(url: str) -> Optional[dict]:
    """
    article URL에서 본문을 추출.
    도구 우선순위: Firecrawl MCP > Scrapling > curl + readability
    """
    # 1) Firecrawl MCP 시도
    try:
        result = _crawl_firecrawl(url)
        if result:
            return result
    except Exception:
        pass
    
    # 2) Scrapling 시도
    try:
        result = _crawl_scrapling(url)
        if result:
            return result
    except Exception:
        pass
    
    # 3) curl + readability fallback
    try:
        result = _crawl_curl_readability(url)
        if result:
            return result
    except Exception:
        pass
    
    return None

def _crawl_firecrawl(url: str) -> Optional[dict]:
    """Firecrawl MCP server 사용"""
    # MCP tool call simulation via subprocess
    import subprocess
    result = subprocess.run(
        ["npx", "-y", "@mendable/firecrawl-mcp", "crawl", url],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode == 0 and result.stdout:
        data = json.loads(result.stdout)
        if data.get("content"):
            return {"title": data.get("title", ""), "content": data["content"], "source_url": url}
    return None

def _crawl_scrapling(url: str) -> Optional[dict]:
    """Scrapling + Cloudflare 우회"""
    import subprocess
    script = f"""
import scrapling
import asyncio

async def main():
    page = await scrapling.async_get("{url}")
    # Cloudflare 우회 시도
    target = page.as_etree()
    article = target.cssselect("article")
    if not article:
        article = target.cssselect("main")
    if not article:
        article = target.cssselect("div[class*='content']")
    if article:
        text = " ".join(article[0].itertext())
    else:
        text = " ".join(target.itertext())
    print(text[:3000])
    
asyncio.run(main())
"""
    result = subprocess.run(
        ["python3", "-c", script],
        capture_output=True, text=True, timeout=45
    )
    if result.returncode == 0 and result.stdout.strip():
        return {"title": "", "content": result.stdout.strip()[:3000], "source_url": url}
    return None

def _crawl_curl_readability(url: str) -> Optional[dict]:
    """curl + Python html2text/readability fallback"""
    import subprocess
    try:
        # curl로 HTML 다운로드
        result = subprocess.run(
            [
                "curl", "-sL", "--max-time", "30",
                "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "-H", "Accept: text/html,application/xhtml+xml",
                url
            ],
            capture_output=True, text=True, timeout=35
        )
        if result.returncode != 0 or not result.stdout:
            return None
        
        html_content = result.stdout
        
        # title 추출
        title_m = re.search(r"<title[^>]*>([^<]+)</title>", html_content, re.I)
        title = title_m.group(1).strip() if title_m else ""
        
        # 간단한 readability: article, main, content 블록 추출
        content_m = re.search(
            r"<article[^>]*>(.*?)</article>",
            html_content, re.I | re.S
        )
        if not content_m:
            content_m = re.search(
                r'<main[^>]*>(.*?)</main>',
                html_content, re.I | re.S
            )
        if not content_m:
            content_m = re.search(
                r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
                html_content, re.I | re.S
            )
        
        if content_m:
            text = re.sub(r"<[^>]+>", " ", content_m.group(1))
            text = re.sub(r"\s+", " ", text).strip()
        else:
            text = re.sub(r"<[^>]+>", " ", html_content)
            text = re.sub(r"\s+", " ", text).strip()
        
        # HTML 엔티티 디코딩
        text = html.unescape(text)
        
        return {"title": title, "content": text[:3000], "source_url": url}
    except Exception as e:
        print(f"  ⚠ curl 실패: {e}")
        return None

# ── 저장 ─────────────────────────────────────────────
def slugify(title: str) -> str:
    """제목을 URL slug로 변환"""
    s = title.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[_\s]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s[:80]

def ensure_seo_index() -> Path:
    """Create the SEO article graph anchor when missing."""
    index_file = SEO_DIR / "index-by-topic.md"
    if not index_file.exists():
        SEO_DIR.mkdir(parents=True, exist_ok=True)
        index_file.write_text(
            textwrap.dedent(
                f"""\
                ---
                title: SEO Articles Index By Topic
                tags: [seo, articles, P2, hippocampus]
                links:
                  - "{wiki_link("P2-hippocampus/memories/index")}"
                  - "{wiki_link("skills/seo-article-harvester/SKILL")}"
                ---

                # SEO Articles Index By Topic

                Cron-collected SEO and AI search articles.
                """
            ),
            encoding="utf-8",
        )
    return index_file

def connect_article(filepath: Path) -> None:
    """Ensure a collected SEO article has parent links and index backlink."""
    index_file = ensure_seo_index()
    content = filepath.read_text(encoding="utf-8", errors="ignore")
    updated = ensure_related_section(
        content,
        [
            wiki_link("P2-hippocampus/knowledge/seo-articles/index-by-topic"),
            wiki_link("skills/seo-article-harvester/SKILL"),
        ],
    )
    if updated != content:
        filepath.write_text(updated, encoding="utf-8")
    index_content = index_file.read_text(encoding="utf-8", errors="ignore")
    index_updated = ensure_related_section(index_content, [wiki_link(filepath, DREW_HOME)])
    if index_updated != index_content:
        index_file.write_text(index_updated, encoding="utf-8")

def save_article(article: dict) -> Path:
    """article를 markdown으로 저장"""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%Y%m%d%H%M")
    
    slug = slugify(article["title"])
    filename = f"{slug}_{time_str}.md"
    
    # frontmatter
    domain = urllib.parse.urlparse(article["source_url"]).netloc
    
    lines = [
        "---",
        f"title: {article['title']}",
        f"source: {article['source_url']}",
        f"source_domain: {domain}",
        f"collected_date: {now.isoformat()}",
        "heritage: false",
        f"tags: [seo, {domain}]",
        "links:",
        f'  - "{wiki_link("P2-hippocampus/knowledge/seo-articles/index-by-topic")}"',
        f'  - "{wiki_link("skills/seo-article-harvester/SKILL")}"',
        "---",
        "",
        f"# {article['title']}",
        "",
        article.get("content", "")[:2000],
    ]
    
    new_dir = SEO_DIR / "_new"
    new_dir.mkdir(parents=True, exist_ok=True)
    
    filepath = new_dir / filename
    filepath.write_text("\n".join(lines), encoding="utf-8")
    connect_article(filepath)
    return filepath

# ── Report JSON (for cron agent delivery) ─────────────────
def write_report_json(new_items: list, saved_count: int, total_rss: int) -> None:
    """Write a machine-readable report for the cron agent to read and deliver."""
    report = {
        "generated_at": datetime.now().isoformat(),
        "harvester_version": "1.1",
        "total_rss_items": total_rss,
        "total": len(new_items),
        "new_items_found": len(new_items),
        "saved_articles": saved_count,
        "articles": [
            {
                "title": item.get("title", "")[:200],
                "url": item.get("link", ""),
                "source": urllib.parse.urlparse(item.get("link", "")).netloc,
            }
            for item in new_items
        ],
    }
    report_file = SEO_DIR / "report.json"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"📊 report.json written: {len(new_items)} articles")


# ── Discord 전달 ─────────────────────────────────────
def send_discord(new_articles: list):
    """Discord 채널에 새 기사 요약 전송"""
    if not new_articles:
        print("📭 새 기사 없음 — Skip")
        return

    # send_discord 호출 시점에 환경변수를 직접 읽음 (source timing 문제 회피)
    webhook_url = os.environ.get("DISCORD_WEBHOOK_SEO")
    if not webhook_url:
        print("⚠ DISCORD_WEBHOOK_SEO 환경변수 없음 — Discord 전달 스킵")
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Embed 형식
    embeds = []
    for art in new_articles[:10]:  # 최대 10개 (Discord embed limit, 400 방지)
        domain = urllib.parse.urlparse(art["link"]).netloc
        summary = (art.get("content", "") or art.get("title", ""))[:150].strip()
        embeds.append({
            "title": art["title"][:200],
            "url": art["link"],
            "description": f"{summary}... — *{domain}*",
            "color": 3447003,  # 파란색
        })
    
    payload = {
        "content": f"📥 **SEO 신문 — {now}**\n{len(new_articles)}건의 새 기사被发现",
        "embeds": embeds,
    }
    
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (compatible; Drewgent-Harvester/1.0)",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"✅ Discord 전달 완료: {resp.status}")
    except Exception as e:
        print(f"⚠ Discord 전달 실패: {e}")

# ── 메인 ─────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="SEO Article Harvester")
    parser.add_argument("--dry-run", action="store_true", help="RSS 확인만 (크롤링 안 함)")
    parser.add_argument("--feed-url", help="특정 피드만 처리")
    parser.add_argument("--limit", type=int, default=0, help="피드 처리 수 제한 (0=전체)")
    args = parser.parse_args()
    
    print(f"🔍 SEO Article Harvester — {datetime.now().isoformat()}")
    print(f"   SEO dir: {SEO_DIR}")
    print(f"   Feeds: {len(RSS_FEEDS)}개")
    print()
    
    # URL 캐시 로드
    url_cache = build_url_cache()
    print(f"   기존 수집 URL: {len(url_cache)}개")
    print()
    
    feeds_to_process = [args.feed_url] if args.feed_url else RSS_FEEDS
    if args.limit > 0:
        feeds_to_process = feeds_to_process[:args.limit]
    
    all_new_items = []
    total_rss_items = 0
    skipped_count = 0
    
    for i, feed_url in enumerate(feeds_to_process, 1):
        print(f"[{i}/{len(feeds_to_process)}] 📡 {feed_url}")
        
        root = fetch_rss(feed_url)
        if root is None:
            continue
        
        items = parse_feed_items(root)
        total_rss_items += len(items)
        print(f"   └ {len(items)}개 item — 필터링 중...")
        
        for item in items:
            url = item["link"] or item["guid"]
            if url and url not in url_cache:
                # 주제 필터: SEO 관련 글만 수집
                title = item.get("title", "")
                domain = urllib.parse.urlparse(url).netloc
                if not is_seo_relevant(title, domain):
                    skipped_count += 1
                    continue
                all_new_items.append(item)
                url_cache.add(url)  # 중복 방지
        
        total_new = len(all_new_items)
        print(f"   └ 새 item: {total_new}개 (누적)")
    
    print()
    print(f"📊 RSS item 총합: {total_rss_items}개")
    print(f"📊 새 item (미수집): {len(all_new_items)}개")
    if skipped_count:
        print(f"📊 주제 필터 제외: {skipped_count}개")
    print()
    
    if args.dry_run:
        print("🟡 DRY-RUN — 크롤링 및 저장 건너뜀")
        for item in all_new_items[:10]:
            print(f"  • {item['title'][:80]} — {item['link']}")
        if len(all_new_items) > 10:
            print(f"  ... (+{len(all_new_items) - 10}개 더)")
        return
    
    if not all_new_items:
        print("✅ 새 기사 없음 — 종료")
        return
    
    # 크롤링
    print(f"🕷 크롤링 시작 — {len(all_new_items)}개 article...")
    saved_files = []
    
    for i, item in enumerate(all_new_items, 1):
        url = item["link"] or item["guid"]
        title = item.get("title", "").strip()
        
        # 1) Title guard: 너무 짧은 title은 junk (letspl.me의 "안녕하세요" 같은 것 차단)
        if len(title) < MIN_TITLE_LENGTH:
            skipped_count += 1
            print(f"   ⏭️ SKIP (title<{MIN_TITLE_LENGTH}): {title!r} — {url}")
            continue
        
        print(f"[{i}/{len(all_new_items)}] 크롤링: {title[:60]}...")
        
        # 2) Body guard: crawl 후 본문이 너무 짧으면 junk
        article = crawl_article(url)
        if not article or not article.get("content"):
            skipped_count += 1
            print(f"   ⏭️ SKIP (no content): {url}")
            continue
        
        content = article.get("content", "").strip()
        if len(content) < MIN_BODY_LENGTH:
            skipped_count += 1
            print(f"   ⏭️ SKIP (body<{MIN_BODY_LENGTH} chars, {len(content)}자): {title!r}")
            continue
        
        article["title"] = title
        filepath = save_article(article)
        saved_files.append(filepath)
        print(f"   ✅ 저장: {filepath.name}")
        
        # 속도 제한: 1초 대기
        import time; time.sleep(1)
    
    # URL 캐시 저장
    save_url_cache(url_cache)
    
    # Discord 전달
    print()
    print(f"📤 Discord 전달 ({len(all_new_items)}건)...")
    send_discord(all_new_items)

    # Write report.json for cron agent delivery
    write_report_json(all_new_items, len(saved_files), total_rss_items)

    print()
    print(f"✅ 완료 — {len(saved_files)}개 저장됨, {skipped_count}개 skip (junk), {len(all_new_items)}개 Discord 전달됨")

if __name__ == "__main__":
    main()
