---
title: project-restructure
name: project-restructure
domain: software-development
type: skill
description: Large-scale codebase refactoring and integration across Cloudflare Workers projects — discovery, master data consolidation, controller splitting, LLM utility unification, and NAS/local workspace merging
tags: [refactoring, integration, architecture, cloudflare-workers]
created: 2026-06-11
updated: 2026-06-11
links:
  - "[[P0-brainstem/brain/rules]]"
related_skills:
  - "codebase-consolidation"
  - "codebase-refactoring"
---

# Project Restructure & Codebase Integration

Class-level skill for large-scale refactoring, integrating separate codebases, and consolidating duplicated logic across a Cloudflare Workers project.

## When to Use
- User says "통합해야 해", "리팩토링", "구조 파악", "다시 설계"
- You discover duplicated code/patterns across 3+ files
- Two or more separate codebases need merging (workspace copy + NAS original)
- Monolithic worker.ts needs splitting into controllers/routes

## Discovery Phase

**Do not start refactoring until the user confirms you understand the full picture.**

1. **Map all source locations**: Check all mounts (SynologyDrive, SMB `/Volumes/`, local workspace)
2. **Compare versions**: `diff -rq` between copies — identify what exists only in each
3. **List ALL routes**: `grep -n "url.pathname ===" worker.ts`
4. **List ALL controller exports**: `grep "^export async function" src/controllers/*.ts`
5. **Find ALL LLM callers**: `grep -rn "api.deepseek\\|integrate.api.nvidia\\|DEEPSEEK_API_KEY\\|NVIDIA_NIM_KEY" src/`
6. **Read architecture and design docs**: `ARCHITECTURE.md`, `DESIGN_REFERENCE.md`, `DESIGN_GUIDE.md`, `plans/*.md`, `AGENTS.md`. The DESIGN docs specify CSS variables, spacing, ohang classes — skipping these guarantees a visual mismatch.
7. **Create AGENTS.md first if missing**: Before any restructuring, propose an AGENTS.md at project root. It defines the target structure, file naming, and search table. Get user approval on the AGENTS.md before touching any code. See `references/agents-dot-md-template.md`.

## Integration Pattern

When merging two codebases:
1. Copy unique files from source to target
2. `diff -rq` to verify no conflicts
3. Fix import paths (relative paths differ between locations)
4. Add missing type definitions (Env interface, config files)
5. Test each endpoint after changes

## Domain-Based Folder Structure

**Recommended target layout for CF Workers + SPA projects**:

```
src/
├── user/           계정/인증/프로필/기록
├── saju/           사주 계산/분석 엔진
├── report/         리포트 생성 + LLM 프롬프트
├── payment/        결제 검증/연동
├── db/             D1 쿼리/스키마/마이그레이션
├── api/            Hono 라우트 (thin layer + 미들웨어)
├── ui/             Svelte SPA 프론트엔드
├── config/         환경 설정
└── utils/          공통 유틸
```

### File Naming Convention (verb-noun.kebab-case)

```
동사-명사.kebab-case.ts
예: get-daewoon.ts, verify-payment.ts, oauth-naver.ts
```

**Rules**:
- File name starts with a verb (get, verify, generate, calculate, resolve, map, save, delete, load, manage)
- Followed by a noun that identifies the entity
- kebab-case only (no snake_case, no PascalCase)
- No file is named after its implementation role (controller, service, handler, util) — the domain folder says that

### Why domain-based beats implementation-based

| Before (implementation-based) | After (domain-based) |
|---|---|
| `controllers/payment.ts` | `payment/verify-payment.ts`, `payment/portone-korean.ts` |
| `views/PaymentView.js` | `ui/routes/page-payment.svelte` |
| `engine/types.ts` | `saju/types.ts` |

In implementation-based, you need to know what layer something is (controller/view/engine) before you can find it. In domain-based, you just need to know WHAT domain it belongs to (payment/saju/user).

### Splitting Monolithic Files with Barrel Re-Export

Monolithic controller files should be split into domain files while maintaining backward compatibility via the **barrel re-export pattern**:

1. Identify the natural verb-noun pairs in the file
2. Create one file per pair: `sign-in.ts`, `oauth-naver.ts`, `oauth-google.ts`, `manage-profile.ts`
3. Each file exports one or two closely related functions
4. **Keep the original file as a barrel re-export**: `export { handleNaverAuth } from './oauth-naver'`
5. Importers continue to use the old path — no cascading changes needed
6. Later, migration to direct imports can happen incrementally

