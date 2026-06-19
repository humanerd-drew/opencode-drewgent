# Opencode Go — Provider Model Catalog

**Base URL**: `https://opencode.ai/zen/go/v1`  
**Verified**: 2026-06-13  
**Total models**: 19

## Query Command

```bash
curl -s "https://opencode.ai/zen/go/v1/models" \
  -H "Authorization: Bearer $OPENCODE_GO_API_KEY" \
  | python3 -c "import json,sys; data = json.load(sys.stdin); models = data.get('data', data); [print(m['id']) for m in sorted(models, key=lambda x: x.get('id',''))]"
```

## Supported Models

| Model | Note |
|---|---|
| `deepseek-v4-flash` | Current cron/auxiliary default ✅ |
| `deepseek-v4-pro` | Fallback in config |
| `glm-5` | Zhipu GLM |
| `glm-5.1` | Zhipu GLM latest |
| `hy3-preview` | Hunyuan 3 preview |
| `kimi-k2.5` | Moonshot Kimi |
| `kimi-k2.6` | Moonshot Kimi |
| `kimi-k2.7-code` | Moonshot Kimi code-tuned |
| `mimo-v2-omni` | MIMO multimodal |
| `mimo-v2-pro` | MIMO pro |
| `mimo-v2.5` | MIMO v2.5 |
| `mimo-v2.5-pro` | MIMO v2.5 pro |
| `minimax-m2.5` | MiniMax |
| `minimax-m2.7` | MiniMax (legacy) |
| `minimax-m3` | MiniMax latest (1M context) |
| `qwen3.5-plus` | Qwen 3.5 |
| `qwen3.6-plus` | Qwen 3.6 |
| `qwen3.7-max` | Qwen 3.7 max |
| `qwen3.7-plus` | Qwen 3.7 plus |

## Name Convention

Opencode Go **preserves dots** in model names:
- `minimax-m3` (not `minimax/minimax-m3` like OpenRouter)
- `deepseek-v4-flash` (not `deepseek/deepseek-v4-flash`)

This means model strings like `opencode-go/deepseek-v4-flash` are
resolved by splitting on `/` → provider prefix + model name.

## When to Re-Verify

The model list may change. Re-query if:
- A Cron job times out with "waiting for provider response"
- A new model is added to config but doesn't work
- More than 30 days since last verification
