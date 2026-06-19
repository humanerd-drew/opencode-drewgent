# M-LOG v2 Barrel Split Audit (2026-06-15)

## Overview

Split 7 monolithic controller files (3,955 lines total) into 20+ domain files across `saju/`, `user/`, `db/`, `report/`, `payment/` directories. All original files preserved as barrel re-exports.

## Files Split

| Monolith | Lines | Split Into | Status |
|----------|-------|-----------|--------|
| `saju/saju-controller.ts` | 369 | `orchestrate-analyze.ts`, `get-iljin.ts`, `get-locations.ts`, `handle-sinsal.ts` | ✅ |
| `user/auth-controller.ts` | 345 | `oauth-naver.ts`, `oauth-google.ts`, `sign-in.ts`, `manage-profile.ts` | ✅ |
| `db/queries.ts` | 410 | `query-user.ts`, `query-myeongsik.ts`, `query-history.ts`, `query-report.ts`, `query-payment.ts` | ✅ |
| `report/dating-controller.ts` | 1,565 | `generate-dating-report.ts`, `prompts/dating-system.ts`, `format/dating-score.ts`, `format/dating-text.ts`, `format/dating-analysis.ts` | ✅ |
| `report/report-controller.ts` | 774 | `generate-free-report.ts`, `generate-paid-report.ts`, `prompts/report-system.ts` | ✅ |
| `report/comprehensive-controller.ts` | 382 | `generate-comprehensive-report.ts`, `prompts/comprehensive-system.ts` | ✅ |
| `payment/payment-controller.ts` | 110 | `verify-payment.ts`, `check-payment.ts` | ✅ |

## Shared Utilities Created (Phase 0 — Before Any Split)

- `src/utils/report-format.ts` — `hasRequiredKeys()`, `sanitizeReportOutput()`, `finalReportText()`
- `src/utils/llm-report.ts` — `callReportLLM(env, sys, userContent, keys, maxTokens, temperature, timeoutMs, options)`
  - Options: `{ tag: string, appendKeysToSys: boolean, sanitizeOutput: boolean }`

## Bugs Found During Audit

### Bug 1: Subagent changed call flow in `generate-free-report.ts`

**What happened**: The subagent changed `handleGenerateFreeLogReport` to call `callLLMJson()` (from `utils/llm.ts`) directly instead of calling `generateAIReportContent()`.

**Impact**: Token budget changed from 1500 to 3000 for DeepSeek, NVIDIA key list dropped from 4 to 3 keys (lost legacy `NVIDIA_API_KEY` safety net).

**Root cause**: The subagent was told "keep function bodies identical" but interpreted "business logic identical" as "same LLM call outcome" rather than "same call chain."

**Fix**: Restored `generateAIReportContent()` call, removed unused `callLLMJson` import.

### Bug 2: Subagent kept NVIDIA_API_KEY legacy reference in `handle-sinsal.ts`

**What happened**: The original `saju-controller.ts` had `env.NVIDIA_API_KEY` as a 4th fallback key (marked "legacy, kept as safety net"). When the sinsal handler was extracted to its own file, this reference was carried over.

**Resolution**: Confirmed with user that `NVIDIA_NIM_KEY` is the correct key family. `NVIDIA_API_KEY` is obsolete. Removed the reference.

## Detection Commands (for future audits)

```bash
# 1. Check that all split file exports match their barrel
for barrel in src/saju/saju-controller.ts src/user/auth-controller.ts src/db/queries.ts \
              src/report/dating-controller.ts src/report/report-controller.ts \
              src/report/comprehensive-controller.ts src/payment/payment-controller.ts; do
  echo "=== $barrel ==="
  grep "export {" "$barrel"
done

# 2. Verify no subagent changed call flow — trace handler LLM paths
grep -rn "callLLMJson\|callReportLLM\|callDeepSeek\|callNvidiaWithFallback" src/report/ --include="*.ts"

# 3. Detect unused imports after splits (import exists but not called in body)
#    Search for imported functions that appear in import line but NOT in function bodies
#    Example: import { callLLMJson, ... } from '...' but callLLMJson is never used below

# 4. Check all route files import from barrels correctly
for route in src/api/route-*.ts; do
  echo "--- $(basename $route) ---"
  grep "import {" "$route"
done
```
