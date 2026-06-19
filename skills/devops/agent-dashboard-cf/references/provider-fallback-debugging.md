# Provider Fallback Debugging: OpenRouter + OpenCode Go HTTP 400

## Symptom
- Dashboard Recent Errors shows repeated `HTTP 400: opencode-go/deepseek-v4-flash is not a valid model ID`
- 222+ occurrences in errors.log
- Affects ~1,605 of ~16,000 total API calls
- Agent continues to work (other 14,421 calls succeed)

## Root Cause
Two providers configured. When a session restores it sometimes binds to the
`openrouter` provider instead of `opencode-go`. The model name
`opencode-go/deepseek-v4-flash` is an OpenCode Go internal identifier --
OpenRouter has no such model. Every call through openrouter with this model
name returns HTTP 400.

## Investigation Commands
```
# Provider split in logs
grep -oP 'provider=\S+' agent.log | sort | uniq -c | sort -rn

# Model name format
grep -oP 'model=\S+' agent.log | sort -u

# Errors per hour
for h in $(seq 0 23); do
  printf "%02d:00  " $h
  grep "$(date '+%Y-%m-%d') $(printf '%02d' $h):" errors.log | grep -c 'HTTP 400'
done
```

## Fix Options
1. Disable openrouter provider -- ensure no API key is set
2. Fix model name for fallback (remove `opencode-go/` prefix)
3. Single provider mode: `provider: "opencode-go"` exclusively

## Dashboard Impact
The error grouping collector groups by first 60 chars of message. As long
as new instances appear in the log, a grouped entry with count badge will
appear. Once the root cause is fixed, the entry ages out naturally.
