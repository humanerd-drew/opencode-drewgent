# Health + Error Collection Patterns

## compute_health_status()

Aggregates multiple signals into a single health level.

### Health levels
```
healthy  → critical=0, warning=0   → green bar
warning  → critical=0, warning>=1  → yellow bar
critical → critical>=1              → red bar
```

### Warning sources counted
| Source | Condition | weight |
|--------|-----------|--------|
| Disk usage | >65% = 1 warning, >85% = 1 critical | 1 per threshold |
| Cron errors | len(cron_data["errors"]) | N warnings |
| Error log level | CRITICAL entries → critical count | 1 per entry |
| Error log level | ERROR/WARNING entries → warning count | 1 per entry |

### Issues list
Top 3 issues as short strings: `["disk 76%", "3 cron errors"]`

## collect_recent_errors()

Parses error logs for last N unique errors.

### Input files
- `~/.drewgent/logs/errors.log` (primary)
- `~/.drewgent/logs/agent.log` (fallback)

### Method
1. Seek to last 200KB of each file
2. Regex: `(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?(ERROR|WARNING|CRITICAL).*?(?:summary=|error=)([^\n]+)`
3. Deduplicate by first 60 chars of message
4. Return max 8 entries

### Why tail 200KB
- errors.log: typically small (<1MB), recent errors at end
- agent.log: can be large (multiple sessions), recent activity at end
- 200KB covers roughly last 30 minutes of high-activity sessions

### Common log patterns
```
# WARNING with summary=
2026-06-15 16:28:01,868 WARNING [session_id] agent.conversation_loop: API call failed ... summary=HTTP 400: model not valid

# WARNING with inline error
2026-06-15 16:28:17,608 WARNING [session_id] agent.tool_executor: Tool terminal returned error ... {"output": "..."}

# INFO streaming failure (also caught)
2026-06-15 16:29:05,593 INFO agent.chat_completion_helpers: Streaming failed ... Error code: 400
```

## collect_alerts()

Generates user-facing alert items (separate from health status).

### Alert types
| Alert | Condition | Severity |
|-------|-----------|----------|
| Disk >80% | disk_used_pct > 80 | error |
| Disk >65% | disk_used_pct > 65 | warn |
| Watchdog cron error | cron job "Drewgent launchd watchdog" in errors | error |
| Watchdog missing | no watchdog cron job active and not in errors | warn |
| Other cron errors | len(other_errors) > 0 | warn |

### Gateway watchdog special case
The `ai.drewgent.gateway-watchdog` launchd service is `OnDemand=true` — it does NOT stay running (no PID). The actual watchdog is the **cron job** "Drewgent launchd watchdog" running every 5 minutes. Alert logic checks the cron job status, NOT the launchd service PID.