**Barrel re-export pattern:**
```typescript
// Before (monolith): src/user/auth-controller.ts — 345 lines
export async function handleNaverAuth(request, env, url) { ... }
export async function handleNaverCallback(request, env, url) { ... }
// ... 8 more exports ...

// After (barrel): src/user/auth-controller.ts — 5 lines
export { handleNaverAuth, handleNaverCallback } from './oauth-naver';
export { handleGoogleAuth, handleGoogleCallback } from './oauth-google';
export { handleDevLogin, handleRegister, handleLogin } from './sign-in';
export { handleMe, handleLogout, handleProfileUpdate } from './manage-profile';
```

Route files continue to `import { handleNaverAuth } from '../user/auth-controller'` — unchanged.

**Used in m-log-v2 (2026-06-15):** 7 monolithic controllers totalling 3,955 lines split into 20+ domain files. Zero import path changes. See `references/m-log-v2-barrel-split-audit-20260615.md`.

### Parallel Delegation for Controller Splitting

For large refactoring across many files, delegate splits to subagents in parallel waves:

**Wave 1 — independent splits first:**
- Files with zero shared dependencies (saju, auth, db queries) can be split simultaneously
- Each subagent receives: exact source file, target file list with exports, all import paths to update

**Wave 2 — dependent splits after consolidation:**
- Files sharing duplicated code (report controllers) need a consolidation pass first
- Create shared utility modules → THEN delegate the splits
- Each subagent must be told about the new shared modules in their context

**Critical context to include in every split task:**
- Exact functions to extract (by line number and export name)
- Target file names and paths
- Which imports stay local vs get replaced with shared utils
- The barrel re-export instruction (DO NOT delete original file)
- Verification step (`npx tsc --noEmit`)
- For each shared function to import instead of keeping inline, state the EXACT import path and options

**This eliminates the spec-review loop** — when instructions are this detailed, the subagent produces correct output on the first attempt.

**⚠️ CRITICAL PITFALL: Subagents change call flow during splits.**

Even when told "do NOT change behavior, only move code," subagents will sometimes rewrite function internals or change which functions get called. Real example from 2026-06-15:

- Source file `report-controller.ts` had `handleGenerateFreeLogReport` calling `generateAIReportContent()`
- Subagent split the file and changed the call to `callLLMJson()` directly (different token budget, different NVIDIA key list)
- The original `generateAIReportContent` function was kept in the new file but was no longer used by its only caller
- This was caught only during manual audit — neither TypeScript nor build tools flagged it

**Detection (post-split audit):**
```bash
# 1. Check that every function still has its original callers
#    Compare exports from the barrel vs. actual usage in the new files
grep -rn "async function" src/report/ --include="*.ts" | grep -v "node_modules"

# 2. Trace each handler's LLM call path — does it go through the expected wrapper?
#    Look for cases where a refactored handler calls an LLM function directly
#    instead of going through the shared wrapper
grep -rn "callLLMJson\|callReportLLM\|callDeepSeek" src/report/ --include="*.ts" | grep -v "node_modules"

# 3. Remove unused imports that the subagent left behind
#    (they import from shared util but no longer use it in function bodies)
```

**Prevention:**
1. After each split wave, spot-check ONE handler per file: trace its complete call path
2. Verify that shared utility imports are actually USED in function bodies, not just imported
3. Check that the original call chain (e.g., handler → `generateAIReportContent` → `callDeepSeek`/`callNvidiaWithFallback`) is preserved, not shortcut

**Reference:** See `references/m-log-v2-barrel-split-audit-20260615.md` for the full audit transcript.

#### Multi-Phase Execution with Pre-Consolidation

Before any subagent split, run a **Phase 0: consolidation pass** to extract shared inline code into utility modules. This prevents splitting from propagating duplicates:

1. Identify duplicated function patterns across the controllers (`callLLMJson`, `hasRequiredKeys`, `sanitizeReportOutput`, `polishReport`, `callNvidiaWithFallback`)
2. Create shared modules (`src/utils/report-format.ts`, `src/utils/llm-report.ts`)
3. Parameterize differences (log prefix, system prompt key injection, sanitize flag) via options objects
4. Keep the original files unchanged during this phase — the shared module is purely additive
5. Only then delegate the splits, telling each subagent to import from the new shared module instead of defining inline

**Evidence:** In the 2026-06-15 m-log-v2 split, this pattern reduced 5 duplicated function definitions across 3 files to 2 shared modules. Without it, each split agent would have propagated the duplication into 5+ new files.

## Frontend Integration

When replacing or merging frontend codebases (e.g. old monolithic SPA → new component-based architecture):

