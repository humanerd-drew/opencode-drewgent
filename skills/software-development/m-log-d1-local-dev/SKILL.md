---
name: m-log-d1-local-dev
title: M-LOG v2 D1 Local Dev Database
description: "Setting up local D1 dev database for m-log-v2 — production data import via better-sqlite3 (workerd-compatible SQLite 3.53.1), clean-state procedure, root-cause analysis of segfault/busy errors"
  session: "2026-06-15 m-log-v2 D1 import — full debug path from SQLITE_BUSY → segfault #11 → root cause: SQLite version mismatch (macOS 3.51.0 vs workerd)"
  decision: "system sqlite3 (3.51.0) creates DB files workerd cannot read — must use better-sqlite3 (bundles SQLite 3.53.1, matches workerd). One working script: scripts/import-db.cjs."
created: 2026-06-15
updated: 2026-06-15
---

# M-LOG v2 D1 Local Dev Database

## TL;DR

The dev workflow has **three layers** — if any one is wrong, dev fails with a different error:

1. **DB file format** — must be written by SQLite 3.53.1 (better-sqlite3), not macOS system sqlite3 (3.51.0). Mismatch → segfault.
2. **Wrangler state** — `.wrangler/state/v3` must be either intact OR fully recreated. Partial cleanup (e.g. `rm d1/` only) → cache metadata drift → segfault.
3. **Process state** — no orphan workerd/wrangler holding stale lock files. Use `dev:clean` script.

**The one working procedure** is below. Use it after any of the failures.

## Standard procedure (the only one that works)

```bash
# 1. Kill anything holding port 8787 or DB locks
pkill -9 -f wrangler 2>/dev/null
pkill -9 -f workerd 2>/dev/null
sleep 1

# 2. Wipe ALL wrangler state (NOT just d1/ — cache metadata also matters)
rm -rf .wrangler/state/v3

# 3. Let wrangler create the empty DB file (sets up metadata.sqlite correctly)
node node_modules/wrangler/bin/wrangler.js d1 execute m_log_db --local --command="SELECT 1;"

# 4. Import production data using better-sqlite3 (script at scripts/import-db.cjs)
node scripts/import-db.cjs
# This script: opens the DB with better-sqlite3 (SQLite 3.53.1, matches workerd),
# deletes the empty DB, recreates it from db-export.sql with foreign_keys=OFF,
# and writes in a single transaction (handles circular FK + large rows).

# 5. Start dev server
npm run dev
# OR if a previous dev session left stale state:
npm run dev:clean
```

