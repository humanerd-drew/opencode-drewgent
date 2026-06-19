---
title: humanerd-site
name: humanerd-site
description: humanerd.kr publishing pipeline — Quartz build, custom draft filter, Cloudflare Pages deploy via wrangler, fswatch LaunchAgent. 3-pillar URL model (Insights / Portfolio / Blog + Services).
type: document
space: growth
tags: [growth, quartz, obsidian, cloudflare, wrangler, humanerd-site]
created: 2026-05-20
updated: 2026-06-02
links:
  - "[[P4-cortex/growth/humanerd-site-url-mapping]]"
  - "[[P4-cortex/portfolio/drewgent]]"
  - "[[P4-cortex/portfolio/quartz-publishing]]"
  - "[[P2-hippocampus/kanban/KANBAN_INDEX]]"
  - "[[P3-sensors/skills/SKILL-INDEX]]"
  - "[[P0-brainstem/brain/rules]]"---





# humanerd.kr — Site Management Skill (3-pillar model, 2026-06-01)

Site is a Quartz 4 static site generated from Obsidian vault markdown files.
All source content lives in `~/.drewgent/` (Obsidian vault).
Build output deploys to Cloudflare Pages.

## 3-Pillar URL Model (2026-06-01)

humanerd.kr is structured around 3 content pillars + 2 utility sections:

| Pillar | 정의 | URL | vault source |
|---|---|---|---|
| **Insights** | 영구 essay, principle, concept | `/insights/[slug]/` | `P4-cortex/knowledge/` |
| **Portfolio** | 구체적 project 산출물 | `/portfolio/[slug]/` | `P4-cortex/portfolio/` |
| **Blog** | 선별된 field note, reviewed observation | `/blog/[year]/[slug]/` | `memories/insights/` |
| **Services** | 제품 detail page (별도 유지) | `/services/[slug]/` | humanerd-site 자체 native |
| **About** | Identity | `/about` | humanerd-site 자체 native |

핵심 구분: **Insights = "What I learned"**, **Portfolio = "What I built"**, **Blog = "What I noticed and refined"**. Raw monthly logs are private source material, not public content. hugh-kim.space 스타일 (7섹션)을 3-pillar로 단순화.

## Quick Commands

```bash
# Build site
cd ~/.drewgent/humanerd-site && npx quartz build

# Build + filter stats (should show "Filtered out N files")
cd ~/.drewgent/humanerd-site && npx quartz build 2>&1 | tail -8

# Local preview
cd ~/.drewgent/humanerd-site && npx wrangler pages dev public/

# Manual deploy (requires valid wrangler auth — see Troubleshooting)
cd ~/.drewgent/humanerd-site && npx wrangler pages deploy public/ --project-name=humanerd-site
```

## Site Architecture (3-pillar reorg, 2026-06-01)

```
~/.drewgent/
├── humanerd-site/                    ← Quartz repo (build tool)
│   ├── content/                      ← Symlinks to Obsidian vault
│   │   ├── index.md                  ← Site home (3-column layout)
│   │   ├── about.md                  ← About page
│   │   ├── insights/   → ../../P4-cortex/knowledge/    (영구 essay)
│   │   ├── portfolio/  → ../../P4-cortex/portfolio/   (project writeup)
│   │   ├── blog/       → ../../memories/insights/     (reviewed field notes)
│   │   ├── services/   (native — Drewgent, notion2web, SEO Harvester)
│   │   ├── landingpage/→ ../../landingpage/           (legacy)
│   │   ├── persona/    → ../../P1-limbic/persona/
│   │   ├── plans/      → ../../P4-cortex/plans/
│   │   ├── skills/     → ../../skills/
│   │   ├── scripts/    → ../../P4-cortex/scripts/
│   │   ├── growth/     → ../../P4-cortex/growth/      (legacy, ignore됨)
│   │   ├── lab/        → ../../P4-cortex/lab/         (legacy, ignore됨)
│   │   └── projects/   → ../../P4-cortex/projects/    (legacy, ignore됨)
│   │   # ⚠️ content/knowledge/ symlink은 삭제됨 (insights와 중복 → build 2배 발생 방지)
│   ├── quartz.config.ts
│   ├── quartz/plugins/filters/
│   │   └── humanerd-draft.ts         ← 커스텀 draft filter (status: draft 인식)
│   └── public/                       ← Build output (deploy this)
│
└── P0-brainstem/ ... P6-prefrontal/  ← Obsidian vault (source)
```

