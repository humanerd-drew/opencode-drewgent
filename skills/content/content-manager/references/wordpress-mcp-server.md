# WordPress MCP Server

Custom STDIO MCP server that wraps wp-cli to provide WordPress management tools to Hermes agents.

## Location
- Script: `~/.{{AGENT_NAME_LOWER}}/scripts/wordpress-mcp-server.js`
- Config: `~/.hermes/config.yaml` under `mcp_servers.wordpress`
- WordPress Docker: `~/.{{AGENT_NAME_LOWER}}/wordpress/docker-compose.yml`

## Registered Tools (7)
create_post, upload_media, list_posts, get_post, create_category, set_site_option, set_theme_mod

## Usage
```bash
# List tools
echo '{"jsonrpc":"2.0","id":1,"method":"list_tools"}' | timeout 5 node ~/.{{AGENT_NAME_LOWER}}/scripts/wordpress-mcp-server.js

# Create a post
echo '{"jsonrpc":"2.0","id":2,"method":"call_tool","params":{"name":"create_post","arguments":{"title":"Test","content":"Hello","category":"systems","status":"draft"}}}' | timeout 10 node ~/.{{AGENT_NAME_LOWER}}/scripts/wordpress-mcp-server.js
```

## Architecture
- WordPress runs in Docker on Mac Mini (colima VM)
- Data stored on Synology NAS at `/Volumes/YOUR_NAS/docker/wordpress/`
- MySQL 8.0 + WordPress 6.7 on arm64
- Blocksy theme activated with custom fonts (Noto Sans KR, Noto Serif KR, JetBrains Mono)

## Credentials
Stored at: `~/.{{AGENT_NAME_LOWER}}/wordpress/.wp-env` (chmod 600)
WP Admin: `YOUR_USERNAME` / password in `.wp-env`
URL: http://localhost:8080

## Key Commands
```bash
# wp-cli via Docker
docker exec YOUR_DOMAIN-wp wp --allow-root <command>

# Container management
export DOCKER_HOST=unix://~/.colima/default/docker.sock
docker-compose -f ~/.{{AGENT_NAME_LOWER}}/wordpress/docker-compose.yml up -d
```
