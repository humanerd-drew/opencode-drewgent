---
title: seo-service
  session: "2026-06-20 seo-service-planning"
  decision: "m-log 아키텍처를 fork해서 SEO 도메인으로 리팩토링. 3단계 차별화: 지속적 모니터링, 자동 수정, 트렌드 선제 대응"
created: 2026-06-20
---

# SEO Service

## What
RSS로 수집된 2,853+ SEO 기사를 지식베이스로 삼아 사용자의 블로그 콘텐츠를 지속적으로 진단/수정/관리하는 SaaS.

## Differentiation
1. **살아있는 규칙** — Google 업데이트 RSS가 들어오면 규칙이 자동 업데이트되고, 기존 글을 재진단
2. **자동 수정** — meta/h1/alt/heading 등 기계적 문제는 플러그인이 직접 수정 (Fix It 버튼)
3. **선제 알림** — 사용자가 모르는 Google 업데이트의 영향을 먼저 알려줌

## Architecture
```
[RSS harvester] → rules.yaml (수동 → 점진적 자동화)
       ↓
[진단 엔진] → crawl URL → rule check → 문제 리스트
       ↓
[SaaS] → 회원/결제/도메인관리/D1
       ↓
[WordPress plugin] → REST API로 글 읽기/쓰기
       ↓
[알림] → Discord webhook / email
```

## Phase 0: Product Rules (초기 30개)
`engine/rules/*.ts`에 저장. 각 규칙은:
- id, name, category, severity, description
- check(url, html): Promise<Pass|Fail[]>
- autoFix? 가능한 경우 fix 함수

## Code Layout
```
~/seo-service/
  worker.ts              # CF entry + routing
  wrangler.jsonc
  src/
    engine/
      crawler.ts         # URL crawl + HTML parse
      rules/             # *.ts — rule 하나당 파일 하나
      engine.ts          # runAllRules(url) → 결과[]
    reports/
      schemas/           # ReportSchema 구현
    controllers/
      auth.ts            # 로그인/회원가입
      sites.ts           # 도메인 등록/관리
      audit.ts           # 진단 실행/결과
      payment.ts         # PortOne 결제 (m-log 카피)
    utils/
      llm.ts             # DeepSeek + NVIDIA fallback
      crypto.ts          # HMAC session
    db/
      queries.ts
      migrations/
  frontend/
    app/
      index.html
      js/
        core/ (Router, Component)
        views/ (Login, Dashboard, SiteDetail, AuditResult)
        components/
  extension/
    wordpress/
    chrome/
```

## Related
- SEO articles: `[[@memory/knowledge/seo-articles]]`
- Product plan: `[[@memory/growth/seo/seo-service/product-plan]]`
