---
name: cf-workers-integration
title: Cloudflare Workers Integration Pattern
description: Class-level skill for integrating separate codebases (analysis engines, NAS controllers, shared utilities, LLM callers) into a single coherent Cloudflare Workers project.
domain: software-development
tags: [cf-workers, architecture, refactoring, LLM]
links:
  - "[[@identity/brain/rules]]"
---

# Cloudflare Workers Project Integration

Integrating separate codebases (NAS controllers, analysis engines, LLM callers) into one coherent CF Workers project.

## Trigger
- Multiple codebases need merging (NAS + working copy + external)
- Worker.ts monolithic → router + controllers refactoring
- LLM caller consolidation (duplicated DeepSeek/NVIDIA fallback)
- Data source unification (master JSON for shared constants)

## Step 1 — Map structure
`diff -rq src/ /source/path/src/` — find unique files on each side.

## Step 2 — Find dead code
Search for orphaned files (imported 0 times), duplicated utilities, hardcoded constants.

## Step 3 — Shared infra modules
1. `src/data/<domain>-constants.json` — master constants
2. `src/utils/llm.ts` — unified DeepSeek + NVIDIA callers
3. `src/analysis/types.ts` — analysis report types

## Step 4 — Worker.ts → router pattern
```typescript
import { handleX } from './src/controllers/x';
export default { async fetch(request, env, ctx) {
  if (url.pathname === '/api/x') return handleX(request, env, url, ctx);
  return env.ASSETS.fetch(request);
}};
```

## Step 5 — LLM unification
`src/utils/llm.ts` provides:
- `callDeepSeek(env, systemPrompt, userContent, maxTokens)` — direct DeepSeek call
- `callNvidiaWithFallback(env, systemPrompt, userContent, maxTokens)` — 3-key NVIDIA NIM + 28s per-key timeout + AbortController
- `callLLMJson(env, systemPrompt, userContent)` — DeepSeek→NVIDIA fallback chain; throws on all failure
- `extractJsonObject(text)` — regex-based JSON extraction from LLM response

All controllers import from this single module instead of duplicating API call logic.

## Step 6 — API Response Enrichment (injectAnalysisReport pattern)
Intercept an API response, add computed data, return enhanced response without breaking existing consumers:

```typescript
async function injectAnalysisReport(response: Response): Promise<Response> {
  const clone = response.clone();
  const body = await clone.json();
  body.data.analysisReport = analyze(body.data);
  return new Response(JSON.stringify(body), {
    status: response.status,
    headers: response.headers, // preserve CORS/auth headers
  });
}
```

Caller pattern: `return injectAnalysisReport(await handleAnalyze(...));`

For routes that need data transformation (e.g. old API expects format A, new engine produces format B), inject the bridge in the router layer before passing to the controller:
```typescript
const body = await request.clone().json();
if (body.sajuData && !body.just5Data) {
  const report = analyze({ pillars: body.sajuData.pillars });
  body.just5Data = { 기질형스펙트럼: report.spectrum, 오행집계: report.ohang.score };
  const modified = new Request(request.url, { method:'POST', headers, body: JSON.stringify(body) });
  return handleController(modified, env, url);
}
```

## Step 7 — Data transformation bridge
When the controller expects a specific data shape (e.g. `just5Data`) but the caller doesn't provide it, transform at the router layer:

| Source (analysisReport) | Target (just5Data format) |
|------------------------|--------------------------|
| `spectrum` | `기질형스펙트럼` |
| `ohang.score` | `오행집계` |
| `currentLuck.daewoon?.layer1` | `layer1.대운분석` |
| `currentLuck.saewoon?.layer2` | `layer2` (세운_오행점수, 대운세운관계, 올해테마) |
| `hapChung.map(h => h.label)` | `특이사항` |

## Step 8 — Layered analysis (L0→L3 progressive computation)
```typescript
L0 = pillarsArray                         // 8자: 원국 ohang + spectrum
L1 = [...pillarsArray, daewoonPillar]     // 10자: L0 + 대운 → delta
L2 = [...l1Pillars, saewoonPillar]       // 12자: L1 + 세운 → delta + relation
L3 = saewoon.wolun.find(month)           // PDC 데이터 직접 추출
```

Each layer accumulates pillars and recalculates ohang/spectrum. Delta comparisons drive the narrative (현상방향/추상방향/유지).

## SPA Routing: Same-Hash Navigation Doesn't Fire hashchange

**Symptom:** Clicking a history item/CTA that navigates to the same hash route (e.g. already on `#/report-dating`, click item that also goes to `#/report-dating`) does nothing. The view doesn't re-render.

