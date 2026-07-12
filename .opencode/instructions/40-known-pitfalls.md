# Known Pitfalls

Edit this file as you encounter recurring issues.

## Common

- **Token/cost data is in SQLite, not stderr logs** — check `opencode.db` directly
- **macOS bash 3.2** — no associative arrays, use `date -j -f`
- **Launchd plists** — use `KeepAlive { SuccessfulExit: false, ThrottleInterval: 10 }`
- **Pre-commit hooks** — check raw source immutability before commit

## Template

```
## [Issue name]
**Symptom:** ...
**Cause:** ...
**Fix:** ...
**File:** path/to/file:line
```
