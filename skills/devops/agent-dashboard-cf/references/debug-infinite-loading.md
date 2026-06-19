# Debug Infinite Loading (Dashboard Stuck on "Connecting...")

## Symptom

Page loads but shows spinner indefinitely. API returns HTTP 200 (confirmed via curl). Other pages work fine.

## Root Causes

### 1. `catch(e){}` swallows all errors

```javascript
// Before: infinite spinner, no error visible
try {
  await fetch('/api/status');
  render(d);
} catch(e) {}
```

If ANY render function throws (vis undefined, DOM element missing), the catch silently swallows it. The spinner never hides.

**Fix**: Always show errors:
```javascript
try {
  ...
  document.getElementById('loading').classList.add('hidden');
  document.getElementById('dashboard').classList.add('ready');
  render(d);
} catch(e) {
  document.getElementById('status').innerHTML = '&#10071; Error: ' + e.message;
  setTimeout(load, 5000); // retry
}
```

### 2. vis-network CDN fails to load

`<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>` — if unpkg is slow or blocked, `vis` is undefined. `new vis.DataSet(...)` throws ReferenceError.

**Fix**: Make graph rendering optional / deferred:
```javascript
var _graphNetwork = null;
function renderGraph(g) {
  if (typeof vis === 'undefined') return; // gracefully skip
  ...
}
```

Or add `onerror` handler on the script tag. Or move graph to separate page (Brain tab) and render only when that tab is active.

### 3. CORS / Mixed Content

Worker serves `/api/status` with `Access-Control-Allow-Origin: *`. But if the Worker changed or the HTML is cached from a different deployment, CORS headers might mismatch. Use relative URL (`/api/status` not `https://.../api/status`).

### 4. Old KV data without expected fields

After adding a new collector, the pusher pushes new fields. But if the page expects a field that doesn't exist in old KV data, accessing `d.newField.nested` throws TypeError.

**Fix**: Always chain with `|| {}`:
```javascript
var cpu = d.cpu_details || {};
var hourly = d.hourly || [];
```

## Verification Checklist

- [ ] `curl https://agent-dashboard.humanerd-me.workers.dev/api/status` returns 200 with JSON
- [ ] HTML contains `<script>` with `load()` at end
- [ ] No `catch(e){}` — always display errors
- [ ] vis-network script loads (check Network tab in DevTools)
- [ ] All `d.field` accesses guarded with `|| {}` or `|| []`
