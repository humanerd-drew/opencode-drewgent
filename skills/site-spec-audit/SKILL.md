---
name: site-spec-audit
title: site-spec-audit — humanerd.kr을 The Website Spec으로 감사
description: Audit any URL (default: humanerd.kr) against The Website Specification (specification.website). Uses the `specification-website` MCP server (search, list_topics, get_topic, get_checklist, get_categories). Reports `required` items first, then `recommended`, with primary sources cited. Use when the user asks to audit/check/validate humanerd.kr, when a new site is deployed, or when planning a new feature that touches foundations/seo/accessibility/security/agent-readiness.
type: skill
space: growth
tags: [skill, audit, web-standards, humanerd-site, agent-readiness]
created: 2026-06-01
updated: 2026-06-01
links:
  - "[[skills/specification-website]]"
  - "[[skills/humanerd-site]]"
  - "[[skills/seo-audit]]"
  - "[[skills/filesystem-truth-audit]]"
  - "[[P3-sensors/skills/SKILL-INDEX]]"
  - "[[P0-brainstem/brain/rules]]"---


# site-spec-audit

humanerd.kr (or any URL) 을 The Website Specification으로 감사하는 스킬. 기본 대상은 `https://humanerd.kr`. 다른 URL은 인자로 전달.

## 사용법

```
/site-spec-audit                              # humanerd.kr 감사
/site-spec-audit https://example.com          # 다른 URL 감사
/site-spec-audit --category=agent-readiness   # 카테고리 한정 감사
/site-spec-audit --status=required            # status=required만
/site-spec-audit --status=recommended         # status=recommended만
```

## 어떻게 작동하는가

이 스킬은 두 가지를 조합한다:

1. **MCP 서버** `specification-website` — `~/.drewgent/config.yaml`의 `mcp_servers.specification-website`에 등록됨
2. **HTTP fallback** — `https://specification.website/.well-known/agent-skills/specification-website/SKILL.md`의 워크플로우대로 직접 fetch

MCP 도구 우선. MCP가 안 되면 llms.txt / 직접 fetch로 fallback.

## MCP 도구

| Tool | 용도 |
|---|---|
| `get_categories()` | 10개 카테고리 + 카운트 + 요약 |
| `list_topics({ category, status, limit })` | 필터된 인덱스 |
| `get_topic({ slug })` | 단일 spec 페이지 풀 마크다운 |
| `get_checklist({ category, status })` | 체크리스트 형식 |
| `search(query, limit)` | 전문 검색 |

Prompt: `audit_url(url, focus?)` — 대상 URL에 대한 감사 플랜 생성.

## 감사 워크플로우 (5단계)

### 1. 스코프 결정

```
url = 인자 또는 기본값 "https://humanerd.kr"
focus = 인자의 --category 또는 None (전체 10 카테고리)
status_filter = 인자의 --status 또는 "required" 먼저
```

### 2. 카테고리 목록 로드

```python
mcp.call("get_categories")  # 10개 카테고리 + 카운트
```

### 3. spec 페이지 fetch (status=required)

```python
for category in categories:
    mcp.call("list_topics", {"category": category, "status": "required"})
    for topic in topics:
        spec = mcp.call("get_topic", {"slug": topic.slug})
        # spec의 "How to verify" 섹션 → 체크리스트 항목으로 변환
```

### 4. URL 실제 검증

각 spec 항목에 대해 humanerd.kr에서 검증:

- **HTTP fetch** (web_search / browser_navigate) — `og:title`, `<meta charset>`, `<title>` 등 HTML head 검증
- **well-known fetch** — `/.well-known/security.txt`, `/.well-known/agent-skills/`, `/robots.txt`, `/sitemap-index.xml`
- **Accept: text/markdown** — `/llms.txt`, `/llms-full.txt` 존재 + Markdown negotiation 작동 여부

### 5. 보고서 작성

```
# humanerd.kr 감사 보고서 — YYYY-MM-DD
## 통과: N개
- ✅ <title> element present
- ✅ <meta charset="UTF-8"> set
- ...

## 누락 (required): M개
- ❌ <meta name="theme-color"> missing
- ❌ /robots.txt returns 404
- ❌ /sitemap-index.xml missing (Quartz 기본 생성 안 함)
- ...

## recommended 미흡: K개
- ⚠️ /llms.txt recommended but not present
- ⚠️ Open Graph tags present but og:image missing
- ...

## 출처
각 spec 항목의 `sources` 필드에서 1차 표준 인용
(W3C, WHATWG, IETF RFC, WCAG, MDN)
```

## humanerd.kr 우선 점검 (Quartz 베이스)

Quartz 빌드 결과를 기준으로 자주 빠지는 항목:

### Foundations (14개)
- [ ] `<!doctype html>` — Quartz 기본 OK
- [ ] `<html lang="ko">` — Quartz `Locale` config OK, 한국어 콘텐츠면 `ko`
- [ ] `<meta charset="utf-8">` — OK
- [ ] `<meta name="viewport">` — OK
- [ ] `<title>` — Quartz `Title.generated` OK
- [ ] `<meta name="description">` — ⚠️ 페이지별 설정 필요 (frontmatter `description`)
- [ ] `<link rel="canonical">` — ⚠️ Quartz plugin `canonical` 옵션
- [ ] Favicon + app icons — ⚠️ `quartz/static/icon.svg` 없으면 누락
- [ ] `<meta name="theme-color">` — ❌ Quartz 미생성
- [ ] `<meta name="color-scheme">` — ❌ Quartz 미생성
- [ ] Open Graph — ⚠️ frontmatter `socialImage`, `socialDescription` 필요
- [ ] `<link rel="alternate" type="application/atom+xml">` — ❌ RSS feed 발견 안 됨

### SEO (13개)
- [ ] `/robots.txt` — ❌ Quartz 미생성
- [ ] `/sitemap-index.xml` — ⚠️ Quartz `enableSiteMap: true`로 가능
- [ ] `<link rel="canonical">` (위와 중복)
- [ ] Heading hierarchy (h1→h2→h3) — OK (Quartz 컴포넌트가 자동)
- [ ] JSON-LD structured data — ❌ Quartz 미생성 (직접 emitter 필요)

### Well-Known URIs (9개)
- [ ] `/.well-known/security.txt` — ❌ (Cloudflare Pages에서 static file로 가능)
- [ ] `/.well-known/agent-skills/` — ❌ (인덱스 + SKILL.md)
- [ ] `/.well-known/api-catalog` — ❌

### Agent Readiness (18개)
- [ ] `/llms.txt` — ❌ (Quartz plugin `llmsTxt` 옵션 확인)
- [ ] `/llms-full.txt` — ❌
- [ ] MCP server (`/mcp`) — ❌ (Cloudflare Pages는 serverless, Workers 필요)
- [ ] `Accept: text/markdown` content negotiation — ❌
- [ ] Content-Signals header — ❌

## cron 자동화 (H3)

`jobs.json`의 `site-spec-audit-weekly` cron job이 매주 일요일 04:00 KST에 실행:

1. Quartz 빌드
2. humanerd.kr 라이브 URL에 spec check 적용
3. 보고서를 `P6-prefrontal/incidents/site-audit-{date}.md`로 저장
4. 회귀 감지 (이전 보고서와 diff)

## Sources

- The Website Specification: https://specification.website/
- Spec SKILL: https://specification.website/.well-known/agent-skills/specification-website/SKILL.md
- humanerd-site skill: [[skills/humanerd-site]]
