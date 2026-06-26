---
title: content-manager
name: content-manager
description: "CMO-style content agent — observes work activity, produces multi-format drafts with SVG/Mermaid/Excalidraw visuals, pushes to WordPress via MCP. User-facing: 'CMO 에이전트가 내 작업을 보고 콘텐트로 만든다'."
  session: "2026-06-14 cmo-content-agent"
  decision: "Kanban + Huly review → WordPress publish pipeline. SVG/Mermaid/Excalidraw for visuals ($0, no paid APIs). WordPress on Mac Mini Docker, data on Synology NAS."
design_principles:
  - "DO NOT decide based on imagination — test the approach first, retreat only if proves inefficient."
  - "DO NOT be conservative about change — 상정한 방향을 현재 환경에 맞춰 최대한 적용해보고 그럼에도 손해라면 그 때 물러도 늦지않다."
  - "Prefer additive over replacement — build on what exists, don't rip out."
  - "$0 visuals — SVG, Excalidraw, Mermaid. No paid image generation APIs. Use existing model (deepseek-v4-pro)."
created: 2026-06-14
updated: 2026-06-14
links:
  - "[[content/content-manager/references/wordpress-mcp-server]]"
  - "[[content/content-manager/references/nas-setup]]"
  - "[[content/content-manager/references/huly-integration]]"
  - "[[content/content-manager/references/excalidraw-pipeline]]"
---

# Content Manager Agent

CMO-style agent that observes Drew's work (sessions, git, kanban) and autonomously produces multi-format blog content with rich visuals. Runs as a daily cron job or on-demand via `task()`.

## Architecture

```
Observer (git log / session_search / kanban_list)
  → Knowledge Base (brand-guide + glossary + narrative_arc + content-inventory)
  → Web Research (optional: related projects, memes, reference images)
  → Story Mining (editorial scoring: reader-value / drew-angle / narrative-fit / platform-fit)
  → Content Production
      ├── Blog post (.md) — Mermaid diagrams inline
      ├── SVG cover (1200×630) — rich illustration using paths/gradients/filters
      ├── SVG meme (optional) — drake/this-is-fine/galaxy-brain/distracted-boyfriend
      ├── Excalidraw diagram (.excalidraw.json) → PNG (via headless Chrome)
      └── X thread (.txt) — 10-15 tweets
  → WordPress Publishing (via custom MCP server, status: draft)
  → Huly / Kanban Review → status: published
  → Narrative Arc Update (narrative_arc.md + content-inventory.md)
```

## Design Rules

### Humanerd.kr Design System (CSS)
```
BG:        #fafaf8 (warm off-white)
Surface:   #ffffff
Border:    #e8e7e4
Text:      #1c1c1a (primary), #6b6b68 (secondary), #9b9b97 (tertiary)
Accent:    #8b7355 (bronze), #7a6349 (accent hover), #d4c4b0 (accent muted)
Heading:   Noto Serif KR (serif)
Body:      Noto Sans KR (sans-serif)
Mono:      JetBrains Mono
```

### Visual Assets — All $0, No Paid APIs
| Type | Format | Method |
|------|--------|--------|
| Cover image | SVG (1200×630) | Written as XML by the model — paths, gradients, filters |
| Architecture diagram | Mermaid or Excalidraw→PNG | Inline `mermaid` or headless Chrome screenshot |
| Meme/reference | SVG | Template-based (4 templates built in) |
| Technical illustration | Excalidraw JSON → PNG | Puppeteer + excalidraw.com embed |

### SVG Cover Design Rules
- Background: `#0d0d1a` → `#1a1a30` gradient (dark theme for hero images)
- Accent: `#7b5f3d` (amber), `#4a90d9` (blue), `#50c878` (teal)
- Text: `#e8e4df` (warm white), `#8a8680` (muted), `#5a5650` (dim)
- Use: paths, bezier curves, multi-stop gradients, feGaussianBlur filters
- Include: title, subtitle, tags, date, simple illustration matching topic

## Key Components

### Agent Profile
- `~/.drewgent/agents/content-manager.md` — role definition (deepseek-v4-pro, opencode-go)
- Toolsets: terminal, file, search, session_search, kanban, web
- Fires daily at 12:00 KST via cron
- Also triggerable via `task(subagent_type="content-manager", description="Content run", prompt="...")`

