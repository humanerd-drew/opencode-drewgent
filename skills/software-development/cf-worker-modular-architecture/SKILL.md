---
title: Cloudflare Worker Modular Architecture
name: cf-worker-modular-architecture
domain: software-development
description: Pattern for organizing CF Workers into router → controllers → engine → utils layers. When a worker exceeds 300 lines, split into thin router + single-responsibility controllers + pure computation engine + shared utilities.
tags: [cf-worker, architecture, refactoring, controllers, router]
created: 2026-06-11
updated: 2026-06-12
---

# Cloudflare Worker Modular Architecture

When a Worker grows beyond 300-500 lines, refactor into:
**Router → Controllers → Engine → Utilities**

## Workflow Protocol
- **Never commit without user review.** Stage changes (`git add -A`) and present the diff or summary. Wait for explicit approval before `git commit`.
- Run `npm run dev` and verify the app works after each batch of changes.
- One change at a time — make the change, watch for wrangler auto-reload, verify with curl, then proceed.
- When dev server crashes (port conflict / SQLITE_BUSY): kill old process, clear `.wrangler/state/v3/d1/`, restart.

## Layers
- **worker.ts** (router, ~100-200 lines): URL matching → dispatch to controller. No business logic.
- **controllers/**: export `handle*(request, env, url): Promise<Response>`. Single responsibility.
- **engine/** or **analysis/**: Pure computation, no HTTP, deterministic.
- **utils/**: Shared helpers (llm, crypto, cors, email)
- **data/**: Static JSON master data

## Key Rules

### Controller Pattern
- All controllers share the same signature `(request, env, url): Promise<Response>`
- Export individual handler functions, not class instances
- Import shared utilities from `../utils/`

### External API Isolation (PDC Principle)
- **Never recalculate what an external API already provides.** Pipe it through and transform format only.
- Example: PersonalDateCalculator returns `tenGods`, `daewoon.direction`, `wolun[]`. Use those values directly rather than recalculating from raw pillars.
- The external API is the single source of truth for core domain calculations. Your engine should only compute what the API doesn't provide.
- *Pitfall:* Duplicating calculation logic creates maintenance burden and subtle drift when the external API gets bug fixes.

### LLM Caller Consolidation
- Don't duplicate LLM call logic across controllers. One `utils/llm.ts` with:
  - `callDeepSeek()` — primary
  - `callNvidiaWithFallback()` — 3-key fallback (NIM_KEY → FALLBACK → FALLBACK_2)
  - `callLLMJson()` — DeepSeek → NVIDIA + JSON extraction
  - 28s per-key timeout to stay under Cloudflare's 30s wall limit
- Each LLM endpoint (report generation, polish, analysis) builds its own system prompt but calls through the same utility.

### Data Injection at Router Level
- Inject missing/cross-cutting data at the router layer (`worker.ts`), not inside controllers.
- Example: `analysisReport` is computed in router's `injectAnalysisReport()` after the controller returns, not inside the controller itself.
- This keeps controllers testable with plain HTTP calls.

### ⚠️ Pitfall: Controller Created But Not Registered

A controller file exists in `src/controllers/` but is **never imported** in `worker.ts` and **never routed**. The module compiles silently, the frontend calls the endpoint and gets 404.

**Always verify the full registration chain after creating a new controller:**

```
┌─────────────────────────────────────────────────┐
│ 1. controller file exists  ✓                    │
│    src/controllers/your-controller.ts            │
├─────────────────────────────────────────────────┤
│ 2. IMPORTED in worker.ts?   ← COMMON MISS       │
│    import { handleX } from                      │
│      './src/controllers/your-controller';        │
├─────────────────────────────────────────────────┤
│ 3. ROUTED in worker.ts?     ← COMMON MISS       │
│    if (url.pathname.startsWith('/api/...')) {    │
│        return handleX(request, env, url);        │
│    }                                             │
└─────────────────────────────────────────────────┘
```

**Detection:** After creating a controller, test the endpoint with curl BEFORE building the frontend:
```bash
curl -s -X POST http://localhost:8788/api/your-endpoint \
  -H "Content-Type: application/json" \
  -d '{}'
# 404 → not imported or not routed
# 200/401 → routing works
```

**Session example (2026-06-12):** `dating-report.ts` existed at `src/controllers/dating-report.ts` but was never imported in `worker.ts`. The frontend called `/api/dating/compatibility` and got 404. Fix required two lines: one import, one route `if` block.

### ⚠️ Pitfall: Dashboard Card Navigation Stubs

When building action cards on a dashboard (report cards, settings links, etc.), developers often stub the navigation handler to a fallback route during initial development:

```typescript
// ❌ Stub — always redirects to input
navigateToDesireReport(e) {
    window.location.hash = '#/input';
}
```

**These stubs are easy to forget.** When the actual page is built and the route exists in the Router, the stub still redirects to the fallback. The page works if accessed directly by URL, but the card click does nothing useful.

**Fix:** After building a page view and registering its route, search for all stub handlers and update them:
```bash
grep -rn "window.location.hash = '#/input'" public/app/js/ --include='*.js'
```

### Master Data JSON Pattern
- Store shared constants (elements, stems, branches, personas) as static `.json` in `src/data/`.
- Uses TypeScript's `resolveJsonModule` to import directly.
- All consumers (engine, controllers, utils) import from the same JSON — single source of truth.
- **When adding new constants:** add to the master JSON first, then update all consumers. Leave a comment in frontend copies pointing to the master.
- *Anti-pattern:* Duplicating the same stem/element/ohang mappings across engine.ts, analyzers, and frontend constants.

### Report Pipeline
Report generation follows a multi-stage pipeline:

1. **Analysis Engine** (deterministic) → computes ohang scores, spectrum, layers L0-L3
2. **Source Builder** → assembles structured data for the LLM prompt (hides saju terminology, presents user-friendly categories)
3. **LLM Generation** → `callLLMJson()` → raw report JSON via DeepSeek (primary) or NVIDIA (fallback)
4. **Polish** → second LLM call with `POLISH_SYSTEM_PROMPT` to strip AI-isms and normalize tone
5. **Return** → structured report delivered to client

**Key design decisions:**
- Each report topic (free log, comprehensive monthly, dating) has its own system prompt builder
- Polish step uses low temperature (0.1) to minimize creative drift
- All LLM calls route through the same `utils/llm.ts` utility
- Separate the "source data" (what the LLM sees) from the "rendered output" (what the user sees)

### Dev Server Testing Protocol
When running local dev with `npm run dev` (`wrangler dev`):

- **Port conflict (SQLITE_BUSY):** kill old process with `pkill -f wrangler`, clear `.wrangler/state/v3/d1/`, restart.
- **Multiple instances:** Only one wrangler dev per D1 database can run at a time. Check `ps aux | grep wrangler` before starting.
- **File changes:** Wrangler auto-reloads on source changes. Watch for `⎔ Reloading local server...` in the log.
- **Verify after change:** Run `curl -s -o /dev/null -w '%{http_code}' http://localhost:8787/app/` plus a targeted API test.
- **Stale processes:** Old wrangler processes can hold port 8787 silently. Kill all before restarting.

### SPA → Passive Renderer Migration
- Frontend should compute nothing from raw data. Analysis engine pre-computes everything.
- `renderer.js` methods like `getElement(char)`, `calculateDirection()`, `getRelClass()` become unnecessary once `analysisReport` provides the computed values.
- Add backward-compatible fallbacks before removing old code:
  ```js
  const direction = analysisReport?.currentLuck?.daewoon?.direction
      || Renderer.calculateDirection(gender, yearStem); // fallback
  ```