**Do NOT do any of these:**
- ❌ `wrangler d1 execute --local --file=./db-export.sql` (121MB → TOOBIG / timeout)
- ❌ `rm -f .wrangler/state/v3/d1/*.sqlite-shm *.sqlite-wal` while DB is in WAL mode (corrupts state)
- ❌ Write D1 files with `/usr/bin/sqlite3` (version 3.51.0, causes segfault when workerd opens them)
- ❌ `wrangler d1 export` then keep the export file in git (contains 35+ users' PII — add to .gitignore)

## Root cause: the SQLite version mismatch

workerd (the Cloudflare Workers runtime) bundles its own SQLite. macOS system sqlite3 is a different version:

| SQLite | Source | Used by |
|---|---|---|
| **3.51.0** | `/usr/bin/sqlite3` (macOS) | CLI / scripts that write D1 files |
| **3.53.1** | bundled in workerd binary | reads D1 files at dev/test time |

When the version gap crosses a file format change, workerd segfaults on open:
```
*** Received signal #11: Segmentation fault: 11
  at workerd/util/sqlite.c++:842
```

**Root-cause fix:** use `better-sqlite3` (already a devDep in m-log-v2) to write D1 files. It bundles SQLite 3.53.1, matching workerd. Verify with:
```js
const Database = require('better-sqlite3');
const db = new Database(':memory:');
console.log(db.prepare('SELECT sqlite_version()').get());
// → { 'sqlite_version()': '3.53.1' }
```

If `npm rebuild better-sqlite3` is needed on a fresh machine, run it before importing.

## The `scripts/import-db.cjs` script

Create this file in the project root. It encapsulates the working pattern:

```js
const Database = require('better-sqlite3');
const fs = require('fs');
const path = require('path');

const DB_DIR = '.wrangler/state/v3/d1/miniflare-D1DatabaseObject';
const files = fs.readdirSync(DB_DIR);
const dbFile = files.find(f => f.endsWith('.sqlite') && !f.includes('metadata'));
if (!dbFile) {
  console.error('No D1 database file. Run `wrangler d1 execute m_log_db --local --command="SELECT 1;"` first.');
  process.exit(1);
}
const dbPath = path.join(DB_DIR, dbFile);

const db = new Database(dbPath);
db.close();
fs.unlinkSync(dbPath);  // delete empty stub

const sql = fs.readFileSync('./db-export.sql', 'utf-8');
const newDb = new Database(dbPath);
newDb.pragma('journal_mode = WAL');
newDb.pragma('synchronous = NORMAL');
newDb.pragma('foreign_keys = OFF');  // ignore circular users↔history FK during import
newDb.exec(sql);  // single transaction, handles 170KB rows without TOOBIG
newDb.close();
```

## Production export

```bash
node node_modules/wrangler/bin/wrangler.js d1 export m_log_db --remote --output=./db-export.sql
# 121MB SQL file, 1-2min, contains 35+ user records (PII)
```

Schema-only export (no data) is 11KB and finishes in seconds:
```bash
node node_modules/wrangler/bin/wrangler.js d1 export m_log_db --remote --no-data --output=./db-schema.sql
```

## Diagnostic flowchart

| Error | Likely cause | Fix |
|---|---|---|
| `SQLITE_BUSY: database is locked` | Stale lock file from killed wrangler | `npm run dev:clean` |
| `Segmentation fault: 11` on wrangler start | DB written with wrong SQLite version, OR partial `.wrangler/state` cleanup | Full `rm -rf .wrangler/state/v3` then re-run standard procedure |
| `wrangler d1 execute ... --file=db-export.sql` times out at 300s | 121MB file too big for the command | Use scripts/import-db.cjs instead |
| `statement too long: SQLITE_TOOBIG` | history rows are ~170KB each | Use scripts/import-db.cjs (no per-statement limit) |
| `FOREIGN KEY constraint failed` (users/history) | Circular FK: `users.primary_saju_id → history.id` and `history.user_id → users.id` | better-sqlite3 import script sets `foreign_keys=OFF` for the import only |
| `wrangler: command not found` | `wrangler` not on PATH | Use `node node_modules/wrangler/bin/wrangler.js` instead of `wrangler` |

## macOS bash 3.2 caveat

`rm -f .wrangler/state/**/*.sqlite-lock` is a no-op on the default macOS bash (3.2.57). The `**` recursive glob was added in bash 4+. Always use `find ... -delete`:

```bash
find .wrangler/state -name '*.sqlite-lock' -delete
```

## `npm run dev:clean` script (the safe one)

```json
"dev:clean": "pkill -9 -f 'wrangler' 2>/dev/null; pkill -9 -f 'workerd' 2>/dev/null; sleep 1; lsof -ti:8787 2>/dev/null | xargs -r kill -9 2>/dev/null; find .wrangler/state -name '*.sqlite-lock' -delete 2>/dev/null; node node_modules/wrangler/bin/wrangler.js dev"
```

Note: this script deliberately does **NOT** delete `*-shm` or `*-wal` files. Those are required by workerd in WAL mode. Deleting them corrupts state and causes segfault.

## NVIDIA Secret Keys (2026-06-15 정리)

Production keys (3 only):
- `NVIDIA_NIM_KEY`
- `NVIDIA_NIM_KEY_FALLBACK`  
- `NVIDIA_NIM_KEY_FALLBACK_2`

Legacy `NVIDIA_API_KEY` is removed from all code. Any new code that mentions `NVIDIA_API_KEY` is a bug — use the three `NVIDIA_NIM_KEY*` family only.

## PII safety

`db-export.sql` contains real user data (emails, names, profile pictures via URL). **Never commit it.** Add to `.gitignore`:
```
db-export.sql
db-schema.sql
.wrangler/
```
