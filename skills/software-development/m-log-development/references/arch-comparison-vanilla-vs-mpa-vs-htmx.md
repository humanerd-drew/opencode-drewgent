# Architecture Comparison: Vanilla SPA vs MPA vs htmx

Decision artifact from 2026-06-14. M-LOG was a Vanilla SPA; the team evaluated three approaches before choosing Svelte MPA.

## Comparison

| Criteria | Vanilla SPA (current) | Svelte MPA (chosen) | htmx |
|---|---|---|---|
| **Current state** | Already works. 11 views, 50KB+ bundle. | New pages coexist with old SPA. | Would need full backend rewrite. |
| **Add a page** | route + view + component, 3 files | entry HTML + Svelte page + vite config | New HTML + htmx attributes |
| **JS size** | 50KB+ all-at-once | 3-8KB per page + 40KB shared runtime | 14KB htmx + custom JS for charts |
| **SEO** | ❌ hash routing | ✅ each page has own URL | ✅ normal URLs |
| **Learning curve** | Already know it | Svelte 5 reactivity | htmx attributes + backend changes |
| **Complexity** | Custom Router + Component base class | Zero framework abstraction | Backend returns HTML instead of JSON |
| **Charts/visualization** | Canvas/vanilla JS | Svelte components | Needs custom JS — htmx alone insufficient |
| **LLM streaming** | Await full response | Fetch ReadableStream | SSE extension exists but complex |
| **PortOne SDK** | Script tag | Script tag in entry HTML | Same as others |
| **Migration risk** | None (staying) | Low — pages work independently | High — full API change |
| **Maintenance burden** | 🤮 (user's assessment) | Each page is standalone | New mental model for team |

## Why MPA over htmx

htmx would require converting all JSON API endpoints to return HTML fragments — a massive backend rewrite with no intermediate state. The existing API layer (Hono + Zod + controllers) is clean and working. htmx adds no value over keeping JSON APIs + Svelte on the frontend.

## Why MPA over Vanilla SPA

The user explicitly stated the SPA was too complex to maintain. The custom Component class, Router, AppShell (970 lines), and shared/ vs views/ duplication were the primary pain points. MPA eliminates all of these with standard `<a>` navigation and page-specific code.

## When SPA would be better

- App with complex client-side state that doesn't persist to server (e.g., game, design tool)
- Single-user dashboard with real-time updates
- Offline-capable PWA
- M-LOG has none of these characteristics.
