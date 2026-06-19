---
name: cloudflare-workers-deploy
title: Cloudflare Workers Deployment & Operations
type: skill
space: outcome
description: Debug and operate Cloudflare Workers deployments — secrets management, local-vs-deployed diagnostics, outbound API troubleshooting, and deployment workflow.
tags: [cloudflare, workers, deployment, secrets, debugging]
created: 2026-06-11
updated: 2026-06-11
links:
  - "[[software-development/systematic-debugging]]"
  - "[[software-development/cf-worker-restructuring]]"
  - "[[software-development/cf-workers-integration]]"
---

# Cloudflare Workers Deployment & Operations

## Overview

Cloudflare Workers behave differently in local dev vs production deployment. This skill covers the operational gaps: secrets sync, network differences, timeout limits, and diagnostic procedures.

## When to Use

- Deployed Worker fails but `wrangler dev` works
- Secrets / env vars don't appear in production
- Outbound API calls (NVIDIA, OpenAI, etc.) fail from Worker but work locally
- `wrangler deploy` succeeds but endpoint returns errors

## Core Principles

### Local ≠ Deployed

`wrangler dev` runs on YOUR machine. These things are different in production:

| Aspect | wrangler dev (local) | wrangler deploy (Cloudflare) |
|--------|---------------------|-----------------------------|
| Source IP | Your home/office IP | Cloudflare shared egress IP |
| Secrets source | `.dev.vars` file | `wrangler secret put` values |
| Request timeout | Unlimited | 30s (free) / 30s per fetch (paid) |
| CPU time | Unlimited | 10s (free) / 30s (paid) / 30min (unbound) |
| Memory | Local | 128MB |
| DNS resolution | System resolver | Cloudflare resolver |
| Subrequests | Unlimited | 1000 per request |

### Secrets are NOT Auto-Synced

**`.dev.vars`** — local development only, read by `wrangler dev`  
**`wrangler secret put KEY`** — production secrets, separate store

Changing `.dev.vars` does NOT update production secrets. You must run `wrangler secret put` for each key.

### Secrets Propagation

After `wrangler secret put`, secrets may take a few moments to propagate. If a test immediately after `secret put` fails, wait 30-60s or **redeploy** (`wrangler deploy`) to force a fresh version with the new secrets.

**Diagnostic tip**: If `wrangler secret put` reports success but the deployed worker still fails, and you changed the worker code at the same time, the deploy may have happened BEFORE the secret fully propagated. Run `wrangler deploy` again with no code changes — this creates a new version that picks up the current secret state.

### Local Dev: `env.ASSETS` Binding Not Available with `assets` Config

Wrangler v4 introduced a new `assets` config format:

```json
{
  "assets": {
    "directory": "./public"
  }
}
```

With this config, static files are served by workerd at the **runtime level** — the worker code never runs for matching paths. `env.ASSETS` (the `Fetcher` binding) is **not available** in the worker in local dev mode.

**Symptoms:**
- `/` returns 404 instead of serving `public/index.html` at root
- Worker code that checks `if (env.ASSETS)` and redirects inside that block never fires
- `/app/*`, `/assets/*` etc. work fine (workerd serves them directly)

**Fix:** Any root redirect or logic that depends on `env.ASSETS` must be moved **outside** the `if (assets)` block:

```typescript
// ❌ Broken — root redirect inside assets block (never runs locally)
const assets = env.ASSETS;
if (assets) {
    if (url.pathname === '/') {
        return Response.redirect('/app/', 302);  // never reached in dev
    }
    let assetRes = await assets.fetch(request);
    // ...
}

// ✅ Fixed — root redirect BEFORE the assets check
if (url.pathname === '/' || url.pathname === '') {
    return Response.redirect(new URL('/app/', url.origin).toString(), 302);
}

const assets = env.ASSETS;
if (assets) {
    let assetRes = await assets.fetch(request);
    // ... SPA fallback only
}
```

**Production note:** Deployed Workers DO have `env.ASSETS` available. Moving the redirect outside the `if (assets)` block works in both environments.

### Static Files vs Worker Code: Different Restart Rules

A critical distinction in `wrangler dev`:

| File type | Changes take effect | No restart needed? |
|-----------|-------------------|-------------------|
| Static files in `public/` | **Immediately** — workerd reads from disk on every request | ✅ Yes — edit and refresh |
| `worker.ts` and source files (`src/`) | **After workerd reloads** — `wrangler dev` auto-recompiles but takes a few seconds | ❌ Wait for "Local server updated and ready" |

**Practical rule:** If you edited an `.html`, `.css`, or `.js` file under `public/`, just refresh the browser. If you edited `worker.ts` or `src/`, wait for the reload log message before testing.

