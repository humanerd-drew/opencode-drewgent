---
name: geo-seo
title: GEO-first SEO — Generative Engine Optimization for Drewgent
description: AI 검색(ChatGPT, Claude, Gemini, Perplexity, Google AI Overviews) 최적화 + 전통 SEO. WordPress 콘텐츠, Cloudflare Workers, Obsidian vault를 GEO 관점에서 진단·최적화·보고한다.
type: skill
space: outcome
tags: [outcome, seo, geo, ai-search, wordpress, schema, brand-authority]
created: 2026-06-27
updated: 2026-06-27
trigger: "Kanban task trend-apply-geo-seo-claude — zubair-trabzada/geo-seo-claude를 Drewgent 아키텍처(WordPress + Cloudflare Workers + Obsidian vault)에 맞게 재구성"
provenance:
  session: "2026-06-27 trend-apply-geo-seo-claude"
  decision: "Drewgent의 기존 skill 레이아웃(단일 SKILL.md)을 따르고, seo-article-harvester/trend-scorer 파이프라인과 연결. geo-seo-claude의 13개 sub-skill 대신 6개 GEO 모듈로 압축하여 opencode run 기반 워커에서 실행 가능하도록 설계."
links:
  - "[[@action/skills/SKILL-INDEX]]"
  - "[[skills/seo-article-harvester]]"
  - "[[skills/seo-audit]]"
  - "[[skills/trend-harvester]]"
  - "[[@memory/growth/seo/index]]"
  - "[[@identity/brain/rules]]"
---

# GEO-first SEO — Generative Engine Optimization for Drewgent

**GEO(Generative Engine Optimization) + 전통 SEO를 동시에 다룬다.**
AI 검색 엔진(ChatGPT, Claude, Gemini, Perplexity, Google AI Overviews)이 콘텐츠를 발견·인용·요약하기 좋게 만드는 것이 목표다.

이 스킬은 Drewgent의 WordPress 사이트(`humanerd.site`), Cloudflare Workers, Obsidian vault를 대상으로 GEO 원칙을 적용한다.

## 1. GEO Fundamentals for Drewgent

### 1.1 What changed in AI search
- **Query → Answer**: 사용자가 링크 목록을 받는 대신 AI가 직접 답변을 생성한다.
- **Citation as currency**: AI가 브랜드를 언급/인용하는 빈도가 새로운 가치 척도다.
- **Entity-first**: 키워드 매칭보다 브랜드/인물/조직의 entity 인식이 중요하다.
- **Passage retrieval**: 전체 페이지가 아닌 특정 문단/정의 블록이 인용된다.

### 1.2 GEO vs SEO

| 구분 | SEO | GEO |
|------|-----|-----|
| 최적화 대상 | Googlebot, Bingbot | GPTBot, ClaudeBot, PerplexityBot, Google-Extended |
| 성공 지표 | Ranking, CTR, impressions | AI mention, citation count, brand recall |
| 핵심 자산 | Backlinks | Brand mentions, entity signals, citability |
| 콘텐츠 단위 | Page | Passage / answer block |
| 구조 자산 | Sitemap, meta tags | `llms.txt`, schema, answerable headings |

### 1.3 Drewgent-specific GEO surface

| 자산 | GEO 활용 |
|------|----------|
| WordPress (`humanerd.site`) | 공개 블로그/랜딩 페이지 — AI 크롤러 대상 |
| Cloudflare Workers | `llms.txt` 서빙, 검증용 micro audit endpoint |
| Obsidian vault (P2/P4/P5) | 날짜/통계/인용 출처가 풍부한 지식 원천 |
| seo-article-harvester | Google/AI 검색 알고리즘 변화를 실시간 감지 |

## 2. AI Crawler Access — robots.txt + llms.txt

### 2.1 robots.txt
WordPress 루트의 `robots.txt` 또는 Cloudflare Workers rewrite 응답에 다음을 포함한다.

