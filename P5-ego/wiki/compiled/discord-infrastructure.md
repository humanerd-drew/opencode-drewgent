---
title: Discord Infrastructure — Compiled
type: wiki-compiled
tags: [compiled, discord, bot, gateway, communication]
trigger: "wiki-compile 2026-06-21 — compiled from P2-hippocampus memories and cron records"
provenance:
  session: "2026-06-21 wiki-compile"
  decision: "Document Discord bot architecture, send pipeline, and token resilience"
created: 2026-06-21
updated: 2026-06-21
links:
  - "P5-ego/wiki/compiled/launchd-system"
  - "P5-ego/wiki/compiled/growth-engine"
  - "P5-ego/wiki/compiled/cron-operations"
---

# Discord Infrastructure — Compiled

## Core Decisions

### 1. Discord ↔ OpenCode Gateway Bot
**What:** `discord_bot.py` runs as launchd service (`ai.drewgent.discord-bot.plist`) with `--attach :8642`. Handles all Discord channels, creates threads, routes messages to opencode for processing.
**Why:** Discord is the primary user interface for Drewgent. The bot bridges Discord messages to opencode's headless agent.
**Alternatives considered:** Direct Discord API calls per channel, polling-based approach.
**Status:** Active. launchd KeepAlive with 10s restart.

### 2. Discord Message Send Script
**What:** `discord_send.py` handles message delivery with chunk splitting for long messages (Discord 2000-char limit per message). Used by all cron jobs for delivery.
**Why:** Standardized delivery ensures consistent formatting and handles edge cases (long messages, embeds).
**Status:** Active. All cron jobs use this for Discord delivery.

### 3. Token Resilience Protocol (3-Layer)
**What:** 3-layer defense against token reset → crash-loop:
- Layer 1: Discord adapter detects 401/LoginFailure → marks as `retryable=False` (no reconnect spam)
- Layer 2: Gateway continues running even when all platforms fail (cron still works)
- Layer 3: Startup failure exits with code 0 (launchd KeepAlive `SuccessfulExit: false` won't restart)
**Why:** Previous behavior: token reset → crash loop → launchd restart storm → cron dead for days.
**Alternatives considered:** No crash protection, auto-rotate tokens.
**Status:** Active since 2026-05-23.

### 4. MCP Discord Server
**What:** Discord MCP server at `~/.config/opencode/opencode.jsonc` provides 14 tools: send message, read history, search, reaction management, attachment download, presence management, friend management, DM channels.
**Why:** MCP tools give the agent direct Discord capabilities without going through the gateway.
**Status:** Active. Uses `discord-mcp` command.

### 5. Notification Pipeline (Cron → Discord)
**What:** All cron jobs deliver results to Discord channels via `discord_send.py`. Configurable per-job `deliver` field in `cron/jobs.json` specifies channel.
**Why:** Unified notification channel. User monitors Discord for system health and cron results.
**Status:** Active. Cron 60s tick + delivery to configured channels.

### 6. Channel Directory
**What:** `P3-sensors/channel_directory.json` and `discord_threads.json` track active channel configurations and thread metadata.
**Why:** Centralized channel management prevents hardcoded channel IDs in scripts.
**Status:** Active.

## Rationale
Discord is the primary notification and interaction channel. Bot architecture separates concerns: bot handles connectivity and message routing, send script handles formatting, token resilience prevents cascading failures.

## Current Status
All channels operational. Token resilience protocol active since 2026-05-23. Gateway bot under launchd management. MCP server provides direct agent access. Cron delivery pipeline functional.