### Dual Source/Deploy Directory Pitfall (frontend/ → public/)

**Symptom:** You edit files under `frontend/app/` (JS, HTML, CSS) but the changes don't appear in the browser. The deployed site still shows old code.

**Root cause:** Many CF Workers projects maintain a **dual directory structure**:
- `frontend/` — source code (working copies edited during development)
- `public/` — deployment directory (what `wrangler.jsonc` points to via `assets.directory`)

These are independent copies. `wrangler deploy` does NOT auto-sync them unless the `npm run deploy` script explicitly copies files first.

**Detection:**
```bash
# Check which directory wrangler serves from
grep '"directory"' wrangler.jsonc
# => "directory": "./public"

# Check if your edits are in the served directory
diff frontend/app/js/views/MyView.js public/app/js/views/MyView.js

# Check what the deploy script actually syncs
grep "cp\|rsync\|sync" package.json
```

**Fix patterns (choose one):**

| Approach | How | When |
|----------|-----|------|
| Manual copy | `cp frontend/app/whatever.js public/app/whatever.js` | Quick dev iteration |
| Add to `sync:local` | Extend the npm script with `cp -r frontend/app/* public/app/` | Keep sync in existing deploy flow |
| Symlink | `ln -s ../frontend/app public/app` | Use when directory structure is stable |
| Build step | `vite build --outDir public` | When using a build tool |

**Pitfall:** The `package.json` `sync:local` script often only syncs shared packages (`core/`, `theme/`, `ui/`), NOT the app JS/HTML files. Always check what's actually in the sync script before assuming files propagate.

**Dev flow reminder:** If you edit a file and it doesn't show, run:
```bash
cp <source-file> <public-path>
# then refresh
```

### Controller Exists But Route Not Wired

**Symptom:** An API endpoint (`/api/dating/{mode}`) returns 404 even though the controller file exists at `src/controllers/dating-report.ts`.

**Common root cause:** In a modular CF Workers architecture, the worker.ts is the central router. Each controller must be:
1. **Imported** at the top of `worker.ts` (add `import { handleX } from './src/controllers/X'`)
2. **Wired** in the fetch handler as a route condition (`if (url.pathname.startsWith('/api/dating/') && request.method === 'POST')`)

**Detection:**
```bash
# Check if the controller is imported
grep "import.*dating" worker.ts

# Check if the route is wired
grep "dating" worker.ts

# Direct test
curl -s -X POST http://localhost:8788/api/dating/analyze \
  -H "Content-Type: application/json" \
  -d '{"personA":{},"personB":{}}'
# If 404 → route not wired. If 401/500 → route wired, other issue.
```

**Field pattern for this architecture:** worker.ts imports controllers but doesn't register all of them. New controllers are added to `src/controllers/` but forgotten in the central router. The lint check doesn't catch this (the controller TypeScript compiles fine on its own; it's the missing import + route in worker.ts that's the problem).

**Fix:**
```typescript
// 1. Import
import { handleGenerateDatingReport } from './src/controllers/dating-report';

// 2. Wire in fetch handler
if (url.pathname.startsWith('/api/dating/') && request.method === 'POST') {
    return handleGenerateDatingReport(request, env, url);
}
```

### Local Dev: SQLITE_BUSY (D1 Lock)

If `wrangler dev` fails with:
```
Fatal uncaught kj::Exception: workerd/util/sqlite.c++:842: failed: SQLITE_BUSY
```

**Scenario A — Stale WAL from previous instance:**
A previous `wrangler dev` instance left stale WAL files in the local D1 database. Fix:

```bash
rm -rf .wrangler/state/v3/d1/
```

Then restart `wrangler dev`. This is safe — the D1 database is a local SQLite copy re-created from your remote D1 on startup.

**Scenario B — Two `wrangler dev` instances running simultaneously:**
Running multiple `wrangler dev` processes (e.g., one on 8787 and another on 8788) creates a write conflict on the shared D1 SQLite file. Only one workerd process can hold the write lock.

Fix: Kill all but one instance:
```bash
# Kill ALL workerd processes
pkill -f "workerd.*wrangler"
# Or target specific ports
lsof -i :8787 | grep LISTEN | awk '{print $2}' | xargs kill
lsof -i :8788 | grep LISTEN | awk '{print $2}' | xargs kill
```

Then start a single fresh instance. The surviving instance may recover on its own after the conflicting process exits (SQLITE_BUSY_RECOVERY clears automatically), but it's safer to restart cleanly.

### D1 Migration Execution

D1 migrations are tracked per-database. Common pitfalls:

