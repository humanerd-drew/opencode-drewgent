# Provider Fallback Debugging — Real Session Trace

## The Problem

Dashboard showed persistent `HTTP 400: opencode-go/deepseek-v4-flash is not a valid model ID`
errors. Total: 222 occurrences. Errors kept appearing every few minutes.

## Investigation

### Step 1 — Identify the failing calls

```bash
grep 'HTTP 400\|not a valid model' ~/.drewgent/logs/errors.log | tail -5
# → HTTP 400: opencode-go/deepseek-v4-flash is not a valid model ID
```

### Step 2 — Find the provider/model signature in agent.log

```bash
grep 'HTTP 400' ~/.drewgent/logs/errors.log | head -1
# → provider=openrouter model=opencode-go/deepseek-v4-flash summary=HTTP 400
```

Two providers in play:
- `opencode-go` → `model=deepseek-v4-flash` → works (14,421 calls)
- `openrouter` → `model=opencode-go/deepseek-v4-flash` → HTTP 400 (1,605 calls)

### Step 3 — Trace the openrouter origin

```bash
grep -B2 'provider=openrouter' agent.log | grep 'restore_primary\|turn_context'
# → INFO run_agent: OpenAI client created (restore_primary, shared=True)
#   provider=openrouter base_url=https://openrouter.ai/api/v1
#   model=opencode-go/deepseek-v4-flash
```

Root cause: `_restore_primary_runtime()` uses session metadata, not current config.

### Step 4 — Find all provider keys

```bash
grep -rn 'API_KEY\|api_key' ~/.drewgent/.env ~/.hermes/.env | grep -v '^#' | grep -v '^.*:#'
# → ~/.drewgent/.env had OPENROUTER_API_KEY set (uncommented)
# → ~/.hermes/.env had OPENROUTER_API_KEY commented out
```

### Step 5 — Fix

```bash
# Comment out the stale OpenRouter key
python3 -c "
with open('/Users/drew/.drewgent/.env') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if line.startswith('OPENROUTER_API_KEY=') and not line.startswith('#'):
        lines[i] = '#' + line
        break
with open('/Users/drew/.drewgent/.env', 'w') as f:
    f.writelines(lines)
"
```

### Step 6 — Verify

```bash
grep 'OPENROUTER' ~/.drewgent/.env
# → #OPENROUTER_API_KEY=***
```

## Why This Happened

The config had:
- `model.default: "opencode-go/deepseek-v4-flash"`
- `provider: "opencode-go"` (current)
- But old sessions stored `openrouter` in their metadata

When `_restore_primary_runtime()` fired at the start of each turn:
1. Read `self.provider = rt["provider"]` → `"openrouter"`
2. Created OpenAI client with `provider=openrouter`
3. Called OpenCode Go model on OpenRouter → HTTP 400

The `OPENROUTER_API_KEY` was still set in `~/.drewgent/.env` from the
pre-subscription era, so OpenRouter was technically usable — just not with
the model name that worked on OpenCode Go.

## Lesson

Never assume the configured provider is the one being used. Session metadata
can override it silently until the process restarts. When debugging model
errors, always check:

1. Which provider is in the error log line (`provider=`)
2. Whether `restore_primary` lines exist for the affected session
3. Whether stale API keys exist in `.env` from earlier configurations
