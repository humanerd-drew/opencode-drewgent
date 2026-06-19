# m-log Frontend Integration Reference

## Context
Merged a new component-based frontend (`frontend/app/`) into an existing Cloudflare Workers SPA (`public/app/`). The new frontend uses:
- Hash-based Router (`core/Router.js`) with declarative view registration
- Component architecture (`Component.js` base class with template/mounted/events lifecycle)
- Atomic design: atoms → molecules → organisms → layouts → views
- Shared packages from `packages/` copied via `sync:local` to `public/app/shared/`

## Key Files Changed

| File | Purpose |
|------|---------|
| `public/app/index.html` | Entry point — loads `js/app.js` (module) |
| `public/app/js/app.js` | Bootstrap — creates Router with 13 view registrations |
| `public/app/js/core/Router.js` | Hash-based router with view lifecycle |
| `public/app/js/core/Component.js` | Base class with template/mounted/events lifecycle |
| `public/app/js/components/layouts/AppShell.js` | Main layout — sidebar, history, auth, login modal |
| `public/app/css/index.css` | Main CSS — imports from `../shared/theme/` and `components/` |
| `worker.ts` | Backend — route dispatch + static asset serving |

## Common Fixes

### CSS @theme alias not resolving
The new frontend uses `@theme/variables.css` which doesn't resolve at runtime.
Fix: `@import url('@theme/variables.css')` → `@import url('../shared/theme/variables.css')`

### Template literal escaping in patch tool
When adding template literal strings to JS files via `patch`, the tool escapes backticks.
Fix: Use `write_file` for files with template literals, or verify with `node --check`.

### Developer bypass preventing auth testing
`crypto.ts` has a `developer_bypass_user` that auto-creates sessions in local dev.
Fix: Return `null` in the `isLocalOrDev` block to disable auto-login.

### localStorage vs sessionStorage
If data was migrated from localStorage to sessionStorage for security, ALL consumers must be updated:
- `core/Router.js` — `localStorage.getItem('__SAJU_DATA__')` → `sessionStorage.getItem('__SAJU_DATA__')`
- `views/DashboardView.js` — may also reference localStorage

### D1 auto-migration
For local dev without pre-existing tables, add `ensureTables()` that:
1. Tries `SELECT 1 FROM users LIMIT 1`
2. If it fails, runs `CREATE TABLE IF NOT EXISTS users (...)` via `env.DB.exec()`

## Routes
| Path | View | Backend |
|------|------|---------|
| `#/input` | InputView | — |
| `#/dashboard` | DashboardView | `/api/analyze` + `/api/report` |
| `#/compare` | CompareView | — |
| `#/report-ai` | ReportAiView | — |
| `#/report-desire` | ReportDesireView | — |
| `#/report-luck` | ReportLuckView | — |
| `#/payment` | PaymentView | — |
| `#/report-dating` | ReportDatingView | — |
| `#/report-desire-deep` | ReportDesireDeepView | — |
| `#/report-comprehensive` | ReportComprehensiveView | — |
