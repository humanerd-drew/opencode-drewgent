---
name: quartz-remove-drafts-customization
title: "quartz-remove-drafts-customization — Quartz RemoveDrafts plugin의 status: draft 미인식 fix + default-draft strict hardening (2026-06-02)"
description: "Quartz 빌드 시스템의 `Plugin.RemoveDrafts()`는 frontmatter의 `draft: true`만 체크함. `status: draft`나 다른 키로 draft를 표시하는 경우 (Obsidian vault + Quartz 셋업의 흔한 패턴), draft가 public/에 그대로 빌드되어 site에 게시됨. `quartz.config.ts`의 `filters: [Plugin.RemoveDrafts()]`를 customized filter로 교체해 `status === draft`도 인식하게 만드는 절차. Drewgent humanerd.kr 포함 Quartz 4.x 사용자 모두 영향. 2026-06-02 patch: default-draft strict mode (status field가 없거나 unknown이면 자동 EXCLUDE) + 5-state machine (draft/in_review/polished/published/archived) + wikilink post-EXCLUDE caveat + 'publish' 단수 trap."
type: skill
space: growth
tags: [skill, quartz, draft, content-pipeline, obsidian, humanerd-site, state-machine, default-draft-strict]
created: 2026-06-01
updated: 2026-06-02
links:
  - "[[skills/content-pipeline/SKILL]]"
  - "[[skills/humanerd-site]]"
  - "[[skills/humanerd-content-status-enforcement]]"
  - "[[skills/site-spec-audit]]"
  - "[[skills/filesystem-truth-audit]]"
  - "[[skills/patch-secret-safety]]"
  - "[[P3-sensors/gateway/drewgent-architecture-dataflow]]"
  - "[[P0-brainstem/brain/rules]]"---


# quartz-remove-drafts-customization

Quartz `Plugin.RemoveDrafts()` 필터가 custom frontmatter 키 (e.g. `status: draft`)를 인식하지 못하는 문제의 진단 + fix 절차.

## 문제 — 2026-06-01 ~ 2026-06-02 incident (2 rounds)

### Round 1 (6/1): 명시적 status: draft 누수
content-pipeline이 만든 `status: draft` 초안 파일들이 검토 없이 humanerd.kr에 자동 게시됨.

### Round 2 (6/2): **default-include의 함정** — status field가 없는 파일이 통과됨
6/1 fix 후에도 5/23~5/26 자동 생성 article 4개가 계속 노출됨. `status: draft`도 아니고 `status: publish`도 아닌, **status field 자체가 없는** 파일들이었음. v1 filter의 "default-include (status field 없으면 통과)" 정책이 이 케이스를 못 잡음. Hardening: **default-draft strict** (status field 없으면 자동 EXCLUDE) — 모든 콘텐트는 pipeline을 거쳐서 publish 명시되어야 라이브.

### 진짜 원인
Quartz 4.x 기본 `RemoveDrafts` plugin:

```typescript
// quartz/plugins/filters/draft.ts (Quartz 4.5.2)
export const RemoveDrafts: QuartzFilterPlugin<{}> = () => ({
  name: "RemoveDrafts",
  shouldPublish(_ctx, [_tree, vfile]) {
    const draftFlag: boolean =
      vfile.data?.frontmatter?.draft === true ||
      vfile.data?.frontmatter?.draft === "true"
    return !draftFlag
  },
})
```

**문제**: `frontmatter.draft` 키만 체크. `frontmatter.status`는 안 봄.

### 흔한 부딪힘 패턴
- Obsidian vault에서 draft를 표시하려면 보통 `status: draft` (또는 `publish: false`, `published: false`) 사용
- Quartz 기본 스키마는 `draft: true`만 인식
- 결과: **drafts가 그대로 public/에 build되어 site에 게시됨**

### 증거
```
$ cd humanerd-site && npx quartz build
Found 63 input files
Parsed 63 Markdown files
Filtered out 0 files    ← RemoveDrafts가 아무것도 필터 안 함
Emitted 4986 files
```

draft 6개 (`status: draft` frontmatter) 모두 `public/insights/*.html`로 빌드됨.

## 진단 — draft가 새고 있는지 확인

### 1. Build log에서 "Filtered out" 줄 확인

```bash
cd ~/.drewgent/humanerd-site
npx quartz build 2>&1 | grep -E "Found|Filtered|Emitted"
```

**예상 정상**:
```
Found 63 input files
Filtered out N files    ← N > 0
Emitted 4986 files
```

