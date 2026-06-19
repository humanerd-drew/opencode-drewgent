# Huly Content Review → Publish Workflow

## Status: SELF-HOSTED ON NAS (DS920+)

Huly self-host is deployed at **`http://192.168.1.53:8087`**.

### Stack (14 containers)
nginx, cockroach, redpanda, minio, elastic, rekoni, transactor, collaborator, account, workspace, front, fulltext, stats, kvs

### Setup Location
```
/volume1/docker/huly/
├── compose.yml          ← Huly v7 compose
├── .env                 ← environment config (CR_DB_URL missing — see below)
├── huly_v7.conf         ← config template (symlinked as .env)
└── data/                ← persistent volumes
    ├── elastic/
    ├── files/
    ├── cockroach/
    ├── cockroach-certs/
    └── redpanda/
```

### .env Configuration
Required variables (set in `huly_v7.conf` / `.env`):
```
HULY_VERSION=v0.7.423
HOST_ADDRESS=192.168.1.53
HTTP_PORT=8087
SERVER_SECRET=<random-hex>
# CockroachDB — currently NOT SET, causing account service to fail
# CR_DATABASE=huly
# CR_USERNAME=huly
# CR_PASSWORD=huly_secret
# CR_DB_URL=postgresql://huly:huly_secret@cockroach:26257/huly
```

### ⚠️ Known Issue: CockroachDB Connection
The account service fails with:
```
Error while initializing postgres account db connect ECONNREFUSED 127.0.0.1:5432
```
Cause: `CR_DB_URL` and related CR_* vars are not set in `.env`. The compose.yml references `${CR_DB_URL}` but has no default value. Without it, services try to connect to PostgreSQL (port 5432) instead of CockroachDB (port 26257).

**Fix pending:** Set these env vars and restart:
```bash
CR_DATABASE=huly
CR_USERNAME=huly
CR_PASSWORD=huly_secret
CR_DB_URL=postgresql://huly:huly_secret@cockroach:26257/huly
```

Also, the compose.yml has `SERVER_SECRET=***` hardcoded in some services — they should use `${SERVER_SECRET}` instead.

## Planned Pipeline
```
Content-manager → draft files (SVG + MD + PNG)
  → Huly issue created (assignee: drew, status: "Todo")
  → Drew reviews in Huly kanban (web UI at http://192.168.1.53:8087)
  → Status changes to "Done"
  → Watcher detects change via MCP polling
  → WordPress MCP pushes to humanerd.kr
```

## Huly MCP Server
- Provider: `@bgx4k3p/huly-mcp-server@latest`
- 81 tools available
- Auth: HULY_KEY from `~/.hermes/.env`
- Key methods: `create_issue`, `list_issues`, `update_issue`, `search_issues`, `add_comment`

## Key Tools for Content Workflow
- `create_issue` — create content review task
- `list_issues` — find content tasks
- `update_issue` — change status
- `add_comment` — review notes
- `search_issues` — find by keywords

## Status: Huly webhooks NOT available
Huly doesn't have outgoing webhooks yet (GitHub issues #6996, #9187).
Planned approach: lightweight polling via gateway internal scheduler.

## Alternative: Local Kanban Board
If Huly integration isn't ready, use the local kanban system:
1. Content-manager creates kanban task (status: "blocked" = needs review)
2. Dashboard: `localhost:8644` or via launchctl `ai.drewgent.kanban-dashboard`
3. Unblock → triggers WordPress publish via dispatch_once_content.py
