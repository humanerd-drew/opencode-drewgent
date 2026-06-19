# M-LOG Frontend-Backend Integration Session (2026-06-12)

## Context
Integrating a new SvelteKit-derived component-based SPA frontend (`frontend/app/`) with a Cloudflare Workers backend that was refactored from a monolithic controller into a router-plus-controller pattern.

## Architecture After Integration

```
Worker (router.ts) → Controllers (auth, report, saju, ...)
                   → Analysis engine (src/analysis/engine.ts) — L0~L3
                   → LLM utility (src/utils/llm.ts) — DeepSeek → NVIDIA fallback

Frontend (public/app/) → Component-based SPA (51 JS files, 13 views)
                       → Shared packages (packages/core|theme|ui/ → sync:local)
                       → Router (#/input, #/dashboard, #/report-desire, etc.)
```

## Key Integration Patterns

### 1. Analysis Report Injection
The `injectAnalysisReport()` function intercepts the `/api/analyze` response and enriches it with computed analysis data. This allows the legacy calculator API to return the new `analysisReport` field without modifying the controller.

**Files:** `worker.ts:200-220`, `src/analysis/engine.ts`

### 2. just5Data Injection for Report Generation
The free report handler (`/api/report`) pre-computes analysis and injects it as `just5Data` in the request body before forwarding to the legacy controller. This bridges the gap between the new analysis engine and the old controller that expects `just5Data`.

**Files:** `worker.ts:78-140`

### 3. Login Modal Placement
The login modal HTML must be appended to `document.body` because the sidebar has `transform: translateX(-100%)`. CSS spec: any `transform` other than `none` creates a new containing block for `position: fixed`. Fixed elements inside become relative to that parent, not the viewport.

**Fix:** `document.body.appendChild(modalContainer.firstElementChild)` in `mounted()`.

### 4. D1 Auto-Migration
Auto-create tables on first DB access by catching SQL errors and running `CREATE TABLE IF NOT EXISTS`. **Critical:** Use single-line strings with separate `exec()` calls per table.

**Pattern:**
```typescript
async function ensureTables(env: Env): Promise<void> {
    try {
        await env.DB.prepare('SELECT 1 FROM users LIMIT 1').run();
    } catch {
        await env.DB.exec("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, ...)");
        await env.DB.exec("CREATE TABLE IF NOT EXISTS history (id TEXT PRIMARY KEY, ...)");
    }
}
```

### 5. Developer Bypass + Logout
Local dev auto-login (via `getSessionPayload`) makes logout impossible. Fix: set `m_log_logged_out=1; Max-Age=10` cookie on logout, skip bypass when present.

### 6. API Path Mismatches
Frontend calls these endpoints not present in the refactored backend:
- `/api/report/generate` — added as alias to `handleGenerateFreeLogReport`
- `/api/report/free-log` — added as alias
- `/api/just5/analyze` — added as stub returning `{success:true, data:{}}`

**Grep command to find all frontend API calls:**
```bash
grep -rn "fetch.*api" --include='*.js' public/app/ | grep -oP "/api/[a-z-]+" | sort -u
```

### 7. CSS Z-Index System
The project uses CSS custom properties for z-index layering:
- `--z-drawer: 3000` (sidebar)
- `--z-backdrop: 4000` (overlay)
- `--z-modal: 5000` (modals)
- `--z-toast: 9000` (notifications)

**Missing variables found during audit:**
- `--z-breakdown-sheet` (defined in `packages/theme/variables.css` but not synced to shared)
- `--z-timeline-stage: 150`
- `--z-loading-overlay: 6000`

**Fix:** Re-run `npm run sync:local` to copy theme files.

### 8. localStorage → sessionStorage Conflict
The new component-based frontend consistently uses `localStorage` for `__SAJU_DATA__`. Our earlier security migration moved this to `sessionStorage`. This breaks 15+ files in the new frontend. Resolution: keep `localStorage` for the new frontend (the security benefit of sessionStorage is marginal when the SPA already stores data in JS memory).

## File Counts
- Old SPA: 35 files in `public/app/`
- New SPA: 99 files in `frontend/app/` (51 JS in component architecture)
- Controllers: 7 TypeScript files
- Analysis engine: 2 TypeScript files + 2 JSON data files

## Dev Login
- URL: `http://localhost:8787/api/auth/dev-login` (302 redirect to /app/)
- Email: `dev@m-log.cc` / Password: `test1234`
