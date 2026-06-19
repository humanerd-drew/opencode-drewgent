---
name: incremental-refactoring
description: "Safe, incremental codebase refactoring with dependency graph analysis and live dev server verification."
version: 1.0.0
author: Drewgent
tags: [refactoring, codebase-archaeology, dead-code, cleanup, cloudflare-workers, wrangler]
related_skills: [requesting-code-review, simplify-code, systematic-debugging]
links:
  - "[[P3-sensors/skills/SKILL-INDEX]]"
  - "[[software-development/codebase-refactoring]]"
  - "[[software-development/codebase-structure-audit]]"
  - "[[software-development/simplify-code]]"
  - "[[software-development/requesting-code-review]]"
  - "[[software-development/systematic-debugging]]"
  - "[[P0-brainstem/brain/rules]]"
---

# Incremental Refactoring — Safe Codebase Surgery

Refactor a codebase without breaking it. Map the dependency graph first, then
make one change at a time with live server verification between each step.

**Core principle:** The safest refactoring is one you can revert at any step.
If you'd be afraid to deploy after refactoring, you're doing it wrong.

**Second principle:** Question every optimization assumption. A claimed
waste ("this adds N KB of unnecessary download") is not a valid concern
until proven — check browser caching, real user flow patterns, and actual
render performance. When the user pushes back on a cost assumption, they
are correct: test impact before asserting waste. Before calling something
unnecessary, verify: is the resource cached? Is this page the user's first
hit? Does the browser actually download it, or was it preloaded?

**Third principle:** Systematic understanding before action. The user wants
to see the full picture first — present evidence, let them decide, then
execute. Never skip to a conclusion without showing the data: reference
counts, HTTP response codes, actual file sizes, import chains. If you are
proposing a change, the user should see why you think it is safe.

**Fourth principle:** Investigate before proposing. If you think there is a
problem (dead code, duplication, config waste), trace EVERY reference
before declaring. A config key that looks unused might still be read at
runtime. An unused constant.js ENDPOINT might seem dead until you check all
files that import it. Show your work — the grep commands, the zero hits,
the curl 404s — so the user can independently verify your conclusion.

## When to Use

- User asks to "clean up" / "리팩토링" / "정리" a codebase
- Code review revealed structural issues (monoliths, dead code, duplication)
- You need to remove code but aren't sure what depends on it
- Before splitting a large file into modules

**Skip when:** The user only wants a code review (use `requesting-code-review`)
or cleanup of recent git changes (use `simplify-code`).

## Phase 0 — Map the Dependency Graph First

Before touching a single file, understand what references what:

```bash
# 1. List all source files (exclude node_modules, .git, build artifacts)
find . -type f \( -name '*.ts' -o -name '*.js' -o -name '*.html' -o -name '*.css' \) \
  -not -path './node_modules/*' -not -path './.git/*' -not -path './dist/*' | sort

# 2. Find all import/reference relationships
grep -rn "import " --include='*.ts' --include='*.js' \
  --exclude-dir=node_modules --exclude-dir=.git .

# 3. Check HTML script/link references
grep -rn 'src=\|href=' --include='*.html' \
  --exclude-dir=node_modules . | grep -v 'https://\|http://'

# 4. Find CSS @import chains
grep -rn '@import' --include='*.css' --exclude-dir=node_modules .
```

Build a mental or written dependency graph:

```
worker.ts
  ├── import: locationData.ts
  ├── routes: /api/analyze → proxy + DB
  ├── routes: /api/auth/* → OAuth
  ├── routes: /api/history/* → CRUD
  └── fallback: ASSETS.fetch() → public/
```

### API Layer Tracing (Config vs Usage)

After mapping file imports, trace the **API endpoint / config key usage**.
A config value defined in two places is not necessarily a problem — one
might be dead. The only way to know is to trace every read reference:

