---
name: cf-worker-restructuring
description: "Use when refactoring a Cloudflare Workers monolith into controller-based architecture. Covers dead code detection, master data consolidation, cross-source sync, and live dev-server testing."
version: 1.0.0
author: m-log session
license: MIT
metadata:
  hermes:
    tags: [cloudflare, workers, refactoring, architecture]
    related_skills: [plan, systematic-debugging, simplify-code, python-large-file-patch-drewgent]
links:
  - "[[@action/skills/SKILL-INDEX]]"
  - "[[@identity/brain/rules]]"
---

# CF Worker Restructuring

## Overview

Cloudflare Workers monoliths (a single `worker.ts` handling all routes) inevitably grow beyond maintainability. This skill provides a repeatable process for restructuring them into controller-based architecture: a thin router dispatching to per-domain controller modules.

The process emphasizes **verification at every step** via live `wrangler dev` and **understanding the full dependency graph** before touching any code.

## When to Use

- `worker.ts` exceeds 400 lines with inline route handlers
- Multiple API domains (auth, analysis, history, reports) coexist in one file
- Shared constants/data (천간/지지/오행) are duplicated across frontend and backend
- Dead files accumulate (`saju-data.js`, `ganji.js`, orphaned `src/api.ts`)
- Frontend computes data that the backend should pre-calculate

**Do NOT use for:**
- Simple routing changes (use `patch` directly)
- Adding new routes to an already-clean structure
- UI-only refactoring

## Step 1 — Map Current State

Before any code changes, build a complete map:

```bash
# All routes in worker.ts
grep -n "url.pathname ===\|url.pathname.startsWith" worker.ts

# All controller exports (if splitting)
for f in src/controllers/*.ts; do
  echo "$(basename $f): $(grep "^export async function" $f | sed 's/.*function //;s/(.*//' | tr '\n' ' ')"
done

# All env vars
grep -n "env\\." worker.ts | grep -o "env\\.[A-Z_]*" | sort -u
```

**Key principle:** Understand the full dependency graph before making any changes. The user will correct you if you miss something — capture those corrections.

**⚠️ Workflow rule: Systematic inventory before fix.** When something fails (e.g., a timeout, a missing dependency), do NOT propose a piecemeal workaround ("change the order so it uses X instead"). Instead, first find ALL components that share the same pattern, understand their purpose and intent, then design a unified fix. The user explicitly corrected this: *"단편적인 해결 방안 말고, llm을 호출하는 애들을 찾아서 그 목적과 의도를 파악하고 해결 방안을 찾아야지."*

**⚠️ Workflow rule: Root cause before workaround.** When an API call fails, prove the infrastructure works first (test with direct curl) before changing logic. The user corrected this: *"키는 정상인데 왜 에러인거지? 딥식을 먼저 쓰는게 해결책은 아니잖아."* Diagnose why the existing code fails with valid infrastructure before reordering calls.

**⚠️ Workflow rule: Never commit without user review.** The user explicitly corrected this: *"커밋을 왜해. 내가 확인도 안했는데?"* Always unstage changes and let the user review before committing. `git reset --soft HEAD~1` to undo a premature commit; `git reset HEAD .` to unstage.

## Step 2 — Dead Code Detection

Find files that exist but are never imported:

```bash
# Check if a file is referenced ANYWHERE
grep -rn "filename\.js\|filename\.ts" --include='*.html' --include='*.js' --include='*.ts' . | grep -v node_modules

# Check for unused exports
grep -rn "export const X\|export function X" --include='*.js' --include='*.ts' . | while read line; do
  symbol=$(echo "$line" | grep -oP "(?<=export const |export function |export class )\w+")
  count=$(grep -rn "$symbol" --include='*.js' --include='*.ts' --include='*.html' . | grep -v "export" | grep -v "node_modules" | wc -l)
  [ "$count" -eq 0 ] && echo "UNUSED: $symbol ($line)"
done
```

**Safety rule:** Only delete a file if zero references exist across ALL file types (.ts, .js, .html).

## Step 3 — Master Data Consolidation

When the same domain data (e.g., 천간/지지/오행 mappings) exists in multiple places:

