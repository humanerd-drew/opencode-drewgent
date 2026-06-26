---
title: Codebase Structure Audit & Safe Refactoring
name: codebase-structure-audit
type: skill
domain: software-development
description: Map dependency graphs, detect dead code, and execute one-change-at-a-time refactoring with live dev server verification.
tags: [refactoring, code-audit, dependency-mapping, dead-code]
links:
  - "[[@action/skills/SKILL-INDEX]]"
  - "[[software-development/codebase-refactoring]]"
  - "[[software-development/codebase-consolidation]]"
  - "[[software-development/incremental-refactoring]]"
  - "[[software-development/project-code-audit]]"
  - "[[software-development/simplify-code]]"
  - "[[@identity/brain/rules]]"
---

# Codebase Structure Audit & Safe Refactoring

Systematic approach to understanding a project's dependency graph and making safe, incremental changes. Designed for the "안전한 것부터 하나씩" workflow.

## When to Use

- Before refactoring a codebase you're unfamiliar with
- When asked to "구조 파악" or map file dependencies
- Before deleting files you suspect are dead code
- When consolidating duplicate resources (CSS, data files, templates)
- When planning incremental refactoring with live verification

**Do NOT use for:** greenfield architecture, performance profiling, or dependency upgrades.

## Step 1 — Map the Dependency Graph

### File Discovery
```bash
find . -type f \( -name '*.ts' -o -name '*.js' -o -name '*.css' -o -name '*.html' \) \
  -not -path './node_modules/*' -not -path './dist/*' -not -path './.wrangler/*' | sort
```

### Import/Reference Tracing
```bash
# TypeScript/JS imports
grep -rn "import " --include='*.ts' --include='*.js' \
  --exclude-dir=node_modules --exclude-dir=dist . | sort

# CSS @import chain
grep -rn "@import" --include='*.css' --exclude-dir=node_modules . | sort

# HTML script/style references
grep -rn 'src=\|href=' --include='*.html' --exclude-dir=node_modules . | sort
```

### Component Isolation Check
For each suspected subsystem, verify whether it shares a common CSS/JS entry point or maintains its own:

```bash
for html in $(find public -name '*.html' -not -path '*/node_modules/*'); do
  echo "=== $(basename $html) ==="
  grep -o 'href="[^"]*\.css[^"]*"' "$html" | sed 's/href="//;s/"//'
done
```

## Step 2 — Dead Code Detection

### File-Level Reference Check
Never delete a file before confirming zero references:

```bash
grep -rn "target-filename\|TargetModule" --include='*.{ts,js,html}' \
  --exclude-dir=node_modules . | grep -v "target-file.js"

# For CSS: check HTML href references
grep -rn "target.css" --include='*.html' --exclude-dir=node_modules .
```

### Dead Code Categories

