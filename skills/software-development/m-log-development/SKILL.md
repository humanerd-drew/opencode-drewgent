---
name: m-log-development
title: M-LOG Development
description: Development patterns for the M-LOG (사주 분석) project — CF Workers MPA with Hono backend, Svelte 5 pages, PortOne payment, D1 database, LLM reports, ontology-driven analysis.
version: 2.5.0
trigger: "2026-06-14 Parallel page creation via delegate_task, directory URL pattern for ASSETS, AppShell children() snippet pattern, CSS variables enforcement, no-mock-data requirement"
provenance:
  session: "2026-06-13 m-log-v2 restructuring (continued 2026-06-14)"
  decision: "Domain 디렉토리 + 동사-명사.kebab-case.ts + AGENTS.md = 에이전트가 검색 키워드로 바로 찾는 구조"
  learnings:
    - "AGENTS.md 템플릿을 references/에 보관해서 재사용 가능"
    - "Svelte 5 {#each}+{@const} 호환성 — @const는 #each 내부에서만"
    - "Hono post-response middleware 패턴 (await next() 먼저)"
    - "vite-plugin-svelte v7은 Vite 8 필요 — v3 사용"
    - "Svelte 5 mount() API, on:click vs onclick 비호환"
    - "Dead code detection: 'has real logic, never routed' trap"
    - "사용자 신호: 배포/운영 얘기는 active dev 중에 금지"
created: 2026-06-13
updated: 2026-06-14
platforms: [macos]
environments: [local, cloudflare]
metadata:
  hermes:
    tags: [m-log, payment, d1, cloudflare-workers, portone, saju, hono, svelte]
    related_skills: [software-development/cf-workers-integration, software-development/incremental-refactoring]
---

# M-LOG Development Guide

Class-level patterns and pitfalls for the M-LOG SPA.

> **⚠️ 2026-06-13 restructuring**: Codebase moved from flat `controllers/engine/analysis/data` layout to domain-based directories. AGENTS.md at project root is the primary navigation tool. This skill covers both current patterns and legacy migration notes.

## Navigation (ALWAYS read first)

**`AGENTS.md`** at project root — contains full file lookup table by keyword. Every session starts here. See `references/agents-md-template.md` for the template pattern reusable in other projects.

## Architecture (Current — MPA)

```
m-log-v2/
├── src/
│   ├── api/             Hono routes + middleware (7 route files, 4 guards)
│   ├── saju/            Saju engine (24 files: types, atoms, ui-atoms, engine, analysis)
│   ├── user/            Auth, history, myeongsik controllers
│   ├── report/          Report generation controllers (3 files + prompts/)
│   ├── payment/         Payment verification
│   ├── db/              D1 queries
│   ├── config/          Constants, JSON data, ontology
│   ├── utils/           Crypto, CORS, email, LLM
│   ├── ui/              Svelte 5 + Vite MPA
│   └── worker.ts        CF Workers entry (36 lines — redirect + Hono app.fetch)
├── public/
│   ├── app/             Legacy SPA (old vanilla JS, preserved for backward compat)
│   └── ui-dist/         Svelte MPA build output (per-page HTML + code-split JS)
├── AGENTS.md            Project navigation map (READ FIRST every session)
└── tsconfig.json        TypeScript config
```

### Key decisions

| Decision | Rationale |
|----------|-----------|
| Domain-based dirs (user/, saju/, etc.) | 검색 키워드로 파일을 바로 찾음. `controllers/`와 같은 what-it-is 이름 대신 what-it-does 이름 |
| AGENTS.md | 모든 에이전트 세션의 첫 번째 참조. 파일 맵, 규칙, 자주 찾는 것 포함 |
| Hono thin routes | route-*.ts는 검증+위임만. 비즈니스 로직은 각 도메인 폴더 |
| Zod validation | analyze/iljin 라우트에 zValidator 적용. 에러 시 자동 400 응답 |
| HMAC cookie sessions (not KV) | 기존 signSession/verifySession이 HMAC-SHA256 서명으로 충분. KV는 overhead만 증가 |
| **Svelte 5 MPA (not SPA, not SvelteKit)** | **2026-06-14 pivot.** MPA = 각 페이지 독립 HTML (`/input.html`, `/dashboard.html`). Router/layout 불필요. 브라우저 기본 `<a>` 네비게이션. 페이지별 JS code-split (3~8KB + 공유 40KB) |
| Vite multi-entry | `rollupOptions.input`에 각 entry HTML 등록. `vite build`가 코드 스플리팅 자동 처리 |
| `{@render children()}` | Svelte 5 snippet 패턴으로 header/footer를 각 페이지에 include |
| `"type": "module"` in package.json | @sveltejs/vite-plugin-svelte가 ESM-only이므로 필수 |

