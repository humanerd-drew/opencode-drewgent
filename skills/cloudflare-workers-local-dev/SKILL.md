---
title: Cloudflare Workers Local Development
name: cloudflare-workers-local-dev
description: Patterns, pitfalls, and workflows for local Cloudflare Workers development with D1, static assets, multi-source integration, and the m-log refactoring architecture.
domain: devops
tags: [devops, cloudflare, workers, d1, wrangler, local-dev]
created: 2026-06-11
updated: 2026-06-15
---

# Cloudflare Workers Local Development

Patterns and pitfalls for local Cloudflare Workers development with D1, static assets, and multi-source integrations.

## Core Principles

### Understand the system before touching code
- Map the complete dependency graph first: which files import what, what data flows where, what's dead code
- Check the ACTUAL running system (curl the endpoints, read the files) before asserting connections
- Look for pre-existing architecture documents (ARCHITECTURE.md, README.md) before refactoring
- Compare original/NAS versions with working copies to find divergence points

### Never reimplement what the external API already provides
- When an external API returns computed data, use it — don't recalculate
- Only compute what the external API doesn't provide
- Check the ACTUAL API response structure before coding against assumptions

## D1 Local Development

### SQLITE_BUSY error
Cause: Another `wrangler dev` instance holds a lock, or a stale `.sqlite-lock` file from a previous crash. Lock files exist in multiple locations (D1 metadata, Cache metadata), not just the D1 data directory.

