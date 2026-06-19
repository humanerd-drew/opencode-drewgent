# NVIDIA NIM — Cloudflare Worker Timeout

## Observed Behavior

`deepseek-ai/deepseek-v4-pro` model on `integrate.api.nvidia.com/v1/chat/completions`:
- **Local (home IP):** HTTP 200, < 2s response
- **Cloudflare Worker:** 28s timeout per key, all 3 keys exhausted → "All NVIDIA API keys exhausted or failed" after ~84s

## Root Cause

Unknown. Possible reasons:
- Cloudflare shared egress IPs are throttled or blocked by NVIDIA for this specific model
- DeepSeek-v4-pro endpoint has a different routing path from llama models
- The model is not available to certain accounts from certain IP ranges

## Working Alternative

Replace:
```
deepseek-ai/deepseek-v4-pro  →  meta/llama-4-maverick-17b-128e-instruct
```

Both use the same endpoint and API format. The llama model works from both local and Cloudflare IPs.

## Key Details

| Detail | Value |
|--------|-------|
| Endpoint | `https://integrate.api.nvidia.com/v1/chat/completions` |
| Working model | `meta/llama-4-maverick-17b-128e-instruct` |
| Non-working model | `deepseek-ai/deepseek-v4-pro` |
| Timeout per key | 28s (must be < Cloudflare 30s fetch limit) |
| Keys used | `NVIDIA_NIM_KEY`, `NVIDIA_NIM_KEY_FALLBACK`, `NVIDIA_NIM_KEY_FALLBACK_2` |
| Source of truth | `.dev.vars` (local) + `wrangler secret put` (Cloudflare) |

## Files Modified (2026-06-11)

- `src/utils/llm.ts:60` — `NVIDIA_MODEL` constant
- `src/controllers/report.ts:37` — local `MODEL` constant
- `src/controllers/dating-report.ts:128` — inline model in payload
- `src/controllers/comprehensive-report.ts:83` — inline model in payload
