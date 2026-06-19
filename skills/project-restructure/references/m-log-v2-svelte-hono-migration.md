# m-log-v2 Svelte + Hono Migration (2026-06-13)

## Context
m-log-v2 was a Cloudflare Workers project with a vanilla JS SPA (hash router, manual DOM, 16 CSS files, no build tool). This reference captures the specific migration techniques used in restructuring it.

**NOTE**: This session started with a SPA approach but PIVOTED to MPA (Multi-Page App) midway. See `references/m-log-v2-mpa-pivot.md` for the MPA details. The SPA sections below document the initial (superseded) approach — they are preserved for historical reference of what was tried and rejected.

## Key Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Backend framework | Hono on CF Workers | Native CF, streamSSE for LLM, `hc` RPC, middleware |
| Frontend framework | Svelte 5 + Vite SPA | Minimal boilerplate, compiler-based reactivity |
| State management | Svelte `$state()` + localStorage | Incremental migration; keep `__SAJU_DATA__` for Router |
| CSS approach | Component-scoped Svelte `<style>` + global variables | No CSS framework needed |
| Build output | `public/ui-dist/` | Worker ASSETS binding reads from `public/` |
| Layout strategy | Single `AppLayout.svelte` with media-query desktop/mobile switch | Avoids route-level layout detection |

## Svelte + CF Workers Integration Points

### Build Config
```
src/ui/vite.config.js  →  builds to ../../public/ui-dist/
src/ui/svelte.config.js → vitePreprocess only (no adapter needed for SPA)
```

### Worker Asset Serving (src/api/index.ts catch-all)
```
1. If path starts with /app/:
   → Rewrite to /ui-dist/<path> and ASSETS.fetch()
   → On 404, return /ui-dist/index.html (SPA fallback)
2. Otherwise: ASSETS.fetch() original path (old SPA, static files)
3. On 404 for /app/*: return old /app/index.html (backward compat)
```

### Package Setup
```json
{
  "type": "module",
  "scripts": {
    "build:ui": "cd src/ui && npx vite build",
    "dev:ui": "cd src/ui && npx vite"
  }
}
```

## Svelte File Structure (src/ui/)

```
src/ui/
├── vite.config.js
├── svelte.config.js
├── index.html              ← Vite entry HTML
├── tsconfig.json           ← extends root, adds svelte types
├── src/
│   ├── main.ts             ← mount(App, target)
│   ├── App.svelte          ← AppLayout > Router
│   ├── lib/
│   │   ├── api.ts          ← fetch wrapper (credentials: include)
│   │   ├── Router.svelte   ← hash-router (12 lines)
│   │   └── AppLayout.svelte ← header + sidebar + mobile nav + footer
│   ├── routes/             ← page components (InputPage, PaymentPage, DashboardPage)
│   ├── components/         ← shared UI (empty, for future)
│   └── stores/             ← state (empty, for future)
```

## Router Component (Svelte 5)

```svelte
<script lang="ts">
  let { routes = {}, defaultRoute = "/" } = $props();
  let currentPath = $state(
    (typeof window !== "undefined"
      ? window.location.hash.replace(/^#/, "")
      : "") || defaultRoute
  );
  function onHashChange() {
    currentPath = window.location.hash.replace(/^#/, "") || defaultRoute;
  }
  $effect(() => {
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  });
  let PageComponent = $derived(routes[currentPath]);
</script>
{#if PageComponent}
  <PageComponent />
{:else}
  <div>404: {currentPath}</div>
{/if}
```

## Lessons Learned

1. **AGENTS.md must be first** — Without it, the user will reject any proposed structure. Present a search-table and naming convention BEFORE creating files.
2. **Kanban phases must be independently revertible** — Old code stays in place until new code is verified. Phase boundary = app runs identically before and after.
3. **Eval "is this feature connected?" before deletion** — Just5 had a real handler (`handleJust5Analyze`, 521 lines) that was NEVER routed (the old worker.ts stubbed `/api/just5/analyze`). Always check both the worker routing AND the function body before labeling something dead code.
4. **Don't discuss deployment during dev** — The user WILL push back. Focus on code.
5. **Svelte 5 migration from vanilla JS is per-view** — Each view (InputView.js → InputPage.svelte) is a standalone replacement. No need to migrate all at once.