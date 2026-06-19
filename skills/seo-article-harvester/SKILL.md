---
name: seo-article-harvester
title: SEO Article Harvester — Full Pipeline
description: RSS 피드 모니터링 → SEO 기사 수집·분석·트렌드 리포트
type: skill
space: outcome
tags: [outcome, seo, rss, crawling, pipeline]
created: 2026-05-20
updated: 2026-06-14
links:
  - "[[P3-sensors/skills/SKILL-INDEX]]"
  - "[[skills/seo-article-harvester/references/crawling-tools]]"
  - "[[P2-hippocampus/knowledge/seo-articles]]"
  - "[[P4-cortex/growth/seo/index]]"
  - "[[P0-brainstem/brain/rules]]"
---

# SEO Article Harvester — Full Pipeline

## Architecture Overview

```
[수집]   cron_seo_harvester.sh     (no_agent, 6h)
  │
  ▼
[분석]   kanban worker             (LLM, daily 12:00)
  │       → 기사 요약 + 주제 태깅 + 중요도 점수
  │       → Google 업데이트/알고리즘 변경 발견 시 kanban task
  ▼
[트렌드] kanban worker             (LLM, weekly Mon 14:00)
  │       → 주간 SEO 트렌드 리포트
  │       → P4-cortex/growth/seo/weekly/ + Discord
  ▼
[정리]   스크립트                  (no_agent, monthly)
          → 3개월 지난 기사 _archive/ 이동
```

## Pipeline Stages

### 1. 수집 (Collection)
- **Cron**: `SEO Article Harvester` (no_agent, `0 */6 * * *`)
- **Script**: `cron_seo_harvester.sh` → `cron_seo_harvester.py` → `harvester.py` + `label_heritage.py`
- **Output**: `seo-articles/YYYY/article-slug.md` (YAML frontmatter 포함)
- **Sources**: 28 SEO/marketing RSS feeds (see below)
- **LLM 필요?**: ❌ No

### 2. 분석 (Analysis)
- **Trigger cron**: `seo-analyze-trigger` (LLM, daily 12:00 KST, fast model)
- **Worker**: Kanban worker
- **Input**: `seo-articles/YYYY/*.md` (아직 분석 안 된 새 기사)
- **Process**:
  1. Read new article files (tracked via seo_analysis_state.json)
  2. LLM extracts: summary (1-2문장), topic tags, SEO relevance score (1-5)
  3. Identify critical: Google algo updates, penalty risks, major industry news
  4. Write analysis to `P4-cortex/growth/seo/analyzed/YYYY-MM-DD-hash.json`
  5. If critical insight found: create kanban task for human attention
- **State file**: `P4-cortex/growth/seo/seo_analysis_state.json`
- **LLM 필요?**: ✅ Yes

### 3. 주간 트렌드 리포트 (Weekly Trend Report)
- **Trigger cron**: `seo-trend-trigger` (LLM, weekly Mon 14:00 KST, fast model)
- **Worker**: Kanban worker
- **Input**: 분석된 기사 중 최근 7일치
- **Process**:
  1. Read analyzed articles from past week
  2. LLM synthesizes hot topics, trends, notable changes
  3. Write report to `P4-cortex/growth/seo/weekly/YYYY-MM-DD-trends.md`
  4. Deliver summary to Discord channel
- **LLM 필요?**: ✅ Yes

### 4. 정리 (Cleanup)
- **Script**: (no_agent, monthly)
- **Process**: Move articles older than 90 days to `_archive/`
- **LLM 필요?**: ❌ No

## Cron Jobs Summary

| Job | Schedule | Type | Model | LLM? |
|-----|----------|------|-------|------|
| SEO Article Harvester | `0 */6 * * *` | no_agent | — | ❌ |
| `seo-analyze-trigger` | `0 12 * * *` | LLM agent | opencode-go/deepseek-v4-flash | ✅ |
| `seo-trend-trigger` | `0 14 * * 1` | LLM agent | opencode-go/deepseek-v4-flash | ✅ |

## Directory Layout

```
P2-hippocampus/knowledge/seo-articles/
├── YYYY/              # 연도별 수집 기사
│   └── *.md
├── _new/              # 최근 수집 (미분류)
├── _archive/          # 오래된 기사
├── collected_urls.json
└── report.json

P4-cortex/growth/seo/
├── seo_analysis_state.json   # 분석 상태 추적
├── analyzed/                 # 분석 결과 (YYYY-MM-DD-hash.json)
└── weekly/                   # 주간 트렌드 리포트
    └── YYYY-MM-DD-trends.md
```

## RSS 피드 목록 (2026-06-05 갱신, 28개)

### SEO / 마케팅 (10개) — 모든 글 통과
- `ahrefs.com/blog/feed`, `searchengineland.com/feed`, `semrush.com/blog/feed`
- `yoast.com/feed/`, `seopress.org/feed`, `ascentkorea.com/feed`
- `growthmk.com/feed`, `moz.com/blog/feed`, `searchenginejournal.com/feed`
- `copyblogger.com/feed`

### 테크 / 개발 (11개) — 제목 기반 키워드 필터
- `blog.google/technology/ai/rss`, `developers.googleblog.com/feeds/posts/default`
- `blog.chromium.org/feeds/posts/default`, `techcrunch.com/feed`
- `theverge.com/rss/index.xml`, `wired.com/feed/rss`, `zdnet.com/rss.xml`
- `feeds.arstechnica.com/arstechnica/index`, `css-tricks.com/feed`
- `smashingmagazine.com/feed`, `aws.amazon.com/blogs/aws/feed`, `github.blog/feed`

### 글로벌 / 커뮤니티 (7개) — 제목 기반 키워드 필터
- `openschema.co.jp/feed`, `hnrss.org/frontpage`, `dev.to/feed`
- `news.ycombinator.com/rss`, `techmeme.com/feed.xml`

## Analysis Format (worker output)

```json
{
  "article_url": "https://...",
  "title": "Article Title",
  "summary": "1-2 sentence LLM summary",
  "topic_tags": ["google-update", "core-web-vitals", "ranking"],
  "relevance_score": 4,
  "key_insight": "Main actionable takeaway",
  "is_critical": false,
  "analyzed_at": "2026-06-14T12:00:00"
}
```

## Related
- [[P3-sensors/skills/SKILL-INDEX]]
- [[P4-cortex/growth/seo/index]]
- `references/crawling-tools.md` — 크롤링 도구
- `references/discord-webhook-limits.md` — Discord embed 제한