1. **Create `src/data/<domain>-constants.json`** — the single source of truth
2. **Backend imports the JSON** — TypeScript with `resolveJsonModule: true` in tsconfig
3. **Frontend gets a comment header** — pointing to the master, keeping a standalone copy for browser performance

```typescript
// Backend import
import SAJU from './src/data/saju-constants.json';

// Frontend (standalone copy with reference)
/**
 * MASTER DATA SOURCE: src/data/saju-constants.json
 * Update that file first, then mirror changes here.
 */
```

**Verify after consolidation:** All three locations produce identical output for the same input.

## Step 4 — Controller Extraction

Extract each route domain into its own controller file under `src/controllers/`:

```typescript
// src/controllers/saju.ts
export async function handleAnalyze(request: Request, env: Env, url: URL, ctx: any): Promise<Response> { ... }
export async function handleIljin(request: Request, env: Env, url: URL): Promise<Response> { ... }
```

All controller signatures should be uniform: `(request, env, url) → Promise<Response>`. The one exception is `ctx` (execution context) for handlers that need `waitUntil`.

After extraction, `worker.ts` becomes a thin router (50-100 lines):

```typescript
import { handleAnalyze, handleIljin } from './src/controllers/saju';

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === '/api/analyze') return handleAnalyze(request, env, url, ctx);
    if (url.pathname === '/api/iljin') return handleIljin(request, env, url);
    // Static assets fallback
    return env.ASSETS.fetch(request);
  },
};
```

### Barrel Re-Export Pattern (preserves backward compatibility)

When **dispatching controller splitting to a subagent** (parallel split across multiple files in one round), the **agent doing the split is NOT responsible for verifying business logic** — they're moving code. To prevent the subagent from silently changing behavior:

1. **Keep the original controller file as a 1-line barrel re-export** of all the new split files.
2. **Do NOT change any importer** (route-*.ts, anywhere) — they keep importing from the original path.
3. **After all splits complete, run a full functionality audit** (see Step 4b) before declaring victory.

```typescript
// Before (monolith): src/report/dating-controller.ts — 1,565줄
export async function handleGenerateDatingReport(...) { ... }
// ... 1500줄의 private helpers ...

// After (barrel): src/report/dating-controller.ts — 1줄
export { handleGenerateDatingReport } from './generate-dating-report';
```

**Result:** Every importer (`route-report.ts` etc.) continues to work with **zero code changes**. The barrel acts as a stability boundary between mechanical refactoring and business logic.

## Step 4b — Functionality Audit After Mechanical Refactoring (필수)

**Trigger:** Whenever you delegate mechanical code movement (split, rename, restructure) to a subagent OR complete one yourself without step-by-step live testing.

The subagent's job is to move code **verbatim**. But subagents (and you, after many similar edits) can:
- **Silently swap an inline implementation for a shared utility** (e.g. `callLLMJson` → `callReportLLM`) and accidentally change behavior (different default options, different token limits, different log tags)
- **Leave dead references to removed parameters** (e.g. legacy `NVIDIA_API_KEY` after consolidating to NIM key family)
- **Use a function's default value when the caller passed an explicit value** (e.g. dropping `maxTokens: 3000` to default 1500)
- **Change a deprecated-wrapper to call the new function directly** but skip the wrapper's extra behavior (sanitize output, log tag, key append)

**Audit procedure (do ALL of these):**

1. **Diff each split file's critical functions against git HEAD** (or the original). Look for:
   - Function bodies that diverge from the original (not just moved)
   - Imports that changed (different library, different version)
   - Default parameter values that got swapped
   - Side effects that disappeared (logging, validation, etc.)

2. **Trace one hot path through the new code.** Pick a real user flow (e.g. "fetch free report") and follow it:
   - route-report.ts → handleGenerateFreeLogReport → ... → callLLMJson
   - At each step, verify the actual call site still passes what the original passed
   - If a parameter was hardcoded differently in the new code, that's a regression

3. **Search for residual references to removed/renamed things:**
   ```bash
   grep -rn "NIM_KEY\\|LegacyAPI\\|oldName" src/ --include="*.ts"
   # Each hit should be either a new key family OR a comment explaining the removal
   ```

4. **Check for ambient noise that the subagent may have added** (e.g. "this is a deprecated wrapper, can be removed" comments where the wrapper is still being used elsewhere).

