---
title: Codebase Consolidation
name: codebase-consolidation
description: "Find and merge duplicate data structures, constants, and logic across architectural boundaries — frontend↔backend, separate workers, independent modules. Create single sources of truth."
type: skill
domain: software-development
tags: [refactoring, deduplication, structural, architecture]
created: 2026-06-11
updated: 2026-06-11
links:
  - "[[P3-sensors/skills/SKILL-INDEX]]"
  - "[[software-development/codebase-refactoring]]"
  - "[[software-development/codebase-structure-audit]]"
  - "[[software-development/incremental-refactoring]]"
  - "[[software-development/project-code-audit]]"
  - "[[software-development/simplify-code]]"
  - "[[P0-brainstem/brain/rules]]"
---

# Codebase Consolidation

Use this when a codebase has the same data or logic defined independently in multiple places — especially across different runtime environments (frontend JS, backend worker A, backend worker B). Consolidation prevents drift: one source updated, others forgotten.

## When to Use

- Same constants (천간/지지/오행 mappings, status enums, lookup tables) appear in 2+ files across frontend/backend
- A backend utility function (retry, sign, validate) is re-implemented in a sibling worker
- Two CSS files load the same component — one via `<link>` and one via `@import`
- Config values (API endpoints, client IDs) defined in both frontend and backend
- The user asks about "data duplication" or "master data source"

## Core Principle

**Single Source of Truth (SSOT)** — pick one authoritative location for each piece of data, and make every consumer reference it. When runtime environments can't share code (e.g., separate Cloudflare Workers), use a **data-level SSOT**: a JSON file that both environments can import at build time.

```
Before:                    After:
  constants.js: {甲→wood}     src/data/constants.json: {甲→wood}
  worker.ts: ['甲','乙',...]       ↑                     ↑
  analyzer.ts: {甲→'wood'}      worker.ts ───┘    analyzer.ts ───┘
                              constants.js → (standalone copy + comment)
```

## Three-Phase Process

### Phase 1: Discovery

Find ALL copies of the same data. Cast a wide net:

```bash
# 1. Search for repeating character sequences (천간 10개, 지지 12개)
grep -rn "'甲','乙','丙','丁','戊','己','庚','辛','壬','癸'" --include='*.ts' --include='*.js' source/

# 2. Search for key-value patterns that suggest mapping data
grep -rn "'甲':.*'wood'\|'甲'.*element\|'wood'.*'목'" --include='*.ts' --include='*.js' source/

# 3. Check for the same array literal in multiple files
grep -rn "\[.*'子','丑','寅'.*\]" --include='*.ts' --include='*.js' source/

# 4. For CSS: compare <link> in HTML against @import chain in master CSS
grep -o 'href="[^"]*\.css"' public/**/*.html | sort
grep "@import" public/css/index.css | sort
# Any CSS loaded via <link> but NOT in @import (or vice versa) needs audit
```

For each candidate, note:
- **File and line** — exact location
- **Data shape** — array, object, Record<string, X>
- **Environment** — frontend (browser), backend worker A, backend worker B
- **Dependencies** — which other modules import/use this data
- **Is it truly identical?** — compare every key-value pair. If they differ, that's a BUG, not just a duplication

### Phase 2: Master Design

Choose the master format based on consumer environments:

| Environment Mix | Best Master Format | Import Method |
|----------------|-------------------|---------------|
| All TypeScript in one build | Single `.ts` file with `export const` | `import { X } from './master'` |
| Multiple independent Workers | `.json` file | Cloudflare Workers / Node: `import data from './x.json'` |
| Frontend + backend Workers | `.json` file + frontend standalone copy with comment | Backend imports JSON; frontend keeps mirrored copy with cross-reference |
| Distributed services | Package published to npm/internal registry | `npm install @org/data-constants` |

**JSON advantages**: universally parseable (JS, TS, Python, Go), no compilation needed, no TypeScript dependency, easy to diff and review.

**JSON disadvantages**: only pure data — no functions, no computed properties, no TypeScript types. For functions (e.g., `getElement(char)`), keep in the consumer code but have it reference the JSON data.

Design the JSON structure to match the natural data hierarchy:

```json
{
  "stemList": ["甲","乙",...],           // ordered list if index access needed
  "stems": { "甲": {"element":"wood",...} },  // keyed lookup
  "branches": { "子": {"element":"water",...} },
  "relations": {
    "threeHarmonies": { "wood": [...], ... },
    "groupLabels": { "亥卯未": "삼합(해묘미)", ... }
  }
}
```

**Always include**: `version`, `lastUpdated`, `description` — so future readers know what this is.

### Phase 3: Migration

Update each consumer one at a time, testing after each:

1. **Backend worker A**: add `import MASTER from './path/to/master.json'`, replace inline data with `MASTER.data`
2. **Backend worker B**: same pattern
3. **Frontend**: can't import backend JSON at runtime in browser. Options:
   - **Best for safety**: keep the frontend copy as-is, add a prominent JSDoc header naming the master JSON path. The frontend is the canonical display layer — its data is consumed by UI rendering, not computation — so drift risk is lower.
   - **Best for purity**: generate the frontend module from the JSON at build time (add a script to `package.json`).
   - **Best for distribution**: serve the JSON as a static asset and have the frontend `fetch()` it at init — adds latency but guarantees freshness.