### UI structure (MPA)

```
src/ui/
├── entries/                    ← HTML entry points (one per page)
│   ├── input.html              ← mounts InputPage.svelte
│   ├── dashboard.html          ← mounts DashboardPage.svelte
│   ├── payment.html            ← mounts PaymentPage.svelte
│   └── ... (more pages)
├── src/
│   ├── pages/                  ← Svelte page components
│   │   ├── InputPage.svelte
│   │   ├── DashboardPage.svelte
│   │   ├── PaymentPage.svelte
│   │   └── report/
│   │       ├── Desire.svelte
│   │       └── ...
│   └── lib/
│       ├── api.ts              ← typed API client
│       ├── AppShell.svelte     ← shared layout (header + sidebar + mobile nav + footer)
│       │                        Uses Svelte 5 children snippet: {@render children()}
│       │                        Accepts active prop for nav link highlighting
│       └── stores/             ← (empty, ready for future use)
├── vite.config.js              ← multi-entry via rollupOptions.input
└── tsconfig.json
```

### AppShell pattern

Every page wraps its content in `<AppShell active="input">`:

```svelte
<AppShell active="input">
  <!-- page content here -->
</AppShell>
```

The AppShell provides:
- Fixed header with logo + menu toggle
- Desktop sidebar (left) with nav links
- Mobile bottom nav bar
- History sidebar (right, loads from API)
- Overlays for sidebar/history

AppShell usses Svelte 5's `{@render children()}` snippet pattern:
```svelte
<script>
  let { active = '', children } = $props()
</script>
<header>...</header>
<aside class="sidebar">...</aside>
<main class="app-content">{@render children()}</main>
<nav class="mobile-nav">...</nav>
```

The `active` prop highlights the current page's nav link.

**Deleted (SPA remnants):** `App.svelte`, `Router.svelte`, `AppLayout.svelte` (split into AppHeader+AppFooter), `main.ts`, SPA `index.html`, `routes/` directory.

### How pages work

```html
<!-- entries/dashboard.html — each page is a standalone HTML file -->
<script type="module">
  import { mount } from 'svelte'
  import Page from '../src/pages/DashboardPage.svelte'
  mount(Page, { target: document.getElementById('app') })
</script>
```

```svelte
<!-- pages/DashboardPage.svelte — includes header/footer, no router -->
<script>
  import AppHeader from '../lib/components/AppHeader.svelte'
  import AppFooter from '../lib/components/AppFooter.svelte'
  import { API } from '../lib/api'
</script>

<AppHeader active="dashboard" />
<main class="main-content">
  <!-- page-specific content -->
</main>
<AppFooter />
```

Navigation via `<a href="/input.html">` — browser native. `active` prop tells AppHeader which nav link to highlight.

### Parallel page creation with delegate_task

For creating multiple MPA pages simultaneously, use `delegate_task` with separate goals:

```
delegate_task(task 1: LandingPage)    → creates entry HTML + Svelte page
delegate_task(task 2: DashboardPage)  → reads original View + creates Svelte page
```

**Best practices:**
- Each task gets the FULL design context: CSS variables list, entry HTML template, original file paths
- Specify exact file paths for both source (original) and destination (new MPA)
- Include the build command (`cd src/ui && npx vite build`) as the final step
- Use toolset `["file", "terminal", "search"]` — the subagent needs search to explore the original codebase
- After all tasks complete, run one final build to verify no conflicts

**When NOT to delegate:**
- Small changes (1-2 files) — do it yourself
- Tasks that modify the same file — serial only
- Framework config changes (vite.config.js, package.json) — do it yourself to avoid conflicts

