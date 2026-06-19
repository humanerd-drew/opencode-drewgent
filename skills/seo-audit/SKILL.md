---
title: SEO + GEO Audit
type: document
space: outcome
name: seo-audit
tags: [productivity, seo, geo, site-management]
created: 2026-05-22
updated: 2026-05-22
links:
  - "[[P3-sensors/skills/SKILL-INDEX]]"
  - "[[P4-cortex/growth/INTEGRATION_PROTOCOL]]"
  - "[[skills/humanerd-site]]"
  - "[[P0-brainstem/brain/rules]]"---

# SEO + GEO Audit — humanerd.site 감사 및 관리

GEO-first SEO 최적화 — AI 검색 (ChatGPT, Claude, Perplexity, Gemini) 대응 포함.
`geo-seo-claude` (zubair-trabzada) 아키텍처에서 영감받음.

## 감사 도구 실행

```bash
python3 ~/.drewgent/P4-cortex/scripts/seo_audit.py
```

### 옵션

```bash
# GEO 모듈만 (빠름)
python3 ~/.drewgent/P4-cortex/scripts/seo_audit.py --modules ai_crawlers,llms,citability,brand

# 전통 SEO만
python3 ~/.drewgent/P4-cortex/scripts/seo_audit.py --modules sitemap,meta,content,links

# JSON 출력
python3 ~/.drewgent/P4-cortex/scripts/seo_audit.py --output seo-20260522.json
```

## 감사 모듈 (13개)

### GEO-FIRST (AI Search Optimization)
| 모듈 | 검사 항목 | 현재 점수 |
|------|-----------|----------|
| ai_crawlers | AI 봇 접근 허용 (GPTBot, ClaudeBot 등) | 100 ✅ |
| llms | llms.txt 존재 및 품질 | 100 ✅ |
| citability | AI 인용 가능성 점수 (0-100) | 46 ❌ |
| brand | 브랜드 권한 signals (schema, mentions) | 75 ⚠ |

### Traditional SEO
| 모듈 | 검사 항목 | 현재 점수 |
|------|-----------|----------|
| sitemap | URL 개수, 중복, lastmod | 95 |
| meta | title/description/OG tags | 55 ❌ |
| content | H1 heading 구조 | 50 ❌ |
| links | 내부 링크 정합성 | 97 |
| robots | robots.txt + canonical tag | 80 |
| headers | 보안 헤더 | 70 ⚠ |
| quartz | quartz.config.ts 설정 | 100 |
| images | alt 텍스트 | 100 |
| mobile | viewport meta | 82 |

## 현재 감사 결과 (2026-05-22)

```
GEO Score:  80.2/100  │  Traditional SEO:  81.0/100
Overall:    80.8/100  (9/13 modules pass)
```

**GEO modules**: AI_CRAWLERS ✅, LLMS ✅, CITABILITY ❌(46), BRAND ⚠(75)
**기존 SEO modules**: 5개 FAIL (meta, content, robots, headers, mobile)

## GEO Citability Scoring (46/100 — F)

AI 인용 readiness 5개 범주로 측정:

| 범주 | 무게 | 설명 |
|------|------|------|
| Answer Block Quality | 30% | 첫 1-2 문장이 직접 답변 형태 |
| Passage Self-Containment | 25% | 주변 문맥 없이 단독으로 이해 가능 |
| Structural Readability | 20% | H1>H2>H3 계층, 짧은 단락 |
| Statistical Density | 15% | 구체적 통계, 날짜, 숫자 |
| Definition Patterns | 10% | "X is...", "X refers to..." 패턴 |

**개선 방법**:
1. 각 섹션 첫 문장을 직접 답변 구조로 작성 (질문-답변形式)
2. 50-200단어 단락으로 분할
3. 통계/숫자/날짜 구체적으로 명시
4. wikilink 제거 후 정의 패턴 확인

## AI Crawler robots.txt 구성 (✅ 완료)

현재 robots.txt: GPTBot, ClaudeBot, Claude-Web, PerplexityBot, Google-Extended 모두 Allow.
llms.txt 생성 완료 — AI 크롤러가 모든 페이지 탐색 가능.

## 즉시 개선이 필요한 항목

### 1. Missing H1 (9개 페이지)
대상: insights/garry-tan-*.md, lab/dream-system-SSPEC.md, blog/2026/05.md
해결: 첫 번째 heading을 `h1`으로 변경

### 2. Missing Description (14개)
해결: 각 .md 파일 frontmatter에 추가:
```yaml
description: "페이지 설명 — 검색 결과에 표시"
```

### 3. Missing OG tags (9개)
해결: quartz.layout.ts 또는 각 .md frontmatter에 og:image 추가

### 4. Missing Canonical Tag (29개)
해결: quartz.layout.ts에서 canonical tag 생성 확인

### 5. Schema 추가 (E-E-A-T)
해결: about.md 또는 config에 Person/Organization JSON-LD schema 삽입

## Cron 등록 (periodic audit)

```bash
# 주 1회 감사 (매주 월요일 오전 9시)
python3 ~/.drewgent/P4-cortex/scripts/seo_audit.py \
  --output ~/.drewgent/P6-prefrontal/logs/seo-geo-audit-$(date +%Y%m%d).json
```

## 점수 기준

- **90+**: A — GEO + SEO 모두 최적화
- **80-89**: B — minor improvements needed
- **70-79**: C — several issues to fix
- **60-69**: D — significant issues
- **<60**: F — major optimization required

## Related
- [[skills/humanerd-site]] — site management
- [[P4-cortex/growth/INTEGRATION_PROTOCOL]] — integration protocol