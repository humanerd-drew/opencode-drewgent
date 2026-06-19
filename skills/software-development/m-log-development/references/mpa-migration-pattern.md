# SPA → Svelte MPA Migration Pattern (for M-LOG v2)

Applied 2026-06-14. This reference documents the pivot from SPA Svelte to Svelte Multi-Page App.

## Motivation

The old vanilla JS SPA had 11 hash-routed views, custom Component base class, custom Router (93 lines), AppShell (970 lines), and 50KB+ monolithic JS bundle. MPA eliminates all of this: each page is a standalone HTML file with only the JS it needs.

## Architecture Change

| Before (SPA) | After (MPA) |
|---|---|
| `src/ui/index.html` (single entry) | `src/ui/entries/{page}.html` (per page) |
| `src/ui/src/App.svelte` (Router + Layout) | deleted |
| `src/ui/src/lib/Router.svelte` (hash router) | deleted |
| `src/ui/src/lib/AppLayout.svelte` (single layout) | `AppHeader.svelte` + `AppFooter.svelte` (components) |
| `src/ui/src/routes/` (SPA pages) | `src/ui/src/pages/` (standalone pages) |
| `window.location.hash = '#/page'` | `<a href="/page.html">` |
| 50KB JS bundle | 3-8KB per page + 40KB shared |

## How to Add a New MPA Page

1. **Vite config** — add entry to `rollupOptions.input` in `src/ui/vite.config.js`:
   ```js
   input: {
     input: resolve(__dirname, 'entries/input.html'),
     dashboard: resolve(__dirname, 'entries/dashboard.html'),
     payment: resolve(__dirname, 'entries/payment.html'),
     mynewpage: resolve(__dirname, 'entries/mynewpage.html'),  // ← add
   }
   ```

2. **Entry HTML** — create `src/ui/entries/mynewpage.html`:
   ```html
   <!DOCTYPE html>
   <html lang="ko">
   <head>
     <meta charset="UTF-8">
     <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
     <title>M-LOG | My New Page</title>
     <!-- shared styles can go here or in the Svelte component -->
   </head>
   <body>
     <div id="app"></div>
     <script type="module">
       import { mount } from 'svelte'
       import Page from '../src/pages/MyNewPage.svelte'
       mount(Page, { target: document.getElementById('app') })
     </script>
   </body>
   </html>
   ```

3. **Svelte page** — create `src/ui/src/pages/MyNewPage.svelte`:
   ```svelte
   <script lang="ts">
     import AppHeader from '../lib/components/AppHeader.svelte'
     import AppFooter from '../lib/components/AppFooter.svelte'
   </script>

   <AppHeader active="mynewpage" />
   <main class="main-content">
     <!-- content -->
   </main>
   <AppFooter />
   ```

4. **Nav links** — add the page to `AppHeader.svelte`'s `navLinks` array

5. **Build**: `npm run build:ui`

## Removing an MPA Page

1. Delete entry HTML, Svelte page, and remove from vite config
2. Remove from AppHeader navLinks
3. Rebuild

## Server-side Serving

`src/api/index.ts` routes:
- `/{page}.html` → `/ui-dist/{page}.html` (MPA)
- `/assets/*` → `/ui-dist/assets/*` (JS/CSS chunks)
- `/app/*` → legacy SPA fallback (backward compat)

### Pitfalls

#### Vite root must match entry location — and use absolute paths

`vite.config.js` sets `root: 'entries'`. Because root changes the working directory, **always use `resolve(__dirname, ...)` for absolute paths in `rollupOptions.input`**, never relative paths:

```js
// ✅ CORRECT — resolve() gives absolute paths
input: {
  input: resolve(__dirname, 'entries/input.html'),
  'report/desire': resolve(__dirname, 'entries/report/desire.html'),
}

// ❌ WRONG — relative paths resolve against entries/ not project root
input: {
  'report/desire': './report/desire.html',  // resolves to entries/report/desire.html? no — entries/entries/report/desire.html
}
```

**Pitfall**: Entry keys with hyphens (`desire-deep`) work fine; the hyphen does NOT cause resolution issues. If the build fails on a key, it's a path problem, not a character problem.

### PortOne SDK

Payment page loads PortOne SDK via `<script src="https://cdn.portone.io/v2/browser-sdk.js">` in its entry HTML, not in the page Svelte component.

### Each entry is independent

State is not shared across pages. For data that needs to persist (saju data), use `localStorage` — the same mechanism as the old SPA.

### Don't mix old and new build outputs

`vite build` with `emptyOutDir: true` wipes `public/ui-dist/` on each build. Keep old SPA at `public/app/` separately.