| 검색어 | Current path | Notes |
|--------|-------------|-------|
| 분석 API | `src/api/route-analyze.ts` | POST /api/analyze with Zod + analysis injection |
| 인증 API | `src/api/route-auth.ts` | 9 auth endpoints via Hono wrapping old controller |
| 사주 계산 | `src/saju/` | calculate-engine, get-compatibility, etc. |
| 리포트 생성 | `src/report/*-controller.ts` | comprehensive, dating, free-log |
| 결제 검증 | `src/payment/payment-controller.ts` | PortOne backend verification |
| LLM 호출 | `src/utils/llm.ts` | DeepSeek, Nvidia fallback |
| DB 쿼리 | `src/db/queries.ts` | 7 tables |
| **MPA entry** | `src/ui/entries/{page}.html` | Add new page HTML here |
| **Svelte page** | `src/ui/src/pages/{Page}.svelte` | Page component with header+footer |
| 공유 컴포넌트 | `src/ui/src/lib/components/` | AppHeader, AppFooter |
| Vite config | `src/ui/vite.config.js` | Add entries to rollupOptions.input |
| 프론트엔드 빌드 | `npm run build:ui` | → `public/ui-dist/` |
| 프론트엔드 개발 | `npm run dev:ui` | localhost:5173, /api → wrangler proxy |

## Page Conversion Workflow (Old SPA → Svelte MPA)

When converting a vanilla JS View to a Svelte MPA page:

1. **Read the old View** — `public/app/js/views/{Name}View.js`. Understand its data sources (localStorage keys, API endpoints), template structure, event handlers.
2. **Create entry HTML** — `src/ui/entries/{page}.html` with `<script type="module">` mounting the Svelte component.
3. **Create the Svelte page** — `src/ui/src/pages/{Name}Page.svelte`. Include `AppHeader` + `AppFooter`. Use `$state()` for reactive data, `$effect()` for initialization.
4. **Register in vite.config.js** — add to `rollupOptions.input` using `resolve(__dirname, ...)` — absolute paths required due to `root: 'entries'`.
5. **Add nav link** — add to `AppHeader.svelte`'s `navLinks` array.
6. **Update server routing** — `src/api/index.ts` catch-all already handles `/{page}.html` → `/ui-dist/{page}.html`.
7. **Build and verify** — `npm run build:ui`.

### Common conversion pattern for report pages

All report pages follow the same structure:
```svelte
<script lang="ts">
  import AppHeader from '../lib/components/AppHeader.svelte'
  import AppFooter from '../lib/components/AppFooter.svelte'
  import { API } from '../lib/api'

  let sajuData = $state(null)
  let report = $state('')
  let loading = $state(false)
  let isPaid = $state(false)

  $effect(() => {
    // 1. Load sajuData from localStorage
    // 2. Check purchase status from __PURCHASED_REPORTS__
    // 3. If paid and data exists, optionally auto-generate
  })

  async function generate() {
    loading = true
    // Call API endpoint, set report text
    loading = false
  }
</script>
```

## Hono Middleware

### Post-response middleware pattern (analysis injection)

`injectAnalysisReport` is a **post-response** middleware that calls `await next()` first, then modifies `c.res`. Register AFTER the handler:

```ts
analyzeRoutes.post('/analyze',
  zValidator('json', schema),  // 1. validate before handler
  wrapHandler(handleAnalyze),  // 2. run handler
  injectAnalysisReport         // 3. modify response after
)
```

Use dynamic `import()` for lazy-loading heavy modules: `const { analyze } = await import('../saju/analyze-engine')` avoids loading JSON imports at startup.

### CORS middleware

Use `hono/cors` with explicit origin validation. Never use `cors({ origin: '*' })` in production.

## Payment Integration (PortOne V2 + KG이니시스)

### Channel Configuration

```
naverpay → KG이니시스 (EASY_PAY + NAVERPAY)
kakaopay → 카카오페이 (EASY_PAY + KAKAOPAY)
card     → 한국결제네트웍스 (CARD)
```

### requestPayment() params

```javascript
PortOne.requestPayment({
    storeId,
    channelKey,
    paymentId: `MLOG-${Date.now()}-${random}`,
    orderName,
    totalAmount: 3800,    // integer
    currency: 'KRW',
    customer: {
        email, fullName,
        phoneNumber,       // KG이니시스 REQUIRED
    },
    redirectUrl: window.location.href,  // REQUIRED for mobile
    payMethod: 'CARD' | 'EASY_PAY',
    easyPay: { easyPayProvider: 'NAVERPAY' | 'KAKAOPAY' },  // EASY_PAY only
});
```

### Purchase Key Model (CRITICAL — do not change)

Payment is per-**myeongsik** (birth chart), NOT per-account.

```
Fingerprint = {year}_{month}_{day}_{hour}_{min}_{gender}_{isLunar}_{location}_{name}
Normal key  = {reportType}_{fingerprint}
Dating key  = {reportType}_{fingerprintA}_vs_{fingerprintB}
```