**Root cause:** `window.location.hash = '#/report-dating'` — if already on that exact hash, the browser doesn't fire a `hashchange` event. The SPA Router never picks up the navigation, so restore data set in `localStorage` is never read.

**Fix:** Append `?t=${Date.now()}` to make each navigation hash unique while keeping the same route path:

```js
// Before (broken for same-route navigation)
window.location.hash = '#/report-dating';

// After (always triggers hashchange)
window.location.hash = '#/report-dating?t=' + Date.now();
```

**Router compatibility:** The Router's `handleRoute()` should strip query params from the path:
```js
let pathWithQuery = hash.replace(/^#/, '');
let path = pathWithQuery.split('?')[0];  // /report-dating ← clean
```

**Applies to:** All hash-based SPA routers where route state is restored from localStorage on navigation. This includes the M-LOG dating report, desire report, luck report, and any other report view that restores data from `__RESTORE_REPORT__` on `init()`.

## Pitfalls
- **Commit**: Never commit without user review. `git add -A && git commit` only after user says "commit". Undo premature commit with `git reset --soft HEAD~1 && git reset HEAD .`
- **Verify before claiming absence**: Exhaustive search (grep + curl + trace) before saying "X doesn't exist in the code". The user corrects you if you jump to conclusions.
- **Understand intent first**: Don't get excited about technical details at the expense of understanding what the app does for users. The user will call this out. First answer: "what does this app DO" — THEN discuss technical approach.
- **Piecemeal**: Trace full dependency chain before proposing a fix.
- **External API data**: If upstream API already computes a value (tenGod, direction, wolun), use it — don't reimplement. Verify with curl.
- **Env drift**: Update `worker-configuration.d.ts` when adding env vars.
- **Secrets**: `.dev.vars` may not exist in working copy — copy from SMB/NAS source.
- **SQLite lock**: `rm -rf .wrangler/state/v3/d1/` and `pkill -f wrangler` to clear port/lock on crash.
- **SMB Korean filenames**: `find`/`grep` may fail on Korean filenames. Use `ls -la` to verify paths, then `cat` with exact path.
- **Incremental rhythm**: One change → verify (curl test) → confirm → next. Never batch without per-step verification. The user expects "하나씩".
- **Avoid "quintax"**: Never mention this term to the user. It's an abandoned separate approach that confuses the architecture discussion.
- ⚠️ **SMB path**: When working via SMB/NAS mount, `find` and `grep` with Korean-encoded filenames may fail silently. Use `ls -la | head` to verify, then reference files by absolute path.
- **Patch tool + JS template literals**: The patch tool escapes backticks inside template literals, causing `SyntaxError: Invalid or unexpected token`. After any patch on JS files, run `node --check <file>`. If broken, rewrite the affected method.
- **Template literal syntax error detection**: When the browser reports `Uncaught SyntaxError: missing } in template string` at a specific line, use Node.js to verify:
  ```bash
  node --input-type=module -e "
  try { await import('./path/to/file.js'); }
  catch(e) { console.log(e.message); }
  "
  # Look for 'Missing } in template expression' or 'Unexpected token'
  ```
  Common cause: a stray backtick inside a template literal that closes it prematurely, making subsequent HTML-like content parse as JS code. Fix by removing the spurious backtick. The error line number from the browser is reliable.
- **D1 auto-migration single-line SQL**: `env.DB.exec()` with multi-line template strings fails with `SQLITE_ERROR: incomplete input`. Flatten to single-line strings, and run each CREATE TABLE as a separate `exec()` call.
- **Developer bypass logout fix**: When running `IS_LOCAL_DEV=true`, the dev bypass auto-creates sessions. Logout doesn't work because the bypass re-creates the session on the next request. Fix: set `m_log_logged_out=1` cookie on logout (10s TTL), and check it in the dev bypass code before creating a session. The `getCookie()` function takes `(request, name)`, not just `(name)`.
- **Frontend replacement protocol**: When replacing `public/app/` with new `frontend/app/`:
  1. Backup: `cp -R public/app public/app.bak.$(date +%s)`
  2. Copy: `cp -R frontend/app/ public/app/`
  3. Re-apply login modal, CSS changes, and event wiring in the new files (they get overwritten)
  4. Re-sync shared theme: `npm run sync:local` (otherwise `--z-breakdown-sheet` etc. variables missing)
  5. Check storage mechanism: new frontend may use `localStorage` while old fix used `sessionStorage` — align all references
  6. Verify no template literal corruption: `node --check public/app/js/components/layouts/AppShell.js`
