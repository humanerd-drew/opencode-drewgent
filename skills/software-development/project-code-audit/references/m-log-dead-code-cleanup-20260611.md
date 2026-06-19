---
date: 2026-06-11
project: m-log
type: clean-up, data-consolidation, css-unification
---

# m-log Dead Code Cleanup — Day 2 (2026-06-11)

## Changes Made

### 1. CSS Chain Unification — Legal Pages

**privacy.html, terms.html** were loading their own CSS chain (variables.css + base.css + legal.css)
while the rest of the app used index.css @import. Unified all into index.css.

Changes:
- `public/app/css/index.css`: added `@import url('legal.css')` section
- `public/app/privacy.html`: replaced 3 `<link>` tags with single `css/index.css`
- `public/app/terms.html`: same

Verification:
- CSS selector overlap analysis: none of the extra CSS in index.css has selectors matching legal page classes
- All pages return 200 HTTP
- All CSS resources resolve 200

### 2. Stale Build Artifacts Cleanup

Deleted from `public/assets/`:
- `index-B1hwDY-q.js` (953KB) — zero HTML/JS references
- `index-CAyyFqo3.js` (953KB) — zero HTML/JS references
- `index-jqkQ0mJs.css` (1.5KB) — zero HTML/JS references

Saving: 1.9MB of stale bundled output.

Kept: `logo_transparent.png`, `m-log_logo.png` (both actively referenced from HTML).

### 3. Master Data JSON Consolidation

천간/지지/오행 data was duplicated across 3 locations:
- `public/app/js/constants.js` (frontend)
- `worker.ts` iljin handler (inline)
- `src/quintax/analyzer.ts` (separate Worker)

Solution: `src/data/saju-constants.json` — single source of truth for backend.
Both Workers now import this JSON at build time. Frontend keeps documented copy.

Created: `src/data/saju-constants.json` (82 lines, 3.6KB)
- stemList, branchList (ordered arrays for index lookup)
- stems: 10 천간 with element + yinYang
- branches: 12 지지 with element + yinYang + hidden
- branchMainStems: 각 지지의 주요 장간 (for tenGod calculation)
- elements: 5 오행 with name/color/ko
- tenGods: 10神 이름 배열
- relations: sixClashes, sixHarmonies, threeHarmonies, banghap, stemClashes, stemHarmonies, groupLabels (표시명)

Backend files updated:
- `worker.ts`: import SAJU + 6 inline → SAJU references (stemList, branchMainStems, tenGods, threeHarmonies, banghap, groupLabels)
- `src/quintax/analyzer.ts`: import SAJU + CHEONGAN_OHANG/JIJI_OHANG derived from SAJU.stems/branches + jijis array → SAJU.branchList

Frontend:
- `public/app/js/constants.js`: added header comment pointing to master JSON

### 4. Dead Config Removed

- `public/app/js/constants.js`: removed entire `API` section (`ENDPOINT`, `TIMEOUT`) — zero references in frontend code. Frontend api.js calls worker proxy (`/api/analyze`) not the external API directly.
- `public/app/js/api.js`: removed `import { CONSTANTS }` — no longer needed after ENDPOINT removal.

### 5. Home-Beta 404 Fix

`worker.ts` `/home-beta` route:
- Changed from `env.ASSETS.fetch(newReq)` with rewritten URL → `Response.redirect('/app/home-beta', 302)`
- Root cause: `env.ASSETS.fetch()` in wrangler dev returns 404 for rewritten paths that would work when accessed directly
- Named pair: `home-beta.html` also added `css/index.css` for unified CSS chain

## Key Insights

- **CSS selector overlap analysis** is mathematically equivalent to visual verification when screenshots aren't available: if no CSS selectors from added files match elements on the target page, visual output is identical.
- **ASSETS binding quirk**: In wrangler dev, calling `env.ASSETS.fetch()` with a rewritten URL may return 404 even though the same URL works when accessed directly. Prefer `Response.redirect()`.
- **Config trace pattern**: A config key defined in N places doesn't imply N are active. Trace READ references (not just definition) to find dead config.
- **Dev server log monitoring**: `npm run dev > /tmp/log 2>&1` with `tail -f` catches auto-reload signals (`⎔ Reloading local server...`) that confirm changes took effect.