**NEVER use flat keys like `purchased.desire = true`.** That's per-account and wrong.

### Backend Verification

```
POST /api/payment/verify
  body: { type, fingerprint, txId, paymentId, amount, payerPhone?, anonymousId? }
  → PortOne GET https://api.portone.io/payments/{paymentId}
    Authorization: PortOne {PORTONE_API_SECRET}
  → Verify status === 'PAID'
  → Save to D1 purchases table
```

### 인증마크

KG이니시스 인증마크는 footer + payment 페이지 내부 두 곳에 배치.
Desktop: footer 표시됨. Mobile: footer 미노출되므로 PaymentView 하단에 직접 포함.

## D1 Migration Management

### NAS Sync

로컬 `migrations/`가 NAS 버전과 자주 불일치:
`~/Library/CloudStorage/SynologyDrive-Log-Project/m-log/migrations/`

**항상 remote history 확인 후 migration 추가:**
```bash
npx wrangler d1 execute m_log_db --remote --command "SELECT name FROM d1_migrations ORDER BY name"
```

**Pitfall:** Remote에 local에 없는 migration이 있을 수 있음. NAS에서 sync 후 적용.
**Pitfall:** Migration 번호 충돌 가능 (두 파일이 같은 prefix 사용). NAS에서 sync 필수.

## Report Pipeline

3-stage: 프롬프트 빌드 → LLM JSON 생성 → 윤문.

Reports:
- `comprehensive-report.ts` → 4 ontology layers + synthesis
- `dating-report.ts` → analyze/compatibility/divorce modes
- `report.ts` → free log report

**Key rule**: flat string values in "라벨: 내용" format. No nested objects in middleware-level keys.

## Legacy Notes (Pre-2026-06-13 paths — for reading old views)

The old vanilla JS SPA is still at `public/app/` and will be migrated to Svelte gradually.

