# WordPress MCP Publishing

Custom MCP server for WordPress management via wp-cli.

## Server

`/Users/drew/.drewgent/scripts/wordpress-mcp-server.js`

A Node.js STDIO MCP server that wraps `docker exec humanerd-wp wp --allow-root` commands as JSON-RPC 2.0 tools.

Registered in `~/.hermes/config.yaml` under `mcp_servers.wordpress`.

## Available Tools

| Tool | Description | Key Params |
|------|-------------|------------|
| `create_post` | Create new post | title, content, category, tags, status, date |
| `upload_media` | Upload file (image/SVG) | file_path, title |
| `list_posts` | List published posts | posts_per_page, status |
| `get_post` | Get post by ID | id |
| `create_category` | Add taxonomy | name, slug |
| `set_site_option` | Update WP option | key, value |
| `set_theme_mod` | Set theme mod (JSON) | key, value |

## WordPress Docker Setup

- **Compose**: `~/.drewgent/wordpress/docker-compose.yml`
- **NAS data**: `/Volumes/humanerd/docker/wordpress/`
- **Colima**: Docker runtime via colima (socket at `~/.colima/default/docker.sock`)
- **URL**: `http://localhost:8080`
- **Admin**: `http://localhost:8080/wp-admin`
- **Theme**: Blocksy (free) with custom color palette + Google Fonts

## Publishing Flow

Content-manager creates markdown drafts → converts to WordPress post via MCP → sets SVG cover as featured image → publishes.

## REST API Backup

Direct REST API access at `http://localhost:8080/wp-json/wp/v2/` with Application Password auth.