**Critical pitfall — `pkill -f 'wrangler'` does NOT kill the child workerd:**
`wrangler dev` spawns a child `workerd` process that holds the SQLite file handle. `pkill -f 'wrangler'` only matches the parent `wrangler.js` node process, so the child workerd keeps running and keeps the DB locked. A `dev:clean` script that only pkill's wrangler is **structurally broken** — it WILL hit SQLITE_BUSY on the next start. **Always match workerd too**, and force-kill (-9) so the lock releases immediately:
```bash
pkill -9 -f 'wrangler' 2>/dev/null
pkill -9 -f 'workerd'  2>/dev/null
# also clear the port in case a stale process is bound:
lsof -ti:8787 2>/dev/null | xargs -r kill -9 2>/dev/null

### SQLITE_BUSY error
Cause: Another `wrangler dev` instance holds a lock, or a stale `.sqlite-lock` file from a previous crash. Lock files exist in multiple locations (D1 metadata, Cache metadata), not just the D1 data directory.

**Diagnose before fixing** — orphan `workerd` processes are the most common root cause and easy to miss:
```bash
# Find all wrangler/workerd processes (note: the holder is `workerd`, not `wrangler.js`)
ps aux | grep -E '(wrangler|workerd)' | grep -v grep
# List every TCP port the dev server and its children are listening on
lsof -nP -iTCP -sTCP:LISTEN | grep -E '(wrangler|workerd|8787)'
# Confirm which PID is the actual SQLite holder (look for `workerd serve` with entry=localhost:8787)
lsof -nP -iTCP:8787 -sTCP:LISTEN
```

Two failure modes to watch for:
- **Stale child workerd** — `pkill -f 'wrangler'` killed the parent but the `workerd` grandchild survived. Force-kill it directly: `kill -9 <workerd-pid>`. Don't trust the process tree to clean itself up.
- **Orphan from a previous session** — a workerd from a different day/session can still hold the lock. Check `ps -o etime=` (elapsed time) — anything > 1 hour without you running dev is suspect.

Fix (least destructive first):
1. Kill the duplicate `wrangler dev` / `workerd` process — identify via `lsof -i :<port>` then `kill <pid>`
2. If that doesn't work, kill ALL wrangler/workerd processes and restart one
3. Remove stale lock files only (preserves data):
   ```bash
   find .wrangler/state -name '*.sqlite-lock' -delete
   ```
   ⚠️ **Why `find -delete` instead of `rm -f` with globs**: macOS bash 3.2 does NOT support `**` glob expansion. `rm -f .wrangler/state/**/*.sqlite-lock` silently does nothing. `find -delete` works reliably.
4. If lock cleanup alone doesn't work, also remove WAL/SHM files left by sqlite3 (the lock might be from a different SQLite process):
   ```bash
   rm -f .wrangler/state/v3/*/miniflare-*Object/*.sqlite-shm
   rm -f .wrangler/state/v3/*/miniflare-*Object/*.sqlite-wal
   ```
   ⚠️ Only delete SHM/WAL if the DB was modified by a non-miniflare tool (sqlite3 CLI). Under normal wrangler usage, SHM/WAL are managed by workerd and should NOT be deleted.
5. Last resort: clear ALL wrangler state entirely:
   ```bash
   rm -rf .wrangler/state/v3/
   ```
   This drops ALL local data. Schema is recreated from migrations on next start, but test data is lost.

### Workerd segfault when reading SQLite database

**Root cause:** macOS system sqlite3 (MacPorts 3.51.0) creates database files with a binary format that workerd's internal SQLite cannot read. The file is structurally valid — queries work, `PRAGMA integrity_check` passes — but workerd segfaults (Signal #11) on open.

**Fix:** Use better-sqlite3 (SQLite 3.53.1) to create the database file. This is the same SQLite version that miniflare/wrangler bundles, so workerd reads it cleanly. See "D1 Export/Import from Production" section below for the exact workflow.

**Detection:**
- Segfault on `wrangler d1 execute --local` even with a simple `SELECT 1`
- Segfault on `wrangler dev` with error "Received signal #11: Segmentation fault"
- Database file created by `/usr/bin/sqlite3` (macOS default) triggers this every time

**Hardening the import chain (so it never happens again):**
```bash
# WRONG — uses system sqlite3 (causes segfault)
sqlite3 database.db ".read export.sql"

# CORRECT — uses better-sqlite3 via Node.js (no segfault)
node scripts/import-db.cjs
```

**Why SHM/WAL deletion causes segfault even with the correct SQLite version:**
When `dev:clean` deletes `.sqlite-shm` and `.sqlite-wal` files from a WAL-mode database, workerd tries to recover the WAL on open. If the SHM file is missing but the WAL has data, the recovery fails and workerd segfaults. **Never delete SHM/WAL in a dev:clean script.** Only delete them if a known external tool (system sqlite3) was used on the DB — and in that case, you should be using better-sqlite3 instead anyway.

### Dev startup script with lock cleanup

**Common bug** (seen 2026-06-15 on m-log-v2): the naive script
```json
"dev:clean": "pkill -f 'wrangler' 2>/dev/null; sleep 1; find .wrangler/state -name '*.sqlite-lock' -delete; node node_modules/wrangler/bin/wrangler.js dev"
```
FAILS on every restart because `pkill -f 'wrangler'` only kills the `wrangler.js` parent process. The actual SQLite holder is the **child `workerd` process**, which survives `pkill -f 'wrangler'` and keeps holding the `.sqlite` lock. The next `wrangler dev` then hits `SQLITE_BUSY` immediately.

**Fix** — kill both, force-kill the port. **Do NOT delete SHM/WAL files** (that causes segfault):
```json
"dev:clean": "pkill -9 -f 'wrangler' 2>/dev/null; pkill -9 -f 'workerd' 2>/dev/null; sleep 1; lsof -ti:8787 2>/dev/null | xargs -r kill -9 2>/dev/null; find .wrangler/state -name '*.sqlite-lock' -delete 2>/dev/null; node node_modules/wrangler/bin/wrangler.js dev"
```

Why each piece matters:
- `pkill -9 -f 'workerd'` — the actual SQLite holder. Without this, the lock survives.
- `lsof -ti:8787 | xargs -r kill -9` — port-level safety net for any process that escaped the pkill pattern match.
- **Only lock files are deleted.** SHM/WAL are never touched — they are essential for WAL-mode database integrity.

Add to `package.json` to prevent SQLITE_BUSY on every dev start.

This kills any stale wrangler, waits for ports to release, removes lock files, then starts dev. The `sleep 1` is critical — without it, the port may still be held.

**bash 3.2 compatibility note**: Use `find -delete` not `**` globs. macOS default shell is bash 3.2 (no `globstar` support).

### ⚠️ Pitfall: `pkill -f 'wrangler'` alone is NOT enough

`pkill -f 'wrangler'` (without `-9`, and without matching `workerd`) only kills the **parent** `node wrangler.js` process. The actual SQLite DB holder is the **child `workerd` binary** that wrangler spawns to run the Worker runtime — and it survives the parent's death as an orphan, still holding the `.sqlite` lock and the dev port (8787 by default).

Result: `wrangler dev` is "killed" but `lsof -i:8787` still shows `workerd` listening, and the next `wrangler dev` start hits `SQLITE_BUSY` immediately.

**Always include in the cleanup chain:**
1. `pkill -9 -f 'wrangler'` — force-kill the parent
2. `pkill -9 -f 'workerd'` — force-kill the orphaned child (THIS is the DB holder)
3. `lsof -ti:<port> | xargs -r kill -9` — belt-and-suspenders port release in case the process name doesn't match (e.g. esbuild service, leftover from crash)
4. `find .wrangler/state -name '*.sqlite-lock' -delete` — leftover lock files
5. ⚠️ Do NOT delete SHM/WAL files in dev:clean — they are essential for WAL-mode database integrity. Only delete them if the DB was modified by a non-miniflare tool (system sqlite3 CLI), and in that case, recreate the DB with better-sqlite3 instead.

**Verification after dev:clean:**
```bash
sleep 2
lsof -nP -iTCP:8787 -sTCP:LISTEN 2>/dev/null   # must be empty
ps aux | grep -E '(wrangler|workerd)' | grep -v grep   # must be empty
# then start fresh and watch for "Ready on http://localhost:8787"
```

If `workerd` keeps reappearing after pkill, an old launchd/keep-alive service is involved — check `launchctl list | grep -iE '(wrangler|workerd)'` and bootout the service with `launchctl bootout gui/$(id -u)/<label>`.

### D1 Export/Import from Production

> **Resources under this skill:** `scripts/import-db.cjs` (reusable import script — uses better-sqlite3, SQLite 3.53.1), `references/d1-sqlite-version-mismatch.md` (debugging guide for segfault/SQLITE_BUSY)

로컬 개발 시 프로덕션 D1 데이터를 그대로 사용해야 할 때. `wrangler d1 export`로 원격 DB를 SQL 파일로 내보내고 로컬에 복원한다.

#### 🚨 `wrangler d1 execute --local --file=` 는 대용량 IMPORT에 부적합

3가지 이유로 실패할 수 있음:
1. **Timeout**: 100MB+ SQL → 300초 초과
2. **Circular FK**: `users ↔ history` 같은 순환 참조가 schema에 있으면 어느 테이블도 먼저 INSERT 불가
3. **SQLITE_TOOBIG**: 한 INSERT 문이 150KB+면 SQLite 문장 길이 제한 초과 (history 테이블의 JSON blob)

#### 🚨 macOS system sqlite3(3.51.0) 사용 절대 금지

`sqlite3 .read db-export.sql`로 DB를 만들면 **workerd segfault** 발생. macOS 기본 sqlite3(3.51.0)와 workerd 내장 SQLite의 바이너리 포맷 불일치가 원인. 반드시 **better-sqlite3(SQLite 3.53.1)** 를 사용해야 함.

**안전한 방법:** better-sqlite3로 DB 파일 직접 생성 (아래 전체 Export/Import 참고).

#### 전체 Export/Import (schema + data, 안정적인 방법)

better-sqlite3는 wrangler/miniflare가 사용하는 SQLite와 동일한 버전(3.53.1)을 내장하고 있음. 이걸로 DB 파일을 만들면 workerd가 segfault 없이 읽을 수 있음.

전체 workflow (`scripts/import-db.cjs` 참고):

```bash
# 1. 프로덕션 D1 전체 export (schema + data)
wrangler d1 export <DB_NAME> --remote --output=./db-export.sql

# 2. 로컬 D1 상태 초기화 + metadata 생성
rm -rf .wrangler/state/v3
wrangler d1 execute <DB_NAME> --local --command="SELECT 1;"

# 3. better-sqlite3로 전체 데이터 import
node scripts/import-db.cjs

# 4. dev 서버 실행
npm run dev
```

**`rm -rf .wrangler/state/v3` (not just `/d1`) is critical** — cache metadata can also be corrupted and cause segfault. Always nuke the whole `v3/` directory, not just the `d1/` subdirectory.

`scripts/import-db.cjs` 내용:

```javascript
const Database = require('better-sqlite3');
const fs = require('fs');
const path = require('path');

const DB_DIR = '.wrangler/state/v3/d1/miniflare-D1DatabaseObject';
const files = fs.readdirSync(DB_DIR);
const dbFile = files.find(f => f.endsWith('.sqlite') && !f.includes('metadata'));
const dbPath = path.join(DB_DIR, dbFile);

// Delete empty DB created by wrangler, recreate from export
fs.unlinkSync(dbPath);
const sql = fs.readFileSync('./db-export.sql', 'utf-8');
const db = new Database(dbPath);
db.pragma('journal_mode = WAL');
db.pragma('synchronous = NORMAL');
db.pragma('foreign_keys = OFF');  // 필수: circular FK (users↔history)
db.exec(sql);
db.close();
```

**왜 이게 유일하게 동작하는가:**
- system sqlite3(3.51.0) → workerd segfault
- `wrangler d1 execute --local` → SQLITE_TOOBIG (170KB+ statements)
- better-sqlite3(3.53.1) = workerd/miniflare SQLite와 동일 버전 → ✅ 정상 동작

**`PRAGMA foreign_keys=OFF`가 필수인 이유:** `users.primary_saju_id REFERENCES history(id)` ↔ `history.user_id REFERENCES users(id)` 순환 FK 때문.

#### Schema-only Export (데이터 없이 구조만)

빠르고 안전함. 테스트 시 schema 구조만 필요한 경우:

```bash
wrangler d1 export <DB_NAME> --remote --no-data --output=./db-schema.sql
wrangler d1 execute <DB_NAME> --local --file=./db-schema.sql
# 11KB, 44개 명령어 1초
```

#### 용도별 선택

| 목적 | 명령어 | 비고 |
|------|--------|------|
| 깨끗한 로컬 DB (schema만) | `wrangler d1 export --no-data` + execute | 11KB, 1초 |
| 프로덕션 전체 복제 | `wrangler d1 export --remote` + `node scripts/import-db.cjs` | 120MB, 2초 |
| lock만 정리 (데이터 보존) | `find .wrangler/state -name '*.sqlite-lock' -delete` | bash 3.2 glob 주의 |
| 전면 초기화 | `rm -rf .wrangler/state/v3/` | 데이터 전소, cache도 같이 초기화됨 |

### Auto-migration for local dev
Add an `ensureTables()` function that auto-creates tables on first write using try/catch pattern with SELECT probe → CREATE TABLE IF NOT EXISTS.

**IMPORTANT:** `env.DB.exec()` does NOT support multi-line template strings or multiple statements in one call. Each SQL statement MUST be a single line in a separate `.exec()` call:
```javascript
// BROKEN — multi-line + multi-statement
await env.DB.exec("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY); CREATE TABLE IF NOT EXISTS history (...);");

// WORKS — single line, single statement
await env.DB.exec("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL)");
await env.DB.exec("CREATE TABLE IF NOT EXISTS history (id TEXT PRIMARY KEY, user_id TEXT NOT NULL)");
```

### D1 error breaks auth chain
If `/api/auth/me` queries users table and D1 doesn't have it, the SPA shows blank screen. Wrap DB queries in try/catch.

## Frontend Integration

### Import path resolution
Absolute imports like `/app/shared/core/store.js` work via HTTP. CSS `@theme/` aliases don't — use relative paths.

### Dev login bypass
Create `/api/auth/dev-login` that works only when `IS_LOCAL_DEV=true`, creates session cookie, redirects to `/app/`.

### Email/password auth in Workers
PBKDF2 password hashing is available via the Web Crypto API (`crypto.subtle`) — no external packages needed.
- Use `crypto.subtle.importKey`, `deriveBits` with salt (16 bytes), 100000 iterations, SHA-256
- Store salt+hash as base64 string; verify by re-deriving with the same salt

## Frontend UX Patterns (m-log)

### Report card navigation
Report cards in the dashboard have different destinations depending on the report type:

- **Free inline report** (나의 Log 리포트): Scroll to the dashboard's inline section. The card should NOT navigate away from the dashboard — use `scrollIntoView` on the hub container:
  ```javascript
  navigateToAiReport() {
      const hub = document.getElementById('aiReportHub');
      if (hub) hub.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  ```
- **Paid standalone reports** (대세월운 종합, 연애/궁합): Navigate to the dedicated route. Each report view has its own input→payment→result flow built in:
  ```javascript
  navigateToLuckReport()   { window.location.hash = '#/report-luck'; }
  navigateToDatingReport() { window.location.hash = '#/report-dating'; }
  ```
- **New/enhanced reports** (욕망 & 기질): Navigate to the report page route. The report view handles input form, payment redirect, and result display within itself:
  ```javascript
  navigateToDesireReport() { window.location.hash = '#/report-desire'; }
  ```

**Principle:** Keep the free report as an inline section on the dashboard to minimize navigation friction. Route paid/enhanced reports to dedicated pages that each encapsulate the full input→payment→result lifecycle.

### History list display
History items (both saju and report) should always show:
- **Label** (user-given name or auto-title)
- **Birth info** (year.month.day) from `item.formData`
- **Analysis date** (formatted timestamp from `item.timestamp`)

**Pitfall: Nested formData causes "undefined" in display**
When saving history, ensure `formData.year/month/day` exist at the top level. Reports that save nested formData (e.g. `{ personA: {...}, personB: {...}, mode: 'analyze' }`) will render `undefined.undefined.undefined` in the history sidebar:
```javascript
// BROKEN - formData exists but has no top-level year
const reportBirthStr = item.formData 
    ? `${item.formData.year}.${item.formData.month}.${item.formData.day}`
    : '';

// FIXED - check for top-level year existence first
const reportBirthStr = (item.formData && item.formData.year)
    ? `${item.formData.year}.${item.formData.month}.${item.formData.day}`
    : '';
```
Always validate `formData.year` before rendering birth info strings.

For **nested formData** (e.g. dating reports with `personA`/`personB`), extract the birth info from the first person that has data:
```javascript
const reportPerson = item.formData?.personA?.year ? item.formData.personA 
    : (item.formData?.personB?.year ? item.formData.personB : null);
const reportBirthStr = reportPerson 
    ? `${reportPerson.year}.${reportPerson.month}.${reportPerson.day}` 
    : '';
```

When **restoring** a dating report from history in `init()`, explicitly restore `personA` and `personB` from `__RESTORE_FORM_DATA__`:
```javascript
const formData = JSON.parse(localStorage.getItem('__RESTORE_FORM_DATA__') || '{}');
if (formData.mode) this.state.activeTab = formData.mode;
if (formData.personA) this.state.personA = { ...this.state.personA, ...formData.personA };
if (formData.personB) this.state.personB = { ...this.state.personB, ...formData.personB };
```
Without this, clicking a history item followed by a CTA tab switch would show empty forms.

Report history items were missing birth info — add via `${item.formData.year}.${item.formData.month}.${item.formData.day}`.

### Free report CTA
The free report's premium CTA should navigate to the comprehensive report (`#/report-luck`) instead of showing a toast placeholder. Change `<button onclick="...toast...">` to `<a href="#/report-luck">`.

## SPA Hash Routing

### History restore from same route (force hashchange)
When restoring a report from history while already on the same hash route (e.g., already on `#/report-dating` and clicking another dating history item), setting `window.location.hash = '#/report-dating'` does NOT trigger a `hashchange` event because the hash value hasn't changed. The Router never re-runs, so the restore data saved to localStorage is never read.

**Fix:** Append `?t=${Date.now()}` to make each navigation hash unique:
```javascript
const hash = '#/report-dating?t=' + Date.now();
window.location.hash = hash;
```
The Router strips query params (`path.split('?')[0]`) so routing still works. This pattern applies to ALL report history restore navigations.

### Payment-flow report restore
For paid reports, the intended flow is:

1. User enters data, clicks analyze
2. **API call runs immediately** (before payment check)
3. Report result saved to `__RESTORE_REPORT__` + `__RESTORE_FORM_DATA__` in localStorage
4. Redirect to payment page
5. After payment, user returns to the report route
6. `init()` finds restore data, restores `reportData`, sets `isSimulatingAnalysis: true`
7. `mounted()` runs loading simulation (2.5s) with animated text
8. Loading ends, `isSimulatingAnalysis: false`, report content renders

Key implementation details:
- **Remove payment early-return** from `handleAnalyze()`. The check `if (activeTab === 'X' && !isPaidX)` must be AFTER the API call, not before.
- **Save restore data** in the redirect branch:
  ```javascript
  localStorage.setItem('__RESTORE_REPORT__', JSON.stringify(savedReport));
  localStorage.setItem('__RESTORE_FORM_DATA__', JSON.stringify({ ...formData }));
  localStorage.setItem('__RESTORE_REPORT_TYPE__', 'dating');
  ```
- **In `init()`**, after restoring report data, check payment and set `isSimulatingAnalysis: true`:
  ```javascript
  const purchased = JSON.parse(localStorage.getItem('__PURCHASED_REPORTS__') || '{}');
  if (purchased.dating_compatibility || purchased.dating_divorce) {
      this.state.isSimulatingAnalysis = true;
  }
  ```
- **In `mounted()`**, guard against re-entry with a `_simStarted` flag:
  ```javascript
  if (this.state.isSimulatingAnalysis && !this._simStarted) {
      this._simStarted = true;
      this.startLoadingSimulation();
      setTimeout(() => {
          this.stopLoadingSimulation();
          this._simStarted = false;
          this.setState({ isSimulatingAnalysis: false });
      }, 2500);
  }
  ```
- **In template**, check `isSimulatingAnalysis || loading` to show the loading animation.

**Pitfall:** If the loading simulation uses `setState` (e.g., text animation), `mounted()` is called again each time. Without `!_simStarted`, multiple simulations stack and the report never stabilizes.

### CTA Tab Switch preserves form data
When clicking a CTA inside a report result (e.g., "궁합 CTA to 갈등"), form elements are NOT in the DOM because the report template is active. `syncInputsFromDOM()` finds no `#meYear` and leaves state unchanged.

**Fix:** Save form data to state BEFORE the API call:
```javascript
const personA = getPersonFromDOM('me');
const personB = getPersonFromDOM('partner');
// ... validation ...
this.state.personA = personA;
this.state.personB = personB;
```
When the CTA switches tabs (`setState({ activeTab, reportData: null })`), the template reads the saved `personA`/`personB` and prefills correctly.

## Refactoring Workflow

### One-at-a-time principle
Make one change, test with curl, show before committing. Never commit without user review.

### Controller-based architecture
1. Create controllers with identical logic
2. Update worker.ts to dispatch to controllers
3. Keep cross-cutting concerns in the router layer

### Analysis engine layers (L0-L3)
L0=원국, L1=+대운, L2=+세운, L3=+월운. Each adds 2 characters. Δ between layers reveals the time period's theme.

### Blank-screen diagnosis protocol
When the SPA loads (200 OK for HTML/CSS/JS) but the screen is blank:

**Check the root URL first (fastest diagnosis):**
1. Curl `http://localhost:8787/`. If it returns 404 instead of a redirect, the root→SPA redirect is inside `if (assets)` which is dead code in local dev (env.ASSETS binding not available). Move the redirect outside the assets check.

**If the root redirect works but page is still blank (JS issue):**
2. Check browser console for JS errors (SyntaxError, reference errors)
3. **Check for stray backticks in template literals** — A common subtle bug is an extra backtick inside an HTML template literal like `">\`` at the end of an HTML tag line. This prematurely closes the template, leaving the rest parsed as raw JS. The error is typically `Missing } in template expression` at a line number that looks like HTML, not JS. 
   - **Diagnosis without a browser:** Run `node --input-type=module -e "try { await import('./path/to/file.js'); } catch(e) { console.log(e.message); }"`. If the error is "Missing } in template expression" → syntax error. If it's "Cannot find module '/app/...'" → that's expected (absolute path resolution on filesystem), the code is syntactically fine.
   - **Targeted check:** Run `node --check file.js` for CommonJS files, or use the `--input-type=module` approach above for ES modules.
4. Run `node --check <file>` on ALL imported modules — Wrangler/esbuild may not catch template literal syntax errors during dev
5. Verify DOM mount points exist in the served HTML: `id="app"`, `id="contentView"` etc.
6. Verify all module import paths resolve by curling each one
7. Wrap each init step in try/catch to isolate which step breaks

## CSS Layer Architecture (z-index)

### Standard layer stack (variables.css)
```
--z-negative: -1       (behind everything)
--z-base: 1            (default content)
--z-sticky: 100        (sticky headers)
--z-header: 500        (top nav bar)
--z-dropdown: 1000     (dropdown menus)
--z-overlay: 2000      (semi-transparent backdrops)
--z-fab: 2000          (floating action buttons)
--z-drawer: 3000       (sidebars, drawers)
--z-backdrop: 4000     (modal backdrops)
--z-modal: 5000        (modal dialogs)
--z-popover: 6000      (popovers)
--z-tooltip: 7000      (tooltips)
--z-toast: 9000        (toast notifications)
--z-max: 10000         (loading overlays)
```

### Key rules
- **NEVER use hardcoded z-index values** — always use `var(--z-*, fallback)` so the layer system is maintainable
- **Find hardcoded z-index values in CSS:** `grep -rn "z-index:" public/app/css/ --include='*.css' | grep -v "var("` — then replace each with the appropriate CSS variable
- **Find hardcoded z-index values in JS inline styles:** `grep -rn "z-index:" public/app/js/ --include='*.js' | grep -v "var(--z"` — these are harder to catch but also need fixing
- **var(--z-breakdown-sheet, 5000)** sits at modal level; define it in variables.css
- **`position: fixed` inside `transform` becomes relative to the transform container, not viewport.** This is a CSS spec behavior. A sidebar with `transform: translateX(-100%)` creates a new containing block for any `position: fixed` children inside it. Fix: append modals to `document.body` via JS.
- **Hardcoded z-index values common in inline styles** — find with `grep -rn "z-index:"` in JS files and replace with CSS variables

### Breakdown sheet desktop fix
The `.breakdown-sheet` uses `position: fixed; left: 0; right: 0;` which covers the full viewport. On desktop with a visible sidebar (280px wide), add:
```css
@media (min-width: 1024px) { body.is-desktop .breakdown-sheet { left: 280px; } }
```

## Modal Positioning

### transform container trap
When a modal's HTML is inside a container with `transform`, `position: fixed; inset: 0` constrains the modal to the container bounds, not the viewport.

**Fix:** Append modal elements to `document.body` in `mounted()`:
```javascript
const container = document.createElement('div');
container.innerHTML = this.renderLoginModal();
document.body.appendChild(container.firstElementChild);
```

### Event delegation with body-appended modals
Elements appended to `document.body` won't be caught by event delegation on a child container (`#app`). **Bind events directly** after appending:
```javascript
document.getElementById('myModalBtn')?.addEventListener('click', () => this.handler());
```

## Backend Route Alignment

### Check frontend API calls match registered routes
Search for all `fetch('/api/...')` calls in the frontend and verify each has a corresponding route in worker.ts. Common mismatches:
- `/api/report/generate` → must add route or change frontend to call `/api/report`
- `/api/report/free-log` → same pattern
- Missing routes cause 404 → JSON parse error on frontend

### Pattern: controller file exists but route is missing
This is a common failure mode. The controller file is already written (`src/controllers/something.ts`) but never imported or routed in `worker.ts`:

1. **Add the import** at the top of worker.ts:
   ```javascript
   import { handleMyController } from './src/controllers/my-controller';
   ```

2. **Add the route** inside the API try-block, before the catch:
   ```javascript
   if (url.pathname.startsWith('/api/my-path/') && request.method === 'POST') {
       return handleMyController(request, env, url);
   }
   ```

3. **Verify** with `curl -X POST http://localhost:8788/api/my-path/test -H "Content-Type: application/json" -d '{}'`. A 401 (Unauthorized) means the route is live — the auth check inside the handler is working. A 404 means the route is still missing.

### Cross-check: frontend URL in run-time API call vs worker.ts route pattern
If the frontend calls `/api/dating/${mode}` (with the mode from the `activeTab` state), the worker.ts route must match with `startsWith('/api/dating/')`. Any mismatch in prefix or HTTP method produces a silent 404 on the frontend, which manifests as a generic "리포트 생성 실패" error in the report view.

## `env.ASSETS` Binding vs `assets` Config

### The two systems
- **`wrangler.jsonc` `assets: { directory: "./public" }`** (v4+): Static files served at the workerd RUNTIME level. This does NOT create an `env.ASSETS` binding in local dev.
- **`env.ASSETS: Fetcher`**: A worker binding that lets the worker code programmatically fetch static files. Only available in PRODUCTION (Cloudflare edge) or when using the legacy `workers.dev` site config.

### What this means for your code
Any code inside `if (env.ASSETS)` is DEAD in local dev:
```javascript
const assets = env.ASSETS;
if (assets) {
    // This block NEVER runs in wrangler dev
    // Root redirect, SPA fallback, etc. all dead
}
```

### Fix: move root redirects OUTSIDE the assets check
```javascript
// ✓ WORKS everywhere — outside the assets block
if (url.pathname === '/' || url.pathname === '') {
    return Response.redirect(new URL('/app/', url.origin).toString(), 302);
}

// Only for programmatic asset access (production only)
const assets = env.ASSETS;
if (assets) {
    let assetRes = await assets.fetch(request);
    // SPA fallback...
}
```

### Production note
On deployed Cloudflare Workers, both systems coexist — the runtime serves `./public/` files directly, AND `env.ASSETS` is available as a `Fetcher` binding for programmatic access. So moving redirects outside `if (assets)` fixes local dev without breaking production.

## Assets Config and Root Index

### `public/index.html` is NOT auto-served at `/` in local dev
Even when a `public/index.html` exists, workerd in local dev mode does NOT serve it at the root URL. Requesting `/index.html` returns a 307 redirect to `/` which then falls to the worker → 404.

**Fix:** Always add an explicit `/` → `/app/` redirect in the worker (outside `if (assets)`), or configure proper `html_handling` in wrangler.jsonc.

## Pitfalls
- **Patch tool backtick escaping:** When `patch` adds JS template literals containing backticks, it encodes them as `\`` which is a syntax error. Verify with `node --check` after every patch that touches template literals.
- **Root redirect inside `if (assets)` is dead code in local dev** — always place root/SPA redirects before the assets check.
- **Template literal stray backtick:** A `\`` character at the end of an HTML tag line inside a template literal (like `">\``) terminates the template early, causing `Missing } in template expression`. This is NOT caught by bundlers — only by `node --input-type=module` or browser JS engine.
- **`node --input-type=module` for ES module syntax check** — `node --check` doesn't work for ES modules. Use the full `await import()` approach with try/catch instead.
- Overwriting `public/app/` loses custom modal work — re-apply
- SynologyDrive corrupts node_modules/.bin symlinks (XSym files)
- CSS `@theme/` alias doesn't resolve without build tool — use `../shared/theme/` instead
- localStorage→sessionStorage migration may break Router's cached-data checks (search ALL files for `localStorage.getItem('__SAJU_DATA__')`)
- Service worker caches old files — use Cmd+Shift+R or clear SW in DevTools
- `npm run build:frontend` fails (no vite config) — use `npm run dev` for static serving
- **Deleting SHM/WAL files in dev:clean causes workerd segfault** — never include `rm -f *.sqlite-shm *.sqlite-wal` in a dev:clean script. Only delete them if the DB was modified by system sqlite3 CLI, and in that case, recreate with better-sqlite3 instead.

## Running dev server in the background (Hermes / Claude Code)
The Hermes `terminal(background=true)` policy rejects shell-level wrappers like `nohup ... &`, `disown`, `setsid`, and trailing `&` when run in foreground mode. The right shape is:

```javascript
// Foreground tool call
terminal({
  background: true,
  notify_on_complete: true,   // almost always pair this; otherwise you go silent
  command: "cd ~/m-log-v2 && exec npm run dev:clean > /tmp/wrangler-dev.out 2>/tmp/wrangler-dev.err"
})
```

Key shape requirements:
- `exec` at the start so the npm wrapper is replaced by wrangler as PID 1 (avoids an extra zombie npm parent)
- explicit `> out 2> err` redirection — `tee` exits on SIGPIPE when the parent shell terminates, which can take the whole process group with it
- DO NOT pipe through `tee` for long-lived servers

Readiness verification (run in a separate `terminal` call, NOT the background tool):
```bash
sleep 8
cat /tmp/wrangler-dev.out
ps aux | grep -E '(wrangler|workerd)' | grep -v grep
lsof -nP -iTCP:8787 -sTCP:LISTEN | head -3
curl -s -o /dev/null -w "HTTP %{http_code} | %{time_total}s\n" http://127.0.0.1:8787/
```

The `sleep` is intentional — wrangler takes 3-8 seconds to print "Ready" depending on bundle size. Poll the file, don't tail.