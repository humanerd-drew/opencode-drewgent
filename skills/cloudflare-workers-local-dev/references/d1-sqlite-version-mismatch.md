# D1 Local SQLite Version Mismatch Debugging

## Symptom
`wrangler dev` starts, shows bindings, then crashes with:
```
*** Received signal #11: Segmentation fault: 11
```
or
```
*** Fatal uncaught kj::Exception: ... database is locked: SQLITE_BUSY
```

## Root Cause

There are **three different SQLite implementations** in play, and they produce incompatible database files:

| SQLite | Version | Where | Used By |
|--------|---------|-------|---------|
| macOS system | 3.51.0 (as of macOS 26.5.1) | `/usr/bin/sqlite3` | Direct CLI usage, `sqlite3 .read` |
| better-sqlite3 | 3.53.1 | `node_modules/better-sqlite3` | miniflare (wrangler's local D1 executor) |
| workerd | ?? (compiled-in) | `@cloudflare/workerd-darwin-arm64` | wrangler dev subprocess (actual D1 runtime) |

**macOS 3.51.0 and workerd's SQLite have incompatible on-disk formats.** Writing a database with `sqlite3 .read` (3.51.0) then trying to open it with workerd causes segfault.

better-sqlite3 (3.53.1) produces databases that workerd can read — likely because both are more recent and share the same file format version.

## Diagnostic Chain

### 1. Check which SQLite actually holds the file handle
The `SQLITE_BUSY` error is often caused by a surviving `workerd` subprocess, not just stale lock files:

```bash
# Find the actual holder — usually workerd, not wrangler.js
lsof -nP -iTCP:8787 -sTCP:LISTEN

# Kill the chain properly (BOTH are needed):
pkill -9 -f 'wrangler'   # kills parent node process
pkill -9 -f 'workerd'    # kills child workerd (THE ACTUAL HOLDER)
```

### 2. Check SQLite version that wrote the database
```bash
# If the DB was created by system sqlite3:
sqlite3 .wrangler/state/v3/d1/miniflare-D1DatabaseObject/*.sqlite \
  "SELECT sqlite_version();"
# → 3.51.0 — this WILL segfault workerd

# If the DB was created by better-sqlite3:
node -e "const Database=require('better-sqlite3'); \
  new Database(':memory:').pragma('sqlite_version')"
# → 3.53.1 — this is SAFE
```

### 3. Check database file integrity
```bash
sqlite3 <DB_FILE> "PRAGMA integrity_check;"
# If this returns 'ok' but wrangler segfaults → version mismatch
```

## Resolution

**Never use macOS system sqlite3 to write local D1 databases.** Always use one of:

1. `wrangler d1 execute --local` (uses miniflare → better-sqlite3 → 3.53.1) — safe but limited (SQLITE_TOOBIG for large statements)
2. `scripts/import-db.cjs` (uses better-sqlite3 directly → 3.53.1) — safe for large imports
3. Just `wrangler d1 export --remote --no-data` for schema-only — safest, fastest

## Circular FK Workaround

The schema has `users.primary_saju_id REFERENCES history(id)` AND `history.user_id REFERENCES users(id)`. This circular reference requires `PRAGMA foreign_keys=OFF` during bulk import. The data is internally consistent (all FK references are valid), so re-enabling after import is safe.

## References

- better-sqlite3 source: `node_modules/better-sqlite3/deps/sqlite3/sqlite3.c` — look for `SQLITE_VERSION`
- workerd version: `node_modules/@cloudflare/workerd-darwin-arm64/bin/workerd --version`
- Wrangler D1 export: `wrangler d1 export --help`