1. **Read design system first**: Check `DESIGN_REFERENCE.md`, `DESIGN_GUIDE.md` for CSS variables, spacing, ohang classes. See `references/design-system-m-log.md`.
2. **Compare entry points**: `diff -q public/app/index.html frontend/app/index.html` — note differences in CSS/JS paths
2. **Fix CSS import paths**: New frontend may use unresolved aliases like `@theme/variables.css` → replace with correct relative path `../shared/theme/variables.css`
3. **Verify JS import chains**: Check ALL files in the new frontend's import tree. The new frontend may use absolute paths (`/app/shared/core/auth.js`) which resolve correctly at runtime but need `sync:local` to copy shared packages.
4. **Check Router routes**: New component-based frontends often use a hash-based Router. Confirm ALL route paths (`'#/report-ai': ReportAiView`) are registered.
5. **Re-apply custom modifications**: After overwriting, re-add project-specific changes (login modal, dev-login, etc.) that got lost.
6. **Storage migration check**: If you changed localStorage→sessionStorage earlier, verify ALL consumers (Router, views, AuthManager, service worker) use the new storage. One missed reference causes silent blank-screen bugs.
7. **Test navigation flow**: Click through every navigation link in the app — sidebar links, report cards, dashboard buttons. Hash routes that don't match Router registrations result in silent blank views.

### SPA → MPA Migration

For apps that don't need client-side routing (no persistent state across pages, no offline requirements, SEO matters), prefer **Multi-Page App (MPA) over SPA**. Each page is a standalone HTML file with its own JS/CSS.

**Rationale**: If every page transition reloads data from the server anyway, there's no benefit to keeping JS state in memory. SPA overhead (Router, client-side state, hash URLs) adds complexity without value.

#### Vite Multi-Entry MPA Setup

```js
// vite.config.js — one entry per page
import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import { resolve } from 'path'

export default defineConfig({
  root: 'entries',                 // HTML entry files in entries/
  plugins: [svelte()],
  build: {
    outDir: resolve(__dirname, '../../public/ui-dist'),
    rollupOptions: {
      input: {
        input: resolve(__dirname, 'entries/input.html'),
        dashboard: resolve(__dirname, 'entries/dashboard.html'),
        payment: resolve(__dirname, 'entries/payment.html'),
      },
    },
  },
})
```

Each entry HTML file directly imports and mounts the page:

```html
<!-- entries/dashboard.html -->
<script type="module">
  import { mount } from 'svelte'
  import Page from '../src/pages/DashboardPage.svelte'
  mount(Page, { target: document.getElementById('app') })
</script>
```

#### MPA Directory Structure

```
src/ui/
├── entries/                    ← HTML entries (one per page)
│   ├── input.html
│   ├── dashboard.html
│   ├── payment.html
│   ├── compare.html
│   └── report/
│       ├── desire.html
│       ├── comprehensive.html
│       └── dating.html
├── src/
│   ├── pages/                  ← Svelte page components
│   │   ├── InputPage.svelte
│   │   ├── DashboardPage.svelte
│   │   └── report/
│   │       ├── Comprehensive.svelte
│   │       └── Dating.svelte
│   └── lib/
│       ├── api.ts              ← shared API client
│       └── components/
│           ├── AppHeader.svelte ← shared header + nav
│           └── AppFooter.svelte
└── vite.config.js
```

#### No Router Component

MPA uses `<a href="/dashboard/">` — no Router.svelte, no App.svelte, no hash-based navigation. Each HTML entry mounts one page component directly.

#### Shared Layout (AppShell) for MPA

When converting from SPA (where a single `AppShell.js` wraps all views) to MPA, the shared layout (header, sidebar, mobile nav, footer) is LOST — each page becomes content-only. You must explicitly create an `AppShell.svelte` and include it in every page.

```svelte
{#page/DashboardPage.svelte}
<script>
  import AppShell from '../lib/AppShell.svelte'
  // ...page logic
</script>

<AppShell active="dashboard">
  <main class="dashboard-content">
    <!-- page-specific content here -->
  </main>
</AppShell>
```