5. **Verify TypeScript compiles with zero new errors:**
   ```bash
   npx tsc --noEmit 2>&1 | grep -v "src/config/ontology/" | head -20
   # Pre-existing errors in untouched files should be filtered
   # Focus on errors in the split files and their importers
   ```

6. **Smoke-test the dev server with a real API call:**
   ```bash
   npm run dev
   # In another terminal:
   curl -s "http://localhost:8787/api/..." | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK' if d.get('success') else d)"
   ```

**Anti-pattern:** "Trust the subagent's claim that the split is done." Subagents often finish with "✓ 0 errors" but the errors they filtered out are exactly the regressions that need to be caught. **Always run a fresh `tsc --noEmit` yourself, and grep for residual legacy references.**

## Step 5 — Live Testing with wrangler dev

Keep `wrangler dev` running in the background throughout the process:

```bash
npm run dev -- --port 8787 > /tmp/wrangler-dev.log 2>&1
```

After each significant change:
1. Wait for reload: `tail -3 /tmp/wrangler-dev.log | grep "Reloading\|updated"`
2. Test the affected route: `curl -s -o /dev/null -w "%{http_code}" http://localhost:8787/api/analyze ...`
3. Verify the response structure: `curl -s ... | python3 -c "import sys,json; print(json.load(sys.stdin).keys())"`

**Common issues:**
- `SQLITE_BUSY`: Kill old wrangler process with `pkill -f "wrangler dev"`, remove `.wrangler/state/v3/d1/`
- Missing env vars: Check `.dev.vars` and `wrangler.jsonc` vars section
- MiniflareCoreError: Usually a locked SQLite database from a previous instance

## Step 6 — Secret Sync & Local-vs-Production Debugging

Cloudflare Workers has **three separate channels** for environment variables. The most common production bug is "works in `wrangler dev`, fails after deploy" — almost always caused by a secret that exists in `.dev.vars` but not in production, or by an API key that works locally but is rejected from the Worker's network.

### The Three Tiers

| Tier | Mechanism | When it applies | Example use |
|------|-----------|-----------------|-------------|
| **Build-time vars** | `wrangler.jsonc` → `"vars": {...}` | Always (local + production) | `BASE_URL`, `NAVER_CLIENT_ID`, `SAJU_API_ENDPOINT` |
| **Local dev secrets** | `.dev.vars` file | `wrangler dev` only | API keys, client secrets, `IS_LOCAL_DEV=true` |
| **Production secrets** | `wrangler secret put <NAME>` | Deployed worker only | `NVIDIA_NIM_KEY`, `DEEPSEEK_API_KEY`, `SESSION_SECRET` |

### Critical Rule

**`.dev.vars` is NEVER deployed.** When you add or update a secret in `.dev.vars` for local development, you MUST also run `wrangler secret put <NAME>` to sync it to Cloudflare. There is no automatic sync. The values can drift independently, and you cannot read existing secret values from the CLI (`wrangler secret list` shows names only).

### Debugging "Works in dev, fails in production"

1. **Check `.dev.vars`** — what secrets does your code access that aren't in `wrangler.jsonc`?
2. **List production secrets** — `npx wrangler secret list`
3. **Compare names** — any secret name in `.dev.vars` that's NOT in the production list is a candidate for the bug
4. **Even if names match, values may differ** — the `.dev.vars` value may have been rotated without re-running `wrangler secret put`. Since you cannot read existing values, the only fix is to overwrite with the known-good value:
   ```bash
   npx wrangler secret put SECRET_NAME
   # (paste value, Ctrl+D)
   ```
5. **For batch sync**, pipe from env file:
   ```bash
   # Not possible directly — wrangler secret put reads stdin, one at a time.
   # Run each secret separately:
   for key in NVIDIA_NIM_KEY NVIDIA_NIM_KEY_FALLBACK DEEPSEEK_API_KEY; do
     echo "Enter value for $key (or skip):"
     read -s val
     [ -n "$val" ] && echo "$val" | npx wrangler secret put "$key"
   done
   ```

### Common patterns that trigger this bug