**비정상 (draft 새는 중)**:
```
Found 63 input files
Filtered out 0 files    ← draft 누수
Emitted 4986 files
```

### 2. draft frontmatter 패턴 확인

```bash
cd ~/.drewgent
echo "=== status: draft 파일 수 ==="
grep -l "^status: draft$" **/*.md **/**/*.md 2>/dev/null | wc -l

echo "=== draft: true 파일 수 (Quartz가 인식) ==="
grep -l "^draft: true$" **/*.md **/**/*.md 2>/dev/null | wc -l

echo "=== status: publish 파일 수 ==="
grep -l "^status: publish" **/*.md **/**/*.md 2>/dev/null | wc -l
```

`status: draft` > 0, `draft: true` = 0이면 RemoveDrafts가 draft를 못 잡고 있다는 신호.

### 3. public/ 디렉토리에 draft HTML 존재 확인

```bash
cd ~/.drewgent/humanerd-site
# draft frontmatter 가진 파일들이 public/에 빌드됐는지 확인
for src in $(grep -l "^status: draft$" ~/.drewgent/memories/insights/*.md); do
  base=$(basename "$src" .md)
  [ -f "public/insights/${base}.html" ] && echo "LEAK: $base"
done
```

### 4. live site에 draft 페이지가 떠 있는지 확인

```bash
# 각 draft 파일의 canonical URL로 접근
curl -s -o /dev/null -w "%{http_code}\n" https://humanerd.kr/insights/<slug>
# 200 = 새고 있음
# 404 = 안전 (또는 build가 deploy 안 됨)
```

## Fix — 4가지 옵션

### Option D: Transformer-based filter (slug-rewrite) — 다양한 marker + state machine (2026-06-01 verified)

**Option A의 한계**: `shouldPublish()` 안에서 단순히 `false`를 return하면 file이 build에서 빠짐. 하지만:

- **다양한 marker 필요**: `status: draft` 외에 `domain: draft` (legacy), `publish: false`, `status: in_review`, `status: polished` 등 다양한 marker를 인식해야 할 때
- **State machine (윤문 단계)**: `draft → in_review → polished → published` 같은 다단계 state. published/polished는 통과, draft/in_review/archived는 차단
- **Filter 이유 추적**: 어떤 파일이 왜 제외됐는지 console.log로 추적 (CI 로그에서 확인 가능)
- **Back-compat 제어**: status field가 없는 파일을 default-include (back-compat) vs default-draft (strict) — 정책 결정 가능

이런 경우 **transformer-based**가 더 강력. file.data.slug를 `drafts/<original>`로 rewrite한 후 `ignorePatterns: ["drafts/**"]`로 제외.

**1단계 — plugin 파일 생성** (`quartz/plugins/transformers/draftFilter.ts`):

```typescript
import { QuartzTransformerPlugin } from "../types"
import { FullSlug } from "../../util/path"

export interface Options {
  excludeStatus: string[]
  includeStatus: string[]
  legacyDomainField: string
  draftPrefix: string
}

const defaultOptions: Options = {
  excludeStatus: ["draft", "in_review", "archived"],
  includeStatus: ["polished", "published"],
  legacyDomainField: "draft",
  draftPrefix: "drafts",
}

function isExcludedFrontmatter(
  fm: Record<string, unknown> | undefined,
  opts: Options,
): { exclude: boolean; reason: string } {
  // default-draft strict (2026-06-02 hardening): status field가 없는 파일은
  // 자동 EXCLUDE. 명시적인 publish 신호 없이는 라이브 안 됨.
  // 6/1 incident의 근본 원인: "default-include"가 status-field-없는 파일을 통과시킴.
  if (!fm) return { exclude: true, reason: "default-draft (no frontmatter)" }

  // 1. status field (canonical, state machine)
  const status = (fm.status as string | undefined)?.toLowerCase()?.trim()
  if (status && opts.excludeStatus.includes(status)) {
    return { exclude: true, reason: `status: ${status}` }
  }
  if (status && opts.includeStatus.includes(status)) {
    return { exclude: false, reason: `status: ${status}` }
  }

  // 2. legacy: domain: draft (older vault articles)
  const domain = (fm.domain as string | undefined)?.toLowerCase()?.trim()
  if (domain === opts.legacyDomainField) {
    return { exclude: true, reason: `domain: ${domain}` }
  }

  // 3. publish: false (explicit opt-out)
  if (fm.publish === false) {
    return { exclude: true, reason: "publish: false" }
  }

  // 4. publish: true (explicit opt-in, override default)
  if (fm.publish === true) {
    return { exclude: false, reason: "publish: true" }
  }

  // 5. default: EXCLUDE (strict, 2026-06-02)
  // status field가 있으나 위 어떤 case에도 안 매칭 (e.g. typo, 새 state)
  // → 통과시키지 말고 명시적 fix 요구
  return {
    exclude: true,
    reason: `unknown status: "${(fm.status as string) || "(none)"}" (strict)`,
  }
}

export const DraftFilter: QuartzTransformerPlugin<Partial<Options>> = (userOpts) => {
  const opts = { ...defaultOptions, ...userOpts }

  return {
    name: "DraftFilter",
    textTransform(_ctx, src) {
      return src
    },
    markdownPlugins() {
      return [
        () => {
          return (tree, file) => {
            const fm = (file.data.frontmatter as Record<string, unknown> | undefined) ?? {}
            const { exclude, reason } = isExcludedFrontmatter(fm, opts)
            if (exclude) {
              const originalSlug = (file.data.slug as FullSlug | undefined) ?? "unknown"
              // Move file to drafts/ namespace → ignorePatterns로 제외
              file.data.slug = `${opts.draftPrefix}/${originalSlug.replace(/^\//, "")}` as FullSlug
              console.log(`[DraftFilter] EXCLUDE ${originalSlug} (${reason})`)
            }
          }
        },
      ]
    },
  }
}
```

**2단계 — `quartz.config.ts`에 import + 등록**:

```typescript
import { QuartzConfig } from "./quartz/cfg"
import * as Plugin from "./quartz/plugins"
import { DraftFilter } from "./quartz/plugins/transformers/draftFilter"  // ← 추가

