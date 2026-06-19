# OpenCode Go Provider Reference

## Standalone Provider (NOT OpenRouter)

OpenCode Go is a **standalone Hermes provider** with its own API base URL
and API key. It does NOT route through OpenRouter.

| Field | Value |
|-------|-------|
| Provider ID | `opencode-go` |
| API base URL | `https://opencode.ai/zen/go/v1` |
| API key env var | `OPENCODE_GO_API_KEY` |
| Auth type | `api_key` |
| Pricing model | $10/month subscription (all models included) |
| Marginal cost | $0 per call (subscription already paid) |

## Aliases in Hermes

- `opencode-go` (canonical)
- `go` (alias)
- `opencode-go-sub` (alias)

## Full Model List (as of 2026-06-13)

Discovered via OpenCode Go `/v1/models` endpoint + Hermes models.dev system:

| Model | Type | Notes |
|-------|------|-------|
| `kimi-k2.7-code` | Coding | MoonshotAI's latest coding model |
| `kimi-k2.6` | General/Coding | MoonshotAI |
| `kimi-k2.5` | General | MoonshotAI, stable older gen |
| `glm-5.1` | General | ZhipuAI, Chinese-strong |
| `glm-5` | General | ZhipuAI |
| `deepseek-v4-pro` | General/Coding | Strong reasoning |
| `deepseek-v4-flash` | General | Fast, economical (current default) |
| `qwen3.7-max` | General/Coding | Qwen's best. Slow but highest quality |
| `qwen3.7-plus` | General | Qwen mid-tier |
| `qwen3.6-plus` | General | Previous Qwen |
| `qwen3.5-plus` | General | Older Qwen |
| `mimo-v2.5-pro` | Multimodal | Xiaomi, supports vision |
| `mimo-v2.5` | Multimodal | Xiaomi, light |
| `mimo-v2-pro` | Multimodal | Xiaomi, older |
| `mimo-v2-omni` | Multimodal | Xiaomi, text+vision+audio |
| `hy3-preview` | General | Tencent Hunyuan |

## Speed Tier (empirical)

```
deepseek-v4-flash (fastest)
  → kimi-k2.5, kimi-k2.6
    → deepseek-v4-pro, qwen3.7-plus
      → kimi-k2.7-code, glm-5.1
        → qwen3.7-max (slowest)
```

## Quality Tier (for coding/reasoning)

```
qwen3.7-max (best)
  → kimi-k2.7-code, deepseek-v4-pro
    → qwen3.7-plus, kimi-k2.6, glm-5.1
      → deepseek-v4-flash, kimi-k2.5
```

## Recommended Routing

| Role | Model | Rationale |
|------|-------|-----------|
| Main agent (interactive) | `deepseek-v4-flash` | Fastest, user waits least |
| Subagent (complex) | `deepseek-v4-pro` or `qwen3.7-max` | Quality over speed in background |
| Subagent (simple) | `deepseek-v4-flash` | Fast and sufficient |
| Vision | `mimo-v2.5-pro` | Only multimodal option |
| Web extract | `deepseek-v4-flash` | Light summarization |
| Session search | `deepseek-v4-flash` | Light summarization |

## Config Example

```yaml
model:
  default: "opencode-go/deepseek-v4-flash"
  provider: "opencode-go"

delegation:
  provider: "opencode-go"
  model: "deepseek-v4-pro"

auxiliary:
  vision:
    provider: "opencode-go"
    model: "mimo-v2.5-pro"
  web_extract:
    provider: "opencode-go"
    model: "deepseek-v4-flash"
  session_search:
    provider: "opencode-go"
    model: "deepseek-v4-flash"
```