**Verification**: For each consumer, run the existing functionality (local dev server, integration tests) and confirm output is identical to before.

**Live dev verification pattern:**

```bash
# Restart dev server if not running
npm run dev -- --port 8787 &

# After each change, wait for reload, then test
sleep 3
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8787/app/
curl -s http://localhost:8787/api/analyze -X POST -H "Content-Type: application/json" \
  -d '{"year":1991,"month":7,"day":24,"hour":6,"minute":30,"location":"서울","gender":"male"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('API OK' if d.get('success') else 'FAIL')"
```

## CSS @import Chain Audit

A common consolidation need: CSS files loaded via both `<link>` in HTML AND `@import` in a master CSS.

```bash
# List all CSS sheets loaded by HTML pages
grep -o 'href="[^"]*\.css[^"]*"' public/**/*.html | sed 's/href="//;s/".*//' | sort -u

# List all CSS sheets in the @import chain  
grep '@import' public/css/index.css | sed "s/.*url('//;s/').*//" | sort -u

# Compare — anything in HTML but not in @import needs attention
```

**Order of loading matters** — especially for CSS variables and base styles. When integrating a previously-standalone page into the master chain, verify:
- Are all CSS variables it uses defined in `variables.css`?
- Is the base reset (`base.css`) included?
- Does the component CSS have unique class names that won't conflict?

## Common Consolidation Targets

### 1. Frontend ↔ Backend Data Duplication

Most common pattern. The frontend has a rich data file (`constants.js`) that the backend re-implements sparsely or with different structure.

**Solution**: Extract the raw data (not functions or display config) into a shared JSON. Functions and UI config remain in the frontend copy.

### 2. Worker ↔ Worker Utility Duplication

Two CF Workers that each implement `withRetry()`, `safeJson()`, or `signSession()` independently.

**Solution in current CF Worker model**: not shareable at runtime (separate deployments). Options:
- Extract to a shared npm package
- Document the duplication with a `// TODO: shared with {other worker}` comment
- Accept duplication (small functions, low maintenance cost)

### 3. CSS Chain Duplication

Same component loaded via both `<link>` and `@import`.

**Verification**: Add the missing CSS to the master @import chain, remove the explicit `<link>` in HTML, reload and check the component renders identically. The extra CSS from the @import chain (layout, nav, etc.) is unused but harmless — class names are unique to their components.

## Phase 4: Backward-Compatible API Extension

A natural follow-up to data consolidation: once you've extracted a master data source, build an analysis engine that pre-computes what the frontend currently calculates ad-hoc. Add the computed data to the **existing API response** as a new field — the frontend keeps working (it ignores unknown fields), and can start using the new data gradually.

### Pattern: Add, Don't Replace

```javascript
// BEFORE: worker.ts sends raw data, frontend computes everything
return { success: true, data: { pillars, tenGods, daewoon } }

// AFTER: worker.ts sends raw data + pre-computed analysis
return { 
  success: true, 
  data: { 
    pillars, tenGods, daewoon,          // unchanged — frontend still works
    analysisReport: {                     // new — frontend can opt in
      ohang: { score: {...}, missing: [...], excess: [...] },
      spectrum: { position: "...", totalValue: N },
      hapChung: [...],
      pillarElements: [...],
      tenGod: {...},
      currentLuck: { daewoon: {...}, saewoon: {...} }
    }
  } 
}
```

**Rules:**
1. **Never remove or rename existing fields.** The frontend depends on them.
2. **Wrap new field generation in try/catch** with `console.warn` on failure, so a bug in the new code can't crash the endpoint.
3. **The new field is optional** — the frontend checks `if (data.analysisReport)` before using it, and falls back to the old calculation path.
4. **Deploy anytime.** Because step 3, the new field can ship before any frontend code uses it.

### Frontend Migration Sequence

For each piece of data that moves from frontend-calculation to backend-report:

1. **Add** the computed value to the backend report (starts appearing in API response, frontend ignores it)
2. **Update** the frontend to prefer the report value when available, with fallback to existing logic:
   ```javascript
   // BEFORE:
   const direction = Renderer.calculateDirection(gender, yearStem);
   
   // AFTER:
   const direction = apiData.analysisReport?.currentLuck?.daewoon?.direction
     || Renderer.calculateDirection(gender, yearStem);
   ```
3. **Test** with the dev server — verify both old cached data (no report) and new API responses (with report) render correctly
4. **Optionally** remove the fallback once all cached data has expired or been migrated

### PII Protection: Storage Migration

An important follow-up to data consolidation: once you pre-compute data server-side, the raw PII (birth dates, names, full API responses) stored in the frontend should be moved from `localStorage` (persists until explicitly deleted) to `sessionStorage` (cleared when tab closes).

**Migration pattern:**