const config: QuartzConfig = {
  // ...
  plugins: {
    transformers: [
      Plugin.FrontMatter(),
      DraftFilter(),  // ← FrontMatter() 다음에 등록 (frontmatter가 먼저 parse되어야 함)
      // ... other transformers
    ],
    // ...
  },
}
```

**3단계 — `ignorePatterns`에 `drafts/**` 추가**:

```typescript
ignorePatterns: [
  // ... existing
  "drafts/**",
],
```

**왜 Option D가 강력한가:**

- **State machine 친화**: `polished`를 통과시키고 `in_review`는 차단 — 윤문 단계 자동화 시 핵심
- **Legacy marker 지원**: `domain: draft` (2026-05 article에서 발견된 패턴) 자동 인식
- **Filter 추적 가능**: build log에 `[DraftFilter] EXCLUDE blog/2026-05-foo (status: draft)` 형태로 출력 → CI/deploy에서 검증 가능
- **다양한 opt-out/opt-in**: `publish: true/false`로 명시적 제어

**Option A vs D 비교:**

| 케이스 | Option A (filter) | Option D (transformer) |
|---|---|---|
| 단순 `status: draft` 처리 | ✅ | ✅ |
| 다단계 state machine | ❌ | ✅ (polished, in_review 구분) |
| Legacy `domain: draft` 처리 | ❌ (수동 추가 필요) | ✅ (default) |
| `publish: true/false` 명시 제어 | ❌ | ✅ |
| Build log에 filter 이유 출력 | ❌ (Quartz가 emit skip) | ✅ (console.log) |
| 구현 복잡도 | 낮음 (10줄) | 중간 (50줄) |

**Drewgent 6/1 incident에서 채택 이유:**
- `domain: draft` marker가 vault의 2026-05 article에 잔존 → Option A로는 별도 처리 필요
- 5단계 state machine (`draft → in_review → polished → published → archived`) 도입 예정 → Option D가 자연스러움
- 6개 status: draft + 1개 domain: draft 모두 한 번에 7개 exclude (single pass)

**Option A (filter) vs D (transformer) 결정 기준:**
- 단순히 `status: draft`만 막고 싶다 → A
- 다양한 marker + state machine + build log 추적이 필요하다 → D

### Option A: 별도 plugin 파일로 분리 (단순 draft, 2026-06-01 verified)

inline patch (`quartz.config.ts` 안에 const CustomRemoveDrafts 정의)보다 별도 파일이 깨끗하고 재사용 가능. **Drewgent는 이 방식을 적용함 (quartz/plugins/filters/humanerd-draft.ts).**

**1단계 — plugin 파일 생성** (`quartz/plugins/filters/humanerd-draft.ts`):
```typescript
import { QuartzFilterPlugin } from "../types"

export const RemoveDraftsHumanerd: QuartzFilterPlugin<{}> = () => ({
  name: "RemoveDraftsHumanerd",
  shouldPublish(_ctx, [_tree, vfile]) {
    const fm = vfile.data?.frontmatter || {}
    const draftFlag =
      fm.draft === true || fm.draft === "true" ||
      fm.status === "draft" || fm.status === "Draft"
    return !draftFlag
  },
})
```

**2단계 — filters index.ts에 export 추가** (`quartz/plugins/filters/index.ts`):
```typescript
export { RemoveDraftsHumanerd } from "./humanerd-draft"
```

**3단계 — `quartz.config.ts`에서 import + 사용**:
```typescript
import { QuartzConfig } from "./quartz/cfg"
import * as Plugin from "./quartz/plugins"
import { RemoveDraftsHumanerd } from "./quartz/plugins/filters"  // ← 추가

const config: QuartzConfig = {
  // ...
  filters: [Plugin.RemoveDraftsHumanerd()],  // ← Plugin.RemoveDrafts() 대신
}
```

**왜 이 방식이 inline보다 나은가:**
- plugin 로직이 한 곳에 isolated → 다른 project에서 그대로 복사 가능
- `filters: [Plugin.RemoveDrafts(), CustomRemoveDrafts]` 같은 실수 방지 (export 자체가 unique)
- Quartz upgrade 시 plugin 파일만 충돌, config는 안전
- 코드 가독성: `RemoveDraftsHumanerd()`라는 이름이 의도를 명확히 표현

**동작 (verified 2026-06-01):**
- `draft: true` → 필터됨
- `status: draft` → 필터됨
- `status: "Draft"` (대소문자) → 필터됨
- `status: publish` → 통과
- `status: archived` → 통과 (의도적 — Quartz 기본 동작 유지)

### Option B: content-pipeline의 frontmatter를 `draft: true`로 변경

content-pipeline SKILL.md의 4-3 단계 + frontmatter template을 수정:

```yaml
# Before
status: draft

# After
draft: true
```

단점:
- SKILL.md의 모든 frontmatter 예시 patch 필요 (4-3, Phase 5, 여러 quality gate 예시)
- 다른 content-pipeline consumer (n8n, custom script)도 같이 변경 필요
- Obsidian 사용자에게 `draft: true`가 boolean으로 직관적이지 않을 수 있음

### Option C: `draft: true` + `status: draft` 둘 다 emit (belt + suspenders)

Option A 또는 B + 추가 안전장치:
- `published_date: YYYY-MM-DD` 가 있는 파일만 통과 (작성 중 draft는 무조건 차단)
- 단, humanerd-style "먼저 다 쓰고 검토 후 publish" 워크플로와 충돌할 수 있음

**추천: Option A.** Quartz 한 곳만 고치면 모든 source의 draft가 안전해짐.

## Fix 적용 후 검증

### 1. dry-run build

```bash
cd ~/.drewgent/humanerd-site
npx quartz build 2>&1 | grep -E "Found|Filtered"
# Found 63 input files
# Filtered out N files    ← N이 status: draft 파일 수와 일치해야
```

### 2. public/에 draft HTML 부재 확인

```bash
for src in $(grep -l "^status: draft$" ~/.drewgent/memories/insights/*.md); do
  base=$(basename "$src" .md)
  [ -f "public/insights/${base}.html" ] && echo "STILL LEAKING: $base"
done
# (출력 없음 = 정상)
```

### 3. deploy 및 live site 확인

```bash
wrangler pages deploy public/ --project-name=humanerd-site

# live site
for url in $(grep -l "^status: draft$" ~/.drewgent/memories/insights/*.md | \
             xargs -I{} basename {} .md); do
  code=$(curl -s -o /dev/null -w "%{http_code}" "https://humanerd.kr/insights/$url")
  echo "$url: $code"  # 404 = 안전
done
```

## 운영 시 자동화

### content-pipeline에서 작성 후 verification 단계 추가

```python
# Phase 4-6 (kanban_complete) 직전
import subprocess
result = subprocess.run(
    ["grep", "-l", "^status: draft$", draft_file],
    capture_output=True, text=True
)
if result.returncode == 0:
    # draft임을 명시 — review gate 통과 전까지 자동 deploy trigger 방지
    # 옵션: fswatch가 draft 파일 무시하도록 ignorePatterns 추가 (단, vault 안에서 일반 editing은 가능)
    pass
```

### fswatch에서 draft 변경 무시 (advanced)

```bash
# fswatch가 draft 파일도 감지해서 quartz build를 트리거하지만, build 후
# draft는 filter에 의해 public/에서 빠지므로 결과는 안전. 단, build 시간 낭비.
# 큰 draft pool이 있을 때만 고려.
```

## 흔한 변형 — 다른 키를 쓰는 경우

| Frontmatter 키 | Fix |
|---|---|
| `status: draft` | Option A (CustomRemoveDrafts) |
| `publish: false` | Option A의 조건문에 `fm.publish === false \|\| fm.publish === "false"` 추가 |
| `published: false` | Option A에 `fm.published === false` 추가 |
| `visibility: draft` | Option A에 `fm.visibility === "draft"` 추가 |
| `state: wip` (work in progress) | Option A에 `fm.state === "wip"` 추가 |
| `kanban: in_progress` | 별도 처리 — Quartz filter는 content용, kanban 메타는 별도 |

## Pitfalls

### 1. `filters` array에 plugin 추가 안 됨 (inline 방식의 함정)

inline CustomRemoveDrafts 방식을 쓸 때 실수:
```typescript
// Wrong
filters: [Plugin.RemoveDrafts(), CustomRemoveDrafts]  // 둘 다 있으면 draft 두 번 체크

// Right
filters: [CustomRemoveDrafts]  // 하나만 — Custom이 RemoveDrafts를 포함
```

**별도 파일 방식 (Option A, 추천)을 쓰면 이 함정이 사라짐** — `RemoveDraftsHumanerd`가 export에서 unique하므로 중복 import 자체가 컴파일 에러로 잡힘.

### 2. `draft: true`인데 `status: publish`인 파일 — filter는 통과

Filter는 `draft: true` 또는 `status: draft` 중 하나만 봐도 통과. 둘 다 필요한 경우:

```typescript
const draftFlag = (
  fm.draft === true || fm.draft === "true" ||
  fm.status === "draft" || fm.status === "Draft"
)
// 통과 조건: !draftFlag
// 즉, draft가 아니면 통과. status: publish + draft: true → 여전히 막힘
// (보수적 — 의도된 동작)
```

### 3. `tags: [draft]` 같은 태그 기반 draft는 안 잡힘

Quartz는 `tags`를 별개 메타로 처리. `tags: [draft]`인 published 글은 정상 publish됨. 위 fix는 frontmatter의 scalar key만 체크.

### 4. fswatch의 vault 변경 감지 후 즉시 build/deploy

`status: draft`를 `status: publish`로 바꾸면:
1. fswatch 5초 debounce
2. quartz build (filter 통과 → public/에 HTML 생성)
3. wrangler deploy (~3-5초)
4. humanerd.kr에 라이브 (~1-2분)

즉, status: publish로 바꾸는 순간 draft가 나감. 검토는 **변경 직전**에 완료해야.

## Pitfalls (2026-06-02 추가)

### 5. **Wikilink는 EXCLUDE 후에도 inline으로 보임** (subtle, 자주 빠짐)

EXCLUDE된 file은 `public/`에 HTML이 안 생성됨. 하지만 **다른 file에 박힌 wikilink는 그대로 inline으로 렌더링됨**. 예: homepage에 `[[blog/2026-05-23-gemini-cli-shutdown|2026-05-23 — Gemini CLI shutdown]]`이 있으면, 그 article이 EXCLUDE되어도 homepage는 그 wikilink를 broken link로 표시함.

**증상 (2026-06-02 발견)**: humanerd.kr homepage의 Blog 섹션에 4개 broken wikilink가 그대로 보였음. 각각 direct URL은 404지만 homepage에서는 link text로 살아있음. 사용자 입장에서 "콘텐트 파이프라인 거치지 않은 article이 안 보이게" 요구 위배.

**해결**: EXCLUDE된 file을 가리키는 wikilink는 **호스트 file에서 수동으로 제거**해야 함. 자동 정리 도구 없음. 권장:

1. EXCLUDE list를 build log에서 추출
2. vault 전체에서 그 list를 가리키는 wikilink 검색 (`rg "\[\[" vault/`)
3. 호스트 file에서 wikilink 제거 또는 comment-out
4. 또는 monthly log에 link를 옮기고 homepage에는 monthly log + index만 표시

### 6. **`status: publish` (단수) naming convention 위반**

Quartz plugin이 인식하는 state: `published`, `polished`, `draft`, `in_review`, `archived`. **단수형 `publish`는 어떤 case에도 매칭 안 됨** → unknown status로 default-draft strict 모드에서 EXCLUDE.

`status: publish`로 쓰면 의도와 정반대로 "라이브 안 됨"이 됨. 흔한 실수 (영어 동사 base form).

**해결**: 항상 `published` (과거 분사) 사용. lint rule:

```bash
# 6/1 incident 후 check
rg "^status: publish$" vault/ -l   # 0건이어야 정상
```

### 7. **state machine은 list가 아니라 transition이다**

`includeStatus: ["polished", "published"]`, `excludeStatus: ["draft", "in_review", "archived"]` 라는 list만으로는 부족. Drewgent humanerd 5-state machine:

```
draft (작성)            →  EXCLUDE (404)
    ↓  human 검토 + frontmatter status: published
published (발행)        →  INCLUDE (200, humanerd.kr 라이브)
    ↓
polished (윤문 완료)    →  INCLUDE (200)
    ↓  재검토
in_review (재검토 중)   →  EXCLUDE (404)
    ↓
archived (보관)         →  EXCLUDE (404)
```

전이 규칙:
- `draft → published` (human 검토 완료) ✅
- `draft → polished` (LLM 자동 윤문) ✅
- `polished → published` (human 최종 확인) ✅
- `published → in_review` (재검토) ✅
- `in_review → published` or `archived` ✅
- `published → archived` (보관) ✅
- **draft skip → published (검토 없이 발행) — **명시적 사용자가 요청할 때만** (default: draft)

이 전이는 `Option D`의 transformer plugin에서 자동 enforce 안 됨. cron job이나 humanerd manual edit에서만 발동. 자동 lint를 원하면 별도 script.

### 8. **state field는 `status` 하나 — `published: true/false` 사용 안 함**

일부 humanerd article은 `published: true` (boolean) 또는 `published_date: YYYY-MM-DD`를 쓰지만, canonical state field는 `status` 하나. 둘 다 쓰면 plugin이 `status`만 본다 (Option D design).

```yaml
# CORRECT (canonical, state machine friendly)
status: published

# WRONG (단순 boolean — state machine 위배)
published: true

# 같이 쓰면 OK (둘 다 정보 제공)
status: published
publish_date: 2026-06-02
```

## Default-draft strict 운영 노트 (2026-06-02)

**Hardening 효과**:
- 새 article 작성 시 status field 안 박으면 → 자동 404
- 따라서 content-pipeline cron이 `status: draft`로 자동 생성 + humanerd가 검토 후 `status: published` 명시 변경이 **default workflow**가 됨
- 실수로 검토 없이 라이브 노출되는 사고 원천 차단

**부수 효과 (양날의 검)**:
- 기존 vault에 status field 없는 정상 article이 6개 (5/23~5/26 자동 생성) 있었음 → 모두 default-draft로 404 처리. 일괄 `status: published` 추가 script 필요.
- 새 state 추가 시 (e.g. `status: needs_review`) plugin code 수정 안 하고도 draft로 처리됨 → 의도된 동작이지만 naming convention 준수 권장

**Recovery 절차** (status field가 없는 정상 article 일괄 처리):

```python
# scripts/add_status_published.py
import re
from pathlib import Path

def add_status_published(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return "MISSING_FM"
    fm = m.group(1)
    if re.search(r"^status:", fm, re.MULTILINE):
        return "SKIP"  # already set
    lines = fm.split("\n")
    new_lines = []
    inserted = False
    for line in lines:
        new_lines.append(line)
        if not inserted and line.startswith("title:"):
            new_lines.append("status: published")
            inserted = True
    if not inserted:
        new_lines.insert(0, "status: published")
    new_fm = "\n".join(new_lines)
    new_text = text[:m.start(1)] + new_fm + text[m.end(1):]
    path.write_text(new_text, encoding="utf-8")
    return "OK"
```

`drewgent-content-status-enforcement` skill의 recovery procedure 참조.

## Related

- [[skills/content-pipeline/SKILL]] — content-pipeline skill (Phase 3에서 status: draft 작성)
- [[skills/humanerd-site]] — humanerd-site 운영 skill
- [[skills/humanerd-content-status-enforcement]] — agent self-apply 규칙 (status field 자동 enforce)
- [[skills/site-spec-audit]] — humanerd.kr 감사 (agent-readiness / well-known 등 점검)
- [[skills/filesystem-truth-audit]] — "docs Done ≠ reality" 검증 패턴
- [[P3-sensors/gateway/drewgent-architecture-dataflow]] — Quartz build → wrangler deploy 흐름