```txt
User-agent: GPTBot
Disallow: /wp-admin/
Allow: /

User-agent: ClaudeBot
User-agent: Claude-Web
Disallow: /wp-admin/
Allow: /

User-agent: PerplexityBot
Disallow: /wp-admin/
Allow: /

User-agent: Google-Extended
Disallow: /wp-admin/
Allow: /

User-agent: *
Disallow: /wp-admin/
Allow: /
```

### 2.2 llms.txt
`https://humanerd.site/llms.txt`에 사이트의 정체성과 중요 경로를 요약한다.

```txt
# llms.txt for humanerd.site

## About
humanerd.site is Drewgent's public lab and blog on AI-native workflows,
Cloudflare Workers, and agentic systems. Primary language: Korean.

## Key pages
- /about — organization and author background
- /blog — latest essays on AI engineering
- /lab — open experiments and tools
- /skills — Drewgent skill catalog

## Crawl policy
- Allowed for all AI crawlers.
- Do not train on private member-only content under /member/.

## Contact
Drew Kim — your-email@example.com
```

**배포 방법**:
- WordPress MU plugin(`YOUR_AGENT-ard.php`) 또는 `humanerd-ai-catalog.php`에 경로 추가
- Cloudflare Workers에서 `/.well-known/llms.txt`로 rewrite

## 3. Citability Scoring

AI가 인용하기 좋은 콘텐츠 블록을 만든다. 최적 인용 구간은 **134–167단어**, 맥락 없이 독립적으로 이해 가능해야 한다.

### 3.1 5-axis citability framework

| 범주 | 비중 | 설명 | Drewgent 적용 |
|------|------|------|---------------|
| Answer Block Quality | 30% | 첫 1–2 문장이 질문에 직접 답변 | Obsidian 글을 WordPress에 싣기 전 "정의 문장" 추가 |
| Passage Self-Containment | 25% | 단독으로 이해 가능 | 인물/회사명 풀네임 사용, 이전 문서 참조 최소화 |
| Structural Readability | 20% | H1→H2→H3 계층, 50–200단어 단락 | Quartz/WordPress 모두 heading tree 점검 |
| Statistical Density | 15% | 구체적 숫자, 날짜, 비율 | 실험 결과, 비용, 처리량 등 수치화 |
| Definition Patterns | 10% | "X는...", "X란..." 패턴 | 핵심 용어에 사전식 정의 블록 추가 |

### 3.2 Citability rewrite checklist
- [ ] H2/H3 직후 첫 문장이 핵심 답변
- [ ] 50–200단어 단락
- [ ] 숫자/날짜/비율 1개 이상
- [ ] "X는 Y다" 또는 "X란 Y를 의미한다" 정의 패턴
- [ ] Wikilink는 인용 블록 외부로 배치하거나 풀 텍스트 설명 추가

### 3.3 측정
`P4-cortex/scripts/seo_audit.py`의 `citability` 모듈로 점수 확인:

```bash
python3 ~/.drewgent/P4-cortex/scripts/seo_audit.py --modules ai_crawlers,llms,citability,brand
```

## 4. Brand Authority Signals

AI 검색에서 백링크보다 **브랜드 멘션**이 3배 강한 상관관계를 보인다.

### 4.1 Signal stack

| Signal | Action | Owner |
|--------|--------|-------|
| Entity consistency | "Drewgent", "Drew Kim", "humanerd" 철자/형식 통일 | 콘텐츠 전반 |
| sameAs links | Website, LinkedIn, GitHub, X, YouTube URL을 schema에 연결 | schema markup |
| Author pages | `/about` 또는 `/author/drew`에 Person JSON-LD | WordPress |
| Knowledge panel hints | Wikipedia/Reddit/YouTube 등 주요 플랫폼 멘션 수집 | brand_scanner.py |
| Original data | 자체 실험/통계를 인용 가능한 형태로 게시 | lab 콘텐츠 |

### 4.2 Brand mention scan
Cloudflare Workers endpoint 또는 cron에서 실행:

```bash
python3 ~/.drewgent/P4-cortex/scripts/brand_scanner.py --brand "Drewgent" --platforms reddit,youtube,linkedin,wikipedia
```

출력은 `P4-cortex/growth/seo/brand-mentions/YYYY-MM-DD.json`에 저장.