- **Key rotation** — You received new API keys (NVIDIA, DeepSeek, etc.) and updated `.dev.vars` but forgot `wrangler secret put`
- **`IS_LOCAL_DEV` flag** — A flag like `IS_LOCAL_DEV=true` in `.dev.vars` used for auth bypass or debug logging. In production it's undefined, which is usually correct behavior, but can catch you off guard if the code checks `env.IS_LOCAL_DEV === 'true'`
- **New secret added to code** — You added `env.NEW_API_KEY` to the code and put it in `.dev.vars` but never added it as a production secret
- **Legacy key references** — The code may reference key names that were never defined (e.g., `env.NVIDIA_API_KEY` singular, with no `_1` suffix — filtered out by `.filter(Boolean)` but never useful)

### API Key Direct Verification

When the worker reports "All keys exhausted" or you see 401/403 errors from an API, determine whether the **key itself** is invalid or the **Worker environment** is broken by testing the key directly from the terminal:

```bash
# Test NVIDIA NIM API directly (same endpoint the worker uses)
curl -s -w "\nHTTP:%{http_code}" \
  "https://integrate.api.nvidia.com/v1/chat/completions" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"meta/llama-4-maverick-17b-128e-instruct","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'

# Test DeepSeek API directly
curl -s -w "\nHTTP:%{http_code}" \
  "https://api.deepseek.com/v1/chat/completions" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'
```

**Interpretation:**
- **Key works locally but fails from worker** → secrets drift (update with `wrangler secret put`), OR the Worker's network IP is being blocked/rate-limited by the upstream API
- **Key returns 403 from both** → the key lacks access to that specific model — test with a different model on the same provider
- **Key returns 401 from both** → key is expired or invalid — rotate the key
- **Key hangs for 28s+ from both** → network connectivity issue, DNS resolution failure, or the model name doesn't exist on that endpoint

### NVIDIA NIM Model Availability

NVIDIA NIM API keys are model-specific. A single key may work for some models but return **403 Forbidden** for others, even on the same `integrate.api.nvidia.com` endpoint. Test with different models to establish what your key has access to:

```bash
# Test each model your code uses with the SAME key
for model in \
  "meta/llama-4-maverick-17b-128e-instruct" \
  "deepseek-ai/deepseek-v4-pro" \
  "mistralai/mistral-large"; do
  echo -n "$model → "
  code=$(curl -s -o /dev/null -w "%{http_code}" \
    "https://integrate.api.nvidia.com/v1/chat/completions" \
    -H "Authorization: Bearer $KEY" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"$model\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":5}")
  echo "$code"
done
```

If one model returns 200 and another returns 403, the key simply doesn't have access to that model. Change the model in your code to one that works, rather than trying to fix the key.

### The 84-Second Diagnostic Pattern

When you see errors like `"AI generation failed after 84000ms: All NVIDIA API keys exhausted or failed"`, the math is diagnostic:

```
84,000ms ÷ 3 keys = 28,000ms per key
```

The code's timeout is 28s per key (set just under Cloudflare's 30s wall-clock limit). When ALL 3 keys time out at exactly 28s each:
1. First key → 28s timeout → `continue`
2. Second key → 28s timeout → `continue`
3. Third key → 28s timeout → all failed → error

This means the `fetch()` call to `integrate.api.nvidia.com` is **neither succeeding nor failing** — it's **timing out** completely. Likely causes: Cloudflare's network cannot reach the endpoint, DNS resolution fails inside the Worker runtime, or the upstream API is blocking Cloudflare's IP range.

If instead you see the same error in under 5 seconds, the keys are returning HTTP errors (401/403) immediately — the key values or model access are the problem.

### Timers in callLLMJson

The unified `callLLMJson` in `src/utils/llm.ts` has a subtle timer design:

```typescript
export async function callLLMJson(...) {
  // 1. DeepSeek — has its own `const start` (block-scoped inside the if)
  if (env.DEEPSEEK_API_KEY) {
    const start = Date.now();       // ← scoped to if-block
    const ds = await callDeepSeek(...);
    console.warn(`DeepSeek failed in ${Date.now() - start}ms`);
  }
  // 2. NVIDIA — has a DIFFERENT `const start` (function-scoped after the if-block)
  const start = Date.now();         // ← different variable, shadows nothing
  const nv = await callNvidiaWithFallback(...);
  throw new Error(`AI generation failed after ${Date.now() - start}ms`);
}
```