### Knowledge Base
at `P4-cortex/content/`:
- `brand-guide.md` — positioning, audience, tone, content pillars (4: Build Log, AI & Tools, Systems, Creative)
- `glossary.md` — project terms (Drewgent, Gateway, M-LOG, PDC, etc.)
- `content-inventory.md` — published/draft tracking + dedup topics
- `narrative_arc.md` — serial continuity (current season, episodes, threads)

### WordPress Stack
- Local Docker (colima VM, 4GB→8GB RAM, 2 CPU)
- WordPress 6.7 + MySQL 8.0 (arm64)
- Blocksy theme (free) with custom fonts
- Data on Synology NAS mount (`/Volumes/humanerd/docker/wordpress/`)
- Custom MCP server at `~/.drewgent/scripts/wordpress-mcp-server.js`
- 7 MCP tools: create_post, upload_media, list_posts, get_post, create_category, set_site_option, set_theme_mod

### Huly Integration (planned)
- Huly Cloud workspace: humanerd (huly.app)
- MCP server: `@bgx4k3p/huly-mcp-server@latest` (81 tools)
- Key tools: create_issue, list_issues, update_issue, search_issues
- Note: Huly has no outgoing webhooks yet (GitHub #6996, #9187 — feature requests)

## Pitfalls & Lessons

### Cron Schedule
- Initially set to `every 3 days` → user corrected: should be DAILY when material exists
- Don't use fixed schedules for content creation — produce when material is available, stay silent when nothing new

### task() Model Override
The agent profile defines `model: deepseek-v4-pro`, but calling via `task(subagent_type="content-manager")` may use a different model. In testing, the actual run used `deepseek-v4-flash` (the parent session's model), not the pro model defined in the profile.

**Implication:** Delegated content-manager runs get the flash model (faster, cheaper, slightly lower quality). Cron jobs (which use the profile's model directly) use the pro model. If output quality from a delegate_task run seems low, check which model was used — it may be the flash fallback.

**Workaround:** For high-quality runs, use the cron trigger or explicitly set `model` in the task() call parameters.

### Image Generation
- DO NOT suggest paid APIs (FAL, DALL-E) first — the user explicitly rejected extra costs
- SVG cover images cost $0 and the model can write them directly
- Excalidraw JSON → PNG via Puppeteer works but needs the NODE_PATH env var set
- Mermaid renders natively in Quartz — no conversion needed

### WordPress MCP Server
- Uses `docker exec humanerd-wp wp --allow-root` internally — WordPress must be running
- Test with `printf '{"jsonrpc":"2.0","id":1,"method":"list_tools"}\n' | timeout 5 node script.js`
- Registered in `config.yaml` under `mcp_servers.wordpress`
- The Automattic `wordpress-mcp` plugin is installed but has route-registration issues on this setup

### NAS Docker Access
- Use `expect` scripts for SSH-based Docker commands (Synology requires TTY for sudo)
- sudoers configured for `NOPASSWD: /usr/local/bin/docker`
- Key-based SSH auth not available — always use expect with password

### User Preferences (Corrected Behaviors)
1. "변화를 두려워 하는 판단 방식은 필요없어" — Don't be conservative. Propose and test, don't list objections based on imagination.
2. "상상만으로 결정하는 방식도 필요없어" — Don't decide based on assumptions. Try it first, then evaluate.
3. "네가 직접 해야 하는게 뭐야, 너는 못해?" — When asked "can you do X?", just try it. Don't list why you can't.
4. "이미지는 머메이드가 아니라 실제 PNG" — When user says "images in the article", they mean rendered PNGs (like Excalidraw exports), not inline diagrams.

## Related Skills & Files
- `content-pipeline` — older content pipeline (external sources), cross-reference only
- `~/.drewgent/scripts/wordpress-mcp-server.js` — WordPress MCP server
- `~/.drewgent/scripts/excalidraw-to-png.js` — Excalidraw → PNG converter
- `~/.drewgent/wordpress/docker-compose.yml` — WordPress Docker setup
- `~/.drewgent/wordpress/.wp-env` — credentials (chmod 600)
