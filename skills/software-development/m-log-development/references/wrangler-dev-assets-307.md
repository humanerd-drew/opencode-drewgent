# wrangler dev ASSETS 307 Workaround

## Problem

In `wrangler dev`, the built-in ASSETS binding returns `307 Temporary Redirect` when a direct file path ending in `.html` is requested (e.g., `/input.html`, `/ui-dist/input.html`). **This does NOT affect production** — it's a wrangler dev quirk.

## Root Cause

`wrangler dev`'s local ASSETS implementation strips `.html` from URLs and redirects to the bare path, which then may or may not resolve correctly. The production Cloudflare Workers ASSETS binding handles all paths correctly.

## Workaround: Directory Pattern

Instead of serving files as `/input.html`, serve them as `/input/index.html` (accessible at `/input/`):

```bash
mkdir -p public/input
cp public/ui-dist/input.html public/input/index.html
# Now accessible at http://localhost:8787/input/ ✅
```

## Implementation in worker.ts

```ts
// MPA_ROUTES map handles backward compat from .html URLs
const MPA_ROUTES: Record<string, string> = {
  '/input.html': '/input/',
  '/dashboard.html': '/dashboard/',
  '/payment.html': '/payment/',
  '/compare.html': '/compare/',
  '/report/desire.html': '/report/desire/',
  '/report/desire-deep.html': '/report/desire-deep/',
  '/report/ai.html': '/report/ai/',
  '/report/comprehensive.html': '/report/comprehensive/',
  '/report/dating.html': '/report/dating/',
}
if (MPA_ROUTES[url.pathname])
  return Response.redirect(new URL(MPA_ROUTES[url.pathname], url.origin).toString(), 301)
```

## Build Script Integration

```json
"build:ui": "cd src/ui && npx vite build && cd ../.. && for f in input dashboard payment compare; do mkdir -p public/$f && cp public/ui-dist/$f.html public/$f/index.html; done && for f in desire desire-deep ai comprehensive dating; do mkdir -p public/report/$f && cp public/ui-dist/report/$f.html public/report/$f/index.html; done"
```

## Verification

```bash
# Dev mode — directory URL works
curl -s -o /dev/null -w "%{http_code}" http://localhost:8787/input/  # → 200

# .html URL redirects to directory
curl -s -o /dev/null -w "%{http_code}" http://localhost:8787/input.html  # → 301 → /input/

# Production — both work
```

## Note on API Routes

Only affects static file serving. API routes (`/api/*`) are handled by Hono and work correctly in both dev and production.