## 5. Schema.org Markup for Agentic Content

### 5.1 Required schemas

| Schema | Purpose | Where |
|--------|---------|-------|
| `Organization` / `Person` | Entity recognition | about.md / site footer |
| `WebSite` + `SearchAction` | Site-level entity | homepage |
| `Article` + `Author` | E-E-A-T | every blog post |
| `BreadcrumbList` | Navigation context | all pages |
| `FAQPage` | AI snippet source | FAQ pages |
| `HowTo` | procedural queries | tutorials |

### 5.2 Organization schema example

```json
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "Drewgent",
  "url": "https://humanerd.site",
  "logo": "https://humanerd.site/logo.png",
  "sameAs": [
    "https://github.com/humanerdkr",
    "https://x.com/humanerdkr",
    "https://www.linkedin.com/company/humanerd",
    "https://www.youtube.com/@humanerd"
  ],
  "founder": {
    "@type": "Person",
    "name": "Drew Kim",
    "sameAs": "https://humanerd.site/about"
  }
}
```

### 5.3 Article schema example

```json
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Cloudflare Workers에서 GEO-first SEO 적용하기",
  "author": {
    "@type": "Person",
    "name": "Drew Kim",
    "url": "https://humanerd.site/about"
  },
  "datePublished": "2026-06-27",
  "dateModified": "2026-06-27",
  "publisher": {
    "@type": "Organization",
    "name": "Drewgent",
    "logo": { "@type": "ImageObject", "url": "https://humanerd.site/logo.png" }
  },
  "description": "AI 검색(ChatGPT, Claude, Gemini, Perplexity)에 최적화된 콘텐츠 구조와 schema markup 실무"
}
```

### 5.4 Deployment in WordPress
- GeneratePress child theme `functions.php`에 `wp_head` 액션으로 삽입
- 또는 Drewgent 전용 SEO plugin이 관리
- Obsidian→WordPress publish 시 frontmatter에서 `author`, `date`, `description` 자동 매핑

## 6. Platform-Specific Optimization

| Platform | Optimization lever | Drewgent tactic |
|----------|-------------------|-----------------|
| **ChatGPT / GPTBot** | Citability, freshness | 6개월 내 재게시/업데이트 날짜 표기 |
| **Claude / ClaudeBot** | Clear structure, citations | H2/H3 직후 답변형 문장, 출처 링크 |
| **Perplexity** | Source diversity, stats | 원본 데이터/실험 결과 페이지 운영 |
| **Gemini / Google AI Overviews** | Schema, E-E-A-T, Core Web Vitals | Person/Organization schema + LCP 최적화 |
| **Google Search** | Backlinks + EEAT | 전통 SEO 기반 유지 |

### 6.1 Perplexity-specific
- Perplexity는 **출처 다양성**을 선호한다.
- `/lab`, `/insights`에 독립적 연구/실험 페이지 추가.
- 통계 출처는 링크와 함께 인용.

### 6.2 Claude-specific
- Claude는 **명확한 구조**와 **도덕적 출처 표시**를 선호한다.
- `llms.txt`에 contact/crawl policy 명시.
- 모든 인용 가능한 claim에 source link 추가.

## 7. WordPress Content Optimization Workflow

### 7.1 Publish checklist
- [ ] `description` frontmatter 120–160자
- [ ] H1 1개, H2/H3 계층적
- [ ] 첫 단락에 "이 글은 X를 설명하고 Y를 제공합니다" 형태의 요약
- [ ] 핵심 용어에 "X는..." 정의 블록 1개 이상
- [ ] Article schema + author link
- [ ] `llms.txt`에 추가할 만한 핵심 페이지면 `/llms.txt` 갱신
- [ ] robots.txt AI crawler allow 확인

### 7.2 Existing content retrofit
1. `seo_audit.py --modules citability,brand,schema` 실행
2. 점수 70 미만 페이지 리스트업
3. Kanban task 생성: `geo-retrofit-<slug>`
4. 우선순위: top 20% 트래픽 페이지 → 최신 글 → FAQ/tutorial

## 8. Integration with Drewgent SEO Pipeline

