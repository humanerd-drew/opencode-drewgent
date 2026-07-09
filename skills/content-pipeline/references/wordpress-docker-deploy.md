# WordPress Docker Deploy — YOUR_DOMAIN

## Architecture

```
Mac Mini (colima Docker)
├── YOUR_DOMAIN-db (MySQL 8.0, port 3306 → host 3307)
│   └── Volume: /Volumes/YOUR_NAS/docker/wordpress/db  (NAS mount)
└── YOUR_DOMAIN-wp (WordPress 6.7 + Apache, port 80 → host 8080)
    ├── wp-content: /Volumes/YOUR_NAS/docker/wordpress/wp-content  (NAS mount)
    ├── plugins:   ~/.{{AGENT_NAME_LOWER}}/wordpress/wp-content/plugins
    └── themes:    ~/.{{AGENT_NAME_LOWER}}/wordpress/wp-content/themes
```

## Docker Compose

File: `~/.{{AGENT_NAME_LOWER}}/wordpress/docker-compose.yml`

```yaml
services:
  db:
    image: mysql:8.0
    platform: linux/arm64
    container_name: YOUR_DOMAIN-db
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PW}
      MYSQL_DATABASE: YOUR_DB_NAME
      MYSQL_USER: YOUR_DB_USER
      MYSQL_PASSWORD: ${MYSQL_WP_PW}
    volumes:
      - /Volumes/YOUR_NAS/docker/wordpress/db:/var/lib/mysql
    ports:
      - "3307:3306"

  wordpress:
    image: wordpress:6.7-php8.3-apache
    platform: linux/arm64
    container_name: YOUR_DOMAIN-wp
    depends_on: [db]
    restart: unless-stopped
    environment:
      WORDPRESS_DB_HOST: db:3306
      WORDPRESS_DB_USER: YOUR_DB_USER
      WORDPRESS_DB_PASSWORD: ${MYSQL_WP_PW}
      WORDPRESS_DB_NAME: YOUR_DB_NAME
      WORDPRESS_TABLE_PREFIX: hnr_
    volumes:
      - /Volumes/YOUR_NAS/docker/wordpress/wp-content:/var/www/html/wp-content
      - ~/.{{AGENT_NAME_LOWER}}/wordpress/wp-content/plugins:/var/www/html/wp-content/plugins
      - ~/.{{AGENT_NAME_LOWER}}/wordpress/wp-content/themes:/var/www/html/wp-content/themes
    ports:
      - "8080:80"
```

## Credentials

Stored in: `~/.{{AGENT_NAME_LOWER}}/wordpress/.wp-env` (chmod 600)

| Field | Value |
|-------|-------|
| WP URL | http://localhost:8080 |
| Admin user | YOUR_USERNAME |
| Admin pass | in .wp-env |
| DB name | YOUR_DB_NAME |
| DB user | YOUR_DB_USER |
| Table prefix | hnr_ |
| PHPMyAdmin | not installed (MySQL via CLI only) |

## Startup / Shutdown

```bash
cd ~/.{{AGENT_NAME_LOWER}}/wordpress
docker compose up -d      # start
docker compose down       # stop (preserves volumes)
docker compose logs -f    # follow logs
```

Docker host: colima (socket at `~/.colima/default/docker.sock`).

## wp-cli

Installed inside container. Run commands via:

```bash
docker exec YOUR_DOMAIN-wp wp --allow-root <command>
```

## Active Theme: Blocksy

Blocksy (v2.1.45, `blocksy-companion` plugin v2.1.45). Free version used — no Pro license.

### Customization Applied via CLI

What was set without the Customizer UI (via wp-cli `eval`):

| Setting | Value |
|---------|-------|
| Color palette | 10-color warm/bronze palette (see `svg-cover-design.md`) |
| Custom CSS | Typography, cards, blockquotes, links, code blocks |
| Google Fonts | Noto Sans KR + Noto Serif KR + JetBrains Mono (MU plugin) |
| Logo | Uploaded from `website/static/img/logo.png` (attachment ID 14) |
| Site width | 1100px desktop, 900px tablet, 90vw mobile |
| Content width | 700px (post body) |
| Header | Default Blocksy header (logo + nav) |
| Front page | Static "Home" page |
| Blog page | `/blog/` |
| Permalink | `/%category%/%postname%/` |
| Timezone | Asia/Seoul |

### Still Needs Customizer

- Header layout (logo size, menu position, sticky)
- Blog card grid layout (2 columns)
- Homepage hero section
- Featured image handling for SVG covers
- Footer design
- Mobile menu styling

## Database Access

```bash
docker exec -it YOUR_DOMAIN-db mysql -u YOUR_DB_USER -p
# Password in .wp-env
```

## Content-Manager → WordPress Integration (Future)

The content-manager produces drafts in `~/.{{AGENT_NAME_LOWER}}/P2-hippocampus/memories/insights/`. To publish to WordPress:

1. Create Application Password in WP Admin → Users → YOUR_USERNAME → Application Passwords
2. Use WordPress REST API (`/wp-json/wp/v2/posts`) with Basic Auth (username + app password)
3. Upload SVG/PNG images via `/wp-json/wp/v2/media`
4. Set featured image as the post's SVG cover

Not yet automated — drafts are currently reviewed in Obsidian and published manually or via Quartz.
