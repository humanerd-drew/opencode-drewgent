# m-log-v2 MPA Pivot (2026-06-13)

## Context
The Svelte frontend started as an SPA (hash Router, App.svelte, single entry). After discussion, the user and agent agreed MPA (Multi-Page App) is a better fit because:
- Every page fetches new data from the API anyway — no persistent client state
- SPA Router and AppLayout added complexity without benefit
- SEO matters (each page should have its own URL)
- Simpler mental model: each page = independent HTML + JS

## MPA vs SPA Decision Matrix

| Factor | SPA | MPA |
|--------|-----|-----|
| Page transitions | Instant (no full reload) | Full reload |
| Client state | Shared in memory | Per-page only |
| Code splitting | Route-based lazy loading | Page-based (natural) |
| JS bundle size | All pages loaded upfront (50KB) | Per page (3-8KB) |
| SEO | Requires SSR/prerender | Native |
| URL structure | Hash routes (#/input) | Clean paths (/input/) |
| Dev complexity | Router + state mgmt | Zero |
| This app's fit | ❌ | ✅ |

## Migration Path (SPA → MPA)

### Delete SPA artifacts

## Second Attempt Outcome (same session)

The first MPA attempt failed (hardcoded colors, placeholders, no layout). Recovery in same session:

1. **Delete the failed attempt entirely**: `rm -rf src/ui/ public/ui-dist/ public/input/ public/dashboard/ public/payment/ public/compare/ public/report/`
2. **Restore `public/app/`** from original m-log backup
3. **Rebuild MPA correctly** with CSS variables only, AppShell shared layout, full functionality per page
4. **Use `delegate_task` to parallelize page creation** — 3 subagents ran simultaneously (landing, dashboard, AppShell wiring)
5. **10 pages completed** — landing, input, dashboard, payment, compare, 5 report pages

Critical lesson: SPA→MPA loses the shared AppShell. Every MPA page must explicitly include `<AppShell active="xxx">...</AppShell>` to restore header/sidebar/footer/mobile-nav.
```
src/ui/index.html              → DELETE (was single entry)
src/ui/src/main.ts              → DELETE (was mount(App))
src/ui/src/App.svelte           → DELETE (was Router + Layout)
src/ui/src/lib/Router.svelte    → DELETE (hash router)
src/ui/src/lib/AppLayout.svelte → → components/AppHeader.svelte + AppFooter.svelte
src/ui/src/routes/*.svelte      → → pages/*.svelte
```

### Create per-page entries
```
src/ui/entries/input.html       ← new (imports InputPage.svelte)
src/ui/entries/dashboard.html    ← new
...
```

### Vite multi-entry config
```js
build: {
  rollupOptions: {
    input: {
      input: resolve(__dirname, 'entries/input.html'),
      dashboard: resolve(__dirname, 'entries/dashboard.html'),
    }
  }
}
```

### Page component pattern (no Router)
```svelte
<!-- pages/DashboardPage.svelte — standalone page -->
<script>
  import AppHeader from '../lib/components/AppHeader.svelte'
  import AppFooter from '../lib/components/AppFooter.svelte'
  // ... page-specific logic
</script>
<AppHeader active="dashboard" />
<!-- page content -->
<AppFooter />
```

## Wrangler Dev ASSETS Workaround

`wrangler dev` ASSETS binding does NOT serve files by explicit path (`.html` files get 307 redirects). Only directory URLs work:

```
/input/ → serves public/input/index.html    ← works
/input.html → 307 → /input/                  ← redirect added in worker.ts
```

### Fix: Build step copies HTML to directory/index.html
```bash
for f in input dashboard payment compare; do
  mkdir -p public/$f
  cp public/ui-dist/$f.html public/$f/index.html
done
```

### Worker.ts MPA route redirects
```ts
const MPA_ROUTES: Record<string, string> = {
  '/input.html': '/input/',
  '/dashboard.html': '/dashboard/',
  '/payment.html': '/payment/',
  '/compare.html': '/compare/',
  '/report/desire.html': '/report/desire/',
}
const redirect = MPA_ROUTES[url.pathname]
if (redirect) {
  return Response.redirect(new URL(redirect, url.origin).toString(), 301)
}
```

## Style Variables Import

The original CSS files from `public/app/css/` (21 files including `variables.css`, `base.css`, component styles) were copied to `src/ui/src/lib/styles/`. The entry HTML files need to import them:

```html
<link rel="stylesheet" href="/css/variables.css">
<link rel="stylesheet" href="/css/base.css">
```

But `public/css/` doesn't exist in the MPA build — the CSS is only in `src/ui/src/lib/styles/`. For production, copy the CSS files to `public/css/` as part of the build step. For now, Svelte pages have hardcoded dark-theme colors instead of using CSS variables.