## Sitemap Structure

```
content/
├── index.md              → Site root (/) — 3-column: latest insights/portfolio/blog
├── about.md              → About (/about)
├── insights/             → 영구 essay
│   ├── index.md
│   └── *.md              → e.g. garry-tan-architecture, neurorfs-rules, opencrab-ontology
├── portfolio/            → 구체적 산출물
│   ├── index.md
│   └── *.md              → e.g. drewgent, quartz-publishing, seo-article-harvester
├── blog/                 → reviewed field note / article
│   ├── 2026/
│   │   └── {slug}.md     ← reviewed field note / article
│   └── index.md
├── services/             → 제품 detail page
│   ├── index.md
│   └── drewgent.md, notion2web.md, seo-harvester.md
└── ... (other legacy symlinks)
```

## Custom Draft Filter — DraftFilter (transformer, default-draft strict, 2026-06-02)

**문제**: Quartz 표준 `Plugin.RemoveDrafts()` 는 `frontmatter.draft === true` 만 체크. humanerd content-pipeline은 `frontmatter.status: draft` 로 마킹 → **draft가 그대로 public/에 build되어 publish됨**. 5/23~5/26 누적 4 article (claude-code-essence, flue-sandbox-agent, gemini-cli-shutdown, remove-ai-watermarks) + 5/30~6/1 누적 7 draft 모두 새어 나감.

**해결 (v1, 2026-06-01)**: `quartz/plugins/filters/humanerd-draft.ts` filter plugin — `draft === true` 와 `status === "draft"` 둘 다 체크. **default-include** (status field 없으면 통과).

**Hardening (v2, 2026-06-02)**: status field가 명시되지 않은 article도 자동 EXCLUDE (default-draft, strict). 모든 콘텐트는 pipeline을 거쳐서 publish 명시되어야 라이브. Plugin을 **filter → transformer**로 이동하여 FrontMatter parse 이후 status 검사.

```typescript
// quartz/plugins/transformers/draftFilter.ts
import { QuartzTransformerPlugin } from "../types"
import { slugTag } from "../../util/path"

export const DraftFilter = (opts?: {
  includeStatus?: string[]   // default: ["published", "polished"]
  excludeStatus?: string[]   // default: ["draft", "in_review", "archived"]
  domainExclude?: string[]   // default: ["draft"]
  defaultExclude?: boolean   // default: true (strict)
}): QuartzTransformerPlugin => ({
  name: "DraftFilter",
  transformEmit(ctx, file) {
    const fm = file.data.frontmatter
    if (!fm) {
      return opts?.defaultExclude !== false
        ? [null, { exclude: true, reason: "default-draft (no status field, strict)" }] as const
        : [ctx.buildTrie ? slugTag(file.slug) : null, null] as const
    }
    // ... checks includeStatus/excludeStatus/domainExclude
  },
})
```

**Plugin include list (live 노출):**
- `status: published` (and `Published`)
- `status: polished` (and `Polished`)

**Plugin exclude list (404):**
- `status: draft`, `in_review`, `archived`
- `status: publish` (단수) — **naming convention** 위배. plugin include에 매칭 안 됨
- `domain: draft`
- status field 없음 (default-draft strict)

**연결**:
1. `quartz/plugins/transformers/draftFilter.ts` 신규 작성 (transformer 위치)
2. `quartz.config.ts`: `transformers: [Plugin.FrontMatter(), DraftFilter({ defaultExclude: true }), ...]`
3. **검증**: `npx quartz build` 로그에 `[DraftFilter] EXCLUDE ...` 라인 N개 + `Filtered out N files`

**근본 해결**: content-pipeline cron이 `status: draft`로 자동 생성, humanerd가 검토 후 `status: published` 명시 변경. 명시되지 않은 article은 자동 EXCLUDE → 자동 publish 사고 원천 차단.

## ignorePatterns — Drop Candidates + Runtime Artifacts

`quartz.config.ts` 의 `ignorePatterns` 배열에 3그룹 (2026-06-01 reorg):

