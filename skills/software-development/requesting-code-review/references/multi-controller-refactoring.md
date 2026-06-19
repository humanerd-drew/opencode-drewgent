# Multi-Controller Refactoring & LLM Consolidation

## Worker Route Splitting (Monolithic → Controller Pattern)

When a single worker.ts (500+ lines) handles all routes inline, split into
controllers while keeping the existing behavior:

### Pattern

```
worker.ts (router only: ~100 lines)
  ├── import { handleAnalyze } from './src/controllers/saju';
  ├── import { handleNaverAuth } from './src/controllers/auth';
  ├── import { handleHistory } from './src/controllers/history';
  └── ...
  └── export default { fetch: dispatch };
        └── url.pathname === '/api/analyze' → handleAnalyze(request, env, url, ctx)
        └── url.pathname === '/api/auth/naver' → handleNaverAuth(request, env, url)
        └── ...
        └── url.pathname.startsWith('/api/history') → handleHistory(request, env, url)
        └── /* → env.ASSETS.fetch(request) (SPA fallback)
```

### Controller Signature Convention

All controllers should share the same signature for consistency:

```typescript
export async function handleXxx(
  request: Request,
  env: Env,
  url: URL,
  ctx?: any,  // only needed for ctx.waitUntil() etc.
): Promise<Response>
```

### Migration Steps

1. **Extract one route at a time** — don't split all at once
2. **Maintain the same request.body parsing** — controllers should handle their own parsing
3. **Keep shared utilities** (CORS, security headers, session) in `src/utils/`
4. **Keep analysis/processing** (analysisReport injection) in the router layer

### Cross-Cutting Concerns

Some logic should stay in the router layer, not in controllers:

```typescript
// worker.ts router — NOT in controller:
const response = await handleAnalyze(...);
return await injectAnalysisReport(response, env);  // adds computed data
```

## LLM Utility Unification

When multiple controllers independently implement similar DeepSeek/NVIDIA callers:

### Problem

```typescript
// report.ts — own callDeepSeek, callNvidiaWithFallback
// comprehensive-report.ts — own callLLMJson
// dating-report.ts — own callLLMJson
// saju.ts — own callNvidiaWithFallback
// 4 implementations of essentially the same thing
```

### Fix: One `src/utils/llm.ts`

```typescript
// Centralized in src/utils/llm.ts:
export async function callDeepSeek(env, systemPrompt, userContent, maxTokens?)
export async function callNvidiaWithFallback(env, systemPrompt, userContent, maxTokens?)
export async function callLLMJson(env, systemPrompt, userContent, maxTokens?, temperature?)
  // 1. Try DeepSeek
  // 2. Fallback to NVIDIA 3-key
export function extractJsonObject(text: string): any
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| DeepSeek first, NVIDIA fallback | DeepSeek is faster/cheaper; NVIDIA is more reliable as backup |
| `callLLMJson` throws on total failure | Caller should handle errors; no silent failures |
| Return `{ text, source, usedKey }` | Lets callers know which provider/key succeeded |
| 28s per-key timeout for NVIDIA | Stays under Cloudflare's 30s limit per invocation |

### LLM Provider Key Verification

When a controller's LLM call fails but direct `curl` tests work, the issue
is likely **not the key**. Verify systematically:

1. **Test each provider directly** with `curl --max-time 15`:
   - DeepSeek: `https://api.deepseek.com/v1/chat/completions`
   - NVIDIA: `https://integrate.api.nvidia.com/v1/chat/completions` (model: `deepseek-ai/deepseek-v4-pro`)
2. **Use the EXACT same payload** as the controller (model, temperature, max_tokens, `chat_template_kwargs`, `response_format`)
3. **Check the prompt size** — the controller's `buildUserContent()` may generate a very long prompt that takes >28s. The keys work; the prompt is too large.
4. **Check the controller's LLM call sequence** — some handlers skip DeepSeek and directly call NVIDIA (`handleGenerateFreeLogReport` does this). Fix by switching to `callLLMJson` which tries DeepSeek first.
5. **Check `.dev.vars` exists** when working from a different mount path (e.g., Synology Drive vs SMB/wrangler dev). Copy it explicitly if missing:
   ```bash
   cp /source/path/.dev.vars ./ # don't assume auto-sync
   ```

### Migration Pattern

```typescript
// BEFORE:
async function callNvidiaWithFallback(env, ...) { /* 60+ lines */ }

// AFTER:
import { callLLMJson, extractJsonObject } from '../utils/llm';

// Replace direct NVIDIA call with callLLMJson:
const genResult = await callLLMJson(env, systemPrompt, userContent);
const parsed = extractJsonObject(genResult.text);
```

## Analysis Engine → Report Pipeline Integration

When an analysis engine (producing structured data about Saju pillars) needs to
feed into a report controller (which expects a different data format):

### The Gap

```
Calculator API output → analysisReport (our format)
                     → just5Data (legacy format expected by report controller)
                     → AI prompt → LLM → polished report
```

### Fix: Dual-Layer Injection

1. **Router layer** (`worker.ts`): Before calling controller, compute analysis
   and inject it into the request body in the format the controller expects:

```typescript
if (url.pathname === '/api/report' && request.method === 'POST') {
  const body = await request.clone().json() as any;
  if (body.sajuData && !body.just5Data) {
    const report = analyze({ ... });
    (body as any).just5Data = {
      기질형스펙트럼: report.spectrum,
      오행집계: report.ohang.score,
      layer1: { 대운분석: { ... } },
      ...
    };
    const modified = new Request(request.url, {
      method: 'POST',
      headers: request.headers,
      body: JSON.stringify(body),
    });
    return handleGenerateFreeLogReport(modified, env, url);
  }
}
```

2. **Controller layer** (`report.ts`): Add fallback chain in prompt builder:

```typescript
// Each field tries: just5Data -> sajuData -> {} (empty)
const spectrum = just5Data?.기질형스펙트럼 || sajuData?.기질형스펙트럼 || {};
```

This way:
- New requests → analysis engine auto-injects → controller works
- Legacy requests with just5Data → controller works unchanged
- No breaking changes

## env.ASSETS.fetch() Quirk in Wrangler Dev

When using `env.ASSETS.fetch(newReq)` with a rewritten URL (e.g., changing
`/home-beta` to `/app/home-beta`), the ASSETS binding may return 404 in wrangler
dev mode even though the same URL returns 200 when accessed directly through the
browser.

**Fix:** Use a 302 redirect instead of internal ASSETS fetching for URL rewrites:

```typescript
// BROKEN (404 in wrangler dev):
url.pathname = '/app/home-beta';
const newReq = new Request(url.toString(), request);
return env.ASSETS.fetch(newReq);

// WORKS:
return Response.redirect(new URL('/app/home-beta', url.origin).toString(), 302);
```

The browser follows the redirect, and the canonical URL reaches the assets
handler through the normal request path, which works correctly.
