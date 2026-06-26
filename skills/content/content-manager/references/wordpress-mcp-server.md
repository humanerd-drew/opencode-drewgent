# WordPress MCP Server

Custom STDIO MCP server that wraps wp-cli to provide WordPress management tools to Hermes agents.

## Location
- Script: `~/.drewgent/scripts/wordpress-mcp-server.js`
- Config: `~/.hermes/config.yaml` under `mcp_servers.wordpress`
- WordPress Docker: `~/.drewgent/wordpress/docker-compose.yml`

## Registered Tools (7)
create_post, upload_media, list_posts, get_post, create_category, set_site_option, set_theme_mod

## Usage
```bash
# List tools
echo '{"jsonrpc":"2.0","id":1,"method":"list_tools"}' | timeout 5 node /Users/drew/.drewgent/scripts/wordpress-mcp-server.js

# Create a post
echo '{"jsonrpc":"2.0","id":2,"method":"call_tool","params":{"name":"create_post","arguments":{"title":"Test","content":"Hello","category":"systems","status":"draft"}}}' | timeout 10 node /Users/drew/.drewgent/scripts/wordpress-mcp-server.js
```

## Architecture
- WordPress runs in Docker on Mac Mini (colima VM)
- Data stored on Synology NAS at `/Volumes/humanerd/docker/wordpress/`
- MySQL 8.0 + WordPress 6.7 on arm64
- Blocksy theme activated with custom fonts (Noto Sans KR, Noto Serif KR, JetBrains Mono)

## Credentials
Stored at: `~/.drewgent/wordpress/.wp-env` (chmod 600)
WP Admin: `humanerd` / `QAq&#q8Zrt(Fxy0vNO`
URL: http://localhost:8080

## Key Commands
```bash
# wp-cli via Docker
docker exec humanerd-wp wp --allow-root <command>

# Container management
export DOCKER_HOST=unix:///Users/drew/.colima/default/docker.sock
docker-compose -f ~/.drewgent/wordpress/docker-compose.yml up -d
```
