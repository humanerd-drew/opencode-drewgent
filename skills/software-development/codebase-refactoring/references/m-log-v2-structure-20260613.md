# m-log-v2 Project Structure (2026-06-13)

## Overview

Cloudflare Workers SPA — vanilla JS frontend (no build step) + TypeScript backend.
Hash-based SPA routing. PortOne V2 payment. Naver/Google OAuth. D1 database.

## Backend (`src/`)

```
worker.ts                     → if/else router (30+ routes)
controllers/
├── saju.ts                   → POST /api/analyze, POST /api/iljin, GET /api/locations
├── auth.ts                   → Naver/Google OAuth, email login, profile
├── payment.ts                → PortOne V2 verify/check
├── report.ts                 → DeepSeek free log report
├── comprehensive-report.ts   → daese-wolun comprehensive report
├── dating-report.ts          → gung-hap / dating report
├── history.ts                → query history CRUD
└── myeongsik.ts              → myeongsik save/load/delete
engine/                       → manse-calculation engine (ohaeng, daewoon, saewoon, gung-hap, persona)
analysis/                     → analysis report generation engine
db/queries.ts                 → D1 query helpers
utils/                        → cors, crypto, email, llm
```

## Frontend SPA (`public/app/`)

11 hash-routed pages via Router.js:

| Route | View | Description |
|-------|------|-------------|
| `#/input` | InputView | Birth data input form |
| `#/dashboard` | DashboardView | Main saju topology dashboard |
| `#/just5` | Just5View | Just5 (embedded iframe) |
| `#/compare` | CompareView | Multi-chart comparison |
| `#/report-desire` | ReportDesireView | Desire analysis report |
| `#/report-desire-deep` | ReportDesireDeepView | Deep desire report |
| `#/report-ai` | ReportAiView | AI report |
| `#/report-luck` | ReportComprehensiveView | Fortune comprehensive (alias) |
| `#/report-comprehensive` | ReportComprehensiveView | Daese-wolun comprehensive report |
| `#/report-dating` | ReportDatingView | Dating/gung-hap report |
| `#/payment` | PaymentView | Payment page (PortOne V2) |

Default route: if `localStorage.__SAJU_DATA__` exists → `#/dashboard`, else `#/input`.

## Layout

AppShell.js (970 lines) manages: header, menu sidebar, history sidebar, legend panel, footer,
login modal, loading overlay, toast container, breakdown bottom-sheet.

## Notable Patterns

- **injectAnalysisReport**: Router-layer response enrichment (clone → parse → add computed fields → re-serialize)
- **No frontend build step**: Raw ESM modules served by Wrangler's `env.ASSETS`
- **No tsconfig.json**: Backend TS compiled by Wrangler's built-in TS support
- **16 CSS files**: Loaded via `<link>` tags with `?v=2.4.0` manual cache-busting
- **shared/ directory**: Duplicate/redundant code vs views/components/ directory

## Related

- `codebase-refactoring` skill — Phase 2.5 Complete Feature Removal covers the quintax deletion pattern used in this session
