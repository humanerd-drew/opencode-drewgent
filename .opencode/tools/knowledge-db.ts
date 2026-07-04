import { Database } from "bun:sqlite";
import { mkdirSync } from "fs";
import { join } from "path";

const DB_PATH = join(process.env.HOME || "/tmp", ".drewgent", ".opencode", "knowledge.db");

let _db: Database | null = null;

export function getDb(): Database {
  if (_db) return _db;
  mkdirSync(join(DB_PATH, ".."), { recursive: true });
  _db = new Database(DB_PATH);
  _db.run("PRAGMA journal_mode=WAL");
  initSchema(_db);
  return _db;
}

function initSchema(db: Database) {
  db.run(`
    CREATE TABLE IF NOT EXISTS knowledge (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      type TEXT NOT NULL DEFAULT 'fact',
      content TEXT NOT NULL,
      source TEXT,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
  `);
  db.run("CREATE INDEX IF NOT EXISTS idx_knowledge_type ON knowledge(type)");
  db.run("CREATE INDEX IF NOT EXISTS idx_knowledge_created ON knowledge(created_at DESC)");

  // FTS5 virtual table for full-text search
  db.run(`
    CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
      content, type,
      content=knowledge,
      content_rowid=id
    )
  `);

  // Sessions table
  db.run(`
    CREATE TABLE IF NOT EXISTS sessions (
      id TEXT PRIMARY KEY,
      title TEXT,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      message_count INTEGER DEFAULT 0
    )
  `);

  // Triggers to keep FTS in sync
  db.run(`
    CREATE TRIGGER IF NOT EXISTS knowledge_ai AFTER INSERT ON knowledge BEGIN
      INSERT INTO knowledge_fts(rowid, content, type) VALUES (new.id, new.content, new.type);
    END;
  `);
  db.run(`
    CREATE TRIGGER IF NOT EXISTS knowledge_ad AFTER DELETE ON knowledge BEGIN
      INSERT INTO knowledge_fts(knowledge_fts, rowid, content, type)
      VALUES('delete', old.id, old.content, old.type);
    END;
  `);
  db.run(`
    CREATE TRIGGER IF NOT EXISTS knowledge_au AFTER UPDATE ON knowledge BEGIN
      INSERT INTO knowledge_fts(knowledge_fts, rowid, content, type)
      VALUES('delete', old.id, old.content, old.type);
      INSERT INTO knowledge_fts(rowid, content, type) VALUES (new.id, new.content, new.type);
    END;
  `);

  // Migrate legacy JSON data if exists
  migrateLegacyJson(db);
}

function migrateLegacyJson(db: Database) {
  const count = db.query("SELECT COUNT(*) as c FROM knowledge").get() as any;
  if (count?.c > 0) return; // already has data

  try {
    const jsonPath = join(join(DB_PATH, ".."), "knowledge.json");
    const fs = require("fs");
    if (fs.existsSync(jsonPath)) {
      const data = JSON.parse(fs.readFileSync(jsonPath, "utf-8"));
      if (data.facts?.length > 0) {
        const insert = db.prepare(
          "INSERT INTO knowledge (type, content, source, created_at) VALUES (?, ?, ?, ?)"
        );
        for (const f of data.facts) {
          insert.run(f.type || "fact", f.content, f.source || null, f.created_at || new Date().toISOString());
        }
        console.log(`Migrated ${data.facts.length} facts from knowledge.json`);
        fs.renameSync(jsonPath, jsonPath + ".bak");
      }
    }
  } catch {}
}

export function addKnowledge(type: string, content: string, source?: string): number {
  const db = getDb();
  const result = db.run(
    "INSERT INTO knowledge (type, content, source) VALUES (?, ?, ?)",
    type, content, source || null
  );
  return Number(result.lastInsertRowid);
}

export function searchKnowledge(query: string, limit: number = 10): any[] {
  if (!query.trim()) return [];
  const db = getDb();
  const safe = query.replace(/['"]/g, "").replace(/\s+/g, " OR ");
  const rows = db.query(`
    SELECT k.id, k.type, k.content, k.source, k.created_at
    FROM knowledge_fts fts
    JOIN knowledge k ON fts.rowid = k.id
    WHERE knowledge_fts MATCH ?
    ORDER BY rank
    LIMIT ?
  `).all(safe, limit);
  return rows;
}

export function countKnowledge(): { total: number; by_type: Record<string, number> } {
  const db = getDb();
  const total = (db.query("SELECT COUNT(*) as c FROM knowledge").get() as any)?.c || 0;
  const rows = db.query("SELECT type, COUNT(*) as c FROM knowledge GROUP BY type").all() as any[];
  const by_type: Record<string, number> = {};
  for (const r of rows) by_type[r.type] = r.c;
  return { total, by_type };
}

export function recentKnowledge(limit: number = 20): any[] {
  const db = getDb();
  return db.query(
    "SELECT * FROM knowledge ORDER BY created_at DESC LIMIT ?"
  ).all(limit);
}
