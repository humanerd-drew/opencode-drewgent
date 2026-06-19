# WordPress Docker Deploy — humanerd.kr

## Architecture

```
Mac Mini (colima Docker)
├── humanerd-db (MySQL 8.0, port 3306 → host 3307)
│   └── Volume: /Volumes/humanerd/docker/wordpress/db  (NAS mount)
└── humanerd-wp (WordPress 6.7 + Apache, port 80 → host 8080)
    ├── wp-content: /Volumes/humanerd/docker/wordpress/wp-content  (NAS mount)
    ├── plugins:   ~/.drewgent/wordpress/wp-content/plugins
    └── themes:    ~/.drewgent/wordpress/wp-content/themes
```

## Docker Compose

File: `/Users/drew/.drewgent/wordpress/docker-compose.yml`

```yaml
services:
  db:
    image: mysql:8.0
    platform: linux/arm64
    container_name: humanerd-db
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PW}
      MYSQL_DATABASE: humanerd
      MYSQL_USER: humanerd
      MYSQL_PASSWORD: ${MYSQL_WP_PW}
    volumes:
      - /Volumes/humanerd/docker/wordpress/db:/var/lib/mysql
    ports:
      - "3307:3306"

  wordpress:
    image: wordpress:6.7-php8.3-apache
    platform: linux/arm64
    container_name: humanerd-wp
    depends_on: [db]
    restart: unless-stopped
    environment:
      WORDPRESS_DB_HOST: db:3306
      WORDPRESS_DB_USER: humanerd
      WORDPRESS_DB_PASSWORD: ${MYSQL_WP_PW}
      WORDPRESS_DB_NAME: humanerd
      WORDPRESS_TABLE_PREFIX: hnr_
    volumes:
      - /Volumes/humanerd/docker/wordpress/wp-content:/var/www/html/wp-content
      - /Users/drew/.drewgent/wordpress/wp-content/plugins:/var/www/html/wp-content/plugins
      - /Users/drew/.drewgent/wordpress/wp-content/themes:/var/www/html/wp-content/themes
    ports:
      - "8080:80"
```

## Credentials

Stored in: `/Users/drew/.drewgent/wordpress/.wp-env` (chmod 600)

| Field | Value |
|-------|-------|
| WP URL | http://localhost:8080 |
| Admin user | humanerd |
| Admin pass | in .wp-env |
| DB name | humanerd |
| DB user | humanerd |
| Table prefix | hnr_ |
| PHPMyAdmin | not installed (MySQL via CLI only) |

## Startup / Shutdown

```bash
cd ~/.drewgent/wordpress
docker compose up -d      # start
docker compose down       # stop (preserves volumes)
docker compose logs -f    # follow logs
```

Docker host: colima (socket at `~/.colima/default/docker.sock`).

## wp-cli

Installed inside container. Run commands via:

```bash
docker exec humanerd-wp wp --allow-root <command>
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
docker exec -it humanerd-db mysql -u humanerd -p
# Password in .wp-env
```

## Content-Manager → WordPress Integration (Future)

The content-manager produces drafts in `/Users/drew/.drewgent/P2-hippocampus/memories/insights/`. To publish to WordPress:

1. Create Application Password in WP Admin → Users → humanerd → Application Passwords
2. Use WordPress REST API (`/wp-json/wp/v2/posts`) with Basic Auth (username + app password)
3. Upload SVG/PNG images via `/wp-json/wp/v2/media`
4. Set featured image as the post's SVG cover

Not yet automated — drafts are currently reviewed in Obsidian and published manually or via Quartz.