```javascript
// BEFORE: PII stored in localStorage (visible in DevTools even days later)
localStorage.setItem('__SAJU_DATA__', JSON.stringify(fullApiResponse));
localStorage.setItem('__FORM_VALUES__', JSON.stringify(formData));  // name, birth date

// AFTER: stored in sessionStorage (cleared on tab close)
sessionStorage.setItem('__SAJU_DATA__', JSON.stringify(fullApiResponse));
sessionStorage.setItem('__FORM_VALUES__', JSON.stringify(formData));
```

**Which keys to migrate:**
| Data | Storage | Rationale |
|------|---------|-----------|
| API analysis results (pillars, birth info) | `sessionStorage` | Re-fetched on new analysis; no need to persist across sessions |
| Form input (name, birth date) | `sessionStorage` | PII — auto-cleared on tab close |
| Theme preference | `localStorage` | User preference, not sensitive |
| Anonymous session ID | `localStorage` | Needs to survive tab close for history merging |
| Offline sync queue | `localStorage` | Must persist for offline resilience |

**Safety**: `sessionStorage` and `localStorage` have identical APIs (`getItem`/`setItem`/`removeItem`). Migration is a simple string replacement. Newly loaded pages with the old `localStorage` keys still work because the sessionStorage lookup returns null first (strategy: prefer sessionStorage with localStorage fallback during transition).

**Dev log monitoring**: When `wrangler dev` is running, redirect its output to a file so you can verify auto-reload succeeds on each change:

```bash
# Start with log file
npm run dev -- --port 8787 > /tmp/wrangler-dev.log 2>&1 &

# Check for reload confirmation
tail -3 /tmp/wrangler-dev.log
# Expected: "⎔ Local server updated and ready"
```

### Common Migration Targets

| Frontend Calculation | Report Field | Complexity |
|---|---|---|
| Character → element lookup (color) | `pillarElements[].*Element` | 🟢 Low |
| Daewoon direction (순행/역행) | `currentLuck.daewoon.direction` | 🟢 Low |
| HapChung string parsing | `hapChung[].label` | 🟢 Low |
| Ohang score / element chart | `ohang.score` | 🟡 Medium |
| Spectrum / personality position | `spectrum.position` | 🟡 Medium |
| TenGod relationships | `tenGod.stems/branches` | 🟢 Low |

## Related Skills
  
This skill overlaps with:
- `codebase-refactoring` — incremental refactoring methodology (same class, different angle)
- `codebase-structure-audit` — dependency graph mapping and dead code detection (audit phase)
- `incremental-refactoring` — incremental approach with verification
- `project-code-audit` — project analysis methodology
- `requesting-code-review` — now covers full project codebase audits

If you're starting a new project audit, load one of the audit skills. If you already have a list of duplicates to consolidate, this skill covers the consolidation mechanics.

The background curator handles deduplication of overlapping skills.

## References

- `references/project-audit-methodology.md` — Systematic dead code detection via zero-reference search across JS/TS/HTML/CSS
- `references/two-codebase-merge.md` — Merging two copies of the same project (e.g., NAS working copy + local dev copy)
- `references/synology-symlink-fix.md` — Fixing XSym-corrupted node_modules/.bin symlinks

## Pitfalls

- **Don't consolidate for the sake of it.** If data changes infrequently (천간/지지 never changes) and consumers are independent, a cross-reference comment may be more practical than a shared JSON.
- **TypeScript type definitions are not data.** `type Ohang = 'wood' | 'fire' | ...` in a `.d.ts` file is fine — it constraints valid values, not duplicate data.
- **Build-time vs runtime sharing.** CF Workers deployed separately CANNOT share code at runtime. JSON import works at build time (the JSON is bundled into each worker). This means each worker still has its own copy — but the JSON is THE SOURCE, so they stay in sync at build time.
- **Object key ordering.** `Object.keys()` on imported JSON preserves insertion order in modern JS engines, but for explicit ordering, add a parallel `xxxList` array to the JSON.
- **Display config vs core data.** Don't put UI-only config (colors, icon paths, animation durations) into the shared JSON. Keep that in the frontend's domain.
- **Inline handler data.** Data defined inside function scopes inside request handlers (e.g. `const CHEONGAN = [...]; const tenGodsName = [...]` inside a POST handler) is easy to miss during grep-based audits. The function boundary hides it from module-level pattern searches. Check handler code specifically for lookup tables, translation maps, and enumerations that may duplicate the master data source.
- **Korean→Hanja transliteration maps** (갑→甲, 을→乙) are translation dictionaries, not core saju data. Keep separate.
- **Entry-point files (worker.ts, main.ts) almost always have different import structures** in diverged copies. Never blindly overwrite them — check git history first, restore from git, then apply targeted patches.
- **Modification times are unreliable in cloud-synced environments.** Synology Drive and similar tools can set bulk timestamps on synced files. Always use SHA256 content hashes to determine which files actually differ.

## Reference

- `references/synology-symlink-fix.md` — Fixing XSym-corrupted node_modules/.bin symlinks, a common issue when the project lives on a Synology Drive synced folder
