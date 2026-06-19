#!/usr/bin/env node
/**
 * huly_bridge.js — Huly Bridge Daemon
 *
 * Connects to Huly Cloud via WebSocket, listens for real-time transactions
 * via pushHandler, and bridges them to Hermes kanban and Discord.
 *
 * Features:
 * - New Huly Issue → kanban_create (dispatcher spawns worker)
 * - Issue status change → Discord notification (real-time)
 * - Auto-reconnect on disconnect
 * - Kanban complete → Huly issue update (via huly_sync cron)
 *
 * Usage: HULY_KEY=... node huly_bridge.js
 */

// Suppress model-load noise
const _log = console.log; const _dbg = console.debug;
console.log = () => {}; console.debug = () => {}; console.warn = () => {};
process.once('beforeExit', () => { console.log = _log; console.debug = _dbg; });

globalThis.window = { addEventListener: () => {} };
const { connect, NodeWebSocketFactory } = require('@hcengineering/api-client');
const { execSync } = require('child_process');
const path = require('path');

const ENV_NAME = 'HULY_KEY';
const TOKEN=process.env.HULY_KEY || "";
process.on("SIGINT", () => { console.log("\nShutting down..."); process.exit(0); });
process.on("SIGTERM", () => { process.exit(0); });

// ── Event queue ──────────────────────────────────────────────
// Process events with a small delay to batch rapid changes
const eventQueue = [];
let processing = false;

function queueEvent(type, data) {
  eventQueue.push({ type, data, ts: Date.now() });
  if (!processing) processQueue();
}

async function processQueue() {
  processing = true;
  while (eventQueue.length > 0) {
    const evt = eventQueue.shift();
    try {
      await handleEvent(evt);
    } catch (e) {
      console.error('Event error:', e.message);
    }
  }
  processing = false;
}

// ── Event handlers ───────────────────────────────────────────

async function handleEvent(evt) {
  const { type, data } = evt;

  if (type === 'issue:created') {
    process.stdout.write(`New Huly issue: "${data.title}"`);
    // Create Hermes kanban task
    try {
      const result = execSync(
        `hermes kanban create --title "${data.title.replace(/"/g, '\\"')}" --assignee default --body "${(data.description || '').replace(/"/g, '\\"').slice(0, 200)}"`,
        { encoding: 'utf8', timeout: 10000 }
      );
      process.stdout.write(`  → kanban task created: ${result.trim()}`);
    } catch (e) {
      console.error(`  → kanban create failed: ${e.message.slice(0, 100)}`);
    }

  } else if (type === 'issue:updated') {
    process.stdout.write(`Issue updated: "${data.title}" → status: ${data.status}`);
    // Status change notification will be handled by huly-check-discord cron
  }
}

// ── Main daemon ──────────────────────────────────────────────

async function main() {
  let reconnectDelay = 1000;

  while (true) {
    try {
      process.stdout.write('Connecting to Huly...\n');
      const client = await connect('https://huly.app', {
        token: TOKEN,
        workspace: 'humanerd',
        WebSocketFactory: NodeWebSocketFactory,
      });
      process.stdout.write('Connected. Listening for transactions...\n');
      reconnectDelay = 1000; // Reset on successful connect

      // Register real-time handler on the underlying WebSocket connection
      client.client.client.conn.pushHandler((...txArr) => {
        for (const tx of txArr) {
          try {
            const txClass = tx._class || '';
            const objClass = tx.objectClass || '';

            // New issue created
            if (txClass.endsWith('TxCreateDoc') && objClass === 'tracker:class:Issue') {
              queueEvent('issue:created', {
                id: tx.objectId,
                title: tx.attributes?.title || '(untitled)',
                description: tx.attributes?.description || '',
              });
            }

            // Issue updated (status change, etc.)
            if (txClass.endsWith('TxUpdateDoc') && objClass === 'tracker:class:Issue') {
              const ops = tx.operations || {};
              if (ops.status || ops.title) {
                queueEvent('issue:updated', {
                  id: tx.objectId,
                  title: ops.title || '(updated)',
                  status: ops.status ? (ops.status + '').split(':').pop() : '?',
                });
              }
            }
          } catch (e) {
            // Skip malformed transactions silently
          }
        }
      });

      // Keep alive — ping/pong is handled by the connection internally
      // Wait until the connection dies
      await new Promise((resolve) => {
        const checkInterval = setInterval(() => {
          if (!client.client.client.conn.isConnected()) {
            clearInterval(checkInterval);
            resolve();
          }
        }, 5000);
      });

    } catch (e) {
      console.error('Connection error:', e.message);
    }

    // Reconnect with exponential backoff
    console.log(`Reconnecting in ${reconnectDelay / 1000}s...`);
    await new Promise(r => setTimeout(r, reconnectDelay));
    reconnectDelay = Math.min(reconnectDelay * 2, 60000); // Cap at 1 min
  }
}

main().catch(e => {
  console.error('Fatal:', e.message);
  process.exit(1);
});