| Legacy path | Note |
|-------------|------|
| `public/app/js/views/*.js` | Old views, being replaced by src/ui/src/routes/*.svelte |
| `public/app/js/components/` | Old components |
| `public/app/js/core/` | Old Router, Component base class |
| `public/app/css/` | Old CSS — CSS variables moved to src/ui/src/styles/ |
| `public/app/shared/` | Old shared services — migrated to src/ui/src/lib/ |

### Legacy PaymentView

The old `PaymentView.js` contains the full PortOne checkout flow. The new `PaymentPage.svelte` reproduces this with Svelte 5 reactive state. Keep the old view until all routes are migrated.

### Legacy Report Views

Report views (ReportDesireView, ReportAiView, etc.) generate LLM-based analysis with streaming. Server-sent events not yet implemented — views wait for complete JSON response.

## CSS / Layer Ordering

### The Dual Variables Problem

Two CSS variable files exist with different z-index values. The app-specific `variables.css` is **never linked** in index.html → only the shared theme loads → z-index conflict between FAB and drawer.

**Fix:** `z-override.css` loaded LAST with explicit `!important` values.

### Correct Layer Order

```
z-index  | Element
---------|-------
100      | restricted-overlay
3000     | menu sidebar drawer
2000     | FAB / legend toggle
1500     | mobile bottom nav
5000+    | modals, loading, toasts
```

## Login UI

### Principle: Additive, Not Replacement

Keep existing sidebar auth buttons (Naver/Google) as-is. Add a `[로그인]` header button that opens a modal with both social login and email/password. Do NOT replace sidebar buttons.

## CRITICAL LESSON: DESIGN_REFERENCE.md FIRST

**Every UI task must start by reading `DESIGN_REFERENCE.md` at `~/m-log/DESIGN_REFERENCE.md`.** The original m-log project at `~/m-log/` IS the reference — not your imagination.

### CSS rules from DESIGN_REFERENCE.md

- ✅ CSS variables only (`var(--bg-deep-space)`, `var(--bg-surface)`, `var(--text-primary)`, `var(--sys-primary)`)
- ❌ NO hardcoded colors (`#080c12`, `#11161f`, `#1e2530` etc.)
- ✅ Ohang elements use `.char.wood/fire/earth/metal/water` classes
- ✅ Font: `var(--font-mono)` + uppercase labels
- ✅ Spacing: 4px based system (`var(--space-xs)` ~ `var(--space-2xl)`)
- ✅ CSS import order: `variables.css → base.css → layout.css → components/* → utility.css`
- ✅ Dark/light mode via `[data-theme="dark"]` — never add new color values outside variables.css

### Framework conversion rule: change the framework, not the content

When converting from one framework to another (e.g. Vanilla JS → Svelte):

1. **Keep ALL functionality identical.** Every feature in the original must be in the new version before you ship it. No "I'll add it later" for features that existed in the original.
2. **Keep the design identical.** Use the original CSS files and variables. Don't create new styles unless the original doesn't have them.
3. **No mock data, no placeholders.** If you can't fully convert a page, don't ship it with mock content. Either state the gap upfront or don't ship the page yet.
4. **Test the navigation flow.** Landing → launcher → feature pages. Make sure the user can actually navigate between pages before polishing individual ones.

**Failure example (this session):** Svelte DashboardPage was shipped with placeholder tabs, empty timeline, and hardcoded colors instead of matching the original DashboardView's sinsal/desire/timeline/report-deck sections. User response: "대충 mock 데이터 박아놓고 했다고 하는거야?"

### User frustration signals (serious — act on these)

| Signal | Meaning |
|--------|---------|
| "처음으로 돌아가서 기획된 문서를 보고도 그런 말이 나온다니" | You didn't read existing design/planning docs. Stop, find and read them. |
| "솔직히 말하면 같은 소리 하지말고" | Stop prefacing statements with "honestly/sincerely". Just say it. |
| "대충 mock 데이터 박아놓고 했다고 하는거야?" | You shipped a placeholder instead of real implementation. Fix it. |
| "황당하다" | You've made a fundamental wrong assumption. Pivot immediately. |
| "멍청아" | You missed critical context that was already available. |
| "딸깍 뾰로롱을 원하지 않아" | You're doing quick half-assed work. Stop rushing. Take the time to do it properly ("제대로"). Ship real implementations, not stubs. |
| "같은 소리 하지말고" | Stop saying "honestly/sincerely/to be honest" — it's defensive and wastes time. Just state the fact. |

### Workflow rule

1. Before ANY UI/architecture work: `cat ~/m-log/DESIGN_REFERENCE.md 2>/dev/null || find ~/m-log -name "DESIGN*.md"` — find and read the design docs.
2. Check the original `~/m-log/public/app/` for the actual visual reference.
3. Use the existing CSS variables. NEVER hardcode colors.
4. Every page should match the original's visual quality — not just functional parity.

## User Preferences

### Answer-first format

결론/요약을 먼저, 상세는 그 다음에. CLI 환경에서 스크롤 강요 금지.

### During active development — NO deployment/operations talk

When the user is actively developing (restructuring, refactoring, adding features), **do not bring up deployment checklists, secrets setup, or "you need to do X before you can Y" operations talk.** This includes:
- `wrangler secret put` reminders
- Deployment prerequisites
- Production configuration concerns
- "You still need to..." lists

Only mention deployment/operations when the user explicitly asks about it ("배포 준비", "체크리스트", or asking to deploy).

**Signal phrase**: The user said "아잇, 배포는 아직 하지 말고. 문제점 해결부터 해." (June 2026) when deployment talk interrupted active restructuring work. If you get a similar annoyed response, pivot immediately to the code work at hand and drop all operations topics.

### Dev workflow (two terminals)

Development requires TWO separate processes:

```
터미널 1: npm run dev            → wrangler :8787  (API + old SPA backup)
터미널 2: cd src/ui && npx vite  → Vite :5173     (MPA + HMR, proxies /api -> wrangler)
```

Open `http://localhost:5173/input.html` for MPA pages with HMR during development. The Vite config proxies `/api/*` to wrangler at :8787.

For quick API testing: `http://localhost:8787/` serves the old SPA as fallback.

**Do NOT install `concurrently`** — the user explicitly rejected the combined-script approach after it was implemented and removed. Two-terminal workflow is the accepted pattern.

### During active development — NO deployment/operations talk

**Don't bring up deployment checklists, secrets setup, or "you need to do X before Y" during active development.** The user knows what they need to deploy. Focus on the code/architecture work they asked for. Deployment/operations talk only when they explicitly ask (배포 준비 or 체크리스트).

**Signal phrase**: The user said "아잇, 배포는 아직 하지 말고. 문제점 해결부터 해." when deployment talk interrupted active work. If you get a similar annoyed response, stop talking about operations and focus purely on the code/infrastructure work at hand.

## Pitfalls

### Dead code detection (Just5/Quintax pattern)

When cleaning up a feature that seems standalone:

1. **Search across ALL layers** — don't check just one directory. A feature may have:
   - Frontend component + route (old SPA views/)
   - Backend handler function (controller files)
   - API route registration (worker.ts or route-*.ts)
   - Standalone app (public/ subdirectory)
   - Data consumed by other features (report generation, dashboard)

2. **Trace the fallback chain**: If the feature's API always returned stubs (`{ success: true, data: {} }`), check that all consumers have `featureData?.field || fallbackData?.field || {}` fallbacks. If they do, the feature is dead code.

3. **The lean delete checklist** — Delete in this order, verifying at each step:
   1. Standalone apps/public directories → `rm -rf public/{feature}/`
   2. Frontend views/routes → delete .js files, remove from app.js
   3. API stubs → remove from route files
   4. Backend handler → remove the exported function (track brace depth for large functions)
   5. Consumer fallback references → replace `featureData?.x || fallback?.x` with just `fallback?.x`
   6. Verify with `grep -rl` — zero hits = clean

4. **Watch for the "has real logic, never routed" trap**: A function may have 500+ lines of real business logic but was NEVER connected to any route. That's still dead code. Don't be fooled by complexity.
**`write_file` OVERWRITES entire file.** Use `patch` for section-level edits. Accidentally truncating `app.js` to just imports crashes the SPA silently.

### ESM module cache-busting
Adding `?v=X.X.X` to singleton imports (Store, AuthManager) creates duplicate instances. Only version view classes.

### v3 @sveltejs/vite-plugin-svelte
v7 needs Vite 8. Install v3 for Vite 5 compat. Must use `--legacy-peer-deps`.

### Svelte 5 specific
- `ComponentType` removed → use `any` in route map
- `$state()` with props reference → use `typeof window` guard or `$derived`
- `mount()` API instead of `new App()`
- `{@const}` only valid inside `{#if}`, `{#each}`, `{#snippet}` etc. — NOT inside plain elements
- Cannot mix old (`on:click`) and new (`onclick`) event syntax in same component
- `let { children } = $props()` + `{@render children()}` for component children (Svelte 5 snippets)
- `onclick={(e) => { e.preventDefault(); ... }}` instead of `on:click|preventDefault`

### Cloudflare ASSETS single-directory limit
Can only serve from one directory. To serve both old and new SPA, rewrite URLs in Hono catch-all (`/app/` → `/ui-dist/`).
### wrangler dev ASSETS binding — directory URLs required

In `wrangler dev`, the ASSETS binding returns `307 Temporary Redirect` for any `.html` file request. **Does not happen in production** — it's a wrangler dev quirk.

**Solution**: Use directory-style URLs (`/input/` instead of `/input.html`). The Vite build outputs HTML files to `public/{page}.html`, then `npm run build:ui` moves them to `public/{page}/index.html`:

```bash
# build:ui script in package.json
cd src/ui && npx vite build
for p in input dashboard payment compare landing; do
  mkdir -p public/$p && mv public/$p.html public/$p/index.html
done
for p in desire desire-deep ai comprehensive dating; do
  mkdir -p public/report/$p && mv public/report/$p.html public/report/$p/index.html
done
```

The worker.ts redirects `.html` to directory URLs:
```ts
const pageMatch = url.pathname.match(/^\/(\w[\w-]*)\.html$/)
if (pageMatch) {
  return Response.redirect(new URL(`/${pageMatch[1]}/`, url.origin).toString(), 301)
}
```

This way both `.html` (backward compat) and directory URLs work in dev AND production.

## Related Skills

| Skill | Relationship |
|-------|-------------|
| `software-development/cf-worker-modular-architecture` | Overlapping — CF Worker layering patterns |
| `software-development/korean-payment-gateway` | Overlapping — Korean PG integration |
| `software-development/portone-payment-integration` | Overlapping — PortOne SDK |
| `software-development/m-log-payment` | Overlapping — M-LOG payment details |
| `software-development/m-log-restructure` | Absorbed into this skill (obsolete) |

## Reference Files

| File | Contents |
|------|----------|
| `references/mpa-migration-20260614.md` | Full MPA migration log — deleted files, Vite config, entry pattern, page pattern, server routing |
| `references/audit-pattern.md` | Content-based gap analysis methodology — how to compare original vs new framework correctly |
| `references/content-based-audit.md` | Feature-by-feature content comparison — detailed methodology |
