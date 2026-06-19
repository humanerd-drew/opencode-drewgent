---
title: Content Pipeline Publish Leak 20260602
type: incident
space: claim
tags: [claim]
created: 2026-06-02
updated: 2026-06-02
links:
  - "[[P0-brainstem/brain/rules]]"
  - "[[P4-cortex/growth/INTEGRATION_PROTOCOL]]"
  - "[[P4-cortex/growth/humanerd-site-url-mapping]]"
  - "[[P4-cortex/portfolio/quartz-publishing]]"
  - "[[skills/humanerd-site]]"
  - "[[skills/humanerd-content-status-enforcement]]"
  - "[[P6-prefrontal/incidents/cron-job-failure-20260518]]"
---

# Incident Report — Content Pipeline Publish Leak
## 2026-06-02

**Date**: 2026-06-02 04:00 KST (detected) → 04:30 KST (resolved)
**Severity**: P1 (콘텐트 publish safety — 5개 article이 human 검토 없이 라이브 노출)
**Status**: ✅ Resolved
**Affected scope**: humanerd.kr public site

## Symptom

5/23~5/26 + 6/1 자동 생성된 5개 trend article이 human 검토 없이 humanerd.kr에 publish됨:

| Article | vault file | publish 일자 | 노출 일자 |
|---|---|---|---|
| Gemini CLI shutdown | `memories/insights/2026-05-23-gemini-cli-shutdown.md` | 5/23 | 5/30~6/2 |
| Remove-AI-Watermarks | `memories/insights/2026-05-23-remove-ai-watermarks.md` | 5/23 | 5/30~6/2 |
| Claude Code의 본질 | `memories/insights/2026-05-26-claude-code-essence.md` | 5/26 | 5/30~6/2 |
| Flue Sandbox Agent | `memories/insights/2026-05-26-flue-sandbox-agent.md` | 5/26 | 5/30~6/2 |
| Microsoft AI Cost | `memories/insights/2026-05-26-microsoft-ai-cost-comparison.md` | 5/26 | 5/30~6/2 |
| AI 에이전트 권위 피로 | `memories/insights/2026-05-ai-agent-authority-fatigue.md` | 6/1 | 6/1~6/2 |

총 6개 article. 모두 humanerd.kr에 200 OK로 노출.

## Root Cause

Quartz 표준 `Plugin.RemoveDrafts()` (in `quartz/plugins/filters/draft.ts`) 의 shouldPublish 로직:

```typescript
shouldPublish(_ctx, [_tree, vfile]) {
  const draftFlag = (vfile.data?.frontmatter?.draft ?? false) === true
  return !draftFlag
}
```

→ **`frontmatter.draft === true` 만 체크**. `status: draft` 또는 status field 없음은 통과시켜 publish.

**humanerd content-pipeline의 마킹 convention**:
- 5/22 content-pipeline-report 시점부터 `frontmatter.status: draft` 로 draft 표시
- `frontmatter.draft: true` 는 사용 안 함
- 일부 article (특히 자동 생성)은 status field 자체가 없음

→ Quartz 표준 plugin이 status: draft를 인식 못 함 → **6개 article이 publish됨**.

## Detection

`site-spec-audit` skill으로 humanerd.kr 점검 중. Live URL 검증:

```bash
$ curl -sI https://humanerd.kr/blog/2026-05-23-gemini-cli-shutdown/ | head -1
HTTP/2 200    ← ❌ draft가 200으로 노출

$ curl -sI https://humanerd.kr/blog/2026-05-26-claude-code-essence/ | head -1
HTTP/2 200    ← ❌ draft가 200으로 노출
```

12개 article 모두 200으로 노출 — 검토 게이트가 작동 안 했음.

## Fix Applied

### Fix 1: DraftFilter v2 (transformer, default-draft strict)

`quartz/plugins/transformers/draftFilter.ts` 신규 작성. filter → transformer 이동하여 FrontMatter parse 이후 status 검사.

```typescript
export const DraftFilter = (opts?: {
  includeStatus?: string[]   // default: ["published", "polished"]
  excludeStatus?: string[]   // default: ["draft", "in_review", "archived"]
  domainExclude?: string[]   // default: ["draft"]
  defaultExclude?: boolean   // default: true (strict)
}): QuartzTransformerPlugin => ({ ... })
```

**Plugin include list (live 노출):**
- `status: published` (and `Published`)
- `status: polished` (and `Polished`)

**Plugin exclude list (404):**
- `status: draft`, `in_review`, `archived`
- `status: publish` (단수) — **naming convention** 위배
- `domain: draft`
- status field 없음 (default-draft strict)

**연결**:
1. `quartz/plugins/transformers/draftFilter.ts` 신규 작성
2. `quartz.config.ts`: `transformers: [Plugin.FrontMatter(), DraftFilter({ defaultExclude: true }), ...]`
3. **검증**: build 로그에 `[DraftFilter] EXCLUDE ...` 라인 N개

### Fix 2: 정상 19 article에 status: published 일괄 추가

`memories/insights/`, `P4-cortex/knowledge/`, `P4-cortex/portfolio/`, `humanerd-site/content/` 의 정상 article 19개에 `status: published` 추가:

