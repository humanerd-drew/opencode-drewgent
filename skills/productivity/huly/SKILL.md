---
name: huly
description: "Huly Cloud (huly.app) — All-in-One Project Management. Covers PM, Chat, Docs, HR, CRM, Storage. Agent's primary work hub replacing Linear + kanban."
version: 1.1.0
author: Drewgent
created: 2026-06-14
updated: 2026-06-14
  session: "2026-06-14 kanban-huly-integration"
  decision: "Huly Cloud free tier over self-host. Node.js API client over REST (WebSocket protocol)."
prerequisites:
  env_vars: [HULY_KEY]
  commands: [node, npm]
links:
  - "[[@action/skills/SKILL-INDEX]]"
  - "[[@action/integrations/huly]]"
references:
  - "references/selfhost-on-synology.md"
  - "references/pushhandler-realtime.md"
---

# Huly — Agent Usage Guide

Huly Cloud (https://huly.app) | Workspace: `humanerd`

## Core Philosophy

Huly replaces **Linear + Notion + Slack + Google Drive** in one platform. As the agent, use Huly for ALL of the following:

| Replace | With Huly |
|---------|-----------|
| Linear | Tracker (Issues, Projects) |
| Notion | Documents (Wiki, Docs) |
| Slack | Chunter (Channels, Chat) |
| Google Drive | Drive (File storage) |
| CRM | Lead/Funnel |
| HR | Contacts/Employees |

---

## PART 1: Task Management (Tracker)

### When to create Huly Issues
- User says "태스크 만들어줘 / 작업 등록해줘"
- You identify a new piece of work during conversation
- A kanban task completes → auto-synced (huly-kanban-sync cron)

### Issue Creation (Preferred: MCP Tools)

Huly tools are available natively via Hermes `mcp_servers.huly`. Use tool calls directly:

| Action | Tool | Key params |
|--------|------|------------|
| List projects | `huly:list_projects` | `{include_details: true}` |
| List issues | `huly:list_issues` | `{project: "PROJ"}` |
| Create issue | `huly:create_issue` | `{project: "TST", title: "...", description: "...", priority: "medium"}` |
| Get issue | `huly:get_issue` | `{issueId: "TST-42"}` |
| Update issue | `huly:update_issue` | `{issueId: "TST-42", status: "In Progress"}` |
| Search issues | `huly:search_issues` | `{query: "..."}` |
| Add comment | `huly:add_comment` | `{issueId: "TST-42", text: "..."}` |
| Log time | `huly:log_time` | `{issueId: "TST-42", hours: 2}` |
| Create from template | `huly:create_issues_from_template` | `{project: "PROJ", template: "feature", title: "..."}` |

### Issue Creation (Fallback: CLI via terminal)

When MCP tools are unavailable (e.g., cron scripts), use the direct SDK:

```bash
cd ~/.drewgent && node -e "
const{connect,NodeWebSocketFactory}=require('@hcengineering/api-client');
globalThis.window={addEventListener:()=>{}};
const c=await connect('https://huly.app',{
  token:process.env.HULY_KEY,workspace:'humanerd',
  WebSocketFactory:NodeWebSocketFactory,
});
await c.addCollection('tracker:class:Issue',
  'tracker:project:DefaultProject',
  'tracker:project:DefaultProject',
  'core:class:Space','issues',
  {title:'TITLE',description:'DESC'});
await c.close();
"
```

### List Issues

```bash
cd ~/.drewgent && node -e "
const{connect,NodeWebSocketFactory}=require('@hcengineering/api-client');
globalThis.window={addEventListener:()=>{}};
(async()=>{
  const c=await connect('https://huly.app',{
    token:process.env.HULY_KEY,workspace:'humanerd',
    WebSocketFactory:NodeWebSocketFactory,
  });
  const issues=await c.findAll('tracker:class:Issue',{});
  for(const i of issues) console.log(i.title,'|',(i.status||'').split(':').pop());
  await c.close();
})()
"
```

### Key Classes
- `tracker:class:Issue` — 개별 이슈 (AttachedDoc, collection: "issues")
- `tracker:project:DefaultProject` — 기본 프로젝트 space
- `core:class:Space` — 모든 공간의 부모 클래스
- 이슈 생성은 `addCollection()` 필수 (createDoc 불가)

### Issue Fields
`title`, `description`, `status`, `assignee`, `priority`, `space`

---

## PART 2: Documents (Knowledge Base)

### When to create Docs
- You discover/configure something non-trivial
- User explains a workflow or preference
- A pattern repeats → document it
- A decision is made → capture rationale

### Document Spaces
- `document:spaceType:DocumentSpaceType` (Quality documents, Unsorted templates)

### Create Document (via API)
```js
// Documents use their own class hierarchy
// Check available document classes first:
const h = client.getHierarchy();
// Try: document:class:Document, document:class:Page
```

---

## PART 3: Channels (Chat)

### Available Channels
| ID | Name | Purpose |
|----|------|---------|
| `chunter:space:General` | general | General discussion |
| `chunter:space:Random` | random | Off-topic |

### Send Message to Channel
```js
// Use addCollection on chunter:class:Message
// attachedTo: channel ID, collection: "messages"
```

---

## PART 4: Storage (Drive)

### Available Drives
- `love:space:Drive` — Records
- `recorder:space:Drive` — Screen Recordings

---

## PART 5: Workspace Setup Checklist

### Current State (mostly empty)
- Projects: DefaultProject (Welcome to Huly! with 6 onboarding issues)
- Channels: general, random
- Documents: empty
- CRM/Leads: empty
- Employees: 1 (you)

### Suggested Projects to Create
When user approves, create via UI or API:

| Project | Purpose |
|---------|---------|
| `Drewgent Core` | Agent infrastructure, kanban, cron |
| `Content Pipeline` | Trend harvesting, SEO, writing |
| `M-LOG` | M-LOG development |
| `Humanerd Site` | Website/Quartz |

### Suggested Channels
| Channel | Purpose |
|---------|---------|
| `#dev` | Development discussion |
| `#alerts` | System notifications |
| `#content` | Content workflow |

---

## PART 6: Agent Workflow Rules

### Rule 1: Task First
When user assigns work → create Huly Issue FIRST, then start working. Reference the issue ID in responses.

### Rule 2: Document What You Learn
After configuring something new → create a Huly Document. Knowledge should live in Huly, not just in conversation history.

### Rule 3: Report via Huly
Status updates → reference Huly Issues. Use `huly-check-discord` for broadcasting to Discord.

### Rule 4: Kanban + Huly Coexistence
- `kanban_create` still works for Hermes-native tasks
- `huly-kanban-sync` cron auto-syncs completed kanban tasks to Huly Issues
- For new work: prefer creating directly in Huly via the API

---

## Technical Reference

For detailed API reference, CRUD operations, connection patterns, and
pitfalls, see the **huly-integration** skill (software-development).
This section covers the Drewgent-specific deployment.

### Self-Hosted Deployment (Synology NAS)

**For the full field playbook (envsubst pitfall, huly_v7.conf write pattern, cockroach v24.2 quirk, kvs-1 fix), see `references/selfhost-on-synology.md`.** This section only summarizes current state.

Current state (last update 2026-06-16):
- 14/14 containers running at `http://192.168.1.53:8087`
- `kvs-1` restart-loops because huly user in cockroach never got created (the catch-22 step in the reference)
- PICKUP for next session: create the huly user in cockroach (see reference), restart kvs/account/transactor
- Standard `setup.sh` is broken on Synology (envsubst missing) — write huly_v7.conf by hand using the recipe in the reference

### Two-Layer Architecture

| Layer | Method | Transport | Used For |
|-------|--------|-----------|----------|
| **MCP Tools** | Hermes native MCP (`mcp_servers.huly`) | stdio → WebSocket | All agent-to-Huly interaction (issue CRUD, search, comments, milestones, projects) |
| **Direct SDK** | `@hcengineering/api-client` (Node.js) | WebSocket | Headless cron scripts, real-time bridge daemon, pushHandler |

**MCP setup:** `@bgx4k3p/huly-mcp-server` via wrapper at `~/.drewgent/scripts/huly-mcp-wrapper.sh`.
The wrapper reads the JWT from `.env` at runtime — never stored in config.yaml.

**MCP verification:** After configuring, confirm the server is actually loaded by searching for `huly:*` tools via `tool_search(query="huly")` at the start of a session. If tools don't appear, the most likely cause is the `mcp_servers:` parent key being commented out in `~/.hermes/config.yaml`. Run `grep '^mcp_servers:' ~/.hermes/config.yaml` — if empty, the key is missing or commented. In YAML, `# mcp_servers:` at the parent level disables ALL children, even if individual server entries like `huly:` are uncommented. Fix: uncomment the `mcp_servers:` line and indent servers correctly under it.

### Architecture
- **Protocol**: WebSocket (not REST)
- **API Client**: `@hcengineering/api-client` (npm public) — legacy direct SDK
- **MCP Server**: `@bgx4k3p/huly-mcp-server` (npm public) — preferred
- **Auth**: JWT token from Settings → Integrations → API Access
- **Node polyfill**: `globalThis.window = { addEventListener: () => {} }` — only for direct SDK
- **WebSocket factory**: `NodeWebSocketFactory`

### Cron Script Rules
- `.sh`/`.bash` → run with bash
- All other extensions → run with **Python** `sys.executable`
- Node.js scripts MUST use `.sh` wrapper:
```bash
#!/bin/bash
HULY_KEY="$(grep '^HULY_KEY=' "$HOME/.hermes/.env" | head -1 | cut -d= -f2-)"
export HULY_KEY
exec 2>/dev/null
exec node --no-warnings script.js
```

### Current Cron Jobs
| Name | Schedule | Script | Function |
|------|----------|--------|----------|
| `huly-kanban-sync` | 120m | `huly_sync.sh` | Kanban done → Huly issue |
| `huly-check-discord` | 30m | `huly_check.sh` | Huly changes → Discord #agent-chat |

### Bridge Daemon (Real-Time)

| Name | Type | Script | Function |
|------|------|--------|----------|
| `ai.drewgent.huly-bridge` | launchd daemon | `huly_bridge.sh` | Real-time pushHandler → kanban create |

The bridge daemon keeps a persistent WebSocket connection to Huly and registers
a `pushHandler` that receives ALL transactions in real-time. When a new Issue
is created (TxCreateDoc), it runs `kanban_create()` to spawn a kanban
worker. See `references/pushhandler-realtime.md` for the full mechanism.

Daemon lifecycle managed by launchd:
```bash
# Start
launchctl load ~/Library/LaunchAgents/ai.drewgent.huly-bridge.plist
# Stop
launchctl stop ai.drewgent.huly-bridge
# Check status
launchctl list ai.drewgent.huly-bridge
# Log
tail -f ~/.drewgent/logs/huly-bridge.log
```

### Real-Time Event Access Path

```js
// The pushHandler is on the RAW Connection, 4 levels deep:
client.client.client.conn.pushHandler((...txArr) => {
  for (const tx of txArr) {
    if (tx._class?.endsWith('TxCreateDoc') && tx.objectClass === 'tracker:class:Issue') {
      // Real-time notification of new Huly issues
    }
  }
});
```

### Environment
- `~/.hermes/.env` → `HULY_KEY` (JWT token)
- `~/.drewgent/state/huly_last_check.json` → check timestamp
- `~/.drewgent/scripts/huly_sync.js` / `.sh`
- `~/.drewgent/scripts/huly_check.js` / `.sh`
- `~/.drewgent/scripts/huly_bridge.js` / `.sh`
- `~/.drewgent/logs/huly-bridge.log`
- `~/Library/LaunchAgents/ai.drewgent.huly-bridge.plist`

### Free Tier Limits
- 10GB storage
- Unlimited users
- Unlimited Huly Objects
- Attachments count against storage
