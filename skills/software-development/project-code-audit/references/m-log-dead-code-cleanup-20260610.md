---
date: 2026-06-10
project: m-log
type: clean-up
---

# m-log Dead Code Cleanup (2026-06-10)

## Project Context

Cloudflare Workers + D1 Saju/Four Pillars analysis platform. SPA frontend (`public/app/`) served via `wrangler assets`. Main worker at `worker.ts` (735 lines).

## Files Deleted (Zero Risk — Zero References)

| File | Lines | Reason |
|------|-------|--------|
| `src/api.ts` | 49 | Orphan — broken import path (`../public/js/` doesn't exist), zero imports from any file |
| `public/app/js/saju-data.js` | 15,975 (756KB) | Orphan — DEV_MODE mock JSON fixture. `DEV_MODE` was `false` in constants.js and never read. No HTML/JS references the file |
| `public/app/js/ganji.js` | 84 | Duplicate module — `GANJI` object duplicated data already in `constants.js` (STEMS/BRANCHES). Zero imports from other files |

## Dead Config Removed

- `constants.js`: removed `DEV_MODE: false` — never read by any module
- `constants.js`: removed `API.LOCAL_JSON: './response.json'` — never read by any module

## Duplicate CSS References Removed

- `public/app/index.html`: removed `<link>` tags for `analysis.css` and `history.css` — both were already loaded via `index.css` `@import`. Versioned with `?v=2.3.1` but `@import` in `index.css` has no cache-busting.

## Pre-existing Bugs Found

- `/home-beta` route in `worker.ts` rewrote to `/home-beta.html` (doesn't exist at assets root). Actual file is at `public/app/home-beta.html`.
- Email templates duplicated: inline `EMAIL_TEMPLATE` in `worker.ts` vs. separate `templates/marketing_v1.html`.
- SPA fallback 307 on `/app/index.html` → `/app/` — cosmetic, works.

## Bugs Fixed

- **`/home-beta` 404**: Changed from `env.ASSETS.fetch()` rewrite to `Response.redirect('/app/home-beta', 302)`. Root cause: `env.ASSETS.fetch()` in wrangler dev doesn't resolve paths the same way as direct HTTP requests. The redirect lets the normal assets serving chain handle it properly. (Applied: `worker.ts` line 149-153)

## CSS Chain Unification

- **`home.css` added to `index.css` @import chain**: was missing, only loaded directly by `home-beta.html`.
- **`home-beta.html` CSS unified**: replaced 3 separate `<link>` tags (variables.css, base.css, home.css) with single `index.css` reference. All pages now share one CSS entry point.

## Verification

All verified via `wrangler dev --port 8787`:
- `/app/` → 200 (31066 bytes)
- `/app/js/app.js`, `api.js`, `utils.js`, `renderer.js`, `canvas.js`, `parser.js`, `home-beta.js`, `constants.js` → all 200
- `/app/css/index.css` → 200
- `/app/js/ganji.js`, `/app/js/saju-data.js`, `/api.ts` → all 404 (confirmed deleted)
- No new 404s introduced by the cleanup