The error timer measures **only the NVIDIA fallback time**, not including DeepSeek. When you see `84000ms`, it means the 3-key NVIDIA rotation took the full 84s. DeepSeek could have failed instantly (401) or taken its own time — that's not included in the error.

### Verification

After updating secrets, the change takes effect immediately — no redeploy needed. Verify with:

```bash
# Hit an endpoint that exercises the secret
curl -s -X POST https://your-worker.com/api/endpoint \
  -H "Content-Type: application/json" \
  -d '{"test": true}' | head -100
```

Check worker logs for any `console.warn` or error output:
```bash
npx wrangler tail       # real-time logs
# or check Cloudflare Dashboard → Workers & Pages → m-log → Logs
```

**pass (Unix password store) for secrets:** If the user gives you new API keys and asks you to store them securely, use `pass`. See `references/pass-setup.md` for the initialization and usage workflow. Organize keys under a project-level directory (e.g., `m-log/`) with descriptive names.

## Step 7 — LLM Caller Consolidation

When multiple controllers each implement their own DeepSeek/NVIDIA callers, unify into `src/utils/llm.ts`:

```typescript
// src/utils/llm.ts — single source of truth for all LLM calls
export async function callDeepSeek(env, systemPrompt, userContent, maxTokens = 1500): Promise<...>
export async function callNvidiaWithFallback(env, systemPrompt, userContent, maxTokens = 1500): Promise<...>
export async function callLLMJson(env, systemPrompt, userContent, maxTokens, temperature): Promise<...>
export function extractJsonObject(text: string): any
```

**Pattern:** `callLLMJson` tries DeepSeek first, falls back to NVIDIA 3-key. This avoids duplicating the fallback logic in every controller.

