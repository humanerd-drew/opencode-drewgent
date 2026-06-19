# WordPress Publish Workflow

Content-manager drafts are published to humanerd.kr via WordPress MCP.

## Architecture

```
content-manager → memories/insights/(slug).md + SVG + Excalidraw + PNG
                → (future) Huly review → publish trigger
                → WordPress MCP server → create_post / upload_media
```

## WordPress MCP Server

**Script:** `~/.drewgent/scripts/wordpress-mcp-server.js`
**Registration:** `config.yaml` → `mcp_servers.wordpress`
**Communication:** STDIO JSON-RPC 2.0 (not standard MCP tools/list — uses `list_tools` and `call_tool`)
**Auth:** Docker socket access (runs as root via `docker exec`)

### Tools

| Tool | Description | Required Args |
|------|-------------|---------------|
| `create_post` | Create WP post | title, content |
| `upload_media` | Upload file to media library | file_path |
| `list_posts` | List recent posts | — |
| `get_post` | Get post by ID | id |
| `create_category` | Create category | name |
| `set_site_option` | Set WP option | key, value |
| `set_theme_mod` | Set theme modification | key, value |

### Testing

```bash
# List tools
echo '{"jsonrpc":"2.0","id":1,"method":"list_tools"}' | node ~/.drewgent/scripts/wordpress-mcp-server.js

# Create test post
echo '{"jsonrpc":"2.0","id":2,"method":"call_tool","params":{"name":"create_post","arguments":{"title":"Test","content":"Hello","status":"draft"}}}' | node ~/.drewgent/scripts/wordpress-mcp-server.js
```

## WordPress Local Docker Setup

### Containers

| Container | Image | Port |
|-----------|-------|------|
| `humanerd-wp` | wordpress:6.7-php8.3-apache | 8080→80 |
| `humanerd-db` | mysql:8.0 | 3307→3306 |

### Data Storage

- WP uploads: `/Volumes/humanerd/docker/wordpress/wp-content/` (NAS SMB mount)
- MySQL data: `/Volumes/humanerd/docker/wordpress/db/` (NAS SMB mount)
- Config: `/Users/drew/.drewgent/wordpress/`

### Theme: Blocksy (Free)

Blocksy was chosen over GeneratePress because:
1. **Free version supports custom fonts** (Noto Sans KR, Noto Serif KR upload). GeneratePress requires $59/yr Premium for this.
2. Built-in Custom Fonts extension
3. Global Color Palette system
4. Header/Footer builder (drag-and-drop)
5. Dark mode built-in
6. No WooCommerce needed (tech blog only)

### Customization via wp-cli

```bash
# Install/activate theme
docker exec humanerd-wp wp --allow-root theme install blocksy --activate

# Set color palette
docker exec humanerd-wp wp --allow-root eval '
set_theme_mod("blocksy_color_palette", [
  ["color"=>"#1c1c1a","id"=>"color1"],
  ["color"=>"#8b7355","id"=>"color8"]
]);
'

# Set logo
docker exec humanerd-wp wp --allow-root media import /path/to/logo.png --porcelain
docker exec humanerd-wp wp --allow-root eval '
set_theme_mod("custom_logo", 14);
set_theme_mod("logo_type", "logo");
'

# Custom CSS
docker exec humanerd-wp wp --allow-root eval '
wp_update_custom_css_post("body { font-family: ... }");
'

# Add Google Fonts via MU plugin
docker exec humanerd-wp wp --allow-root eval '
$plugin = "/var/www/html/wp-content/mu-plugins/humanerd-fonts.php";
file_put_contents($plugin, "<?php add_action(\"wp_enqueue_scripts\", function() {
  wp_enqueue_style(\"humanerd-fonts\", \"https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&family=Noto+Serif+KR:wght@400;600;700&family=JetBrains+Mono:wght@400;700&display=swap\", array(), null);
});");
'
```

### .htaccess Fix

WordPress permalink rewrite rules may not be auto-generated in Docker. Manual fix:

```bash
docker exec humanerd-wp sh -c "cat > /var/www/html/.htaccess << 'EOF'
# BEGIN WordPress
<IfModule mod_rewrite.c>
RewriteEngine On
RewriteRule .* - [E=HTTP_AUTHORIZATION:%{HTTP:Authorization}]
RewriteBase /
RewriteRule ^index\\.php$ - [L]
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule . /index.php [L]
</IfModule>
# END WordPress
EOF"
```

### Commands Reference

```bash
# wp-cli
docker exec humanerd-wp wp --allow-root <command>

# Docker compose
export DOCKER_HOST=unix:///Users/drew/.colima/default/docker.sock
cd /Users/drew/.drewgent/wordpress && docker-compose up -d

# Colima (Docker runtime)
colima status
colima start --cpu 4 --memory 8 --disk 50

# Access WordPress
open http://localhost:8080/wp-admin
# User: humanerd
# Password: stored in ~/.drewgent/wordpress/.wp-env (chmod 600)
```

## Publish Pipeline (Future)

```
content-manager → draft ready → kanban task (status: blocked = "needs review")
                              → Drew unblocks → status: ready
                              → publisher cron → WordPress MCP create_post
                              → upload SVG + PNG as media
                              → set featured image
                              → post status: draft (not published)
                              → Drew reviews in WP → publishes
```
