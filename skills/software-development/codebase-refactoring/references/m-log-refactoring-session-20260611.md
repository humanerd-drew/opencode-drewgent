# m-log Refactoring Session — 2026-06-11

## Project Context
- Cloudflare Workers + D1 + Static Assets (Wrangler)
- Dual worker architecture: main (m-log.cc) + quintax sub-worker
- SPA frontend at `/app/` with vanilla JS ES modules
- External saju calculator API at `saju-calculator-api.humanerd.workers.dev`

## Dead Code Removed
| File | Size | Reason |
|------|------|--------|
| `src/api.ts` | 49 lines | Broken import path, zero references |
| `public/app/js/saju-data.js` | 15,975 lines / 756KB | Dev mock data, zero references |
| `public/app/js/ganji.js` | 84 lines | Duplicate of constants.js STEMS/BRANCHES, zero references |
| `public/assets/index-B1hwDY-q.js` | 953KB | Build artifact, zero references |
| `public/assets/index-CAyyFqo3.js` | 953KB | Build artifact, zero references |
| `public/assets/index-jqkQ0mJs.css` | 1.5KB | Build artifact, zero references |

## Dead Config Removed
- `constants.js`: `DEV_MODE`, `API.ENDPOINT`, `API.LOCAL_JSON`, `API.TIMEOUT`
- All had zero read-side references

## CSS Chain Consolidated
- `index.css` now @imports all 17 component CSS files + `legal.css` + `home.css`
- `privacy.html`, `terms.html`, `home-beta.html` all use `css/index.css` (single entry point)
- Removed duplicate `<link>` tags for `analysis.css` and `history.css` from `index.html`

## Master Data Source Created
- `src/data/saju-constants.json`: single source of truth for saju core data
- Backend consumers updated: `worker.ts` (iljin handler), `src/quintax/analyzer.ts`
- Frontend (`constants.js`): kept as standalone copy with master reference comment

## Bugs Found & Fixed
- `/home-beta` 404: worker.ts looked for `home-beta.html` at root, file was at `app/home-beta.html` → fixed with 302 redirect

## Security Fixes
- `localStorage` → `sessionStorage` for `__SAJU_DATA__` and `__FORM_VALUES__` (PII/birth data)
  - `__SAJU_DATA__`: 3 occurrences (line 97 getItem, line 523 setItem, line 852 getItem in app.js)
  - `__FORM_VALUES__`: 2 setItem + 2 getItem (lines 520, 1980, 863, 1394 in app.js)
  - Left in localStorage: `__ANONYMOUS_ID__` (cross-session merge), `theme` (preference), `SYNC_QUEUE_KEY` (offline delivery)
- Removed email from `console.log("Authenticated as:", this.user.email)` in `home-beta.js:31` → `this.user.id`
- Removed raw API response from `console.error('[History] Sync failed:', response.status, result)` in `app.js:1746` → removed `result` param
- Fixed `utils.js:14,38` response body snippets in error logs (kept but noted as residual risk)

## User-Preferred Workflow
- "하나씩" (one change at a time)
- Verify with `wranger dev` running, monitor reload logs
- Show dependency maps before making changes
- Detailed analysis data before asking for decisions