**NVIDIA 3-key rotation:** Keys are tried sequentially with 28s timeout each (Cloudflare's 30s wall limit). Move from old function signatures (`callNvidiaWithFallback`) to the unified `callLLMJson` which wraps DeepSeek → NVIDIA chain.

**Verification:** Test each key directly with curl before trusting the controller:
```bash
curl -s --max-time 10 "https://api.deepseek.com/v1/chat/completions" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"hi"}],"max_tokens":5}'
```

## Step 9 — PDC-First Principle (External API as Authoritative Source)

When an external API (PDC — PersonalDateCalculator) provides computed values, **do not recalculate them**. The reason PDC is external is because saju calculations need extensive correction/bug-fixing; recalculating internally duplicates those bugs and creates drift.

**Use PDC data (always prefer it over local calculation):**
```typescript
// tenGods: PDC already computed every stem/branch relationship
const tenGod = pdcTenGods?.stems
  ? { dayMaster: dm, stems: pdcTenGods.stems, branches: pdcTenGods.branches ?? {} }
  : calcTenGod(dm, pillarElements);  // fallback only

// direction: PDC returns 'forward'/'backward', just format it
const direction = pdcDaewoonDirection === 'forward' ? '순행'
  : pdcDaewoonDirection === 'backward' ? '역행'
  : calcDaewoonDirection(gender, yearStem);  // fallback only

// wolun (monthly fortune): PDC returns 12-month array in saewoon[].wolun
wolunData = currentSw.wolun.find(w => w.month === currentMonth);
```

**Only calculate what PDC doesn't provide:**
- Ohang scores (element frequency in pillars)
- Spectrum (Qi-Zhi-Xing personality position via totalValue)
- Pillar element mappings (cheonganElement, jijiElement per pillar)
- Layer combinations (L0+L1, L0+L1+L2 with deltas)
- Persona (dominant element from ohangScore + sheng/ke relationships)

**Pass PDC data through AnalysisInput to avoid recalculation:**
```typescript
body.data.analysisReport = analyze({
  pillars: body.data.pillars,
  pdcTenGods: body.data.tenGods,
  pdcDaewoonDirection: body.data.daewoon?.direction,
  daewoonCycles: body.data.daewoon?.cycles,  // already has saewoon[].[].wolun
});
```

**⚠️ Pitfall: Verifying PDC coverage.** Before adding a new calculation to your engine, check if the external API already returns it. Typical saju data (tenGods, daewoon direction, hapChung, saewoon/wolun cycles) is already computed by PDC — only add code for what's MISSING.

## Step 8 — Cross-Source Sync

When working with NAS/SynologyDrive/SMB sources:

```bash
# Copy from stable SMB source
cp -R /Volumes/stable-source/src/controllers/ ./src/controllers/
cp -R /Volumes/stable-source/src/engine/ ./src/engine/

# Rebuild after copy (wrangler dev auto-reloads)
```

**Warning:** Synology Drive corrupts symlinks (replaces with XSym files). Fix with:
```bash
for f in node_modules/.bin/*; do
  if head -1 "$f" 2>/dev/null | grep -q "^XSym$"; then
    target=$(sed -n '4p' "$f")
    real_target=$(echo "$target" | sed 's|^\.\./||')
    [ -f "node_modules/$real_target" ] && rm "$f" && ln -s "$target" "node_modules/.bin/$(basename $f)"
  fi
done
```

## Common Pitfalls

1. **Skipping the dependency map.** Jumping into code changes without understanding the full graph leads to the user correcting you multiple times. Do step 1 thoroughly.

2. **Assuming deployment = connection.** A worker can be deployed and responding 200 at its URL without being wired into the main app. Verify by searching for `fetch()` calls and env var references. The frontend needs standalone copies for performance (no async fetch at module init). Use comments to link back to the master instead of trying to import JSON at runtime.

4. **Controller signature mismatch.** Some handlers need `ctx` for `waitUntil`, others don't. Check before writing the router.

5. **SQLITE_BUSY after restart.** Always clean up old wrangler processes and D1 state files between runs.

6. **Two wrangler instances.** After a session restart, check for stale processes:
   ```bash
   ps aux | grep wrangler | grep -v grep
   ```
   Each project path spawns its own process — they conflict on SQLite locks.

8. **`.dev.vars` is not production.** Secrets added to `.dev.vars` for local testing are NEVER deployed. After adding or rotating a secret in `.dev.vars`, run `wrangler secret put <NAME>` to sync to production. This is the #1 cause of "works locally, fails in production."

9. **No way to read existing secrets.** `wrangler secret list` shows names only, not values. To verify parity between `.dev.vars` and production, you must overwrite the production secret with the known-good value. If you're unsure which value is live, the safest bet is to re-apply from `.dev.vars`.

10. **Legacy key references in code.** When consolidating LLM callers (Step 7), verify that every key name referenced in code has a corresponding entry in either `.dev.vars` or `wrangler secret`. A reference like `env.NVIDIA_API_KEY` (singular, not `_1`/`_2`/`_3`) with no matching secret anywhere will silently fail (`.filter(Boolean)` removes it), reducing your fallback chain.

11. **Wrong project copy (Synology Drive dual-sync).** When the project is synced via Synology Drive, macOS creates separate mount points per sync task (e.g., `SynologyDrive-drewgent/` and `SynologyDrive-Log-Project/`). A project may exist in MULTIPLE directories with different versions and package.json. Always confirm which copy the user is running from before editing files. Use `pwd`, `git log --oneline -1`, or check `package.json` version field.

12. **Tool output masking of secrets.** When testing API keys, the tool replaces actual secret values with `***` in displayed output. This is display-only — the actual command has the real value. **Never** copy a `***`-masked value into a subsequent command. If you see `curl -H "Authorization: Bearer *** the `***` was only in what you saw. Read keys fresh from source files when re-testing, not from terminal output.

## Step 10 — D1 Auto-Migration & Session Storage

For local development, D1 databases are ephemeral. Auto-create tables on first handler call:

```typescript
async function ensureTables(env: Env): Promise<void> {
    try { await env.DB.prepare('SELECT 1 FROM users LIMIT 1').run(); }
    catch { await env.DB.exec("CREATE TABLE IF NOT EXISTS users (...)"); }
}
```

**⚠️ Single-line SQL requirement:** Multi-line template literals cause `SQLITE_ERROR: incomplete input`. Always use single-line strings with `env.DB.exec()`:
```typescript
// ❌ FAILS with "incomplete input"
await env.DB.exec(`CREATE TABLE users (
  id TEXT PRIMARY KEY
)`);

// ✅ WORKS
await env.DB.exec("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL)");
```

**⚠️ Error chain: D1 failure → handleMe → AuthManager.init() → blank screen.**
When `handleMe` queries the users table and D1 doesn't have it yet, the unhandled exception propagates:
```
handleMe → dbQueries.getUserWithPrimarySaju → D1_ERROR: no such table → exception
  → AuthManager.checkStatus() fails → AuthManager.init() rejects
  → App.init() stops → nothing renders → blank screen
```
**Fix both ends:**
1. Wrap the DB query in `handleMe` with try/catch:
   ```typescript
   let user;
   try { user = await dbQueries.getUserWithPrimarySaju(env.DB, payload.id); }
   catch { /* D1 not ready in dev */ }
   ```
2. Wrap `AuthManager.init()` in app.js with try/catch:
   ```typescript
   try { await AuthManager.init(); }
   catch(e) { console.warn('[App] Auth init failed (non-fatal):', e); }
   ```

**⚠️ Patch tool corrupts JS template literals:** When patching JS files that contain template literals (backtick strings `` ` ``), the patch tool may escape backticks as `\``, causing `Uncaught SyntaxError: Invalid or unexpected token`.
```javascript
// ❌ PATCHED (backtick escaped — syntax error)
return \`<div id="app">\`;

// ✅ MANUAL FIX (unescaped backtick)
return `<div id="app">`;
```
**Fix:** After patching any JS file with template literals, verify with `node --check <file>`. If the file has syntax errors, the backticks were likely corrupted. Rewrite the affected method with unescaped backticks.