| Issue | Cause | Fix |
|-------|-------|-----|
| `table users already exists` | Run against a DB that already has tables but missing migration tracking | `rm -rf .wrangler/state/v3/d1` (로컬) or use `--remote` for production |
| `Migrations to be applied` shows ALL migrations (not just new ones) | 로컬 D1이 migration tracking table 없이 생성된 경우 | 방법 1: `rm -rf .wrangler/state/v3/d1` 후 재시도. 방법 2: 직접 SQL 실행으로 필요한 migration만 적용 |
| New migration not found | 파일명이 `migrations/` 디렉토리에 있고 `0006_*.sql` 형식인지 확인 | wrangler가 `migrations/` 디렉토리 스캔, 숫자 prefix로 순서 결정 |

**로컬 vs 리모트 구분:**
```bash
# 로컬 (dev DB)
npx wrangler d1 migrations apply DB_NAME

# 운영 (production DB)
npx wrangler d1 migrations apply DB_NAME --remote

# 특정 SQL 직접 실행
npx wrangler d1 execute DB_NAME --command "CREATE TABLE IF NOT EXISTS ..."
```

### Controller Export/Import Sync

When adding a new controller to a CF Workers project:

1. **Check `worker-configuration.d.ts`** — the `Env` interface must declare any new env vars
2. **Add import + route** in `worker.ts` — missing either causes 404
3. **Add to `.dev.vars`** for local dev
4. **Add `wrangler secret put`** for production

```bash
# Verify controller is wired
grep "import.*payment" worker.ts  # import exists?
grep "payment" worker.ts          # route exists?
```

## Workflow

### 1. Pre-Deploy Checklist

- [ ] `.dev.vars` has ALL keys the Worker needs
- [ ] `wrangler secret list` shows matching keys (names must match)
- [ ] Run `wrangler dev` and test all endpoints that use external APIs
- [ ] Check `worker-configuration.d.ts` or `Env` interface has all env vars declared
- [ ] Run `wrangler deploy --dry-run` to verify the build succeeds BEFORE deploying (catches import resolution failures, missing modules, TypeScript errors)

### 2. Deploy

```bash
npm run deploy
# or: npx wrangler deploy
```

### 3. Post-Deploy Verification

- Run a quick smoke test against the deployed endpoint
- Check `wrangler tail` for console.log output during the request

### 4. When Local Works but Deployed Fails

Follow this elimination chain:

#### Step A — Verify Secret Values

```bash
# Check which secrets exist (names only, values are hidden)
npx wrangler secret list

# Update a secret
echo "actual-key-value" | npx wrangler secret put SECRET_NAME
```

If secrets were just updated, add a fresh deploy:
```bash
npx wrangler deploy
```

#### Step B — Check the Error Path

Get the exact error from the deployed Worker, not from your machine:

```bash
# Live logs
npx wrangler tail --format pretty

# Or curl the failing endpoint with timing
curl -s -w "\nHTTP:%{http_code} (%{time_total}s)" https://your-worker.com/api/endpoint \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
```

Look for console.warn / console.error output in tail logs.

#### Step C — Test External API from ACTUAL Worker

If the Worker calls an external API (NVIDIA, OpenAI, DeepSeek, etc.):

1. Test the SAME API call from your local machine with the SAME credentials → does it work? (required baseline)
2. If local works but Worker fails → it's a Cloudflare-specific issue:
   - IP-based blocking / rate limiting by the upstream API
   - DNS resolution differences
   - TLS / SSL issues
   - Timeout too short for upstream response time
3. If both fail → credentials are wrong

#### Step D — Common Fixes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Fast failure (< 1s), all keys | Wrong secrets | `wrangler secret put` with correct values |
| 28-30s timeout per key | Network block or upstream timeout | Test locally, check if model/key combo is allowed from CF IPs |
| "Missing env var" | Key name mismatch | Check `.dev.vars` keys match `wrangler secret list` match `worker-configuration.d.ts` |
| "Unauthorized" / 401 | Invalid API key | Rotate the key |
| 403 Forbidden | Key doesn't have access to that model/resource | Check API provider docs, try a different model |
| Random 5xx | CPU/memory limit | Check Worker observability dashboard |

## Adding Secrets

```bash
# Read key from pass and pipe to wrangler
pass show m-log/nvidia-nim-key | npx wrangler secret put NVIDIA_NIM_KEY

# Or echo directly (avoid putting key in shell history)
echo "sk-your-key-here" | npx wrangler secret put DEEPSEEK_API_KEY
```

Secrets take effect immediately for most plans. If unsure, deploy after updating:
```bash
npx wrangler deploy
```

