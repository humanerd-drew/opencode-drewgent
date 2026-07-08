---
name: drewgent-update-checker
description: "Auto-check Drewgent GitHub updates and notify via Discord or file. Sets up scheduled cron job."
version: 1.0.0
links:
  - "[[@identity/brain/rules]]"
---

# Drewgent Update Checker

Automatically checks for Drewgent updates from GitHub and notifies you.

## Overview

This skill sets up a cron job that periodically checks for Drewgent updates:
- **Checks**: Every 6 hours (configurable)
- **Notification**: Discord webhook (if configured) or status file
- **Auto-pull**: Optional (disabled by default)

## Setup

### 1. Enable Discord notifications (optional)

```bash
# Add to ~/.drewgent/.env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your/webhook
```

### 2. Activate this skill

```
/skill drewgent-update-checker
```

### 3. The skill will:
1. Create the update checker script in `~/.drewgent/scripts/`
2. Set up a cron job to run every 6 hours
3. Write status to `~/.drewgent/update_status.json`
4. Send Discord notification if updates are available

## Manual Commands

### Check for updates now
```bash
cd ~/.drewgent/drewgent-agent
python3 check_drewgent_update.py --status
```

### Check with Discord notification
```bash
python3 check_drewgent_update.py --notify
```

### Check and auto-pull
```bash
python3 check_drewgent_update.py --autopull
```

## Cron Management

### List update checker cron jobs
```bash
drewgent cron list | grep -i update
```

### Remove update checker
```bash
drewgent cron remove <job_id>
```

### Manual cron setup (if skill fails)
```bash
drewgent cron add "every 6h" "Check Drewgent updates" \
  --script ~/.drewgent/scripts/check_drewgent_update.py
```

## Output

### Status file: `~/.drewgent/update_status.json`
```json
{
  "timestamp": "2026-04-08T12:00:00",
  "status": "update_available",
  "behind": 3,
  "message": "Drewgent is 3 commit(s) behind. Consider updating!"
}
```

### Discord notification (when enabled)
- Green: Up to date
- Orange: Updates available
- Red: Error checking

## How It Works

1. **Cron trigger**: Drewgent scheduler runs the script every 6h
2. **Git check**: Uses `git fetch` + `git rev-list` to count commits behind
3. **Cache**: Results cached for 6 hours to avoid rate limiting
4. **Notify**: 
   - If `DISCORD_WEBHOOK_URL` set → sends Discord embed
   - Always writes to `update_status.json`
5. **You check**: Read Discord or file, decide whether to `git pull`

## Customization

### Change check frequency
Edit the cron schedule:
```bash
drewgent cron edit <job_id> --schedule "every 12h"
```

### Enable auto-pull (not recommended)
```bash
drewgent cron edit <job_id> --prompt "Check Drewgent updates" --append "--autopull"
```

## Files

- Script: `~/.drewgent/scripts/check_drewgent_update.py`
- Status: `~/.drewgent/update_status.json`
- Cron job: Stored in Drewgent's cron scheduler

## Related

- [[drewgent]] - Core Drewgent agent skill
- [[cron]] - Cron job management
