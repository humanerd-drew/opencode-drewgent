---
title: WordPress CMS
name: wordpress-cms
description: WordPress CMS setup on Docker + Blocksy theme + MCP integration for autonomous content publishing
trigger: "humanerd.kr 사이트를 Quartz에서 WordPress로 전환하면서 구축한 인프라"
provenance:
  session: "2026-06-14 wordpress-setup"
  decision: "CMS 워크플로우 + blocksy 무료로 커스텀 폰트/디자인 가능 → Quartz 대체"
created: 2026-06-14
updated: 2026-06-14
---

# WordPress CMS

WordPress + Docker + Blocksy + MCP integration for humanerd.kr.

## Docker Setup

```yaml
# ~/.drewgent/wordpress/docker-compose.yml
services:
  db:
    image: mysql:8.0
    container_name: humanerd-db
    ports: ["3307:3306"]
    volumes:
      - /Volumes/humanerd/docker/wordpress/db:/var/lib/mysql
  wordpress:
    image: wordpress:6.7-php8.3-apache
    container_name: humanerd-wp
    depends_on: [db]
    ports: ["8080:80"]
    volumes:
      - /Volumes/humanerd/docker/wordpress/wp-content:/var/www/html/wp-content
      - /Users/drew/.drewgent/wordpress/wp-content/plugins:/var/www/html/wp-content/plugins
      - /Users/drew/.drewgent/wordpress/wp-content/themes:/var/www/html/wp-content/themes
```

**pw 저장:** `~/.drewgent/wordpress/.wp-env` (chmod 600)

## Blocksy Theme

Blocksy is the active theme. Free version supports:
- **Custom Fonts** upload (Noto Sans KR, Noto Serif KR) — included free
- **Header/Footer Builder** — drag and drop
- **Global Color Palette** — 10-color system with bronze accent (#8b7355)
- **Blog Layout** — card grid, list, masonry
- **Typography** — per-element font/size/line-height
- **Dark Mode** — built-in

### Setup via wp-cli

```bash
docker exec humanerd-wp wp --allow-root theme install blocksy --activate
docker exec humanerd-wp wp --allow-root plugin install blocksy-companion --activate
```

### Custom Fonts (Google Fonts)

MU plugin at `wp-content/mu-plugins/humanerd-fonts.php`:
```php
add_action("wp_enqueue_scripts", function() {
  wp_enqueue_style("humanerd-fonts",
    "https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&family=Noto+Serif+KR:wght@400;600;700&family=JetBrains+Mono:wght@400;700&display=swap"
  );
});
```

### Color Palette (Blocksy)

```php
$palette = array(
  array("color" => "#1c1c1a", "id" => "color1"),   # text primary
  array("color" => "#6b6b68", "id" => "color2"),   # text secondary
  array("color" => "#9b9b97", "id" => "color3"),   # text tertiary
  array("color" => "#ffffff", "id" => "color4"),   # white
  array("color" => "#fafaf8", "id" => "color5"),   # bg
  array("color" => "#f2f2ee", "id" => "color6"),   # surface
  array("color" => "#e8e7e4", "id" => "color7"),   # border
  array("color" => "#8b7355", "id" => "color8"),   # accent (bronze)
  array("color" => "#7a6349", "id" => "color9"),   # accent hover
  array("color" => "#d4c4b0", "id" => "color10"),  # accent muted
);
set_theme_mod("blocksy_color_palette", $palette);
```

### .htaccess

WordPress Docker 이미지는 .htaccess rewrite rules를 자동 생성하지 않음. 수동 설정 필수:

```apache
# BEGIN WordPress
<IfModule mod_rewrite.c>
RewriteEngine On
RewriteRule .* - [E=HTTP_AUTHORIZATION:%{HTTP:Authorization}]
RewriteBase /
RewriteRule ^index\.php$ - [L]
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule . /index.php [L]
</IfModule>
# END WordPress
```

## WordPress MCP Server

Custom MCP server for autonomous agent→WordPress interaction.

**Path:** `/Users/drew/.drewgent/scripts/wordpress-mcp-server.js`
**Config:** `mcp_servers.wordpress` in `~/.hermes/config.yaml`
**Backend:** Node.js wrapping `docker exec humanerd-wp wp --allow-root` via STDIO JSON-RPC 2.0

### Available Tools

| Tool | Params | Returns |
|------|--------|---------|
| create_post | title, content, category, tags, status | Post ID |
| upload_media | file_path (inside container), title | Media ID |
| list_posts | posts_per_page, status | JSON array |
| get_post | id | JSON |
| create_category | name, slug | Term ID |
| set_site_option | key, value | Success msg |
| set_theme_mod | key, value (JSON string) | Success msg |

### Test

```bash
printf '{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n' | node /Users/drew/.drewgent/scripts/wordpress-mcp-server.js
```

## Huly MCP Integration

Huly workspace "humanerd" with MCP server (`@bgx4k3p/huly-mcp-server@latest`).
81 tools available including issue management, project management, team management.

Key tools for content workflow:
- `create_issue` — 제목/설명/담당자/프로젝트 지정
- `list_issues` — 필터링 + 커서 페이지네이션
- `search_issues` — 풀텍스트 검색
- `get_issue` — 상세 내용 + 상태
- `update_issue` — 상태 변경 (e.g. "Todo" → "Done")
- `list_statuses` — 프로젝트별 상태 workflow 조회

## Site Structure

| Page | URL | Content |
|------|-----|---------|
| Home | / | 최근 글 + 프로젝트 소개 |
| Blog | /blog/ | 포스트 목록 (카드 그리드) |
| About | /about/ | 사이트 소개 |

Categories: build-log (Build Log), ai-tools (AI & Tools), systems (Systems), creative (Creative)

## wp-cli Cheatsheet

```bash
# Post management
docker exec humanerd-wp wp --allow-root post create --post_title="T" --post_content="C" --post_status=publish --post_category=systems

# Theme/plugin
docker exec humanerd-wp wp --allow-root theme install <slug> --activate
docker exec humanerd-wp wp --allow-root plugin install <slug> --activate

# Options
docker exec humanerd-wp wp --allow-root option update blogname "humanerd"
docker exec humanerd-wp wp --allow-root rewrite flush

# Media
docker exec humanerd-wp wp --allow-root media import /path/to/file.png --title="Logo"

# Custom PHP
docker exec humanerd-wp wp --allow-root eval 'echo get_option("blogname");'
docker exec humanerd-wp wp --allow-root eval-file /tmp/setup.php
```

## Path Pitfalls

- All paths in wp-cli commands inside container are **container paths** (/var/www/html/...)
- Host paths need `docker cp` before `docker exec`
- `.htaccess` must be manually written (Docker image bug)
- Always use `--allow-root` with wp-cli inside container
- env vars (DOCKER_HOST) needed when colima manages Docker