## Outbound API Troubleshooting

### Cloudflare to NVIDIA NIM

- **Model access varies by source IP.** Some NVIDIA NIM models work from home IP but timeout from Cloudflare IPs. This is a confirmed pattern: the SAME API key + model combo responds instantly locally but hangs at 28s+ from Cloudflare's egress IP.
- If `deepseek-ai/deepseek-v4-pro` times out from Workers, try `meta/llama-4-maverick-17b-128e-instruct` (different model family, same endpoint, same NVIDIA NIM API key).
- The `integrate.api.nvidia.com` endpoint has 28s+ response times for some models.
- Always set per-key AbortController timeout (28s max) to stay under Cloudflare's 30s fetch limit.
- **Always test the SAME model+key combination** from your local machine first to establish a baseline. If it works locally but hangs from Workers, the model is blocked/throttled on Cloudflare IPs.

### Cloudflare to DeepSeek

- `api.deepseek.com` is reachable from Workers.
- DeepSeek API keys can expire without warning.
- `DeepSeek` response_format: `{ type: "json_object" }` is supported.

## Logging in Production

```typescript
// Always log entry/exit of API calls:
console.log(`[LLM] Attempting DeepSeek...`);
console.warn(`[LLM] DeepSeek failed: ${error}`);
console.warn(`[LLM] NVIDIA key ${idx} failed (${res.status}): ${errBody.slice(0, 200)}`);
```

View these with:
```bash
npx wrangler tail --format pretty
```

## CDN Cache Busting for Static Assets

**Problem:** When deploying updated `.js` files via `wrangler deploy`, the CDN may serve cached versions. `cf-cache-status: HIT` confirms old versions are being served.

**Root cause:** Cloudflare CDN edge caches static assets. With `cache-control: public, max-age=0, must-revalidate`, the CDN can still serve cached responses. For ES modules specifically, there's a deeper issue:

ES modules are cached **by their absolute URL** in the browser. If `index.html` loads `app.js?v=2.3.1`, the `?v` busts the cache for `app.js`. But static imports within `app.js` (e.g., `import { DashboardView } from './views/DashboardView.js'`) resolve to URLs **without** the parent's query string. The browser caches `DashboardView.js` independently and never re-fetches it.

**Detection:**
```bash
curl -sI https://your-worker.com/app/js/views/DashboardView.js | grep cf-cache-status
# → cf-cache-status: HIT  (CDN cached old version)
```

**Fix — Add `?v=` to import paths in the entry module:**

```javascript
// ❌ Browser caches DashboardView.js independently, never re-fetched
import { DashboardView } from './views/DashboardView.js';

// ✅ Browser treats this as a unique URL, re-fetches on version change
import { DashboardView } from './views/DashboardView.js?v=2.4.0';
```

Also update the HTML script tag to bust the entry point:
```html
<script type="module" src="js/app.js?v=2.4.0"></script>
```

**⚠️ CRITICAL PITFALL — ES Module Singleton Duplication:**

Do NOT add `?v=` to imports of **singleton modules** that export shared state (Store, AuthManager, or any module with a mutable singleton pattern like `export const Store = { ... }`):

```javascript
// ❌ BROKEN — Creates TWO separate Store instances
import { Store } from '/app/shared/core/store.js?v=2.4.0';  // in app.js
// Later, AppShell.js imports without version:
import { Store } from '/app/shared/core/store.js';  // ← DIFFERENT instance!
```

The browser treats `store.js?v=2.4.0` and `store.js` as **different module URLs**, creating separate module instances. Each module is executed independently, so `Store.state` set by `app.js` is invisible to `AppShell.js` and vice versa. The app renders a blank screen because the shared state never synchronizes.

**Safe approach:** Only add `?v=` to **view/component class imports** (which are never singletons — each `new ViewClass()` creates a fresh instance). Keep singleton/stateful module imports unversioned:

```javascript
// ✅ SAFE — View classes are instantiated per-use, no shared state
import { DashboardView } from './views/DashboardView.js?v=2.4.0';

// ✅ SAFE — Singleton Core/Router are only imported by app.js (single consumer)
import { Router } from './core/Router.js?v=2.4.0';

// ❌ BROKEN — Imported by multiple modules, must NOT have version
import { Store } from '/app/shared/core/store.js';
import { AuthManager } from '/app/shared/core/auth.js';
```

**Why it works:** ES module resolution treats the query string as part of the module URL. `./views/DashboardView.js?v=2.4.0` is a different URL than without the param, so the browser fetches it fresh. Bump to `v=2.5.0` on the next deploy to bust all caches again.