| Signal | Likelihood | Confidence |
|--------|-----------|------------|
| `import` from broken path (e.g. `../public/js/` doesn't exist) | 100% dead | Certain |
| File exports but zero `import` from other files across project | >95% dead | High |
| Config key defined but zero `grep` hits for the key name | >95% dead | High |
| CSS file not in any `@import` chain nor directly linked from HTML | 100% dead | Certain |

### Config-Level Dead Code
```bash
grep -rn "CONFIG_KEY\|VARIABLE_NAME" --include='*.{ts,js,json}' \
  --exclude-dir=node_modules . | grep -v "definition-file"
```

## Step 3 — Risk Assessment Matrix

Before each change, classify:

| Risk Level | Criteria | Examples | Verification |
|-----------|----------|----------|-------------|
| **Zero** | Dead code, unreferenced, broken imports | Orphan files, dead config keys | grep for references |
| **Low** | Additive only, no deletion of active code | Adding CSS @import, new route | Dev server + curl |
| **Medium** | Replacing references, path changes | Moving files, changing import paths | Dev server + full test |
| **High** | Deleting active code, restructuring | Worker split, view refactors | Staging + regression |

## Step 4 — Incremental Change Cycle

Never batch changes. Each cycle:

```
1. Make ONE change (file edit)
2. Verify dev server reloaded: check "⎔ Reloading local server..." log
3. Test with curl:
   curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:PORT/path
4. For resource files: verify 200 for active, 404 for deleted
5. Confirm no new errors in dev server log
6. Proceed to next change
```

### Dev Server Setup for Testing
```bash
cd /project && npm run dev > /tmp/dev-server.log 2>&1

# Check logs
tail -f /tmp/dev-server.log

# Quick smoke test
curl -sS -D - http://localhost:PORT/key-path 2>&1 | head -15
```

## Step 5 — Structural & Architecture Gap Analysis

### 5a. Resource & Data Duplication

Identify structural inefficiencies:

1. **Unshared resources** — Pages/features with separate CSS/JS entry points that could share a common base
2. **Duplicate data** — Same domain data (enums, constants, mappings) defined in N places
3. **Orphaned build artifacts** — Hashed bundle files in `assets/` with zero HTML references
4. **Disconnected templates** — Template files not consumed by any code

### 5b. Architecture Pattern Inventory

Catalog the project's architectural decisions to diagnose maintenance friction:

```bash
# 1. Routing strategy — hash-based vs history API vs file-system routes
grep -rn 'hashchange\|window.location.hash\|Router\|createBrowserRouter' \
  --include='*.{ts,js}' --exclude-dir=node_modules . | head -10

# 2. State management approach
grep -rn 'localStorage\|useState\|createStore\|reducer\|signal\|store' \
  --include='*.{ts,js}' --exclude-dir=node_modules . | head -10

# 3. Framework detection
grep -rn 'extends Component\|React\|Svelte\|Vue\|Preact\|createApp' \
  --include='*.{ts,js}' --exclude-dir=node_modules . | head -5

# 4. Build tooling
ls package.json | xargs -I{} node -e "const p=require('{}'); \
  console.log('build:', p.scripts?.build || '(none)'); \
  console.log('dev:', p.scripts?.dev || '(none)');"

# 5. CSS architecture — bundled, scoped, or global flat files?
grep -rn '@import' --include='*.css' --exclude-dir=node_modules . | wc -l
echo "---"
grep -rn '<link.*href.*\.css' --include='*.html' --exclude-dir=node_modules .
```

### 5c. Maintenance Friction Diagnosis

For each finding, classify the pain level and root cause:

| Finding | Friction Signal | Typical Root Cause |
|---------|-----------------|-------------------|
| Custom hash router (100+ loc) | Route changes break UI state | No framework-provided router |
| Manual DOM in views (`innerHTML + join`) | Hard to debug, hard to extend | No reactive component model |
| `localStorage` as primary state store | State sync bugs across views | No state management layer |
| Duplicate API service files | Inconsistent return values | No shared client layer |
| No build step (raw ESM) | ~50 HTTP requests, no HMR | Missing bundler |
| Manual CSS cache-busting (`?v=2.4.0`) | Stale CSS in production | No asset hashing |
| if/else route matching in worker | Route logic mixed with business logic | No backend router framework |
| 30+ CSS files, some loaded multiple ways | Style conflicts, dead rules | No CSS architecture |

Present findings with **concrete file paths and line counts**, then let the user decide which pain points matter most.

### 5d. Language & Type Consistency Check

```bash
# Check if Frontend and Backend use the same language
echo "Backend: $(find src -name '*.ts' 2>/dev/null | wc -l) .ts files"
echo "Frontend: $(find public -name '*.js' 2>/dev/null | wc -l) .js files"
echo "Frontend: $(find public -name '*.ts' 2>/dev/null | wc -l) .ts files"

# Check for shared types between FE/BE
grep -rn 'export interface\|export type' --include='*.ts' --exclude-dir=node_modules src/ | head -5
```

Mismatched languages (TS backend, JS frontend) means no shared types — a common source of API contract bugs.

## Step 6 — Framework Migration Path Evaluation

When the project's architecture friction is high enough to warrant a framework change, follow this evaluation pattern.

### 6a. Backend Framework Options (Cloudflare Workers)

| Framework | Native CF Workers | Routing | Middleware | Type RPC |
|-----------|-------------------|---------|------------|----------|
| **Hono** | ✅ First-class | `.get()/.post()` groups | CORS, auth, validation | `hono/client` RPC |
| Itty Router | ✅ | Basic pattern matching | Manual | None |
| Plain CF Workers (current) | ✅ | Manual if/else chain | Manual | None |

**Hono recommendation**: Zero migration risk — controllers are pure functions that Hono route handlers can call directly. CORS, auth, and validation become middleware instead of inline code. Migrate one route group at a time.

### 6b. Frontend Framework Options (SPA)

Pragmatic ranking for a solo-maintained CF Workers SPA:

| Framework | Bundle Impact | Reactivity Model | Migration Effort | Best For |
|-----------|--------------|-----------------|-----------------|----------|
| **Svelte** | ~2KB gzip | Compiler-based, true reactivity | Medium (per-view) | Solo devs, minimal boilerplate |
| **Preact + Signals** | ~4KB gzip | Fine-grained reactivity | Medium | React-ecosystem familiarity |
| **Solid** | ~3KB gzip | Signal-based, JSX | Medium | Signal fans who want JSX |
| **React** | ~40KB gzip | Virtual DOM | High | Team hires |
| **Alpine + htmx** | ~10KB gzip | DOM-driven | Low | Keep existing HTML, partial enhancement |
| Vanilla JS (current) | 0KB | None (manual) | Zero | High maintenance cost |

### 6c. Migration Strategy

**Always incremental — never rewrite from scratch.**

1. **Hono first** (1-2 hours, low risk):
   - Controllers remain unchanged; only worker.ts routing layer changes
   - CORS becomes middleware
   - Route groups can be migrated independently

2. **Choose frontend framework** based on pain tolerance:
   - **Svelte + Vite**: New build output in `public/app-svelte/`, worker serves it first, fall back to old SPA
   - One view at a time: convert `DashboardView.js` → `Dashboard.svelte`, verify, then the next view
   - Shared components migrate first (atoms → molecules → organisms → views)

3. **Shared type layer** (optional, high value):
   - Extract API response/request types into a shared `types/` directory
   - Both Hono backend and Svelte frontend import from the same types
   - Eliminates API contract bugs between frontend and backend

### 6d. Common Migration Pitfalls

- **Don't mix routers** — Keep hash-based routing during incremental migration; switch to framework router only after all views are migrated
- **CSS bleed** — Svelte scopes CSS by default; old global CSS won't affect new components. Keep old `index.css` for unmigrated views.
- **PortOne SDK** — It loads via `<script>` tag; framework integration needs `window.PortOne` reference or a wrapper component
- **OAuth redirect flow** — Naver/Google callbacks go to backend endpoints; frontend framework change doesn't affect them
- **PWA service worker** — `sw.js` is independent of UI framework; keep it as-is during migration

## Pitfalls

- **Wrangler `env.ASSETS.fetch()` doesn't resolve extensionless URLs** — Prefer `Response.redirect()` over internal ASSETS fetch for URL rewrites.
- **Synology Drive corrupts symlinks** — If `node_modules/.bin/*` files show `XSym` header, delete and recreate symlink.
- **`@import` vs `<link>` CSS loading** — Files loaded both ways cause duplicate downloads.
- **ESM import paths** — `grep "from 'module'"` misses `from './module.js'`. Check both patterns.
- **Memory tool for user preferences** — Workflow preferences belong in SKILL.md, not just memory.

## Related Skills

- [[software-development/requesting-code-review]]
- [[software-development/simplify-code]]
