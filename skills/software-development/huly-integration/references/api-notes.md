# Huly API Client — Reverse-Engineering Notes

Session: 2026-06-14 kanban-linear-huly
Target: Huly Cloud (huly.app), workspace `humanerd`

## Connection Flow

1. `connect()` from `@hcengineering/api-client` opens a WebSocket to Huly Cloud
2. Accepts `token` (JWT), `workspace` (slug), `WebSocketFactory` params
3. On success, returns a `Client` object with full CRUD capabilities
4. The server version was `0.7.423` at time of testing

### Authentication

JWT token payload:
```json
{
  "extra": {},
  "account": "<uuid>",
  "workspace": "<uuid>"
}
```

Huly Cloud URL: `https://huly.app`
Workspace URL pattern: `https://huly.app/workbench/{slug}/`

### Configuration Discovery

The app config at `https://huly.app/config.json` revealed microservice URLs:
- `ACCOUNTS_URL`: `https://account.huly.app/`
- `COLLABORATOR_URL`: `wss://collaborator-eu.huly.app`
- `PULSE_URL`: `wss://pulse.huly.app/ws`
- File storage: `https://dl-eu.huly.app/`

## Data Model (Partial)

Discovered through `client.getHierarchy().findClass()`:

| Class | Domain | Extends |
|-------|--------|---------|
| `tracker:class:Issue` | undefined | `task:class:Task` |
| `task:class:Task` | `task` | `core:class:AttachedDoc` |
| `core:class:AttachedDoc` | undefined | `core:class:Doc` |
| `core:class:Space` | `space` | `core:class:Doc` |

## Space Inventory (typical workspace)

27 spaces found. Key ones:
- `tracker:project:DefaultProject` — where issues live
- `board:space:DefaultBoard` — Kanban board (not for direct issue creation)
- `chunter:space:General`, `chunter:space:Random` — chat channels
- Various system spaces (model, tx, configuration)

## Issue Structure

Key fields from a sample issue:
```json
{
  "title": "Write backstory for main character",
  "description": "...",
  "identifier": "GAME-1",
  "number": 1,
  "status": "tracker:status:Backlog",
  "assignee": "6a2d4e83...",
  "space": "6a2d4e8b...",
  "attachedTo": "tracker:ids:NoParent",
  "attachedToClass": "tracker:class:Issue",
  "collection": "subIssues",
  "priority": 3,
  "kind": "task"
}
```

## Window Polyfill Issue

The `client-resources` package's `Connection` constructor (line 88 in `connection.js`) unconditionally calls `window.addEventListener("beforeunload", ...)`. This is a Huly library bug for Node.js environments. The polyfill is required.

The `NodeWebSocketFactory` is exported from `@hcengineering/api-client` but doesn't fix the `window` dependency — that's in a different part of the same module.
