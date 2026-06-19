# CF Worker Restructuring — Session Reference

## 3-Way Data Duplication Pattern

When saju/four-pillars domain data exists in three places:

| Data | Frontend (`constants.js`) | Worker (`worker.ts`) | Quintax (`analyzer.ts`) |
|------|--------------------------|---------------------|------------------------|
| 천간 10개 문자 | `STEMS` key | `CHEONGAN` array | `CHEONGAN_OHANG` key |
| 지지 12개 문자 | `BRANCHES` key | `JIJI` array | `JIJI_OHANG` key |
| 천간→오행 | `element` property | ❌ (uses indexOf) | `CHEONGAN_OHANG` |
| 삼합 그룹 | `THREE_HARMONIES` | `samhapGroups` (inline) | ❌ |

**Fix:** Create `src/data/<domain>-constants.json` as master. Backend imports it; frontend keeps standalone copy with `MASTER DATA SOURCE` comment header.

## Route Audit Commands

```bash
# Extract all routes with line numbers
grep -n "url.pathname ===\|url.pathname.startsWith" worker.ts

# Compare with controller exports
for f in src/controllers/*.ts; do
  echo "$(basename $f): $(grep "^export async function" $f | sed 's/.*function //;s/(.*//' | tr '\n' ' ')"
done
```

## Controller Signature Standard

```typescript
// Standard
export async function handleXxx(request: Request, env: Env, url: URL): Promise<Response> { ... }

// With execution context (for waitUntil)
export async function handleAnalyze(request: Request, env: Env, url: URL, ctx: any): Promise<Response> { ... }
```

## Analysis Report Injection Pattern

In the router layer, after the controller returns:

```typescript
async function injectAnalysisReport(response: Response): Promise<Response> {
  const body = await response.clone().json();
  if (body?.success && body?.data?.pillars) {
    body.data.analysisReport = analyze({ pillars: body.data.pillars, ... });
    return new Response(JSON.stringify(body), { status: response.status, headers: response.headers });
  }
  return response;
}
```

## Synology Symlink Repair

```bash
for f in node_modules/.bin/*; do
  if head -1 "$f" 2>/dev/null | grep -q "^XSym$"; then
    target=$(sed -n '4p' "$f")
    real_target=$(echo "$target" | sed 's|^\.\./||')
    if [ -f "node_modules/$real_target" ]; then
      rm "$f" && ln -s "$target" "node_modules/.bin/$(basename $f)"
    fi
  fi
done
```
