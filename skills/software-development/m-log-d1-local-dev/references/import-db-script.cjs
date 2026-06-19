/**
 * Import production D1 export into local D1 database using better-sqlite3.
 *
 * Place at: scripts/import-db.cjs in the m-log-v2 project root.
 *
 * Why better-sqlite3 (not system sqlite3):
 *   - workerd bundles SQLite 3.53.1
 *   - macOS system sqlite3 is 3.51.0
 *   - version mismatch causes Segfault #11 when workerd opens the DB
 *   - better-sqlite3 bundles SQLite 3.53.1, matching workerd
 *
 * Why this works (when wrangler d1 execute --local --file= fails):
 *   - 121MB SQL file → wrangler execute times out at 300s
 *   - history rows are ~170KB each → SQLITE_TOOBIG
 *   - users ↔ history circular FK
 *   - single-transaction .read handles all three
 *
 * Usage:
 *   1. rm -rf .wrangler/state/v3
 *   2. node node_modules/wrangler/bin/wrangler.js d1 execute m_log_db --local --command="SELECT 1;"
 *   3. node scripts/import-db.cjs
 *   4. npm run dev
 */

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
console.log('Target DB:', dbPath);

// Verify version before writing
const probe = new Database(dbPath);
console.log('SQLite version:', probe.prepare('SELECT sqlite_version() as ver').get().ver);
probe.close();

// Delete the empty stub wrangler created
fs.unlinkSync(dbPath);
console.log('Deleted empty DB, recreating from export...');

const sql = fs.readFileSync('./db-export.sql', 'utf-8');
console.log('SQL export size:', (sql.length / 1024 / 1024).toFixed(1), 'MB');

const newDb = new Database(dbPath);
newDb.pragma('journal_mode = WAL');
newDb.pragma('synchronous = NORMAL');
newDb.pragma('foreign_keys = OFF');  // ignore users↔history circular FK during import

console.log('Importing...');
newDb.exec(sql);  // single transaction — handles 170KB rows without TOOBIG
console.log('Import complete.');

// Verify
const tables = newDb.prepare("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").all();
const counts = tables.map(t => {
  const row = newDb.prepare(`SELECT COUNT(*) as cnt FROM "${t.name}"`).get();
  return `${t.name}: ${row.cnt}`;
});
console.log('Tables (' + tables.length + '):');
counts.forEach(c => console.log('  ' + c));

console.log('DB size:', (fs.statSync(dbPath).size / 1024 / 1024).toFixed(1), 'MB');
newDb.close();
