# Live Activity Monitor — Collector Reference

## Purpose

Tail agent.log for recent activity events, parse into structured event stream for dashboard.

## Event Types

| Type | Icon | Log Pattern | Priority |
|------|------|-------------|----------|
| msg | 💬 | `msg='...'` in `turn_context: conversation turn:` | High |
| api | 🤖 | `API call #N:` in `conversation_loop:` | High |
| tool | ⚡ | `tool_executor: tool X completed` | High |
| tool_error | ❌ | `tool_executor: Tool ... returned error` | High |
| error | ❌ | `Streaming failed` or `HTTP 400` | High |
| fallback | 🔀 | `Fallback activated:` | Medium |
| done | ✅ | `stream_request_complete` | Low |
| session | ↻ | `restore_primary` | Low |
| terminal | 🖥️ | `environment ready` in `terminal_tool` | Low |
| turn | 💬 | `turn_context` / `conversation turn` | Low (duplicate of msg) |
| sys | 📊 | `pruning oldest`, `Checkpoint store exceeded` | Low |

## Collector Implementation (`collect_live_activity`)

```python
def collect_live_activity():
    log = os.path.join(DREWGENT, "logs", "agent.log")
    # Read last 150KB of log
    # Split into last 80 lines
    # Iterate reversed (newest first)
    # Match timestamp: re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
    # Extract session ID: re.search(r"\[([^\]]+)\]", line)
    # Categorize by keyword matching on the line
    # Return max 15 events
    
    # Key parsing rules:
    # - msg='...' lines: split by `msg='` and take last element
    # - model= from API call lines: match after "model=" up to next space
    # - latency= from API call lines: match after "latency=" up to "s"
    # - tool name from tool_executor lines: match "tool (\S+) completed"
```

## Dashboard Display

- Activity row at top: 🔴/🟡/⚫ LED + session ID + elapsed time
- Activity panel in Usage tab: scrollable event list (max 15)
- Elapsed time determines LED color: <15s=green Active, <120s=yellow Idle, >120s=gray Offline
- Refreshes every 15s along with full page update

## Common Issues

- **Duplicate events**: `msg='...'` and `turn_context` lines overlap → skip turn_context when msg already caught
- **Session ID not present**: Some log lines (run_agent, streaming) don't have session brackets → leave empty
- **Timestamps**: strptime with "%Y-%m-%d %H:%M:%S" format, truncate milliseconds
