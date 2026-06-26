---
title: codebase-refactoring
name: codebase-refactoring
description: Safe, incremental codebase refactoring methodology — dead code removal, data consolidation, CSS chain unification, and PII protection. One change at a time, verified with a running dev server.
domain: software-development
type: skill
tags: [refactoring, dead-code, dependency-analysis, safety]
created: 2026-06-11
updated: 2026-06-12 (package.json shell-script escape pitfall added 2026-06-15)
links:
  - "[[@action/skills/SKILL-INDEX]]"
  - "[[software-development/codebase-structure-audit]]"
  - "[[software-development/codebase-consolidation]]"
  - "[[software-development/incremental-refactoring]]"
  - "[[software-development/simplify-code]]"
  - "[[software-development/project-code-audit]]"
  - "[[software-development/requesting-code-review]]"
  - "[[@identity/brain/rules]]"
---

# 코드베이스 안전 리팩토링

Systematic, safe refactoring — not big-bang rewrites. One change at a time, verified between each step.

## Core Principles

1. **Map before you cut.** Never delete or move code without tracing its import/reference graph first.
2. **Smallest safe step first.** Dead config removal → orphan file deletion → data consolidation → structural change. Each step must be independently reversible.
3. **Verify between each change.** With a running dev server, confirm HTTP 200 before the next edit.
4. **Master data pattern.** When the same data exists in 2+ places (frontend constants, backend arrays, separate workers), extract to a JSON file and have every consumer import it. JSON is universally readable by JS and TS.
5. **No "while I'm here" expansions.** One class of change per session.

## Step-by-step Workflow

### Phase 1 — Discovery

```bash
# 1. Map all files under the project root (exclude node_modules, build artifacts)
find . -type f -name '*.ts' -o -name '*.js' -o -name '*.html' -o -name '*.css' -o -name '*.sql' | grep -v node_modules | sort

# 2. Map all import/reference edges
grep -rn "^import\|from.*['\"]" --include='*.ts' --include='*.js' . | grep -v node_modules | sort

# 3. Identify dead code by reference counting
# If a file/export has zero import references, it's a candidate for deletion
grep -rn "export const\|export function\|export class" --include='*.ts' . | grep -v node_modules
# Cross-reference each export against import statements in other files
```

### Phase 2 — Dead Code Removal (Risk: 🟢 Zero)

Safe to delete when:
- No `import` or `require` references from any other file
- No `<script src="...">` or `<link href="...">` from any HTML
- Config keys that are defined but never read (grep for the read-side)

**Verification command:**
```bash
# After deletion, confirm 404 on deleted paths and 200 on everything else
curl -s -o /dev/null -w "%{http_code}" "http://localhost:PORT/path/to/deleted/file"
```

### Phase 2.5 — Complete Feature Removal (Risk: 🟢 Low–🟡 Medium)

When you need to remove an entire feature module (not orphan cleanup but known live code):
the risk is lower than refactoring because you're not moving anything, just deleting.
But the danger is leaving dangling references that produce runtime 404s or undefined errors.

### Procedure

**Step 1 — Full text inventory (case-insensitive):**
```bash
grep -rl "FeatureName\|feature-name\|FEATURE_NAME" --include='*.ts' --include='*.js' \
  --include='*.json' --include='*.css' --include='*.html' \
  src/ public/ | grep -v node_modules | sort
```

This catches every reference including comments, CSS classes, HTML IDs, and import paths.
Case-insensitive matters — imports use PascalCase (`QuintaxView`), CSS uses kebab-case (`quintax-placeholder`), HTML IDs use camelCase (`quintaxSummary`), comments use any case.

**Step 2 — Classify each hit into a bucket:**

| Bucket | Action | Tool |
|--------|--------|------|
| Dedicated directory | `rm -rf` entire dir | `terminal` |
| Standalone file | `rm` the file | `terminal` |
| Import statement in a remaining file | `patch` to remove the import line | `patch` |
| Route registration | `patch` to remove the route entry | `patch` |
| Nav link / UI element | `patch` to remove the HTML node | `patch` with surrounding context |
| CSS class / selector | `patch` to remove the ruleset | `patch` |
| Combo ref (class name + call site) | Read file first, then `patch` both | `patch` |

**Step 3 — Delete directories and standalone files first:**
```bash
rm -rf src/feature/ public/feature-standalone/
rm -f public/app/js/views/FeatureView.js public/app/js/components/FeatureReport.js
```
This immediately eliminates the bulk of the removal and surfaces any hard-linked refs via grep.

