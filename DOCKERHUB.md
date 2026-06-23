---

title: Dockerhub
type: guide
space: concept
tags: [concept]
created: 2026-05-20
updated: 2026-05-20
links: []
links:
  - "[[P5-ego/SELF_MODEL]]"
---


# Drewgent on Docker Hub

**Docker Images:**
- `humanerdkr/drewgent:latest` - Gateway + Agent
- `humanerdkr/drewgent-monitor:latest` - Discord Monitor

## Quick Start

```bash
mkdir -p data
# Create .env with API keys

docker-compose up -d
```

## docker-compose.yml

See main README.md for full configuration.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `MINIMAX_API_KEY` | MiniMax API key |
| `DREW_DISCORD_WEBHOOK` | Discord webhook for monitor |

## Monitor

The monitor container sends hourly reports to Discord. Set `DREW_DISCORD_WEBHOOK` environment variable.