```typescript
ignorePatterns: [
  // 1. internal process docs (vault에는 유지, public에서는 제외) — 24개
  "growth/P0-brainstem-pilot-plan.md",
  "growth/stabilization_report.md",
  // ... (총 24개 — P-layer + lab/* internals)
  "lab/drewgent-architecture.md", "lab/qa-gate.md", "lab/index.md",
  
  // 2. glob patterns (symlink reorg 후 path resolution 대응)
  "**/laws-of-ux-wiki/**",         // 110+ 외부 wiki article
  "**/laws-of-ux-wiki/external-links/**",
  
  // 3. runtime state files (vault root에 우연히 들어간 .py, .json)
  "**/bus.py",
  "**/drewgent_hidden_state.json",
  "**/drewgent_knowledge.json",
  "**/growth_engine_sync.json",
  "**/harvester_sync_state.json",
]
```

**교훈**:
- `knowledge/laws-of-ux-wiki/**` 같은 fixed path는 symlink 타겟 변경 시 안 맞게 됨 → **glob (`**/...`) 사용 권장**
- `P4-cortex/knowledge/` 같은 vault 폴더에 runtime state file (bus.py, .json) 이 우연히 들어갈 수 있음 → build artifact에 새어 나옴. glob 으로 제외

## Content Authoring

### Creating a new page

1. Create `.md` file in appropriate section under `~/.drewgent/`
2. Add proper frontmatter:
   ```yaml
   ---
   title: Page Title
   tags: [section-tag]
   links: [[related-page]]  ← Connect to existing wiki nodes
   created: 2026-05-15
   updated: 2026-05-15
   ---
   ```
3. Run build: `cd ~/.drewgent/humanerd-site && npx quartz build`

### Content pipeline (trend → post)

1. Trend Harvester collects → `memories/insights/`
2. Author content → appropriate section (growth/, knowledge/, etc.)
3. Connect via wikilinks to existing nodes
4. Build + deploy

## Review Pipeline (Status State Machine)

Drewgent가 draft를 vault에 작성하면 humanerd가 Obsidian에서 검토 후 status 변경:

```
draft (작성)            →  plugin EXCLUDE (404)
    ↓  human 검토 + frontmatter status: published
published (발행)        →  plugin INCLUDE (200, humanerd.kr 라이브)
    ↓
polished (윤문 완료)    →  plugin INCLUDE (200)
    ↓
in_review (재검토)      →  plugin EXCLUDE (404)
    ↓
archived (보관)         →  plugin EXCLUDE (404)
```

**중요**: `status: publish` (단수) 는 plugin이 인식 안 함. 반드시 `published` 또는 `polished` 사용.

### Obsidian Review Workflow

1. `memories/insights/` folder 열기
2. `status: draft` 파일 찾기 (Dataview plugin으로 필터 가능)
3. 파일 열기 → 내용 확인
4. 수정 필요하면 직접 편집
5. 완료 시 frontmatter 수정:
   ```yaml
   status: published   # or polished
   publish_date: 2026-06-02
   ```

### Status State Tracking

| status | 의미 | Quartz publish |
|---------|------|---------------|
| `published` | 검토 완료, 라이브 | ✅ (200) |
| `polished` | 윤문 완료, 라이브 | ✅ (200) |
| `publish` (단수) | **잘못된 표기** — plugin이 매칭 안 함 | ❌ (404, default) |
| `draft` | 작성 중 / 검토 필요 | ❌ (404) |
| `in_review` | 재검토 중 | ❌ (404) |
| `archived` | 보류/삭제 | ❌ (404) |
| `domain: draft` | 도메인 단위 draft | ❌ (404) |
| (status field 없음) | 명시 안 됨 | ❌ (404, strict default-draft) |

## Build & Deploy Workflow

### Build
```bash
cd ~/.drewgent/humanerd-site
npx quartz build
# Output: public/ directory (~50MB, 2400+ files)
```

### Deploy to Cloudflare Pages

**Option A: Direct upload**
1. Go to https://dash.cloudflare.com → Pages
2. Create project or select existing
3. Drag `~/.drewgent/humanerd-site/public/` folder

**Option B: GitHub integration**
- Push `humanerd-site/` to GitHub
- Connect repo to Cloudflare Pages
- Auto-deploy on push

### Verify deployment
```bash
# Check sitemap
curl -s https://humanerd.kr/sitemap.xml | head -20

# Check robots
curl -s https://humanerd.kr/robots.txt
```

## Quartz Config Notes

Config: `~/.drewgent/humanerd-site/quartz.config.ts`

