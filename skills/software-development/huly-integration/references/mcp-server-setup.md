# Huly MCP Server — Setup Reference

Session: 2026-06-15 huly-mcp-setup
Server: `@bgx4k3p/huly-mcp-server` v2.4.3
Decision: Chosen over `@firfi/huly-mcp` for richer tool coverage (milestones, time tracking, components, templates, multi-workspace) and Streamable HTTP transport option.

## Why Not the SDK Approach

Previously, every Huly operation required:
1. `npm install @hcengineering/api-client`
2. `globalThis.window = { addEventListener: () => {} }`
3. `connect()` + `addCollection()` / `findAll()` / etc.
4. Manual error handling for AttachedDoc vs standalone doc

The MCP server wraps all of this and exposes it as 81 clean Hermes tools — no boilerplate, no polyfills, no class-IDs to memorize.

## Auth Architecture: Wrapper Script Pattern

The core challenge: MCP server config in `config.yaml` supports `env` section for secrets, but putting a JWT directly in the yaml is bad practice — it'd be visible in `git diff`, backups, and screenshots.

**Solution:** A bash wrapper that reads the token from `~/.hermes/.env` at MCP server launch time:

```bash
#!/bin/bash
# ~/.drewgent/scripts/huly-mcp-wrapper.sh
export HULY_URL="https://huly.app"
export HULY_WORKSPACE="humanerd"

HULY_KEY="$(grep '^HULY_KEY=' "$HOME/.hermes/.env" | head -1 | sed 's/^HULY_KEY=//' | tr -d '[:space:]')"
export HULY_TOKEN="$HULY_KEY"

exec npx -y "@bgx4k3p/huly-mcp-server@latest" "$@"
```

The config.yaml just points to the wrapper:

```yaml
mcp_servers:
  huly:
    command: /Users/drew/.drewgent/scripts/huly-mcp-wrapper.sh
```

This pattern is reusable for any MCP server that needs a credential bridge to `.env`.

## Available npm Packages (Discovery Notes)

| Package | Version | Auth | Key Features |
|---------|---------|------|-------------|
| `@bgx4k3p/huly-mcp-server` | 2.4.3 | `HULY_TOKEN` or email/password | 81 tools, milestones, time tracking, components, templates, multi-workspace, Streamable HTTP |
| `@firfi/huly-mcp` | 0.32.0 | email/password + workspace | Simpler, fewer tools, well-tested |
| `@starhui/huly-cli` | 0.2.1 | Via `@firfi/huly-mcp` | CLI wrapper on `@firfi/huly-mcp` |

The `HULY_KEY` from Huly Cloud Settings → Integrations → API Access works as `HULY_TOKEN` for `@bgx4k3p/huly-mcp-server` — no additional token generation needed.

## Verification

```bash
# Quick smoke test: pipe a tools/list request to the server
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | \
  timeout 8 ~/.drewgent/scripts/huly-mcp-wrapper.sh 2>&1

# Expected: "Huly MCP Server v2.4.3 running on stdio (81 tools, resources enabled)"
#          + JSON-RPC response with all 81 tools
```

## Design Decisions

1. **Wrapper over inline env** — avoids JWT in config.yaml
2. **bgx4k3p over firfi** — richer tool set; milestones, time tracking, and templates matter for real project management
3. **Stdio transport** — simplest for Hermes native MCP; Streamable HTTP available if remote access needed later
4. **Workspace hardcoded in wrapper** — `humanerd` is the only workspace; if multi-workspace needed, can be promoted to an env var

## Known Pitfalls

### Commented-Out Parent Key

The `mcp_servers:` key in `config.yaml` was commented out (`# mcp_servers:`) while the individual server entries (`huly:`, `wordpress:`) were uncommented and correctly formatted. This made the entire section inert — in YAML, commenting out a parent key disables ALL children, and orphaned children become root-level keys that Hermes ignores.

**Verification:** Run `grep '^mcp_servers:' ~/.hermes/config.yaml`. If the output is empty, the key is missing or commented. Fix by uncommenting `mcp_servers:`.

**Detection:** At session start, `tool_search(query="huly")` returns no results even though the config looks correct. Always check the parent key, not just the server entry.

## Future Considerations

- If the bridge daemon (`huly_bridge.js`) can be reimplemented using the MCP server's Streamable HTTP transport, it could eliminate the direct SDK dependency entirely
- The `linear` MCP server in config.yaml is unused since Linear → Huly migration — candidate for removal
