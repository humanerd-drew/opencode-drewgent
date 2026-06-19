# LIVE Activity Monitor

The dashboard's most "alive" feature. Shows agent actions in real-time.

## Architecture

```
agent.log (append-only, on disk)
    ↓ tail -80 lines, reverse parse
collect_live_activity() in pusher script
    ↓ every 5 minutes (same cron as everything else)
KV: latest.live
    ↓ 12-second fetch loop in browser
Dashboard LIVE card
```

**Key insight**: The log is the canonical source of truth. No special IPC or WebSocket needed. Just parse what's already being written.

## Log Parsing Patterns

Each line matched in priority order (first match wins):

| Pattern | Icon | Type | Example |
|---------|------|------|---------|
| `msg='...'` | 💬 | msg | User message content |
| `Streaming failed` / `HTTP 400` | ❌ | error | API call failed |
| `Fallback activated:` | 🔀 | fallback | Provider fallback |
| `tool_executor: ... completed` | ⚡ | tool | Tool finished |
| `tool_executor: ... error` | ❌ | tool_error | Tool returned error |
| `API call #` | 🤖 | api | Model call with latency |
| `terminal ... environment ready` | 🖥️ | terminal | Terminal session ready |
| `restore_primary` | ↻ | session | Session restored from DB |
| `turn_context ... conversation turn` | 💬 | turn | New turn started |
| `stream_request_complete` | ✅ | done | Response complete |
| `Checkpoint store exceeded` | 📊 | sys | Checkpoint cleanup |

Lines that don't match any pattern are skipped entirely.

## Pusher Implementation (`collect_live_activity()`)

```python
def collect_live_activity():
    # Read last 150KB of agent.log
    # Split into last 80 lines
    # Reverse iterate (most recent first)
    # For each line: match patterns, extract timestamp + session ID + icon + text
    # Return top 15 events, active_session, elapsed seconds since last event
```

**Return shape**:
```json
{
  "events": [
    {"time": "21:25:38", "icon": "⚡", "text": "Tool: write_file", "type": "tool", "session": "...", "ts_unix": 1781522738}
  ],
  "active_session": "20260615_152532_1c7ad7",
  "elapsed": 2
}
```

## Browser Implementation

```javascript
// Start after initial render
setTimeout(refreshLive, 12000);

async function refreshLive() {
  var res = await fetch('/api/status');
  var data = await res.json();
  updateLive(data.live);
  setTimeout(refreshLive, 12000);
}
```

**updateLive()** replaces the `#live-feed` container innerHTML entirely (small DOM, 15 items max). Updates the pulsing dot and elapsed counter.

**Elapsed thresholds**:
- `< 15s` → 🔴 green pulsing dot ("on")
- `15-120s` → 🟡 yellow ("idle")
- `> 120s` → ⚫ gray ("off")

## Why not WebSocket?

WebSocket would be more real-time but requires:
- Gateway modification to emit events
- Server-side state management
- Reconnection logic
- More complex pusher

The poll-every-12s approach works well because:
- agent.log is local, fast to read
- 12s latency is imperceptible for "live" feel
- No infra changes needed
- Works through the existing KV push mechanism
