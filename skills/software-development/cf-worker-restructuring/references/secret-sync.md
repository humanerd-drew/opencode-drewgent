# Secret Sync — m-log Session Reference

## Root Cause: Three-tier mismatch

The m-log project (Cloudflare Workers + D1 + Assets) had NVIDIA NIM API keys working in `wrangler dev` but failing after `wrangler deploy`.

### The setup

| Tier | File | Contents |
|------|------|----------|
| Build-time vars | `wrangler.jsonc` → `vars` | `BASE_URL`, `NAVER_CLIENT_ID`, `GOOGLE_CLIENT_ID`, `SAJU_API_ENDPOINT` |
| Local dev | `.dev.vars` | `NVIDIA_NIM_KEY`, `NVIDIA_NIM_KEY_FALLBACK`, `NVIDIA_NIM_KEY_FALLBACK_2`, `DEEPSEEK_API_KEY`, `NAVER_CLIENT_SECRET`, `NVIDIA_API_KEY_1/2/3`, `IS_LOCAL_DEV` |
| Production secrets | `wrangler secret` | Same names as `.dev.vars` NIM keys, but potentially **different values** |

### The bug

1. User rotated NVIDIA API keys and updated `.dev.vars`
2. `wrangler dev` reads `.dev.vars` → new keys work
3. `wrangler deploy` does NOT read `.dev.vars` → old/stale keys deployed
4. NVIDIA endpoint returns 401/403 in production → user sees "NVIDIA key error"

### The fix

```bash
cd /path/to/m-log
npx wrangler secret put NVIDIA_NIM_KEY
# paste value from .dev.vars
npx wrangler secret put NVIDIA_NIM_KEY_FALLBACK
# paste value
npx wrangler secret put NVIDIA_NIM_KEY_FALLBACK_2
# paste value
npx wrangler secret put DEEPSEEK_API_KEY
# paste value
```

Secrets update live — no redeploy needed.

### Verification

```bash
npx wrangler secret list
# Confirm all expected names present
```

Then test the actual endpoint that uses the keys (e.g., `/api/report` or `/api/analyze`).

### Code pattern that made this harder to spot

In `saju.ts` line 748 and `report.ts` line 43, the code references `env.NVIDIA_API_KEY` (singular, no suffix) as a legacy fallback. This key does NOT exist in `.dev.vars` (which has `NVIDIA_API_KEY_1/2/3`) or in production secrets. The `.filter(Boolean)` removes it harmlessly, but a developer reading the code sees a key name that might exist somewhere — adding confusion.

**Lesson:** When rotating from old key naming (`NVIDIA_API_KEY_1`) to new (`NVIDIA_NIM_KEY`), delete the legacy reference entirely rather than keeping it as a "safety net." It's dead code that misleads debugging.

### Key discovery: You cannot read existing secret values

`wrangler secret list` returns only names. There is no `wrangler secret get <NAME>` command. This means:
- You cannot audit whether production values match `.dev.vars`
- The only fix is to overwrite (destructive, but safe if you have the correct value)
- Always mirror a new entry in `.dev.vars` to production immediately, not later

### Related wrangler.jsonc discovery

The main `wrangler.jsonc` has a `vars` section with non-sensitive values like `NAVER_CLIENT_ID` and `GOOGLE_CLIENT_ID`. These ARE deployed with the worker and don't need `secret put`. But they're also visible in the deployed worker's env — never put actual secrets here.

The rule of thumb:
- **`vars`**: non-sensitive configuration (URLs, client IDs that are public anyway)
- **`.dev.vars`**: anything you'd need locally but shouldn't be in git (put it in `.gitignore`)
- **`wrangler secret`**: the actual production secrets — these are the ONLY ones deployed live

## Session context

- User: m-log project maintainer (Saju/Korean astrology analysis platform)
- Deploy target: Cloudflare Workers (m-log.cc)
- Symptoms: "npm run dev로 확인하고 배포했는데, 배포하면 에러. 엔비디아 키 관련 에러"
- Debug time: ~5 min to identify, ~2 min to fix (4 `wrangler secret put` commands)
- Trigger: Key rotation on NVIDIA NIM platform

## NVIDIA NIM Model Availability (2026-06-11 session — CORRECTED)

### ⚠️ RETRACTION: The model mismatch was a false diagnosis

In the original version of this file, I incorrectly claimed that `deepseek-ai/deepseek-v4-pro` returned HTTP 403 and that the model change was the fix. **This was wrong.** The model works perfectly fine with the key.

**What actually happened:**
1. I tested the key from Python with `key = '***'` (a literal mask placeholder, not the real key) → got 401/403
2. The terminal tool masks sensitive values in displayed output; when I wrote `key = '***'` in Python code, the tool's output masking had me believing I had sent the real key when I hadn't
3. I concluded "model returns 403" without cross-verifying with a different method (like reading from file directly)
4. The user corrected me — and re-testing with the ACTUAL key value showed both models return HTTP 200

**Actual root cause of the deploy failure:**
- Stale Cloudflare secrets (`.dev.vars` had newer keys than `wrangler secret` list)
- The 4 `wrangler secret put` calls + redeploy fixed it. The model change was unnecessary.
- After the second deploy, the secrets had propagated. The timing (secrets update + model change + redeploy) made it LOOK like the model change fixed it, but it was the secret propagation.

**Lesson for future debugging:** Always verify API keys by reading directly from the source file in one step (Python with `open()`), never from terminal output that could be masked.