The AppShell component (NOT a Svelte layout — that's SPA thinking) is a regular Svelte component that accepts an `active` prop for nav highlighting and renders its content via `{@render children()}`:

```svelte
{#lib/AppShell.svelte}
<script lang="ts">
  let { children, active = '' }: { children: any, active?: string } = $props()
  // Nav links use active prop to highlight current page
</script>

<header class="header">...</header>
<aside class="sidebar">
  <a href="/input.html" class:active={active === 'input'}>Input</a>
  <a href="/dashboard.html" class:active={active === 'dashboard'}>Dashboard</a>
</aside>
{@render children()}
<nav class="mobile-bottom-nav">...</nav>
<footer class="footer">...</footer>
```

**Pattern**: Every page file has the same three-line template:
1. Import AppShell
2. `<AppShell active="xxx">`
3. Page content
4. `</AppShell>`

No Router, no App.svelte, no top-level mounting component. Each HTML entry directly mounts its page component.

**Svelte 5 `{@render children()}` note**: In Svelte 5, children are passed as a render function via `$props()`:
```svelte
<script>
  let { children } = $props()
</script>
{@render children()}
```
This replaces Svelte 4's `<slot>`. The children snippet is automatically created when content is nested inside the component tag. Using `let { children }: { children: any }` in TypeScript works but loses type safety — you can type it as a Snippet:
```typescript
import type { Snippet } from 'svelte'
let { children }: { children: Snippet } = $props()
```

**Dev server with `concurrently`**:

```json
{
  "scripts": {
    "dev": "concurrently -k \"wrangler dev\" \"cd src/ui && vite\"",
    "dev:ui": "cd src/ui && vite",
    "build:ui": "cd src/ui && vite build && cd ../.. && for f in input dashboard payment compare; do mkdir -p public/$f && cp public/ui-dist/$f.html public/$f/index.html; done"
  }
}
```

Vite dev server (port 5173) serves entries with HMR, proxying `/api` to wrangler (port 8787).

#### Wrangler Dev ASSETS Binding Issue

In `wrangler dev`, the ASSETS binding does NOT serve files by explicit path (`/input.html` → 307 redirect instead of 200). Only directory URLs (`/input/` → serves `public/input/index.html`) work reliably.

**Fix**: Copy MPA build output to `public/{page}/index.html` pattern:
```bash
mkdir -p public/input && cp public/ui-dist/input.html public/input/index.html
```

Then in worker.ts, redirect `.html` URLs to directory URLs:
```ts
const MPA_ROUTES = {
  '/input.html': '/input/',
  '/dashboard.html': '/dashboard/',
}
const redirect = MPA_ROUTES[url.pathname]
if (redirect) return Response.redirect(new URL(redirect, url.origin).toString(), 301)
```

The build:ui script handles this automatically with the `for f in ...` loop.

#### Build Output + ASSETS Deployment

```
public/
├── input/index.html         ← MPA page (copied from ui-dist/)
├── dashboard/index.html
├── payment/index.html
├── ui-dist/                 ← Vite build staging
│   ├── input.html
│   ├── assets/*.js, *.css
│   └── report/
├── assets/                  ← logos + MPA JS/CSS
│   ├── m-log_logo.png
│   ├── dashboard-xxx.js
│   └── dashboard-xxx.css
├── app/                     ← old SPA (removed when MPA is stable)
└── index.html               ← landing page

## Systematic Code Deletion (grep → rm → patch → verify)

Use this workflow to remove a module/feature entirely:

1. **Full grep scan**: `grep -rl "FeatureName\|feature-key\|FEATURE_CONSTANT" --include="*.ts" --include="*.js" --include="*.css" --include="*.html" src/ public/ | grep -v node_modules | sort`
2. **Categorize hits**: Directories to delete entirely, files to patch, comments-only
3. **Delete directories first**: `rm -rf src/feature/ public/feature/`
4. **Delete standalone files**: `rm -f public/app/js/views/FeatureView.js`
5. **Patch remaining files one by one**: Remove imports, routes, CSS classes, nav links
6. **Final verification**: Run the grep again — should return empty
7. **Test**: Build/dev to confirm nothing broke

**Rules**:
- Delete directories/files BEFORE patching imports (patches that reference deleted files will error, which confirms the dependency is gone)
- Do NOT delete old files if they're still referenced by production code — copy first, switch worker.ts later
- CSS classes and HTML comments count: grep every file type, not just TS/JS

## Multi-Phase Kanban Decomposition

For large restructuring, decompose into kanban tasks. Each phase must be independently revertible (old code still works while new structure builds alongside).

### Standard 4-Phase Template

1. **Phase 1: Structure + File Migration** — Create domain dirs, copy files to new locations, update import paths. NO behavior changes. Keep old files in place for production compatibility.
2. **Phase 2: Framework Upgrade** — Hono routes, middleware, worker.ts switch. Router goes from if/else chain (232 lines) to thin dispatch (36 lines). Controller function bodies stay identical.
3. **Phase 3: Security** — HTTP-only session cookies, Zod validation on API inputs, rate limiting, secrets moved from wrangler.jsonc to `wrangler secret put`.
4. **Phase 4: Frontend** — Svelte/Vite project bootstrapped in src/ui/, component migration, CSS consolidation. Old public/app/ stays operational.

### Phase Boundaries
- Each phase has a CLEAR before/after state that's independently testable
- Phase boundary test = the app runs identically before and after the phase
- File BODY changes only in Phases 1+2; BEHAVIOR changes in Phases 3+4
- Old directories are NEVER deleted until Phase 4 worker.ts switch is confirmed

### Concrete Phase Deliverables (from m-log-v2 session)
- Phase 1: 51 files moved across 9 domain directories, imports updated. Old src/{engine,analysis,controllers,data}/ untouched.
- Phase 2: worker.ts 232→36 lines. 6 route files, 4 middleware files. Hono + Zod installed.
- Phase 3: HttpOnly cookie flags fixed. Zod schemas on POST /api/analyze and /api/iljin. guard-*.ts middleware skeletons.

## AGENTS.md as Project Map (Phase 0 — Do This First)

**User preference signal**: The user WILL reject a restructuring that doesn't lead with an intuitive agent map. If you propose a structure and the user says "이전과 다를바 없어보이는데" or "직관적이야?", you skipped this step.

Before any code changes — BEFORE creating a single directory or moving a single file — create or update AGENTS.md at the project root. This is the FIRST deliverable, not a nice-to-have. Present it to the user for approval before touching any code.

### Structure Requirements for Agent-Findability

The AGENTS.md must be structured so that an AI agent can find any file by SEARCHING for the keyword it expects. Not by knowing the architecture, not by guessing the layer:

```
| 검색어 | 파일 |
|---|---|
| 결제 검증 | src/payment/verify-payment.ts |
| 로그인/인증 | src/user/sign-in.ts |
| 대운 조회 | src/saju/get-daewoon.ts |
```

**Rules**:
- Each row = the exact term an agent would type into `search_files` or `grep`
- File paths use verb-noun.kebab-case so the filename itself is searchable
- Include "아직 없음" annotations for planned files so agents don't search fruitlessly
- Include a "현재 상태" section marking completed/in-progress/pending phases so agents know what exists vs planned
- Include a "다가올 리팩토링" section listing planned splits (e.g. `auth-controller.ts → sign-in.ts + oauth-*.ts`)

### What Makes a Structure "Agent-Findable" vs "Architect-Correct"

| Architect-Correct (bad) | Agent-Findable (good) |
|---|---|
| `controllers/payment.ts` | `payment/verify-payment.ts` |
| `views/PaymentView.js` | `ui/routes/page-payment.svelte` |
| `engine/types.ts` | `saju/types.ts` |
| Role-based grouping (controller, view, model) | Domain-based grouping (payment, user, saju) |
| File named after WHAT IT IS (PaymentView) | File named after WHAT IT DOES (verify-payment) |

**Test**: If an agent searching for "verify payment" would land on the wrong file, restructure.

### Multi-Pass Approval Workflow

1. First pass: propose the top-level directories and naming convention
2. Let the user reject/correct (they WILL have opinions about what's intuitive)
3. Build the search table as the concrete artifact
4. Only after AGENTS.md is approved, start creating directories and moving files

See `references/agents-dot-md-template.md` for the template.

## Refactoring Sequence

1. **Dead code removal**: Search zero-reference files, remove unused config keys
2. **External API first**: Before building custom calculations, check if the external API (PDC calculator) already provides the data. User explicitly said "PDC에서 가져오는 결과를 대입하면 돼" — don't reimplement what's already computed.
3. **Master data creation**: Single JSON source of truth, all consumers import it
4. **Worker → Controller split**: Route dispatch only in worker.ts (50-200 lines)
5. **Shared utility consolidation**: LLM callers into `src/utils/llm.ts`

## LLM Integration

```
src/utils/llm.ts — single source
callLLMJson(env, systemPrompt, userContent):
  1. DeepSeek (primary)
  2. NVIDIA NIM key 1 → key 2 → key 3 (28s timeout each)
  3. Throw if all exhausted
```

## User Preferences (CRITICAL)
- No commit without review: stage, show git status, get approval
- Verify each step: npm run dev + curl test + show results
- One thing at a time: one logical change → test → show → next
- Understand before act: read architecture docs first
- No quick workarounds: identify root cause, present options, discuss
- Communicate in Korean for architecture discussions
- **Never discuss deployment during active development**: While restructuring or page-converting, DO NOT mention secrets, `wrangler secret put`, DNS, production config, or deployment steps. The user interprets this as noise and reacts negatively ("아잇, 배포는 다 끝나고 얘기하고"). Secrets and deployment checklists belong in a separate section that's only presented when (a) all code work is complete AND (b) the user explicitly asks about deployment.
- **"딸깍 뾰로롱 금지"** — The user explicitly said this phrase. It means: no quick half-assed work, no placeholders, no mock data, no "일단 구조만 잡고 디자인은 나중에". Every page you deliver must be COMPLETE — matching the original in functionality AND visual design. If you're tempted to put a `<p class="placeholder">`, DON'T. Ship nothing instead of shipping broken.
- **Read design docs BEFORE restructuring**: Not after, not during. `DESIGN_REFERENCE.md`, `DESIGN_GUIDE.md`, `ARCHITECTURE.md`, `AGENTS.md` must be read and understood before the first file is moved. The user will say "처음으로 돌아가서 기획된 문서를 보고도 그런 말이 나온다니" if you skip this step.
- **Provoke review early**: Before creating a new frontend, before restructuring a page, present the PLAN first. A one-paragraph description of what you'll do, which files you'll touch, what the result will look like. If the user says "이해했어" you can proceed. If they say anything else, you haven't understood yet.

## 🛑 CARDINAL RULE: Framework Swap ≠ Content Rewrite

**This is the single most important principle in the entire skill.** The user will fire you (figuratively or literally) if you violate it.

When the user agrees to a framework migration (e.g. Vanilla JS → Svelte, SPA → MPA), the agreement is to change the FRAMEWORK, NOT the content:

| ✅ Framework swap | ❌ Content rewrite |
|---|---|
| Same CSS variables (`var(--bg-deep-space)`) | New hardcoded colors (`#080c12`) |
| Same component hierarchy | Flattened/simplified components |
| Same data flow | Mock data or placeholders |
| Same UX patterns | New interaction patterns |
| Same visual output | Visibly different page |

**The user's words**: "svelte로 바꾸는 것도 맞는데, 프레임워크를 바꾸는거지 내용을 바꾸는게 아니라고."

**How to detect you're about to violate this**:
- "일단 구조만 잡고 디자인은 나중에" → ❌ You're about to create a visual regression
- "기능은 동일한데 CSS를 안 옮겼어요" → ❌ You're about to ship without CSS
- "플레이스홀더지만 API는 연결됐습니다" → ❌ You're about to ship incomplete pages
- "Svelte로 처음부터 다시 짜는 게 더 깔끔할 것 같아서요" → ❌ You're about to throw away existing UI

**What to do instead**:
1. Keep the EXISTING frontend code (`public/app/`) completely untouched during backend restructuring
2. When you DO create a new frontend, start by copying the EXISTING CSS variables and component styles FIRST
3. Build one page at a time, comparing visually with the original
4. Never deploy placeholder/mock pages
5. If the old frontend must keep running during migration, don't touch it AT ALL — not even dead code removal

### Catastrophe Recovery: When You've Gone Wrong

If you've created a new frontend that the user rejects (different design, missing features, placeholders), the fastest recovery is:

```bash
# 1. DELETE the new frontend entirely
rm -rf src/ui/ public/ui-dist/

# 2. RESTORE the original frontend from backup
rm -rf public/app/
cp -r <backup-source>/public/app public/app/

# 3. VERIFY original is intact
diff -rq public/app/ <backup-source>/public/app/
# → Should show only intentionally-deleted files (Quintax, Just5, etc.)

# 4. CLEAN up MPA build artifacts
rm -f public/input/ public/dashboard/ public/payment/ public/compare/ public/report/
rm -f public/index.html public/landing.html
```

**Cost**: This loses ALL frontend migration progress. The alternative (patching the new frontend to match the old one) takes longer and still leaves the user unhappy with the delay. Cut losses fast.

**This is the single most important rule in this skill.** When restructuring a project that already has a working UI, the UI must remain 100% visually identical before and after the restructuring. Any deviation (different colors, different layout, missing elements, placeholder content) is a failure.

### Why This is Non-Negotiable

The user's existing UI has been iterated on, tested, and approved through their design process. It uses their design system (CSS variables, specific components, specific colors, dark mode, light mode, responsive breakpoints, Japanese/Korean font stacks, etc.). When you restructure:

- **CSS variables disappear**: You copy the JS files but write new CSS with hardcoded colors. The result looks completely different.
- **Components get simplified**: Complex UIs (sinsal grids, fortune timelines, desire reports) get replaced by `<p class="placeholder">`. This signals "I didn't prioritize this" to the user.
- **Login/auth flow breaks**: The old SPA depends on specific localStorage keys, API response shapes, and DOM events that exist nowhere in the new code.
- **Payments break**: PortOne SDK integration depends on specific callback patterns and DOM IDs.

**Result**: The user sees a worse product and loses confidence in the entire restructuring effort, including the parts that are correctly done (backend structure, dead code removal, secrets).

### What TO Do with Frontend Code During Restructuring

| ✅ DO | ❌ DON'T |
|---|---|
| Leave frontend code (`public/app/`, `public/css/`) completely untouched | Create a new frontend framework (Svelte, React, Vue) |
| Copy existing HTML/CSS unchanged to new locations | Rewrite CSS using hardcoded colors |
| Update import paths in existing JS files | Add new build tools (Vite, bundler) for frontend |
| Add AGENTS.md references for frontend files | Replace working components with placeholders |
| Only touch frontend files when removing dead code (Quintax, Just5) | Change the visual design or UX flow |

### Exception: When a Full Frontend Rewrite IS the Task

If the user explicitly asks for a new frontend ("UX가 구식이다", "프레임워크 갈아타자", "SPA → MPA 전환"), then:
1. Confirm the visual design must match the old one exactly
2. Copy the EXISTING CSS variables and component styles FIRST
3. Build one page at a time, comparing visually with the original
4. Never deploy placeholder/mock pages

### Detection: How to Know You're About to Violate This Rule

If you hear yourself saying any of these, STOP:
- "일단 구조만 잡고 디자인은 나중에" ❌
- "기능은 동일한데 CSS를 안 옮겼어요" ❌
- "플레이스홀더지만 API는 연결됐습니다" ❌
- "Svelte로 처음부터 다시 짜는 게 더 깔끔할 것 같아서요" ❌

The user's project is NOT a greenfield. Every placeholder is a visible regression.

## Pitfalls
- SynologyDrive symlink corruption: fix with `rm .bin/wrangler && ln -s`
- Duplicate wrangler dev: `pkill -f wrangler; rm -rf .wrangler/state/v3/d1/`
- TypeScript env types: use `(env as any).KEY` or update worker-configuration.d.ts
- JSON key order: use explicit arrays for ordered data, not Object.keys()
- **Patch tool + template literals**: The `patch` tool ESCAPES backticks in the replacement text (`` \` `` becomes `` \` ``) which breaks JavaScript. To add template literal strings to JS/TS files via patch, either:
  - Use `write_file` with the entire file content instead of `patch`
  - Or use plain string concatenation instead of template literals in the injected code
  - Or verify the result immediately with `node --check file.js`
- **Developer bypass masking auth issues**: A `developer_bypass_user` in `crypto.ts/getSessionPayload` auto-creates sessions in local dev mode, which masks logout/login issues. To test real auth flows:
  - Remove the bypass entirely (return null in the `isLocalOrDev` block)
  - Use `/api/auth/dev-login` for quick login instead
  - Test logout by verifying the Set-Cookie header clears the session
- **Router + storage consistency**: The Router's `handleRoute()` checks `localStorage.getItem('__SAJU_DATA__')` to determine the default route. If data was migrated to `sessionStorage`, the Router defaults to `#/input` instead of `#/dashboard`, causing the dashboard to appear empty after data entry.
- **Flat rename is not a restructuring**: Changing `controllers/payment.ts` → `routes/payment.ts` doesn't fix the underlying problem — files still mix multiple concerns. The key insight is: group by DOMAIN (payment, user, saju) not by LAYER (controller, view, engine). Always pair domain folds with verb-noun file naming and AGENTS.md.
- **Middleware silently lost during monolithic-to-route migration**: When moving from monolithic worker.ts (if/else chain) to Hono routes, middleware embedded inside the if/else blocks is silently dropped. In one session, `injectAnalysisReport` was called AFTER `handleAnalyze` inside the if/else block — it wasn't a `app.use()` middleware, so it didn't survive the route split.
  - **Detection**: `grep -E "^(async )?function " old-worker.ts | grep -v "fetch|handleCors"` to find ALL helper functions. Each must be migrated or intentionally dropped.
  - **Fix**: Wrap inline post-processing into the route handler or convert to explicit middleware.
- **Import cycles during incremental migration**: When copying files to a new structure while keeping old files, two copies of the same function exist. Worker.ts imports from old paths; route-*.ts imports from new paths. During transition:
  - Each function import must resolve to exactly ONE copy
  - Route files must NOT import from old paths (creates circular dependency risk)
  - Old worker.ts and old controllers must remain untouched until Hono switch
  - New route files import from the new domain copies
- **Pre-existing TypeScript errors outside wrangler context**: CF types (Env, D1Database, D1Result) are only resolved during `wrangler dev` / `wrangler build`. `tsc` or lint will show dozens of false-positive errors about missing types. These are NOT blockers. The only real signal is `wrangler dev` behavior.
- **Multiple JSON module copies cause path confusion**: If both `src/data/saju-constants.json` and `src/config/saju-constants.json` exist, some files import from the old path, some from the new. Fix: delete the old copy after confirming all consumers use the new path. Use `grep -rn "saju-constants" src/ --include="*.ts"` to find all consumers.
- **Hono wrapHandler bridge for CF Workers**: Cloudflare Workers handler functions have the signature `(request: Request, env: Env, url: URL, ctx?: any) → Promise<Response>`. Hono route handlers have `(c: Context) → Response`. To reuse existing handlers inside Hono routes without rewriting them:
  ```typescript
  function wrapHandler(fn: (req: Request, env: any, url: URL, ctx?: any) => Promise<Response>) {
    return async (c: Context) => {
      const request = c.req.raw
      const url = new URL(request.url)
      if (fn.length >= 4) {
        return fn(request, c.env, url, c.executionCtx)
      }
      return fn(request, c.env, url)
    }
  }
  // Usage: existing handlers work unchanged
  analyzeRoutes.post('/analyze', zValidator('json', schema), wrapHandler(handleAnalyze))
  ```
  The `fn.length >= 4` check handles handlers that accept 3 parameters vs 4 (`ctx`).
- **Hono + zValidator removes validated body from raw request**: When using `zValidator('json', schema)`, the validated JSON body is consumed from the request stream. The downstream handler (called via `wrapHandler`) receives a request whose body has already been read. If the wrapped handler calls `request.json()` again, it gets a `TypeError: Body has already been consumed`. Fix during migration: the route can pass validated data via `c.req.valid('json')` to the handler, or the handler should read from `c.req.valid()` instead of `request.json()`. For incremental migration where handlers still call `request.json()`, avoid `zValidator` on those routes until the handler is refactored to accept pre-parsed data.
- **ESM-only packages + Vite config loading**: `@sveltejs/vite-plugin-svelte` is ESM-only. When the root `package.json` lacks `"type": "module"`, esbuild fails with `ESM file cannot be loaded by require`. Fix: add `"type": "module"` to root `package.json`. Check if any existing `.js` file uses `require()` — those must be converted or removed.
- **Svelte plugin version + Vite compatibility**: `@sveltejs/vite-plugin-svelte@7` requires Vite 8. If the project has Vite 5, install `@sveltejs/vite-plugin-svelte@^4` instead. Installing a mismatched major version produces opaque errors (`Cannot read properties of undefined (reading 'config')` at `load-custom.js:27`).

- **data-theme missing on standalone HTML pages**: If the CSS uses `[data-theme="dark"]` selectors (common with design systems that support dark/light mode), standalone HTML pages (home-beta, landing pages, MPA entry HTML) will render in LIGHT MODE by default. The original SPA sets `data-theme` via JavaScript initialization (`App.restoreTheme()` in app.js), but standalone pages don't run this code. Fix: add `<script>document.documentElement.setAttribute('data-theme','dark');</script>` to the `<head>` of EVERY standalone HTML page. Run this grep to find all HTML files that need fixing: `grep -L "data-theme" public/**/*.html src/ui/entries/**/*.html`. Apply to both the source entries AND the old public/app/ pages.

- **wrangler dev SQLITE_BUSY on D1**: When wrangler dev crashes or is killed uncleanly, the local D1 SQLite database stays locked (`SQLITE_BUSY`). This prevents the next `wrangler dev` from starting. Fix: kill any stale wrangler processes and clear the D1 state:
  ```bash
  pkill -f wrangler
  rm -rf .wrangler/state/v3/d1/
  ```
  This drops local test data (schema is recreated from migrations on next start). To preserve data, run `wrangler d1 execute --local --command=".dump" > db-backup.sql` before stopping dev, then `wrangler d1 execute --local --file=db-backup.sql` to restore.

- **Report page mock data detection**: Report pages (Desire, Ai, Comprehensive, Dating) are often written by subagents with hardcoded mock content instead of real API calls. Specifically, look for:
  - `generateReportContent()` functions that produce static HTML strings
  - SWOT analysis with "분석 완료" or "▸ 분석 완료" text
  - Loading simulations with `setInterval`/`loadingTexts` that never actually call the API
  - `reportHtml` assigned from a template literal instead of from a fetch response
  
  **Fix**: Replace the mock generator with a real API call and use a shared formatting module:
  ```typescript
  import { parseCommentaryText } from '../../lib/formatDesireReport'
  
  async function generate() {
    const res = await fetch('/api/report', { method: 'POST', ... })
    const data = await res.json()
    const narrative = data.data?.narrative || data.narrative || ''
    reportHtml = narrative ? parseCommentaryText(narrative) : '<p>내용 없음</p>'
  }
  ```
  
  **Detection script**: `grep -rl "분석 완료\|generateReportContent\|swot-item\|loadingTexts\[" src/ui/src/pages/report/ --include="*.svelte"`
- **Worker catch-all order for dual SPA serving**: During incremental frontend migration, try the Svelte build path first, fall back to old ASSETS SPA. Without this order, the old SPA's 404-catcher always intercepts before the new SPA gets a chance.
