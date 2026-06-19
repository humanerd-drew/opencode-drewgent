# Codebase Audit Patterns

## Dead Code Detection

Before deleting any file, verify ZERO references exist:

```bash
# 1. Check imports in JS/TS
grep -rn "module-name" --include='*.ts' --include='*.js' . | grep -v node_modules

# 2. Check HTML references (scripts, stylesheets)
grep -rn "filename" --include='*.html' . | grep -v node_modules

# 3. Check CSS @import references
grep -rn "filename" --include='*.css' . | grep -v node_modules

# 4. Check JSON/configuration references
grep -rn "filename" --include='*.json' . | grep -v node_modules

# 5. Verify via HTTP (if dev server running)
curl -s -o /dev/null -w "%{http_code}" http://localhost:PORT/path/to/file
# 200 = still served, 404 = gone
```

## Data Duplication Consolidation

When the same data appears in 2+ places (frontend JS, backend TS, separate workers):

1. **Trace ALL consumers** — grep for each occurrence, note file+line
2. **Create a single JSON source** — placed in `src/data/` (universally readable by JS and TS)
3. **Update backend** — add `import DATA from '../data/file.json'` (TypeScript with `resolveJsonModule: true`)
4. **Update frontend** — add comment header pointing to master JSON location
5. **Verify** — check that API responses didn't change format

```typescript
// Backend import pattern (TypeScript):
import DATA from '../data/saju-constants.json';

// Frontend comment pattern (JS):
/**
 * MASTER DATA SOURCE: src/data/saju-constants.json
 * Update that file first, then mirror changes here.
 */
```

## API Layer Tracing

When a project has multiple external services, trace actual connections vs perceived connections:

```bash
# 1. Find ALL external HTTP calls in the backend
grep -rn "fetch(" --include='*.ts' --include='*.js' src/ worker.ts 2>/dev/null | grep -v "env.ASSETS\|node_modules"

# 2. Find ALL external URLs in frontend code
grep -rn "https\?://" --include='*.js' --include='*.html' public/ | grep -v "node_modules\|google\|naver\|clarity\|gtag\|font"

# 3. Find ALL worker/service bindings in config files
grep -rn "workers.dev\|binding\|service" --include='*.jsonc' --include='*.toml' . | grep -v node_modules

# 4. Test each discovered service independently (is it alive?)
for url in "https://service1.workers.dev/" "https://service2.workers.dev/"; do
  echo -n "$url => "
  curl -s -o /dev/null -w "HTTP %{http_code}\n" "$url" 2>&1
done
```

### Key distinction: "deployed" vs "integrated"

A service returning HTTP 200 when curled directly does NOT mean the app uses it.
Three separate states:

| State | Evidence |
|-------|----------|
| **Deployed** | Service URL returns HTTP 200 when curled directly |
| **Configured** | Service URL/name appears in wrangler.jsonc `vars`, `services`, or `bindings` |
| **Integrated** | App code calls the service — `fetch(env.SERVICE_URL)` or `fetch('https://...')` appears in runtime code |

Always check all three. A service that is deployed (state 1) but not integrated
(state 3) may still have prototype code, reference implementations, or the user's
mental model of the system — but the app doesn't call it.

### External API Data Verification — "Check Before Build"

**CRITICAL RULE: Before implementing any new calculation, verify that the external API doesn't already provide it.**

The user called this out: "PDC에서 가져오는 결과를 대입하면 되는데 왜 자꾸 너네들을 계산하려고 하지?"
(Why do you keep trying to calculate things yourselves when the API already returns the results?)

**Pattern:**
1. Call the external API and inspect the full nested response structure
2. Map each field you need to the API response before writing calculation code
3. Only implement what the API doesn't already provide

```bash
# Step 1: Check the full response structure
curl -s "https://api.workers.dev/" -X POST -H "Content-Type: application/json" \
  -d '{"year":1991,"month":7,"day":24,"hour":6,"minute":30,"location":"서울","gender":"male"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(list(d.keys())))"

# Step 2: Drill into nested objects
curl ... | python3 -c "
import sys,json; d=json.load(sys.stdin)
cycle = d['data']['daewoon']['cycles'][0]
print('cycle keys:', list(cycle.keys()))
if 'saewoon' in cycle and cycle['saewoon']:
    print('saewoon[0] keys:', list(cycle['saewoon'][0].keys()))
    if 'wolun' in cycle['saewoon'][0]:
        print('wolun[0]:', cycle['saewoon'][0]['wolun'][0])"
```

**What to check for in a PDC-type external API before writing engine code:**

| Feature | Check if API has it | Implement yourself if missing |
|---------|-------------------|-------------------------------|
| Daewoon direction | `data.daewoon.direction` | 한국어 매핑만 필요 (순행/역행) |
| TenGods (십신) | `data.tenGods.stems/branches` | Already calculated |
| Saewoon (세운) | `data.daewoon.cycles[i].saewoon` | Yearly pillar calculation |
| **Wolun (월운)** | **`data.daewoon.cycles[i].saewoon[j].wolun`** | **Already has 12 monthly entries!** |
| Iljin (일진) | Check if daily endpoint exists | Daily pillar calculation |
| HapChung | `data.analysis.hapChung` | Only reformatting |

When in doubt, exhaustively inspect the API response before writing any engine code.

### Proxy chain tracing

For apps with a frontend + backend worker + external API:

```
Frontend (browser)
  └─ fetch('/api/analyze')       ← relative URL = same origin = worker proxy
       └─ worker.ts handler
            └─ fetch(env.EXTERNAL_API)  ← actual external call
```

Check every frontend fetch() call — is it relative (`/api/*`) or absolute
(`https://external.service`)? Relative calls go through the worker proxy,
which can add auth, freemium restrictions, caching, or enrichment. Absolute
calls bypass the proxy entirely.

To trace what really happens at each layer:

```bash
# 1. Check worker.ts for ALL env.X references (config vars, secrets, service bindings)
grep -rn "env\." worker.ts | grep -v "// " | sort -u

# 2. Check the frontend for absolute API URLs
grep -rn "fetch(" public/ --include='*.js' | grep -oE "fetch\(['\"][^'\"]+['\"]" | sort -u

# 3. Verify by making an actual request through the app
curl -s "https://app.example.com/api/analyze" -X POST -H "Content-Type: application/json" \
  -d '{"year":1991,"month":7,"day":24,"hour":6,"minute":30,"location":"서울","gender":"male"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('response keys:', list(d.keys()))"
```

## Security Hygiene

### localStorage → sessionStorage Migration

Sensitive user data (birth dates, API responses, PII) should not persist in
localStorage after tab close. Migrate to sessionStorage:

```javascript
// Before (persists forever):
localStorage.setItem('__SAJU_DATA__', JSON.stringify(data));
localStorage.getItem('__SAJU_DATA__');

// After (clears on tab close):
sessionStorage.setItem('__SAJU_DATA__', JSON.stringify(data));
sessionStorage.getItem('__SAJU_DATA__');
```

Keep ONLY these in localStorage:
- User preferences (theme, language)
- Anonymous session IDs (needed for cross-session history merge)
- Offline sync queues

### Console Log PII Audit

Search for console.log/error/warn calls that expose PII:

```bash
grep -rn "console\." --include='*.js' --include='*.ts' . | grep -v node_modules
```

Flag patterns:
- `console.log("Authenticated as:", user.email)` — remove email
- `console.error("...", responseData)` — remove full response body
- Any log with raw API response, user name, email, or birth data