- insights 7 (NEURONFS_RULES, OPENCRAB_ONTOLOGY, garry-tan-architecture, garry-tan-complexity-ratchet, garry-tan-building-with-ai, vault-site-principle, prd-template)
- monthly log 2 (2026-05, 2026-06)
- index + about + services 3 (drewgent, notion2web, seo-harvester)
- portfolio 3 (drewgent, quartz-publishing, seo-article-harvester)
- Insights.md (blog index)

### Fix 3: Homepage Blog 섹션 wikilink 정리

`humanerd-site/content/index.md` 의 Blog 섹션에서 3 broken wikilink 제거:
- 2026-05-23 — Gemini CLI shutdown
- 2026-05-26 — Claude Code의 본질
- 2026-06-01 — AI 에이전트 권위 피로

monthly log 2개 (2026-05, 2026-06) + Blog Index 만 유지. 주석 추가: "개별 trend article은 검토 후 발행으로 전환되면 자동으로 노출됩니다."

## Verification (P0 3-Phase QA)

### Contract
- [x] 12개 article이 build에서 EXCLUDE 확인
- [x] 19개 정상 article이 build에서 INCLUDE 확인
- [x] humanerd.kr live URL 18개 article 200 OK
- [x] humanerd.kr live URL 12개 article 404 OK
- [x] Homepage Blog 섹션에서 4 broken wikilink 제거 확인
- [x] wrangler deploy 성공 (preview `2e88ba70.humanerd-site.pages.dev`)

### Micro
- [x] `npx quartz build` exit 0
- [x] `[DraftFilter] EXCLUDE ...` 12 article 로그
- [x] `Filtered out 6 files` (FrontMatter 있는 article만)
- [x] `Emitted 1302 files to public`
- [x] `npx wrangler pages deploy public/ --project-name=humanerd-site` exit 0
- [x] `✨ Success! Uploaded 44 files` + `Deployment complete!`
- [x] humanerd.kr curl 18 article 200 / 12 article 404
- [x] humanerd.kr homepage에서 3개 title 0 occurrence

### Full
- [x] 6/2 04:30 KST — manual test 통과
- [x] 재발 방지: humanerd-content-status-enforcement skill로 agent self-apply 가능
- [x] 5/29 우려 사항 (`wrangler token 403`) 해소 — 이번엔 정상 deploy, token 유효

## Prevention

### Skill: humanerd-content-status-enforcement
Agent가 vault .md file 생성/편집 시 status field 강제:

**Trigger**: write_file 또는 patch on:
- `memories/insights/**`
- `P4-cortex/knowledge/**`
- `P4-cortex/portfolio/**`
- `humanerd-site/content/**` (services, insights, portfolio, blog, about, index)

**Pre-flight check**:
```python
def check_status(path: Path) -> str:
    # parse frontmatter, return MISSING_FRONTMATTER / MISSING_STATUS / OK
    # or WRONG_STATUS / UNKNOWN_STATUS
```

**Decision tree**: 새 article은 무조건 `status: draft` (default). user가 명시적으로 "publish" / "발행" / "라이브" 라고 하면 `status: published`.

### Quartz config hardening
- DraftFilter strict default (`defaultExclude: true`)
- Plugin include: `["published", "polished"]` 만
- Plugin exclude: `["draft", "in_review", "archived"]` + `domain: draft` + no-status

### Naming convention
- `status: published` (and `polished`) — O
- `status: publish` (단수) — X (plugin이 인식 안 함)
- `domain: draft` (도메인 단위) — X

## Documentation Updates

| File | 변경 |
|------|------|
| `P4-cortex/portfolio/quartz-publishing.md` | state machine + plugin include/exclude list 추가 |
| `P4-cortex/growth/humanerd-site-url-mapping.md` | Step 1~3, 6 ✅ + Step 4, 5 partial 체크 |
| `skills/humanerd-site/SKILL.md` | DraftFilter v2 코드 + state machine table |
| `skills/humanerd-content-status-enforcement/SKILL.md` | 신규 생성 — agent self-apply |
| `humanerd-site/content/index.md` | Blog 섹션 wikilink 3개 제거 |
| `humanerd-site/quartz/plugins/transformers/draftFilter.ts` | 신규 — strict default-draft |
| `humanerd-site/quartz.config.ts` | transformers 등록 |

## Related

- [[P4-cortex/portfolio/quartz-publishing]] — pipeline overview
- [[P4-cortex/growth/humanerd-site-url-mapping]] — 3-pillar URL mapping + rolling checklist
- [[skills/humanerd-site]] — main site skill (v2)
- [[skills/humanerd-content-status-enforcement]] — agent self-apply skill
- [[P6-prefrontal/incidents/cron-job-failure-20260518]] — 직전 incident
- [[P0-brainstem/brain/rules]] — P0 brainstem governance

## Links
- [[P4-cortex/growth/INTEGRATION_PROTOCOL]]

## Related Neurons
- [[禁auto_validate.neuron]]
- [[禁subagent_verify.neuron]]
- [[禁blind_write.neuron]]
