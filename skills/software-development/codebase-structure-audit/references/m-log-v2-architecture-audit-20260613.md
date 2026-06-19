# M-LOG v2 Architecture Audit — 2026-06-13

## Project Context

Cloudflare Workers SPA — Saju (사주) topology dashboard. Vanilla JS frontend, TypeScript backend stack.

## Repository Location

`~/m-log-v2/`

## Architecture Pattern Inventory Results

### Routing Strategy

**Backend** — Manual `if/else` in `src/worker.ts` (232 lines):
- 30+ sequential `if (url.pathname === ...)` blocks
- Cross-cutting concern: `injectAnalysisReport()` called inline in `/api/analyze` handler
- POST fallback redirect, root redirect, SPA fallback all in the same function

**Frontend** — Custom hash router in `public/app/js/core/Router.js` (93 lines):
- `window.addEventListener('hashchange', ...)` — reactive, but limited
- Default route logic: if `localStorage.__SAJU_DATA__` exists → `#/dashboard`, else `#/input`
- Routes registered in `public/app/js/app.js`:
  ```
  '/input' → InputView
  '/dashboard' → DashboardView
  '/quintax' → QuintaxView
  '/just5' → Just5View
  '/compare' → CompareView
  '/report-desire' → ReportDesireView
  '/report-ai' → ReportAiView
  '/report-luck' → ReportComprehensiveView (alias)
  '/payment' → PaymentView
  '/report-dating' → ReportDatingView
  '/report-desire-deep' → ReportDesireDeepView
  '/report-comprehensive' → ReportComprehensiveView
  ```

### State Management

- Primary: `localStorage` — `__SAJU_DATA__`, `__THEME__`, `__SAJU_ANONYMOUS_ID__`
- `Store` singleton in `public/app/shared/core/store.js` — custom pub/sub, logged-in user state
- Each View reads `localStorage` directly — no typed accessors, no validation

### Framework / Component Model

- Custom `Component` base class in `public/app/js/core/Component.js`
- Each view: `class DashboardView extends Component` with `init()`, `template()`, `events()`
- Template = raw HTML string from `template()` method
- Events = object mapping `'click #selector': 'methodName'`
- Manual `innerHTML` replacement on every render

### Build Tooling

**Frontend**: Zero build step — raw ESM modules served by Wrangler's `env.ASSETS.fetch()`
- `type="module"` imports resolve to individual files (no bundling)
- All imports use bare ESM paths like `import { X } from './core/Router.js'`
- Cache-busting via manual `?v=2.4.0` query params on CSS/JS

**Backend**: Wrangler compiles `src/worker.ts` automatically on `wrangler dev`/`wrangler deploy`

### CSS Architecture

- 20+ global CSS files, loaded via `<link>` in `index.html`:
  ```
  /app/shared/theme/variables.css
  /app/css/index.css
  /app/css/z-override.css
  /app/css/base.css
  /app/css/layout.css
  /app/css/utility.css
  /app/css/components/analysis.css
  /app/css/components/compare.css
  /app/css/components/elements.css
  /app/css/components/footer.css
  /app/css/components/form.css
  /app/css/components/history.css
  /app/css/components/home.css
  /app/css/components/legend.css
  /app/css/components/myeongsik.css
  /app/css/components/nav.css
  /app/css/components/restricted.css
  /app/css/components/sinsal.css
  /app/css/components/timeline.css
  /app/css/components/toast.css
  /app/css/components/wonguk.css
  /app/css/legal.css
  ```
- No CSS scoping — all global, potential selector conflicts
- Components use BEM-like class names but no enforcement
- Two theme variable sets (`data-theme="dark"` / `"light"`) via CSS custom properties

### Code Duplication Detected

- `public/app/shared/services/myeongsik-api.js` vs `public/app/shared/services/myeongsikApi.js` (different casing)
- `public/app/shared/hooks/use-myeongsik.js` vs `public/app/shared/hooks/useMyeongsik.js` (same difference)
- CSS: `public/app/shared/theme/` duplicates `public/app/css/components/*` patterns

### API Endpoints

```
POST   /api/analyze           → saju.ts (injects analysis report)
POST   /api/iljin              → saju.ts
GET    /api/locations           → saju.ts
*      /api/auth/* (9 routes)   → auth.ts (Naver/Google OAuth, email login, register, profile)
POST   /api/payment/verify     → payment.ts (PortOne V2)
GET    /api/payment/check      → payment.ts
GET    /api/history*            → history.ts
GET    /api/meongsik*|/myeongsik* → myeongsik.ts
POST   /api/report              → report.ts (DeepSeek-based)
POST   /api/report/generate     → report.ts (alias)
POST   /api/report/free-log     → report.ts (alias)
POST   /api/report/comprehensive → comprehensive-report.ts
POST   /api/dating/*            → dating-report.ts
POST   /api/just5/analyze      → stub (empty response)
```

### Engine Layers (Pure TS — no framework dependencies)

```
src/engine/          — 만세력 calculator (ohang atoms, compatibility, daewoon, saewoon, persona)
src/analysis/        — Analysis report engine
src/quintax/         — Quintax personality analysis
src/controllers/     — API route handlers
```

These layers are framework-independent and reusable regardless of frontend/backend choice.

## Maintenance Friction Summary

| Pain Point | Files Affected | Estimated Impact |
|-----------|---------------|-----------------|
| 20+ global CSS files | 22 CSS files | Style conflicts, dead rules |
| Manual DOM in 12 views | 12 views × avg 200+ lines | Bug-prone, hard to extend |
| localStorage as state | 4+ keys, read in every view | Sync bugs between views |
| Custom framework (Router + Component) | 2 core + 12 views + sub-components | Learning overhead, no ecosystem |
| No FE build step | All ESM imports unoptimized | ~50 HTTP requests, no HMR |
| Duplicate API service files | 4 files in shared/ vs views/ | Inconsistent error handling |
| 230-line if/else router in worker.ts | 1 file | Hard to add routes safely |

## Recommended Migration

Per `codebase-structure-audit` Step 6:

1. **Hono backend** — Replace worker.ts manual routing. Controllers unchanged. ~2h
2. **Svelte + Vite frontend** — New build output, one view at a time
3. **Incremental** — Old SPA serves as fallback during migration
