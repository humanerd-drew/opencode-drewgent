# Huly Real-Time Events via `pushHandler`

Discovered 2026-06-14 during Huly API exploration.

## Background

Huly Cloud has no webhook support. All data is transferred via a persistent WebSocket connection. The `@hcengineering/api-client` `connect()` function opens this WebSocket and exposes a `pushHandler` method on the underlying raw `Connection` object.

## Access Path (IMPORTANT)

The raw WebSocket `Connection` is nested FOUR levels deep from the high-level client:

```js
const client = await connect(BASE, { token, workspace, WebSocketFactory });

// The raw Connection is at:
client.client.client.conn.pushHandler(callback)
// ^^^ PlatformClientImpl → TxOperations → createClient result → Connection

// client.connection.pushHandler DOES NOT WORK — `connection` is a wrapper
```

### Why this nesting

```
PlatformClientImpl  (returned by connect())
  └── client        (TxOperations instance)
       └── client   (createClient() result from @hcengineering/core)
            └── conn  (raw Connection from client-resources/connection.js)
```

## Mechanism

```js
const client = await connect(BASE, { token, workspace, WebSocketFactory });

// Access the raw Connection (4 levels deep)
const conn = client.client.client.conn;

// Register a handler for ALL server transactions — real-time!
conn.pushHandler((...txArr) => {
  // txArr is an array of Transaction objects
  for (const tx of txArr) {
    // Transaction types (from core:class:Tx hierarchy):
    // - TxCreateDoc  — document created
    // - TxUpdateDoc  — document updated  
    // - TxRemoveDoc  — document removed
    // - TxMixin      — mixin applied
    
    if (tx._class?.endsWith('TxCreateDoc') && tx.objectClass === 'tracker:class:Issue') {
      // New issue created! tx.attributes.title, tx.attributes.description, tx.objectId
    }
    if (tx._class?.endsWith('TxUpdateDoc') && tx.objectClass === 'tracker:class:Issue') {
      // Issue updated — tx.operations contains changed fields
    }
  }
});
```

## Handler Invocation Point

From `client-resources/lib/connection.js` line ~407:

```js
this.handlers.forEach((handler) => {
  handler(...txArr);
});
```

Called whenever the server pushes transactions — typically immediately after any write operation (create, update, delete) on any document across the ENTIRE workspace.

## Architecture: Bridge Daemon

Deployed as `ai.drewgent.huly-bridge` (launchd daemon):

```
Huly Server ──WebSocket──→ client.client.client.conn
                               │ pushHandler
                               ▼
                          huly_bridge.js (running at PID)
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
              Issue         Issue     Status
              Created       Updated   Changed
                    │          │          │
                    ▼          ▼          ▼
              kanban      (logs)    (logs / future
              create                    notify)
```

## Scripts

| File | Purpose |
|------|---------|
| `~/.drewgent/scripts/huly_bridge.js` | Bridge daemon — connects, registers pushHandler, processes events |
| `~/.drewgent/scripts/huly_bridge.sh` | Bash wrapper (reads key, launches node) |
| `~/.drewgent/logs/huly-bridge.log` | Daemon stdout/stderr |

## launchd plist

Installed at `~/Library/LaunchAgents/ai.drewgent.huly-bridge.plist`:

- Label: `ai.drewgent.huly-bridge`
- Uses `KeepAlive` with `SuccessfulExit: false` for auto-restart on crash
- `ThrottleInterval: 10` seconds between restarts
- `RunAtLoad: true`

## Caveats

- The `pushHandler` registration must happen AFTER `connect()` resolves.
- The connection must remain open — this is a long-running daemon pattern, not a cron job.
- Use launchd plist for daemon lifecycle management (not `terminal(background=true)`).
- Filter by `tx.objectClass` heavily — you'll receive transactions for ALL document types.
- `tx.objectId` and `tx.attributes` (for create) or `tx.operations` (for update) contain the relevant data.
- Auto-reconnect with exponential backoff (1s → 60s max) is built into the daemon.