- **build:frontend is intentionally broken**: `npm run build:frontend` fails with "Could not resolve entry module 'index.html'" because there's no vite config. The frontend is served directly as static files by wrangler. This is intentional — don't try to fix it.
- **CSS z-index audit**: When UI layers overlap incorrectly (tooltip behind modal, sidebar above overlay, etc.), do a systematic audit:
  1. Check `shared/theme/variables.css` for `--z-*` custom property definitions → this is the single source of truth
  2. Search for hardcoded `z-index: NNNN` values in CSS files and JS inline styles: `grep -rn "z-index:" --include='*.css' --include='*.js' | grep -v "var(--z"`
  3. Replace each hardcoded value with the appropriate `var(--z-*)` variable
  4. Check that component CSS files use `var()` references instead of hardcoded values
  5. Verify missing layer variables: compare `packages/theme/variables.css` (canonical) with `public/app/shared/theme/variables.css` (deployed copy) — they may drift

## Ontology Integration (Knowledge Base → LLM Prompt Injection)

For projects where a domain ontology (knowledge graph, concept catalog, evidence database) drives LLM-generated reports:

### Source → Project Pipeline

```
NAS/원본: postziping_public_docs/*.md (10개 파일, 12,701라인, ~600KB)
  ↓ cp (manual sync from authoritative source)
로컬 프로젝트: src/data/ontology/postziping/*.md
  ↓ TypeScript loader (key docs embedded, large catalogs excluded as CF Worker bundle limit)
로더: src/data/ontology/ontology.ts  (~16KB, 5 embedded docs)
  ↓ getOntologyContext(mode) → string
LLM System Prompt → [온톨로지 컨텍스트] + [기존 시스템 프롬프트]
  ↓
LLM generates report with ontology-grounded reasoning
```

### What Gets Embedded

| File | Size | Include? | Reason |
|------|------|---------|--------|
| `postziping_relationship_psychology_latest_backbone.md` | 5.5KB | ✅ | Essential: framework rules |
| `01_structure_overview.md` | 1KB | ✅ | Essential: ontology structure |
| `08_llm_usage_prompt.md` | 1KB | ✅ | Essential: LLM rules |
| `03_graph_catalog.md` | 8.5KB | ✅ | Important: node IDs |
| `02_example_uses.md` | 1.3KB | ✅ | Useful: query examples |
| `04_concept_catalog.md` | 183KB | ❌ | Too large; reference only |
| `05_claim_catalog.md` | 145KB | ❌ | Too large; reference only |
| `06_evidence_catalog.md` | 432KB | ❌ | Too large; reference only |

### TypeScript Loader Pattern

```typescript
// src/data/ontology/ontology.ts
const BACKBONE = `...core ontology embedded as template literal string...`;
const STRUCTURE = `...`;

export function getOntologyContext(mode: 'analyze' | 'compatibility' | 'divorce'): string {
  const parts = [
    '[온톨로지 백본]', BACKBONE, '',
    '[온톨로지 구조]', STRUCTURE, '',
  ];
  if (mode === 'compatibility' || mode === 'divorce') {
    parts.push('[관계 원칙]', '...mode-specific content...');
  }
  return parts.join('\n');
}
```

### Injection into System Prompt

```typescript
// In controller:
import { getOntologyContext } from '../data/ontology/ontology';

async function generateReport(data, env, mode) {
  const ontologyCtx = getOntologyContext(mode);
  const sys = ontologyCtx + '\n\n' + buildSystemPrompt(keys);
  // sys sent to LLM as system message
}
```

### Pitfalls
- **Bundle limit**: Don't embed all ~600KB into worker bundle. Select ~16KB of essential docs.
- **NAS authority**: NAS is the canonical source. `diff` before overwriting local copies.
- **Terminology rewrite**: Replace "온톨로지" → "관계 해석" in final LLM output for readability.
- **Per-mode context**: `getOntologyContext(mode)` selects mode-relevant sections.
- **NAS path varies**: Check `/Volumes/` and `~/Library/CloudStorage/` — the mount path may differ.
- **Hardcoded ontology exists**: If a function like `ontologyLens()` already hardcodes concept IDs, merge markdown content into it rather than replacing.

## Related
- [[software-development/requesting-code-review]]
- [[software-development/gateway-module-extraction]]
- `references/m-log-paid-report-payment-flow.md` — M-LOG payment flow pattern: API-first → save → redirect → restore → loading simulation
- **Overlap note**: `software-development/korean-payment-gateway` and `software-development/portone-payment-integration` overlap significantly. The curator should consider consolidating into one class-level skill.