```
[seo-article-harvester]  ──►  [trend-scorer]  ──►  [GEO rule update]
        │                            │
        ▼                            ▼
   Google/AI algo news          hot topic detection
        │                            │
        └──────────────┬─────────────┘
                       ▼
              [kanban task: geo-apply-<trend>]
                       │
                       ▼
              [geo-seo skill execution]
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   WordPress     Cloudflare      Obsidian vault
   content       llms.txt/       source material
   update        audit endpoint    enrichment
```

### 8.1 Trigger conditions
- seo-article-harvester가 "AI Overviews", "GEO", "ChatGPT search", "Claude", "Perplexity" 키워드로 critical 기사 태깅
- trend-scorer가 SEO/GEO 트렌드 6.0점 이상으로 선정
- weekly SEO trend report에서 GEO 관련 action item 발생

### 8.2 Output destinations
- WordPress post update
- `P4-cortex/growth/seo/geo-actions/YYYY-MM-DD-<slug>.md`
- Discord #growth summary
- Monthly GEO report PDF: `P4-cortex/growth/seo/reports/GEO-YYYY-MM.pdf`

## 9. GEO Report Template

Monthly/one-off report structure:

```markdown
# GEO Report — humanerd.site (2026-06)

## Scorecard
| Module | Score | Status |
|--------|-------|--------|
| AI Crawler Access | 100 | ✅ |
| llms.txt | 90 | ✅ |
| Citability | 46 | ❌ |
| Brand Authority | 75 | ⚠️ |
| Schema Markup | 60 | ❌ |
| Platform Readiness | 70 | ⚠️ |
| **Composite GEO Score** | **74** | **C** |

## Quick Wins
1. Add answer-first sentences to top 10 pages.
2. Insert Organization + Person schema on about page.
3. Generate/verify llms.txt.

## Next 30 Days
- Retrofit 20 low-citability pages.
- Brand mention scan (Reddit/YouTube/LinkedIn).
- FAQPage schema for 3 tutorial posts.
```

## 10. Operational Commands

### 10.1 One-off audit
```bash
python3 ~/.drewgent/P4-cortex/scripts/seo_audit.py \
  --url https://humanerd.site \
  --output ~/.drewgent/P6-prefrontal/logs/geo-seo-audit-$(date +%Y%m%d).json
```

### 10.2 GEO-only quick check
```bash
python3 ~/.drewgent/P4-cortex/scripts/seo_audit.py \
  --modules ai_crawlers,llms,citability,brand,schema
```

### 10.3 Brand mention scan
```bash
python3 ~/.drewgent/P4-cortex/scripts/brand_scanner.py \
  --brand "Drewgent" \
  --output ~/.drewgent/P4-cortex/growth/seo/brand-mentions/$(date +%Y-%m-%d).json
```

### 10.4 Retrofit task creation (kanban)
```bash
# via kanban_create in opencode run
python3 ~/.drewgent/scripts/kanban_create.py \
  --title "GEO retrofit: <page-slug>" \
  --body "Improve citability + schema for <URL>. See skills/seo/geo-seo."
```

## 11. Scoring Methodology

Composite GEO Score = weighted average across 6 modules.

| Module | Weight | Pass threshold |
|--------|--------|----------------|
| AI Crawler Access | 15% | 90 |
| llms.txt Quality | 10% | 80 |
| Citability | 25% | 70 |
| Brand Authority | 20% | 70 |
| Schema Markup | 15% | 80 |
| Platform Readiness | 15% | 70 |

**Grade scale**:
- 90–100: A — GEO + SEO 모두 최적화
- 80–89: B — minor improvements
- 70–79: C — several issues
- 60–69: D — significant issues
- <60: F — major optimization required

## 12. Related

- [[skills/seo-article-harvester]] — SEO 기사 수집 파이프라인
- [[skills/seo-audit]] — 기존 SEO + GEO audit 결과 및 스크립트
- [[skills/trend-harvester]] — 트렌드 수집·평가·적용
- [[@memory/growth/seo/index]] — SEO 성장 지식베이스
- [[@action/skills/SKILL-INDEX]]