Key settings:
```typescript
pageTitle: "humanerd"          // Browser tab title
baseUrl: "humanerd.kr"         // Canonical URL
locale: "ko-KR"                // Korean locale
enableSPA: true                // Single page app
```

## Graph Integrity

All pages in the site are Obsidian vault files.
Every .md file must have:
- `title` in frontmatter
- `tags` in frontmatter
- `links` connecting to existing vault nodes

This ensures the site cluster appears in Obsidian graph view as a connected group.

## Troubleshooting

### Build fails — YAML frontmatter error
- `obsidian-vault-site-principle.md` 처럼 code block 안에 `links:` 예시가 있는 경우 gray-matter parser가 두 번째 `links:` 를 frontmatter의 일부로 오해. 해결: code block을 ` ```yaml\n---\n...\n---\n``` ` 으로 명시적 분리
- No tabs in YAML (use spaces)
- Special characters in description fields can cause issues

### Draft가 public/에 나옴 (workflow leak)
- `quartz.config.ts` line 156: `filters: [Plugin.RemoveDraftsHumanerd()]` 확인 (RemoveDrafts 아님)
- 빌드 로그에 `Filtered out N files` (N > 0) 확인
- vault의 draft 파일 frontmatter: `status: draft` (대소문자 무관, `toLowerCase()` 처리됨)

### Build counts 이상 (예: 47 → 155)
- **원인**: 같은 vault 폴더를 가리키는 중복 symlink (예: `insights` + `knowledge` 둘 다 `P4-cortex/knowledge` 가리킴)
- **해결**: `content/knowledge` symlink 삭제 (한쪽만 유지)

### Runtime state files (.py, .json) 가 public/에 나옴
- vault root에 우연히 들어간 `bus.py`, `drewgent_*.json` 등 → ignorePatterns에 `"**/bus.py"`, `"**/drewgent_*.json"` 추가
- 또는 vault root에서 다른 위치 (P3-sensors/state/) 로 이동

### wrangler OAuth token 403 (Authentication error)
- 증상: `wrangler pages deploy` → 403 on `/accounts/.../pages/projects/...`, `Failed to automatically retrieve account IDs`
- **원인**: OAuth token이 scope는 `pages:write` 있어도 project 자체 접근 권한 잃음 (token expiration 또는 revoked)
- **해결**:
  1. **권장**: `npx wrangler login` 실행 → OAuth 토큰 갱신 (interactive 필요)
  2. **대안**: Cloudflare Dashboard에서 API token 생성 (Pages:edit scope) → `CLOUDFLARE_API_TOKEN` env var에 설정
  3. `wrangler.toml`에 `account_id = "dc0199b6b6c27bc9bb2f3201d47cb643"` 명시 (project ID 자동 resolve)

### fswatch가 trigger 안 됨
- LaunchAgent 상태: `launchctl list | grep quartz-fswatch` (PID가 숫자면 정상, `-`면 stopped)
- 수동 restart: `launchctl unload ~/Library/LaunchAgents/com.drewgent.quartz-fswatch.plist && sleep 1 && launchctl load -w ~/Library/LaunchAgents/com.drewgent.quartz-fswatch.plist`
- vault 변경 후 5초 안에 deploy 안 됨 → `tail /Users/drew/Library/Logs/quartz-fswatch.log`

### Cloudflare Pages 안 업데이트
- Dashboard에서 deploy 상태 확인
- upload folder가 `public/` 내용물인지 `public/` 자체인지 확인 (직접 upload 시)
- fswatch가 마지막 deploy 시각 (`quartz-fswatch.log` 마지막 줄) — 5분+ stale이면 위의 wrangler auth 섹션 확인

## Site Verification (3-pillar URL 패턴)

```bash
# 4개 URL 패턴 검증
curl -sI https://humanerd.kr/insights/garry-tan-architecture | head -1   # 200
curl -sI https://humanerd.kr/portfolio/drewgent | head -1              # 200
curl -sI https://humanerd.kr/blog/2026-05 | head -1                     # 200
curl -sI https://humanerd.kr/services/drewgent | head -1                # 200

# draft가 404로 filter되었는지
curl -sI https://humanerd.kr/insights/2026-05-cc-switch-cli | head -1   # 404 (정상)

# 3-pillar homepage 검증
curl -s https://humanerd.kr | grep -cE "Insights|Portfolio|Blog"        # ≥ 3
```

## Related
- [[P3-sensors/skills/SKILL-INDEX]]