**Step 4 — Read remaining affected files (don't guess):**
For each file with remaining references, read the surrounding context with `read_file`.
A CSS class reference in one file might be shared with a non-feature element — reading context
prevents removing something that still works. **Do not search-and-replace blind.**

**Step 5 — Patch each file with minimal precise edits:**
- Remove import lines: `import { FeatureView } from './views/FeatureView.js'`
- Remove route entries: `'/feature': FeatureView,`
- Remove nav links: the entire `<a>` block including its children
- Remove CSS rulesets: the full block including the opening rule and closing `}`
- Remove call sites: `this.renderFeature();` and the method definition

Each patch is one old_string → new_string replacement with surrounding context for uniqueness.
Use `replace_all: false` (default) to catch accidental duplicate matches.

**Step 6 — Verify zero references remain:**
```bash
grep -rl "FeatureName\|feature-name\|FEATURE_NAME" --include='*.ts' --include='*.js' \
  --include='*.css' --include='*.html' \
  src/ public/ | grep -v node_modules | sort
```
Empty output = complete removal. Any remaining hit means you missed a file.

### Common pitfalls

- **Case mismatch in grep.** Imports use PascalCase, CSS uses kebab-case, HTML IDs use camelCase, comments use any case. Always use case-insensitive grep for the inventory.
- **Blind regex replace.** A CSS class like `.quintax-placeholder` might be used by TWO views — one being removed, one staying. Always read context before patching.
- **CSS selector on same line.** When two selectors share a rule block (`.restricted-overlay.full-view, .restricted-overlay.quintax-view`), removing just the name leaves a dangling comma or empty selector. Remove the ENTRY from the grouped selector, including the comma.
- **Router serves deleted route.** If the route definition is removed but a nav link still points to it, user clicks → router falls to fallback → confusing. Remove nav links AND the route definition in the same pass.
- **iframe-based feature embedding.** A feature served as an iframe (standalone HTML built separately) may be referenced from multiple views — the iframe src path, the placeholder CSS, the nav link. All three must be removed together.
- **Shared types files.** If the feature has its own types file, check if OTHER files import from it. Extract shared types to a neutral location before deleting the feature directory.

## Phase 3 — Data Consolidation (Risk: 🟢 Low)

When the same domain data appears in frontend JS + backend TS + inline arrays:

1. Create `src/data/<domain>-constants.json` as the single source of truth
2. Backend: `import DATA from './path/to/data.json'` (needs `resolveJsonModule: true` in tsconfig)
3. Frontend: Keep the JS file as a standalone copy with a prominent JSDoc comment pointing to the JSON master
4. Verify the JSON import works: `curl` the API endpoint that uses it

```typescript
// worker.ts — import pattern
import DATA from './src/data/saju-constants.json';

// Derive runtime structures from the master
const cheonganList = DATA.stemList;  // ordered array from JSON
const ohangMap: Record<string, string> = {};
for (const [char, val] of Object.entries(DATA.stems)) {
  ohangMap[char] = val.element;
}
```

### Phase 4 — CSS Chain Consolidation (Risk: 🟢 Low)

1. Find all `<link rel="stylesheet">` tags across all HTML files
2. Identify the main CSS orchestrator (usually `index.css` with `@import` chain)
3. Check which CSS files are loaded directly vs via @import
4. Add missing imports to the orchestrator, switch HTML pages to use it

**Watch out for:**
- CSS files loaded both as `<link>` AND via `@import` (duplicate downloads)
- Pages with their own CSS chain (legal pages, beta pages) — check if they should share the main chain
- Element selectors (`p {}`, `h1 {}`) in component CSS that could accidentally affect other pages

### Phase 5 — Sensitive Data Protection (Risk: 🟢 Low)

For PII/birth data stored on the client:
- `localStorage` → persists across sessions, viewable in devtools → **Application → Local Storage**
- `sessionStorage` → persists across refresh (same tab), cleared on tab close

The migration is a simple string replacement — API is identical:
```javascript
// Before — persisted forever, viewable in devtools
localStorage.setItem('__SAJU_DATA__', JSON.stringify(apiResponse));
localStorage.getItem('__SAJU_DATA__');
localStorage.setItem('__FORM_VALUES__', JSON.stringify(formData));

// After — cleared when tab closes
sessionStorage.setItem('__SAJU_DATA__', JSON.stringify(apiResponse));
sessionStorage.getItem('__SAJU_DATA__');
sessionStorage.setItem('__FORM_VALUES__', JSON.stringify(formData));
```

**Scope decision chart:**
| Data | Storage | Rationale |
|------|---------|-----------|
| PII (birth date, name, location) | `sessionStorage` | Tab close = session end |
| API responses with personal analysis | `sessionStorage` | Re-render on refresh OK, don't persist |
| User preferences (theme) | `localStorage` | Should survive tab close |
| Anonymous session ID (history merge) | `localStorage` | Must survive for cross-session merge |
| Offline sync queue | `localStorage` | Must survive for reliable delivery |

**Console.log data leak audit — step-by-step:**

Search ALL `console.log`/`console.error`/`console.warn` calls:

```bash
grep -rn "console\\.log\\|console\\.error\\|console\\.warn" --include='*.js' public/ --exclude='*.min.js'
```

For each call, check if any argument contains:
1. **Full API response objects** — e.g. `console.error('[History] Sync failed:', response.status, result)` where `result` is the complete API body
2. **User emails** — e.g. `console.log("Authenticated as:", this.user.email)`
3. **LocalStorage/sessionStorage values being logged**
4. **Raw response body snippets** — `text.substring(0, 200)` in error logs (lower risk but avoid if easy)

**Fix patterns:**
```javascript
// Before: logs email
console.log("Authenticated as:", this.user.email);
// After: log minimal identifier
console.log("Authenticated as:", this.user.id);

// Before: logs full API response on error
console.error('[History] Sync failed:', response.status, result);
// After: status code only (sufficient for debugging)
console.error('[History] Sync failed:', response.status);
```

## Pitfalls

- **Synology Drive corruption:** `node_modules/.bin/` files may be replaced with XSym metadata instead of proper symlinks. Fix: `rm broken-file && ln -s ../package/bin/file.js node_modules/.bin/file`
- **wrangler dev logging:** stdout may buffer in background processes. Use `> /tmp/wrangler-dev.log 2>&1` and `tail -f` for reliable log capture.
- **Wrangler ASSETS redirect:** Accessing `/file.html` returns 307 to `/file` (extension stripping). Use the extensionless URL with `env.ASSETS.fetch()`, or use `Response.redirect()` instead of ASSETS fetch for route-to-page mapping.
- **CSS @import order matters:** Always maintain the correct cascade order (variables → base → layout → components → utilities).
- **`Object.values()` order:** When deriving ordered arrays from JSON objects, `Object.values()` follows insertion order. Add explicit ordered array fields (`stemList`, `branchList`) to the JSON for guaranteed ordering.
- **Patch tool + template literals = syntax errors:** The `patch()` tool double-escapes backticks inside the inserted text. When inserting JavaScript code that contains template literals (`` ` ``), the tool writes `\\`` (escaped backtick) instead of a raw backtick, causing `SyntaxError: Invalid or unexpected token`. **Workaround:** Use `write_file()` to rewrite the entire file when the patch includes template literals, or structure the template string so backticks never appear inside the patch content (e.g. build HTML with string concatenation instead of template literals in the patched region).
- **package.json shell-script escape traps:** When the `scripts` field contains shell pipelines with `&&`, `cp`, or `echo`, JSON string escaping breaks in three ways that all look identical (Invalid JSON / build error). Rules: (1) Outer string uses **double quotes** only — never single quotes (the JSON parser fails). (2) Inner shell quoting: `echo "UI build done"` in shell must become `echo \"UI build done\"` in JSON (raw `\"` chars, not escaped `\\"`). (3) `&&`, `cd public/$p`, etc. are fine raw inside the JSON string — no backslash escape needed. (4) **No raw newlines inside a JSON string** — must be a single line, or use `\\n` (escaped) which is decoded to literal `\n` by the JSON parser, which shell prints as newline. (5) When in doubt, write the whole `scripts` value to a `.sh` file and reference it as `"build:ui": "bash ./scripts/build-ui.sh"` — JSON escaping is for the value, shell escaping is for the value-after-decoding. Verify with `python3 -c "import json; json.load(open('package.json'))"` before running `npm run`.
- **localStorage → sessionStorage migration breaks Router hash detection:** If you migrate PII data from `localStorage` to `sessionStorage` (for security), any Router that checks `localStorage.getItem('__SAJU_DATA__')` to determine the default route will always see `null` and route to the wrong default page. Search ALL files for the localStorage key after migration — don't assume one file is the only consumer.
- **Z-index CSS variable system:** Projects with CSS custom properties for z-index layers (e.g. `--z-modal: 5000`, `--z-overlay: 2000`) break when individual CSS files or inline styles use hardcoded `z-index` values instead of `var(--z-layer)`. Always grep for hardcoded `z-index:` values (> 100) after introducing a layer variable system, and fix them to use `var(--z-name, fallback)`.
- **Component-based frontend event delegation:** When migrating from a monolithic SPA to a Component class with declarative events (`events()` returning `{ 'click #btn': 'handlerName' }`), note that events are bound via the container's event delegation. Dynamically injected HTML (e.g. via `innerHTML` in `mounted()`) IS covered by delegation, but the `_bindEventsInternal()` method sets `_eventsBound = true` on first render — subsequent full re-renders via `render()` call it again because `render()` always calls `_bindEventsInternal()` (which is idempotent by early return). Verify by checking Component.js line order: `render()` calls `mounted()` then `_bindEventsInternal()`, so events ARE available for elements created in `mounted()`. However, manual `addEventListener` attachments in `mounted()` (not delegation) are lost on re-render.
- **Overwriting public/app/ with frontend/app/:** When the project has TWO frontend directories — an old SPA at `public/app/` and a new component-based frontend at `frontend/app/` — copying `frontend/app/ → public/app/` overwrites ALL files including `index.html` and `app.js`. This discards any custom modifications made to the old SPA (login modal, email auth, etc.). After overwrite, re-apply any custom features by editing the new component files (`components/layouts/AppShell.js` for auth UI, `app.js` for initialization). Check file counts before/after: `find public/app -type f | wc -l`.
- **`position: fixed` inside `transform` ancestor:** When a parent element has `transform: translateX(...)` (e.g. off-screen sidebar), any `position: fixed` child becomes relative to that parent instead of the viewport. This is CSS spec: `transform` creates a new containing block for `position: fixed`. Fix: append modal/overlay elements to `document.body` via JavaScript instead of nesting them inside the transformed element. Verify by checking if ancestor chain has `transform`, `will-change`, or `filter` CSS properties.
- **D1 auto-migration pattern:** Auto-creating D1 tables on the first request by catching SQL errors and running `CREATE TABLE IF NOT EXISTS` via `env.DB.exec()`. CRITICAL: multi-line template literals with D1's `exec()` can fail with `SQLITE_ERROR: incomplete input`. Always use SINGLE-LINE strings for each `exec()` call, and run each CREATE TABLE in a separate `exec()` call — never concatenate multiple statements in one string.
- **Developer bypass + logout conflict:** When `getSessionPayload()` auto-creates a session for local development (bypass pattern), explicit logout becomes impossible because the NEXT request after `location.reload()` triggers the bypass again. Fix: on logout, set a short-lived cookie (`m_log_logged_out=1; Path=/; Max-Age=10`) alongside clearing the session cookie. Check for this cookie in the bypass logic before creating a new session.
- **Frontend-backend API path mismatch after frontend swap:** After replacing a monolith SPA with a new component-based frontend, the new frontend may call API endpoints that don't exist in the backend (`/api/report/generate`, `/api/report/free-log`, `/api/just5/analyze`). Before fixing individual 404s, grep the frontend for fetch URLs: `grep -rn "fetch.*api" --include='*.js' public/app/ | grep -oP "/api/[a-z-]+" | sort -u`. Compare against the backend route table and add missing routes as aliases or stubs. A simple stub returning `{success:true, data:{}}` is sufficient for deprecated endpoints still called by the frontend.
- **injectAnalysisReport pattern:** When a new analysis engine is added alongside legacy controllers, enrich legacy API responses with new computed data by intercepting the response in the router layer. Pattern: `const response = await legacyController(request, env, url); const enriched = await injectNewData(response); return enriched;`. The inject function clones the response, parses JSON, adds new fields, and returns a new Response. This keeps legacy controllers untouched while the new frontend receives the richer data. The same pattern works for request bodies: clone the request, parse JSON, inject missing fields (e.g., `just5Data`), and forward to the legacy handler.

### Phase 6 — Domain Restructuring with File Renames (Risk: 🟡 Medium)

When you split a monolith into domain directories AND rename individual files simultaneously:

**Risk pattern:** A file moves from `src/controllers/foo.ts` → `src/domain/foo-controller.ts`, AND internal files it imports from are also renamed (`src/engine/bar.ts` → `src/saju/calculate-bar.ts`). The double move produces import paths that reference files that no longer exist at either the old OR the new location.

**Procedure:**

**Step 1 — Map all orig→dest name pairs before moving anything:**
```bash
# Create a rename mapping table
echo "src/engine/types.ts → src/saju/types.ts" >> /tmp/rename-map.txt
echo "src/engine/engine.ts → src/saju/calculate-engine.ts" >> /tmp/rename-map.txt
echo "src/analysis/engine.ts → src/saju/analyze-engine.ts" >> /tmp/rename-map.txt
echo "src/controllers/foo.ts → src/domain/foo-controller.ts" >> /tmp/rename-map.txt
```

**Step 2 — After copy, scan ALL new files for imports of old names:**
```python
import re, os
# For each new file, extract all import paths
# Check if any path component matches an OLD directory name (engine/, analysis/, controllers/)
# If it does, it needs rewriting to the new directory name
old_dirs = ['engine', 'analysis', 'controllers']
for root, dirs, files in os.walk('src'):
    for fn in files:
        path = os.path.join(root, fn)
        with open(path) as f:
            for i, line in enumerate(f.readlines(), 1):
                m = re.search(r"""from\s+['"]([^'"]+)['"]""", line)
                if m:
                    imp = m.group(1)
                    for old in old_dirs:
                        if f'/{old}/' in imp or imp.startswith(f'./{old}/'):
                            print(f"BROKEN: {path}:{i}: imports '{imp}' — references old dir '{old}'")
```

**Step 3 — Handle the `analysis/engine` vs `engine/engine` name collision:**

When BOTH `src/analysis/engine.ts` and `src/engine/engine.ts` exist at the same time, they both export different things under the same filename. After moving:
- `src/analysis/engine.ts` → `src/saju/analyze-engine.ts` (exports `analyze`)
- `src/engine/engine.ts` → `src/saju/calculate-engine.ts` (exports `calculateLayeredSynthesis`)

An import rewrite that simply changes `'../analysis/'` → `'../saju/'` AND `'../engine/'` → `'../saju/'` will turn:
- `import { analyze } from '../analysis/engine'` → `'../saju/engine'` ❌ (should be `'../saju/analyze-engine'`)
- `import { calculateLayeredSynthesis } from '../engine/engine'` → `'../saju/engine'` ❌ (should be `'../saju/calculate-engine'`)

**Fix:** After the directory rewrite pass, do a SECOND pass that resolves each import path against the file's location and verifies the target EXISTS on disk. This catches any rename that the directory-only rewrite missed.

```python
# Second pass: verify every import resolves to a real file
for root, dirs, files in os.walk('src'):
    for fn in files:
        path = os.path.join(root, fn)
        with open(path) as f:
            content = f.read()
        for m in re.finditer(r"""from\s+['"]([^'"]+)['"]""", content):
            imp = m.group(1)
            if imp.startswith('./') or imp.startswith('../'):
                target = os.path.normpath(os.path.join(os.path.dirname(path), imp))
                # Check with .ts, .js, .json extensions
                found = any(os.path.exists(target + ext) for ext in ['', '.ts', '.js', '.json'])
                if not found:
                    print(f"BROKEN: {path}: imports '{imp}' → target not found at {target}")
```

**Step 4 — Also update FILES OUTSIDE the moved directories that import from old paths.**

A controller at `src/controllers/report.ts` that imports `'../engine/engine'` needs rewriting even though the controller itself moved to `src/report/report-controller.ts`. Both the source AND the destination files' imports need updating. The verification scan in Step 3 catches these automatically — run it on the ENTIRE src/ tree, not just new files.

## Related

- [[software-development/requesting-code-review]]
- [[software-development/simplify-code]]

## Linked References

- `references/m-log-refactoring-session-20260611.md` — Session-specific audit findings
- `references/analysis-engine-injection.md` — Pattern for enriching API responses with computed analysis data (pure compute engine → router-layer injection → backward-compatible response)
- `references/extraction-completeness-checklist.md` — Checklist for verifying method→function extractions are complete across all files. **Critical: scan first, fix after — don't whack-a-mole extraction errors.** Updated 2026-06-12: added section 13 (uninitialized `self.xxx` attributes), expanded detection commands.
- `references/m-log-frontend-backend-integration-20260612.md` — Frontend-backend integration patterns for Cloudflare Workers SPA projects