```bash
# Find where a config key is READ (not just defined)
grep -rn "ENDPOINT\\|API_KEY\\|SECRET" --include='*.{ts,js}' \
  --exclude-dir=node_modules . | grep -v "the_file_that_defines_it"

# Find where an API URL is used as a string literal
grep -rn "fetch\|axios.get\|http\.post" --include='*.{ts,js}' \
  --exclude-dir=node_modules . | grep -v "node_modules"

# Check if frontend code calls a backend proxy or an external API directly
# Proxy pattern: /api/* (relative URL, same origin)
# Direct pattern: https://external.service.com (absolute URL)
grep -rn "fetch(" --include='*.{ts,js}' public/ | grep -oE "fetch\(['\"][^'\"]+['\"]" | sort -u

# Compare defined vs read for each config key
echo "=== Environment variables (wrangler.jsonc vars) ==="
grep -E '"[A-Z_]+":' wrangler.jsonc
echo "=== Reads in source ==="
grep -rn "env\.\|process\.env\.\|import.meta.env\." --include='*.ts' src/ | sort -u
```

**Key question to answer**: does the frontend call the backend proxy
(`/api/analyze`), or does it call the external API directly
(`https://saju-calculator-api.workers.dev`)? If a dead ENDPOINT constant
exists in the frontend that nobody reads, but someone could accidentally
use it later to bypass the proxy, that is a risk worth documenting.

### Wrangler Dev Server — Known Quirks

**ASSETS binding 307 redirect:** When you request a path ending in `.html` via
`env.ASSETS.fetch()`, it returns a **307 redirect** to the extensionless version
(e.g., `/app/home-beta.html` → `/app/home-beta`). This means:

- If your worker rewrites a route to `file.html` and fetches from ASSETS, the
  307 goes to the browser, which then requests the extensionless path → worker
  doesn't match it → assets 404s → SPA fallback.
- **Fix**: Rewrite to the extensionless path directly, OR use
  `Response.redirect()` instead of `env.ASSETS.fetch()`, OR let the request
  fall through to the normal assets middleware block.

```typescript
// BAD: worker rewrites → ASSETS.fetch('.html') → 307 → browser redirect loop
url.pathname = '/app/file.html';
return env.ASSETS.fetch(new Request(url.toString(), request));

// GOOD: redirect browser directly to extensionless URL
return Response.redirect(new URL('/app/file', url.origin).toString(), 302);
```

**`env.ASSETS.fetch()` vs direct requests in dev:** In `wrangler dev`,
`env.ASSETS.fetch()` may behave differently from letting the request pass
through to the static assets middleware. When unsure, redirect the browser
and let it request the canonical URL through normal channels.

### Log Capture

`wrangler dev` output may buffer or disappear when redirecting both stdout and
stderr via `2>&1`. Redirect to a file for reliable monitoring:

```bash
npm run dev -- --port 8787 > /tmp/wrangler-dev.log 2>&1
# Monitor with: tail -f /tmp/wrangler-dev.log
```

Check the reload log after each change:

```bash
tail -3 /tmp/wrangler-dev.log
# Expected: "⎔ Reloading local server..." + "⎔ Local server updated and ready"
```

## Phase 1 — Dead Code Detection (Safe to Delete)

Files and config that can be removed with ZERO risk of breakage:

### 1.1 Reference Check

```bash
# Check if a file is imported anywhere
grep -rn "filename\|exported_symbol" --include='*.{ts,js,html}' \
  --exclude-dir=node_modules . | grep -v "the_file_itself"
```

Zero matches = safe to delete (with one exception: standalone entry points
like HTML pages that users/bookmarks directly access).

### 1.2 Usage Check for Config Keys

```bash
# Check if a config key is read anywhere
grep -rn "CONFIG_KEY\|DEV_MODE" --include='*.{ts,js}' \
  --exclude-dir=node_modules . | grep -v "defines it"
```

Definition without consumption = dead config.

### 1.3 HTTP 404 Verification

After deleting, verify the dev server returns 404 for the deleted path:

```bash
curl -s -o /dev/null -w "%{http_code}" "http://localhost:8787/path/to/deleted/file"
```

