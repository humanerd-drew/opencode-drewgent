/**
 * import-db.cjs — Import production D1 export into local D1 database
 *
 * Uses better-sqlite3 (SQLite 3.53.1) to create a database file that
 * workerd can read without segfault. macOS system sqlite3 (3.51.0)
 * creates incompatible binary format files.
 *
 * Usage:
 *   1. wrangler d1 export <DB_NAME> --remote --output=./db-export.sql
 *   2. rm -rf .wrangler/state/v3
 *   3. wrangler d1 execute <DB_NAME> --local --command="SELECT 1;"
 *   4. node scripts/import-db.cjs
 *   5. npm run dev
 *
 * Requirements:
 *   - better-sqlite3 installed (npm install better-sqlite3)
 *   - db-export.sql in the project root
 *   - .wrangler/state/v3/d1/miniflare-D1DatabaseObject/ exists
 */

const Database = require('better-sqlite3');
const fs = require('fs');
const path = require('path');

const DB_DIR = '.wrangler/state/v3/d1/miniflare-D1DatabaseObject';

// Find D1 database file (not metadata*)
if (!fs.existsSync(DB_DIR)) {
  console.error('D1 database directory not found:', DB_DIR);
  console.error('Run first: wrangler d1 execute <DB_NAME> --local --command="SELECT 1;"');
  process.exit(1);
}

const files = fs.readdirSync(DB_DIR);
const dbFile = files.find(f => f.endsWith('.sqlite') && !f.includes('metadata'));
if (!dbFile) {
  console.error('No D1 database file found in', DB_DIR);
  console.error('Run first: wrangler d1 execute <DB_NAME> --local --command="SELECT 1;"');
  process.exit(1);
}

const dbPath = path.join(DB_DIR, dbFile);
console.log('Target DB:', dbPath);

// Delete the empty database created by wrangler, recreate from export
fs.unlinkSync(dbPath);
console.log('Deleted empty DB, recreating from export...');

const sqlPath = path.resolve(process.cwd(), 'db-export.sql');
if (!fs.existsSync(sqlPath)) {
  console.error('db-export.sql not found in', process.cwd());
  console.error('Run first: wrangler d1 export <DB_NAME> --remote --output=./db-export.sql');
  process.exit(1);
}

const sql = fs.readFileSync(sqlPath, 'utf-8');
console.log('SQL export size:', (sql.length / 1024 / 1024).toFixed(1), 'MB');

const db = new Database(dbPath);
db.pragma('journal_mode = WAL');
db.pragma('synchronous = NORMAL');
db.pragma('foreign_keys = OFF');  // Required: circular FK (users <-> history)

console.log('Importing...');
db.exec(sql);
console.log('Import complete.');

// Verify
const tables = db.prepare("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").all();
console.log('Tables:', tables.length);
tables.forEach(t => {
  const row = db.prepare(`SELECT COUNT(*) as cnt FROM "${t.name}"`).get();
  if (row.cnt > 0) console.log(`  ${t.name}: ${row.cnt}`);
});

const size = fs.statSync(dbPath).size;
console.log('DB size:', (size / 1024 / 1024).toFixed(1), 'MB');

db.close();