**SessionStorage migration:** Moving sensitive data (API responses, PII) from localStorage to sessionStorage:
```bash
grep -rn "__SAJU_DATA__\\|__FORM_VALUES__" --include='*.js' public/
```
Same API (getItem/setItem), only the object name changes. Use `replace_all=true` in patch.

## Step 11 — CSS @theme Alias Resolution

New `index.css` from `frontend/app/` may use build-time aliases that don't resolve in static serving:
```css
/* ❌ Fails in wrangler static serve */
@import url('@theme/variables.css');
/* ✅ Relative path works */
@import url('../shared/theme/variables.css');
```

## Step 12 — Component-Based Login Modal

When the frontend uses Component.js architecture (AppShell + views), UI additions go to THREE files:

1. **AppShell.js — template**: Add `renderLoginModal()` method, call from `renderAuth()`
2. **AppShell.js — events**: Add declarative bindings via `events()` method (event delegation works for dynamically rendered elements)
3. **index.css**: Modal CSS classes

**⚠️ Frontend overwrite:** Copying `frontend/app/` → `public/app/` overwrites manual UI changes. Re-apply after each copy.

**⚠️ Auth init isolation:** Wrap `await AuthManager.init()` in try/catch in `app.js` — if it fails (D1, network), the Router still mounts and the app still renders (blank screen prevention).

## Step 13 — Cross-Source Sync

The project may exist in THREE locations (SynologyDrive working copy, SMB NAS, local `~/m-log/`). Use `rsync`:
```bash
rsync -av --exclude='node_modules' --exclude='.wrangler' /source/ /dest/
npm run sync:local  # refresh shared/ from packages/
```

**⚠️ Synology Drive corrupts symlinks:** Fix `.bin` symlinks replaced with XSym files:
```bash
for f in node_modules/.bin/*; do
  head -1 "$f" | grep -q "^XSym$" && rm "$f" && ln -s "$(sed -n '4p' "$f")" "node_modules/.bin/$(basename $f)"
done
```

## Verification Checklist

- [ ] `worker.ts` reduced from 700+ lines to under 100 (router only)
- [ ] Each controller handles exactly one API domain
- [ ] Uniform controller signature `(request, env, url) → Response`
- [ ] All original routes still return correct HTTP codes and response shapes
- [ ] Analysis report (or equivalent) still injected at router level
- [ ] Dead code confirmed unreferenced before deletion
- [ ] Master JSON changes reflected in all consumers
- [ ] `wrangler dev` reloads cleanly after each change
- [ ] Commit after each major phase (dead code, master data, controller extraction)
