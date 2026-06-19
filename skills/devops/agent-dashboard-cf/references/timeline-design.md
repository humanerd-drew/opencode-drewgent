# Activity Timeline Design

## Data Sources

The timeline merges events from three sources:

### 1. Cron job runs
- Source: `cron_data["active"]` + `cron_data["errors"]`
- Fields: `last_run_at` (ISO 8601 timestamp), `last_status` (ok/error), `name`
- Icon: `⏰` (&#9200;)
- Type: `cron`

### 2. Session activity
- Source: `sessions` list (from `hermes sessions list`)
- Fields: session id, preview text, source
- Currently: **not included in timeline** because sessions lack reliable timestamps
- Future: parse `last_active` from session DB

### 3. Recent errors
- Source: `recent_errors` (from `collect_recent_errors()`)
- Fields: `time` (YYYY-MM-DD HH:MM:SS), `level`, `message`
- Icon: `❌` (&#128308;)
- Type: `error`

## Merge Logic (`collect_timeline()`)

```python
events = []

# Cron jobs
for j in active + errors:
    ts = j.get("last_run_at", "")
    t = parse_iso_timestamp(ts[:19])  # "2026-06-15T09:00:17" → epoch
    events.append({"time": t, "icon": "⏰", "msg": name + status_suffix, "type": "cron"})

# Errors
for err in recent_errors:
    t = parse_ymdhms_timestamp(err["time"][:19])  # "2026-06-15 09:00:17" → epoch
    events.append({"time": t, "icon": "❌", "msg": message[:60], "type": "error"})

# Deduplicate by message prefix + sort reverse chronological
seen = set()
for e in sorted(events, key=lambda x: x["time"], reverse=True):
    if e["msg"][:40] not in seen:
        seen.add(e["msg"][:40])
        result.append(e)

return result[:12]
```

## Rendering

### Initial render (in `buildCards()`)
- Timeline card spans 2 columns: `{ id:'timeline', wide:true, ... }`
- `.timeline-card { grid-column: span 2; }`
- Each event: CSS timeline with `border-left` + `::before` circle dot
- Status colors: green=ok, red=error

### Incremental update (in `updateTimeline()`)
```javascript
// Check existing events' data-ts attributes
var existing = container.querySelectorAll('.tl-event');
var latestId = existing.length ? existing[0].dataset.ts : '0';

// Only prepend events newer than latest
timeline.forEach(function(e) {
    if (e.time <= parseInt(latestId)) return;  // already shown
    var html = '<div class="tl-event tl-new" data-ts="' + e.time + '">...</div>';
    container.innerHTML = html + container.innerHTML;
});
```

### timeAgo() utility
```javascript
function timeAgo(ts) {
    var diff = (Date.now() / 1000) - ts;
    if (diff < 60) return 'just now';
    if (diff < 3600) return Math.round(diff/60) + 'm ago';
    if (diff < 86400) return Math.round(diff/3600) + 'h ago';
    return Math.round(diff/86400) + 'd ago';
}
```

## Design Principles

1. **Scannability**: Color-coded dots let the user find errors instantly. Green = ok, red = problem.
2. **Freshness**: `timeAgo()` makes events feel current. "12m ago" > "2026-06-15 09:00:17"
3. **Animation**: New events slide in from top (`slideIn 0.4s`). Creates "live feed" sensation.
4. **Live indicator**: Pulsing green dot in header with timeAgo string. Visual confirmation the agent is active.
5. **No interruption**: Timeline updates don't reset scroll position or close accordion.

## Anti-patterns to Avoid

| Anti-pattern | Why | Fix |
|-------------|-----|-----|
| Re-render all events on update | Loses animation, resets scroll | Only `prepend` new events, check `data-ts` |
| Absolute timestamps | "2026-06-15T10:48:48" is unreadable in context | Use `timeAgo()` relative times |
| Show all 21 cron jobs | Timeline gets cluttered | Max 12 events, deduplicate |
| Mixed-source in same card | Confusing layout | Timeline card = events only, separate from static data |