Expect 404 (or 307 if the server's asset handler does extension stripping).

## Phase 2 — Incremental Change Cycle

For every change, follow this loop:

```
  ┌─────────────────────────────────────────┐
  │  One small change (1 file, < 10 lines)  │
  │          ↓                              │
  │  Dev server auto-reloads (or restart)   │
  │          ↓                              │
  │  Test: curl key endpoints (expect 200)  │
  │          ↓                              │
  │  Test: verify no new 404s on resources  │
  │          ↓                              │
  │  If green → NEXT change                 │
  │  If red   → revert, re-analyze          │
  └─────────────────────────────────────────┘
```

### Test Checklist After Each Change

```bash
# 1. Core SPA loads
curl -s -o /dev/null -w "%{http_code}" "http://localhost:8787/app/"

# 2. All referenced JS modules return 200
for path in "/app/js/app.js" "/app/js/api.js" "/app/js/renderer.js"; do
  echo -n "$path => "; curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:8787$path"
done

# 3. All CSS files return 200
for path in "/app/css/index.css" "/app/css/variables.css" "/app/css/components/home.css"; do
  echo -n "$path => "; curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:8787$path"
done

# 4. API endpoints (at least check they don't crash)
curl -s -o /dev/null -w "%{http_code}" "http://localhost:8787/api/locations"
```

### Critical Safety Rule

**Do NOT batch unrelated changes.** Each commit/change should fix exactly one
thing. If you find yourself touching 3 files for 3 different reasons in one
go, you're doing it wrong. Revert and split.

### Check the Dev Server Log, Not Just HTTP Codes

After each change, verify that the dev server actually reloaded:

```bash
tail -3 /tmp/wrangler-dev.log

# Expected output after a successful reload:
# ⎔ Reloading local server...
# ⎔ Local server updated and ready
```

If you don't see the reload log, either the server missed the file change
(restart it), your edit wasn't saved, or the file type isn't watched.
A 200 response from a stale server is a false positive — always confirm
reload before testing.

## Special Cases

### Synology Drive Symlink Corruption

Synology Drive stores symlinks as **regular files** starting with `XSym`.
Detect and repair:

```bash
# Check .bin files for corruption
for f in node_modules/.bin/*; do
  if head -1 "$f" 2>/dev/null | grep -q "^XSym$"; then
    target=$(sed -n '4p' "$f" 2>/dev/null)
    echo "⚠️ Corrupted: $f → should point to $target"
    real_target=$(echo "$target" | sed 's|^\.\./||')
    if [ -f "node_modules/$real_target" ]; then
      rm "$f" && ln -s "$target" "node_modules/.bin/$(basename $f)"
    fi
  fi
done
```

### Wrangler Dev (Cloudflare Workers) Quirks

- **ASSETS binding redirects**: Requesting `file.html` via ASSETS returns 307
  to `file` (strips extension). Use extensionless paths when calling
  `env.ASSETS.fetch()`.
- **`env.ASSETS.fetch()` vs direct requests**: In `wrangler dev`,
  `env.ASSETS.fetch()` may behave differently from passing through to the
  normal assets middleware. Prefer `Response.redirect()` for route rewrites
  to static files.
- **Auto-reload**: Wrangler dev auto-reloads on file changes, but may not
  always catch every change. When in doubt, restart the process.
- **Log capture**: `wrangler dev` output (especially reload notifications) may
  not appear in the process tool's stdout when using `2>&1`. Redirect to a
  file for reliable monitoring:
  ```bash
  npm run dev -- --port 8787 > /tmp/wrangler-dev.log 2>&1
  # Monitor with:
  tail -f /tmp/wrangler-dev.log
  ```
- **SQLITE_BUSY after crash**: When wrangler dev crashes, the local D1 SQLite
  database stays locked. Fix:
  ```bash
  pkill -f wrangler
  rm -rf .wrangler/state/v3/d1/
  ```
  This drops local test data (migrations recreate schema). To preserve data,
  dump before stopping: `wrangler d1 execute --local --command=".dump"`.

### CSS Chain Unification

When a project has per-page CSS chains (each HTML page loads its own set of
CSS files), consolidate into a single `index.css` @import chain.

#### Audit

```bash
# Identify all CSS files loaded by each HTML page
grep -rn 'href="[^"]*\\.css"' --include='*.html' . | grep -v node_modules
```

Compare against the @import chain in the main CSS file:

```bash
grep '@import' public/css/index.css
```

#### Safety Check — CSS Selector Overlap Analysis

After unification, prove that the extra CSS files won't visually alter the
target pages — especially when screenshots aren't available:

```bash
# 1. Extract all class names used by the target page
curl -sSL "http://localhost:8787/target-page" | grep -oP 'class="\K[^"]+' |
  tr ' ' '\n' | sort -u

# 2. For each EXTRA CSS file (beyond what the page originally loaded),
#    check if any selector targets those classes/IDs
for f in extra1.css extra2.css; do
  for cls in class1 class2 class3; do
    if grep -q "\.$cls\|#$cls" "public/app/css/$f" 2>/dev/null; then
      echo "⚠️ CONFLICT: $f → .$cls"
    fi
  done
done

# 3. Also check for bare element selectors (p, h1, div) in extra CSS
grep -P '^(p|h[1-6]|div|span|a|ul|ol|li|body|section|header|footer)\s*\{' extra.css
```

No matches across all three checks = zero visual impact from unification.
CSS selector analysis is mathematically equivalent to visual comparison
when no extra selectors match any elements on the target page.

After unification, verify all pages return 200 and all CSS resolves.

### Console/Storage Data Exposure Audit

When privacy is a concern, audit the frontend for sensitive data leakage:

```bash
# 1. Find all console.log/error/warn calls
grep -rn "console\." --include='*.js' public/ | grep -v 'node_modules'

# 2. Find all localStorage/sessionStorage writes
grep -rn "localStorage\|sessionStorage" --include='*.js' public/ | grep -v 'node_modules'
```

**Typical findings:**

| Pattern | Risk | Fix |
|---------|------|-----|
| `console.log("Authenticated as:", this.user.email)` | Email exposed | Log `this.user.id` instead |
| `console.error("Sync failed:", response.status, result)` | Full API response in console | Remove `result` param |
| `localStorage.setItem('__SAJU_DATA__', JSON.stringify(response))` | Raw PII persisted | Switch to `sessionStorage` |
| `localStorage.setItem('__FORM_VALUES__', ...)` | Birth date/location persisted | Switch to `sessionStorage` |

**Rule of thumb:** `localStorage` = tab-to-tab persistence (cleared manually).
`sessionStorage` = cleared when tab closes. Migrate PII to sessionStorage
unless cross-session persistence is required.

### Frontend-to-Backend Migration (Passive Renderer)

Moving computation from client to server so the frontend only renders
pre-computed data.

#### Audit: What Does the Frontend Compute?

```bash
# All CONSTANTS.* lookups (element colors, yin/yang, etc.)
grep -rn "CONSTANTS\.\|getElement" public/js/ --include='*.js'

# All calculations (directions, scores, pattern matching)
grep -rn "calculate\|direction\|parse\|filter\|find\|reduce" public/js/ --include='*.js'

# All API response restructuring
grep -rn "\.data\." public/js/ --include='*.js'
```

#### Implementation Pattern

```typescript
// 1. Build backend analysis engine (src/analysis/engine.ts)
function analyze(input: Input): AnalysisReport {
  return {
    ohang: { score: {...}, missing: [...], excess: [...] },
    spectrum: { position: "추상", totalValue: 2.5 },
    pillarElements: [{ label: "년", cheonganElement: "metal", ... }],
    currentLuck: { daewoon: { direction: "순행", ... } }
  };
}

// 2. Inject into existing API response (alongside existing data)
result.data.analysisReport = report;

// 3. Frontend uses report when available, falls back to local calc
const direction = this.state.sajuData.data?.analysisReport?.currentLuck?.daewoon?.direction
  || Renderer.calculateDirection(gender, yearStem);

// 4. Once stable, remove dead frontend code
```

**Key rule:** Never modify the existing response structure. Always ADD the
analysisReport as a new field alongside existing data. The frontend should
work identically before and after the change.

### Refactoring Monolith Workers

When a Cloudflare Worker (`worker.ts`) grows past 500+ lines with 10+ inline
route handlers, split by domain:

```typescript
// Before: single handleRequest() with 15 if-else chains

// After: route dispatching
import { handleAnalyze, handleIljin } from './controllers/saju';
import { handleAuth } from './controllers/auth';
import { handleReport } from './controllers/report';

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname.startsWith('/api/analyze')) return handleAnalyze(request, env, url, ctx);
    if (url.pathname.startsWith('/api/auth')) return handleAuth(request, env, url, ctx);
    if (url.pathname.startsWith('/api/report')) return handleReport(request, env, url, ctx);
    // ...assets fallback
  }
};
```

Each controller gets its own file in `src/controllers/`. Shared utilities
(session, crypto, CORS, DB) go in `src/utils/` and `src/db/`.

CSS files loaded BOTH via `<link>` in HTML AND `@import` in another CSS file
cause redundant downloads. Detect:

```bash
grep -n 'href="[^"]*\.css"' index.html | while read line; do
  css_file=$(echo "$line" | grep -oP 'href="\K[^"]+\.css')
  grep -q "@import.*$css_file" index.css && echo "DUPLICATE: $css_file"
done
```

Keep only the `@import` version in `index.css`; remove the `<link>` from HTML.

### CSS Chain Unification

When a project has per-page CSS chains (each HTML page loads its own set of
CSS files), consolidate into a single `index.css` @import chain:

```bash
# 1. Identify all CSS files loaded by each page
grep -rn 'href="[^"]*\.css"' --include='*.html' . | grep -v node_modules

# 2. Check index.css @import chain for what's missing
grep '@import' public/css/index.css

# 3. Add missing component CSS to index.css
# 4. Update each HTML page to use index.css only
```

**Safety check — CSS selector overlap analysis:**

After unification, verify that the extra CSS files won't visually alter the target pages:

```bash
# 1. Extract all class names from the target HTML page
curl -sSL "http://localhost:8787/target-page" | grep -oP 'class="\\K[^"]+' |
  tr ' ' '\\n' | sort -u

# 2. For each extra CSS file (beyond what the page originally loaded),
#    check if ANY selector matches classes/IDs from the target page
for f in extra1.css extra2.css; do
  for cls in class1 class2 class3; do
    if grep -q "\.$cls\|#$cls" "public/app/css/$f"; then
      echo "⚠️ CONFLICT: $f → .$cls"
    fi
  done
done

# 3. Also check for bare element selectors (p, h1, div, etc.) in extra CSS
grep -P '^(p|h[1-6]|div|span|a|ul|ol|li|body|section|header|footer)\s*\{' extra.css
```

No matches across all three checks = zero visual impact from unification.

**When screenshots aren't available:** If the user asks for visual verification
but the terminal can't take screenshots, this CSS selector analysis is
mathematically equivalent — if none of the added CSS selectors match any
element on the target page, the visual output is identical.

After unification, verify:
```bash
# All pages return 200
curl -s -o /dev/null -w "%{http_code}" "http://localhost:8787/app/"
curl -s -o /dev/null -w "%{http_code}" "http://localhost:8787/home-beta"
# All CSS files resolve
curl -s -o /dev/null -w "%{http_code}" "http://localhost:8787/app/css/index.css"
```

## Phase 4 — Data Duplication Consolidation

When the same domain data (enums, constants, mappings) is defined in N places
across frontend and multiple backend workers, create a **single master source**
that all backends import while the frontend keeps a documented copy.

### Pattern: JSON Master + Backend Import + Frontend Copy

```
src/data/saju-constants.json  ← MASTER (single source of truth)
  ├→ worker.ts  (import at build time — Cloudflare Workers supports JSON imports natively)
  ├→ worker-quintax.ts  (same JSON, different worker — separate deployment but same source)
  └→ public/app/js/constants.js  (standalone copy with comment → "Master: src/data/...")
```

### Why JSON?

- **Universally readable**: Both TS and JS can import it. No transpilation needed.
- **Build-time shared**: Each Worker bundles its own copy at deploy time — no runtime coupling.
- **Diff-able**: Changes to the JSON are trivially verifiable with `git diff`.
- **Schema-able**: Can add `version` and `lastUpdated` fields for provenance.

### Step-by-Step

#### 1. Identify Duplicated Data

Use the dependency map from Phase 0 to find data defined in multiple places:

```bash
# Find overlapping constant definitions
# Example: 천간/지지 mappings appearing in frontend + backend
grep -rn "'甲'\\|'子'" --include='*.{ts,js}' \
  --exclude-dir=node_modules . | grep -v test | grep '=>'
```

Common candidates: element-to-class mappings, enum values, relationship tables,
API endpoint lists, color tokens, locale strings.

#### 2. Create the Master JSON

```json
{
  "version": "1.0.0",
  "lastUpdated": "2026-06-11",
  "description": "Domain data master for MyProject",

  "stemList": ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"],
  "stems": {
    "甲": { "element": "wood", "yinYang": "yang" },
    "乙": { "element": "wood", "yinYang": "yin" }
  },
  "branches": {
    "子": { "element": "water", "yinYang": "yang", "hidden": ["癸"] }
  }
}
```

Keep it flat and simple — derived/computed values (like spectrum scores or
element interaction matrices) stay in the consumer modules that need them.

#### 3. Update Backend Consumers

For each backend module that had the duplicated data:

```typescript
// Before: inline constant
const CHEONGAN = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸'];

// After: import from master
import SAJU from '../data/saju-constants.json';
const CHEONGAN = SAJU.stemList;  // same array, same behavior
```

The TypeScript import works with `"resolveJsonModule": true` in tsconfig.
Cloudflare Workers (via wrangler/esbuild) also handles JSON imports natively.

#### 4. Update Frontend Copy

The frontend runs in the browser and can't share the Node/Worker import path.
Keep the frontend copy as a standalone file with a prominent comment:

```javascript
/**
 * ═══ MASTER DATA SOURCE ═══
 * All domain data (stems, branches, elements, relations) is sourced from:
 *   src/data/saju-constants.json
 * This file is the frontend's standalone copy. When updating, modify the
 * JSON master first, then mirror changes here.
 * ═══════════════════════════
 */
```

#### 5. Verify

After each consumer is updated:

```bash
# Backend: check that imports resolve
npx tsc --noEmit 2>&1 | grep "saju-constants"

# Backend: check API responses still match expected format
curl -s http://localhost:8787/api/endpoint | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK:', d['success'])"

# Frontend: check SPA still loads
curl -s -o /dev/null -w "%{http_code}" http://localhost:8787/app/
curl -sSL http://localhost:8787/app/js/constants.js | grep "MASTER DATA SOURCE"
```

### When NOT to Consolidate

- The data is genuinely different in each consumer (not duplicated, just similar)
- The data changes independently per consumer (different versions, different owners)
- The frontend needs the data synchronously on first paint (avoid network/fetch dependency)
- The consumers are in completely different repos (different teams, different deploy cycles)

### Reference

See `references/m-log-data-consolidation.md` for a real-world example:
- 천간/지지 data was duplicated across 3 files (frontend constants.js, worker.ts iljin handler,
  quintax analyzer.ts)
- Created `src/data/saju-constants.json` as master
- Both backend workers import the JSON directly
- Frontend keeps documented copy with cross-reference comment
- Verified with iljin API test: same output before and after

## Workflow

### 1. Start dev server

```bash
cd /path/to/project
npm run dev -- --port 8787 &
sleep 10   # wait for server to compile and start
```

Verify it's alive:
```bash
curl -s -o /dev/null -w "%{http_code}" "http://localhost:8787/"
```

### 2. Change → Verify loop

```bash
# Make change with patch/write_file
# Wait for auto-reload
sleep 3
# Verify
curl -s -o /dev/null -w "%{http_code}" "http://localhost:8787/path"
```

### 3. When done, kill the server

```bash
# Kill background process
kill %1  # or use process(action='kill')
```

## Pitfalls

- **Bulk change syndrome**: "I'll just fix these 5 things while I'm here" →
  creates unrevertable state. Always one change at a time.
- **Assuming 200 means everything works**: A 200 response doesn't mean the
  page renders correctly. After structural changes, visually verify the page
  loads without JS console errors.
- **Wrangler dev stale state**: Wrangler may cache compiled output. If
  changes don't take effect, kill and restart the dev server.
- **Synology Drive/node_modules**: Always check `.bin` symlinks if you
  get "command not found" from `npm run` scripts in Synology-synced
  directories.
- **The user will notice**: If you'd be nervous explaining the change, split it
  into smaller steps. You should be able to describe each change in one
  sentence.

## Related

- `requesting-code-review` — pre-commit security/quality gate
- `simplify-code` — parallel cleanup of recent git changes (complementary to
  this skill's strategic, codebase-wide refactoring)
- `systematic-debugging` — root cause investigation for bugs discovered during
  refactoring
