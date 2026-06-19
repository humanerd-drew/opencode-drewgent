#!/usr/bin/env node
/**
 * huly_check.js - Poll Huly for recent changes, output to stdout.
 * Used as a no_agent cron script with deliver=discord:channel.
 *
 * Suppresses Huly client model-load noise so only meaningful output
 * reaches the cron delivery channel.
 */
// Quiet the Huly client's noisy model-load console.log/debug calls
const _log = console.log;
const _debug = console.debug;
console.log = () => {};
console.debug = () => {};
process.once('beforeExit', () => { console.log = _log; console.debug = _debug; });

globalThis.window = { addEventListener: () => {} };
const { connect, NodeWebSocketFactory } = require('@hcengineering/api-client');
const fs = require('fs');
const path = require('path');

const envPath = path.join(require('os').homedir(), '.hermes', '.env');
const TOKEN = fs.readFileSync(envPath, 'utf8').split('\n')
  .find(l => l.startsWith('HULY_KEY='))
  ?.split('=').slice(1).join('=') || '';

if (!TOKEN) { process.exit(0); }

const STATE_FILE = path.join(require('os').homedir(), '.drewgent', 'state', 'huly_last_check.json');

async function main() {
  const client = await connect('https://huly.app', {
    token: TOKEN, workspace: 'humanerd',
    WebSocketFactory: NodeWebSocketFactory,
  });

  let lastCheck = 0;
  try { lastCheck = JSON.parse(fs.readFileSync(STATE_FILE, 'utf8')).lastCheck || 0; } catch(e) {}
  const now = Date.now();

  const issues = await client.findAll('tracker:class:Issue', {});
  const recent = issues.filter(i => {
    const created = new Date(i.createdOn || 0).getTime();
    const modified = new Date(i.modifiedOn || 0).getTime();
    return created > lastCheck || modified > lastCheck;
  });

  if (recent.length === 0) {
    fs.writeFileSync(STATE_FILE, JSON.stringify({ lastCheck: now }));
    await client.close();
    return;
  }

  const lines = ['**Huly Updates**'];
  for (const issue of recent) {
    const title = issue.title || '(untitled)';
    const status = (issue.status || 'open').split(':').pop() || 'open';
    lines.push(`:small_blue_diamond: **${title}** [${status}]`);
  }
  console.log(lines.join('\n'));

  fs.writeFileSync(STATE_FILE, JSON.stringify({ lastCheck: now }));
  await client.close();
}

main().catch(e => {
  console.error('Huly check error:', e.message);
  process.exit(0);
});
