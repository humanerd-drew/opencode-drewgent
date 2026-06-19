#!/usr/bin/env node
/**
 * huly_sync.js - Sync Hermes kanban completions to Huly Cloud.
 *
 * Reads recently completed tasks from Hermes native kanban DB and creates
 * Huly issues in the tracker project.
 *
 * Usage: HULY_KEY=<token> node scripts/huly_sync.js
 *
 * Cron: every 120m, no_agent
 */

if (typeof globalThis.window === 'undefined') {
  globalThis.window = { addEventListener: () => {} };
}

const { connect, NodeWebSocketFactory } = require('@hcengineering/api-client');
const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const BASE = 'https://huly.app';
const WS = 'humanerd';
const PROJECT = 'tracker:project:DefaultProject';

function getToken() {
  const fromEnv = process.env.HULY_KEY;
  if (fromEnv) return fromEnv;
  const tf = '/tmp/huly_api_key.txt';
  if (fs.existsSync(tf)) return fs.readFileSync(tf, 'utf8').trim();
  return null;
}

/** Get kanban tasks completed in last N hours. */
function getRecentKanbanTasks(hours = 4) {
  const home = process.env.HOME || '/Users/drew';
  const dbPath = path.join(home, '.drewgent', 'kanban.db');
  if (!fs.existsSync(dbPath)) return [];
  const cutoff = Math.floor(Date.now() / 1000) - hours * 3600;
  try {
    const out = execSync(
      `sqlite3 "${dbPath}" "SELECT id, title, summary FROM tasks WHERE status='done' AND completed_at > ${cutoff} ORDER BY completed_at DESC LIMIT 10;"`,
      { encoding: 'utf8', timeout: 5000 }
    );
    return out.trim().split('\n').filter(Boolean).map(line => {
      const [id, title, summary] = line.split('|');
      return { id, title: title || 'untitled', summary: summary || '' };
    });
  } catch {
    return [];
  }
}

async function main() {
  const token = getToken();
  if (!token) { console.error('HULY_KEY not set'); process.exit(1); }

  // Connect
  const client = await connect(BASE, {
    token, workspace: WS,
    WebSocketFactory: NodeWebSocketFactory,
  });

  // Get recent completed kanban tasks
  const tasks = getRecentKanbanTasks(4);
  console.log(`Kanban tasks done in 4h: ${tasks.length}`);

  if (tasks.length === 0) {
    await client.close();
    return;
  }

  // Get existing issues to avoid duplicates
  const existing = await client.findAll('tracker:class:Issue', {});
  const existingTitles = new Set(existing.map(i => i.title));

  let synced = 0;
  for (const task of tasks) {
    const title = `[Kanban] ${task.title}`;
    if (existingTitles.has(title)) {
      console.log(`  SKIP (duplicate): ${task.title}`);
      continue;
    }
    try {
      await client.addCollection(
        'tracker:class:Issue',
        PROJECT,
        PROJECT,
        'core:class:Space',
        'issues',
        {
          title,
          description: `Kanban task: ${task.id}\n\n${task.summary || 'Completed via Hermes kanban'}\n\n---\nAuto-synced from Drewgent kanban.`,
        }
      );
      console.log(`  ✓ ${task.title}`);
      synced++;
    } catch (e) {
      console.error(`  ✗ ${task.title}: ${e.message.slice(0, 100)}`);
    }
  }

  console.log(`Synced ${synced}/${tasks.length} to Huly`);
  await client.close();
}

main().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
