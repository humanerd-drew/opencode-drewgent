# Gateway Platform Connection Diagnosis (2026-06-11)

Diagnostic pattern for "gateway process is running but no messaging platforms (Discord, Telegram, etc.) are connected."

## Symptom

- `ps aux | grep gateway` shows the process running
- Cron jobs fire normally (BrainSignalMonitor entries appear in gateway.log)
- But **no** `"Connecting to discord..."` / `"✓ discord connected"` log entries after the last restart
- Discord bot is offline, Telegram bot doesn't respond

## Root Cause: Orphaned Extracted Method

The canonical case (2026-06-11): `GatewayRunner.start()` in `gateway/run.py` was a stub (`self._running = True`) left behind after module extraction. `AdapterLoader.connect_all()` existed in `gateway/adapters.py` but was never called from the startup flow.

### How it happens

1. Someone extracts platform connection logic from `GatewayRunner.start()` into `gateway/adapters.py` (new `connect_all()` method)
2. The original `GatewayRunner.start()` body is accidentally replaced with a stub
3. The new `connect_all` has **zero call sites** — it exists in the module but nobody invokes it
4. Result: gateway starts, cron runs, but no platforms connect (silent failure)

## Diagnosis

```bash
# Check if any platform connection was attempted since last restart
grep -E "Connecting|connected|Connecting to" ~/.drewgent/logs/gateway.log | tail -20
```

Expected output for a healthy gateway:
```
Connecting to discord...
✓ discord connected
Connecting to api_server...
✓ api_server connected
Connected 3/3 platform(s)
```

If output is empty or only shows disconnect messages, platforms are not being connected.

## Triage

```bash
# 1. Confirm gateway is using the right .env
grep DISCORD_BOT_TOKEN ~/.drewgent/.env | head -1
# Should show the bot token (first 20 chars visible)

# 2. Check if connect logic exists but isn't wired
grep -rn "connect_all\|connect_adapter" ~/.drewgent/source/drewgent-agent/gateway/adapters.py | head -5
# Should show the method definition

# 3. Verify no call site exists
grep -rn "connect_all" ~/.drewgent/source/drewgent-agent/gateway/run.py
# If empty = orphaned method, needs wiring

# 4. Check GatewayRunner.start()
grep -A 5 "async def start" ~/.drewgent/source/drewgent-agent/gateway/run.py
# BAD: just "self._running = True; return True"
# GOOD: calls self._adapter_loader.connect_all()
```

## Fix (if orphaned)

Add the call site in `GatewayRunner.start()`:

```python
async def start(self) -> bool:
    self._running = True
    connected, enabled, nonretryable, retryable = (
        await self._adapter_loader.connect_all()
    )
    # ... log results
    return True
```

Then restart the gateway:
```bash
# Kill current processes (launchd will auto-restart with --replace)
kill -TERM $(pgrep -f "drewgent_cli.main gateway")
# Or if not auto-restarting:
launchctl start ai.drewgent.gateway
```

## Verify

```bash
sleep 5 && grep -E "Connecting|connected" ~/.drewgent/logs/gateway.log | tail -10
```

## Prevention

After any module extraction from `gateway/run.py`, verify the startup flow still connects platforms:

```bash
grep -rn "connect_all\|\.start(" gateway/ --include="*.py" | grep -v __pycache__ | grep -v test_
```

Every method that was called during startup in the old code must have a call site in the new code.