**How to identify singletons:**
1. `export const X = { ... }` with mutable state (e.g., `Store.state`)
2. Modules imported by more than one consumer
3. Modules that maintain app-wide state (auth tokens, user data)

**Verification after deploying versioned imports:**
```bash
# Check that singleton modules do NOT have ?v=
grep -rn "from '.*store.js?v=" public/app/   # should return nothing
grep -rn "from '.*auth.js?v=" public/app/    # should return nothing

# Check that view/safely-versioned modules DO have ?v=
grep -rn "from '.*views/DashboardView.js?v=" public/app/   # should match
```

## D1 Migration Sync Pitfall

**Problem:** Local `migrations/` directory is missing migrations that were already applied to the remote D1 database. Running `wrangler d1 migrations apply --remote` re-applies old migrations, causing "table already exists" errors or wrong ordering.

**Scenario:** Two branches/dev machines. Remote D1 has migrations up to `0011`. Local `migrations/` only has up to `0005`.

**Detection:**
```bash
# Check remote migration history
npx wrangler d1 execute DB_NAME --remote --command "SELECT name, applied_at FROM d1_migrations ORDER BY name"

# Compare with local
ls migrations/*.sql
```

**Fix:** Copy missing migration files from the source (NAS, other dev machine, git history):
```bash
cp /path/to/source/migrations/0006_rebuild_myeongsik_v2.sql migrations/
```

**NAS check (for SynologyDrive-backed projects):** The NAS at `~/Library/CloudStorage/SynologyDrive-Log-Project/` may have a MORE COMPLETE version of the project with additional migrations and updated files. Always check NAS version before deploying:
```bash
# Compare migration counts
echo "Local: $(ls migrations/*.sql | wc -l), NAS: $(ls ~NAS_PATH/migrations/*.sql | wc -l)"
# Copy any missing from NAS to local before deployment
diff -q <(ls migrations/*.sql) <(ls ~NAS_PATH/migrations/*.sql)
```

**Prevention:** Keep `migrations/` in version control. Push/pull before creating new migrations. Check NAS mirror for updates before assuming local is canonical.

## Static Assets Pattern: Worker API + `public/` Directory

When building a Worker that serves BOTH a frontend (HTML/CSS/JS) AND an API, the cleanest approach is **Worker handles only `/api/*`, static files serve everything else** via `assets` config:

```toml
# wrangler.toml
assets = { directory = "public", binding = "ASSETS" }
```

### Why This Pattern

Embedding HTML directly in a Worker JavaScript file via template literals (`` ` `` `` `<div class="section">` `` ` ``) triggers **esbuild JSX confusion**:

- esbuild sees `<div` inside a template literal, treats it as JSX
- `class` is a reserved word in JSX (needs `className`) → build error: `Expected ";" but found "class"`
- This happens even though Node.js accepts the syntax — esbuild's JSX parser is the issue

The fix is NOT to escape `class` attributes or avoid template literals. The fix is to **separate concerns**:

### Structure

```
project/
├── public/
│   └── index.html         # served at / — static, no esbuild involved
├── src/
│   └── index.js           # Worker API — handles only /api/* routes
├── wrangler.toml           # assets + kv_namespaces + main
```

### Worker Logic

Keep the Worker focused on API endpoints. The static files are served automatically by workerd (local) and Cloudflare (production):

```javascript
export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Worker ONLY handles /api/* routes
    if (url.pathname.startsWith('/api/')) {
      return handleApi(request, url, env);
    }

    // Everything else — 404 (static assets are served before the Worker runs)
    return new Response('Not Found', { status: 404 });
  },
};
```

### Client-Side HTML Fetches API

The HTML page in `public/` calls the Worker's own API endpoints:

```javascript
fetch('/api/status')
  .then(res => res.json())
  .then(data => renderDashboard(data));
```

### Deploy

```bash
wrangler deploy
```

Worker + assets deploy together. `wrangler dev` serves both locally. Works identically in production.

### Pitfalls

- **`env.ASSETS` binding is NOT available locally** with `assets` config (workerd level serving). But you don't need it — static files are served before the Worker runs.
- **Worker only runs for non-static paths.** If `/` should also be handled by the Worker (e.g., redirect), use a `_redirects` file or handle it before the static fallback.
- **Static file changes require `wrangler deploy`** — unlike `wrangler dev` which reads from disk live.

## Related

- `[[software-development/systematic-debugging]]` — Root cause investigation before fixing
- `[[software-development/cf-worker-restructuring]]` — Codebase restructuring for Workers

## Reference Files

- `references/nvidia-nim-cloudflare-timeout.md` — NVIDIA NIM model access quirk: some models work locally but timeout from Cloudflare IPs
