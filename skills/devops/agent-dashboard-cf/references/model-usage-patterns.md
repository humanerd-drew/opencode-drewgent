# Model Usage Collection Patterns

## Log Format

The agent log records model usage in two formats:

### 1. API Call Summary (with token counts)
```
model=deepseek-v4-flash provider=opencode-go in=263769 out=289 total=264058 latency=4.9s cache=263168/263769 (100%)
```
Fields: `model`, `provider`, `in` (input tokens), `out` (output tokens), `total`, `latency`, `cache`

### 2. Client Create/Close (no token counts)
```
model=deepseek-v4-flash provider=opencode-go base_url=https://opencode.ai/zen/go/v1/
```

### 3. Model name variants
- `deepseek-v4-flash` (clean, most common)
- `opencode-go/deepseek-v4-flash` (with provider prefix — from OpenRouter calls)
- `minimax-m3` (auxiliary client)
- `mimo-v2.5-pro` (vision/summary tasks)

## Collection Strategy

### `collect_model_usage()` in pusher script

```python
# Read last 1MB of agent.log
with open(log, "rb") as f:
    f.seek(0, 2)
    size = f.tell()
    f.seek(max(0, size - 1024 * 1024))
    content = f.read().decode("utf-8", errors="ignore")

# Count model appearances (any context)
for m in re.finditer(r'model=(\S+)', content):
    model_name = m.group(1).strip()
    if '/' in model_name:
        model_name = model_name.split('/')[-1]  # strip provider prefix
    model_counts[model_name] += 1

# Extract token data (API call lines only)
for m in re.finditer(r'model=(\S+).*?in=(\d+)\s+out=(\d+)\s+total=(\d+)', content):
    model_name = m.group(1).strip()
    if '/' in model_name:
        model_name = model_name.split('/')[-1]
    model_tokens[model_name]["in"] += int(m.group(2))
    model_tokens[model_name]["out"] += int(m.group(3))
    model_tokens[model_name]["total"] += int(m.group(4))

# Extract providers
for m in re.finditer(r'model=(\S+)\s+provider=(\S+)', content):
    model_name = m.group(1).strip()
    if '/' in model_name:
        model_name = model_name.split('/')[-1]
    model_providers[model_name].add(m.group(2).strip())
```

### Token counting caveats
- Token counts come from API call log lines — may not cover all model invocations (e.g., streaming failures never produce a `total=` line)
- 1MB tail only captures recent data; older `minimax` calls may be outside range
- Cache hit count (`cache=`) is available but not currently collected — add if cache ratio tracking is needed

## Dashboard Display

### Models Card (summary)
```
🤖 Models · 3,396 total calls
━ 1 models
━ deepseek-v4-flash: 3,396
```

### Models Card (expanded)
| Model | Calls | % | Tokens | Providers |
|-------|-------|---|--------|-----------|
| deepseek-v4-flash | 3,396 | 100% | 1,284K | opencode-go, openrouter |

### Token formatting
- Raw integers can be large (e.g., 1,284,567)
- Display as K (thousands): `Math.round(tokens_total/1000) + 'K'`
- Call counts: use `fmtNum()` with locale separators

## When to Update
- A new model appears in the log naturally (no code change needed — the regex picks it up)
- Only update if the log format changes (e.g., different field names, different separator)
