# Huly Content Review Workflow

Content-manager drafts are reviewed via Huly kanban before WordPress publishing.

## Current Status (June 2026)

**Huly does NOT support outgoing webhooks.** Feature requests exist (issues #6996, #9187 on hcengineering/platform) but are not implemented. MCP `resources/subscribe` also returned "Method not found."

Without webhooks, polling is required. The gateway internal scheduler (1-minute tick) is the most efficient approach — not a separate cron.

## Planned Architecture

```
content-manager → draft → create_issue via Huly MCP (status: "In Progress")
                                │
            User reviews in Huly → moves to "Done"
                                │
                                ▼
            Gateway tick (1min) → search_issues("Done")
                                → WordPress MCP push
                                → issue status → "Closed"
```

## Huly MCP Server Details

- **Package:** `@bgx4k3p/huly-mcp-server@latest`
- **Version:** v2.4.3
- **Tools:** 81 total
- **Workspace:** `humanerd` (huly.app)
- **Auth:** `HULY_KEY` from `~/.hermes/.env`

### Key Tools for Content Review

| Tool | Purpose | Example |
|------|---------|---------|
| `create_issue` | Create review task | `create_issue(project="CONTENT", title="[review] slug", description="path/to/draft.md")` |
| `list_issues` | Find review tasks | `list_issues(project="CONTENT", status="Done")` |
| `get_issue` | Get task details | `get_issue(identifier="CONTENT-42")` |
| `update_issue` | Change status | `update_issue(identifier="CONTENT-42", status="Done")` |
| `search_issues` | Full-text search | `search_issues(query="slug-name")` |
| `list_statuses` | Available workflow states | `list_statuses(project="CONTENT")` |
| `add_comment` | Leave review notes | `add_comment(issue="CONTENT-42", text="Approved")` |

### MCP Protocol Note

The Huly MCP server uses standard MCP method naming (NOT `list_tools`):
- ✅ `tools/list` — list available tools
- ✅ `tools/call` — invoke a tool
- ❌ `list_tools` — returns "Method not found"

This differs from the custom WordPress MCP server which uses `list_tools` for simplicity.

### Testing from CLI

```bash
# Set env
HULY_KEY="$(grep '^HULY_KEY=' ~/.hermes/.env | head -1 | sed 's/^HULY_KEY=//' | tr -d '\"[:space:]')"
export HULY_URL="https://huly.app"
export HULY_WORKSPACE="humanerd"
export HULY_TOKEN="$HULY_KEY"

# List tools
printf '{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n' | timeout 10 npx -y "@bgx4k3p/huly-mcp-server@latest"

# Call tool (e.g., list_issues)
printf '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"list_issues","arguments":{"project":"CONTENT"}}}\n' | timeout 10 npx -y "@bgx4k3p/huly-mcp-server@latest"
```

## Alternative Approaches (Without Huly Webhooks)

| Approach | When to Use |
|----------|-------------|
| Gateway 1-min tick | Default. Already running, minimal overhead |
| Cloudflare Tunnel | If Huly ever supports webhooks |
| n8n webhook relay | Already installed, has built-in webhook receiver |
| Discord bridge | Huly → Discord notification → gateway detects message |

## Connection Issues

If SSH to NAS fails:
- Port 22 is open on the NAS (Synology DS920+)
- Need to register the Mac Mini's SSH public key in NAS `~/.ssh/authorized_keys`
- Once SSH works, Docker on NAS can be managed remotely
