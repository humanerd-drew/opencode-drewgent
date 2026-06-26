---
name: teams-meeting-pipeline
description: "Operate the Teams meeting summary pipeline via Hermes CLI — summarize meetings, inspect pipeline status, replay jobs, manage Microsoft Graph subscriptions."
version: 1.1.0
author: Hermes Agent + Teknium
license: MIT
prerequisites:
  env_vars: [MSGRAPH_TENANT_ID, MSGRAPH_CLIENT_ID, MSGRAPH_CLIENT_SECRET]
  commands: [hermes]
metadata:
  hermes:
    tags: [Teams, Microsoft Graph, Meetings, Productivity, Operations]
    related_docs:
      - /docs/guides/microsoft-graph-app-registration
      - /docs/user-guide/messaging/teams-meetings
      - /docs/guides/operate-teams-meeting-pipeline
links:
  - "[[@identity/brain/rules]]"
links:
  - "[[@action/skills/SKILL-INDEX]]"
  - "[[@identity/brain/rules]]"
---

# Teams Meeting Pipeline

Use this skill whenever the user asks about Microsoft Teams meeting summaries, transcripts, recordings, action items, Graph subscriptions, or any operational question about the Teams meeting pipeline. Works in any language — the triggers below are examples, not an exhaustive list.

Everything operator-facing was a `hermes teams-pipeline` subcommand run via the terminal tool. **Note:** The hermes CLI has been removed from the system. These subcommands are no longer available. The pipeline functionality may still exist through direct script execution in `~/.drewgent/scripts/`.

## When to use this skill

The user is asking to:
- summarize a Teams meeting / extract action items / pull meeting notes
- check pipeline status, inspect a stored meeting job, or see recent meetings
- replay / re-run a stored job that failed or needs a fresh summary
- validate Microsoft Graph setup after changing env or config
- troubleshoot "meeting summary never arrived" or "no new meetings are ingesting"
- manage Graph webhook subscriptions (create, renew, delete, inspect)
- set up automated subscription renewal (see pitfall below)

Multilingual trigger examples (not exhaustive):
- English: "summarize the Teams meeting", "pipeline status", "replay job X"
- Turkish: "Teams meeting özetle", "action item çıkar", "toplantı notu", "pipeline durumu", "replay job"

## Prerequisites

Before using the pipeline, verify these are set in `~/.hermes/.env`:

```bash
MSGRAPH_TENANT_ID=...
MSGRAPH_CLIENT_ID=...
MSGRAPH_CLIENT_SECRET=...
```

If any are missing, direct the user to the Azure app registration guide at `/docs/guides/microsoft-graph-app-registration` — they need an Azure AD app registration with admin-consented Graph application permissions before the pipeline will work.

## Command reference (DEPRECATED — hermes CLI removed)

The following `hermes teams-pipeline` subcommands were previously available but are no longer accessible since the hermes CLI was removed. The underlying pipeline scripts may still be usable directly.

### Status and inspection (start here)

```bash
# These commands no longer work — hermes CLI removed
# hermes teams-pipeline validate              # config snapshot
# hermes teams-pipeline token-health          # Graph token status
# hermes teams-pipeline list                  # recent meeting jobs
# hermes teams-pipeline show <job-id>         # full detail of one job
# hermes teams-pipeline subscriptions         # current Graph webhook subscriptions
```

### Re-running / debugging

```bash
# hermes teams-pipeline run <job-id>          # replay a stored job
# hermes teams-pipeline fetch --meeting-id <id>   # dry-run
```

### Subscription management

```bash
# hermes teams-pipeline subscribe ...
# hermes teams-pipeline renew-subscription <sub-id> --expiration <iso-8601>
# hermes teams-pipeline delete-subscription <sub-id>
# hermes teams-pipeline maintain-subscriptions
```

## Decision tree for common asks

> **Note:** The hermes CLI has been removed. The commands referenced below (`list`, `show`, `subscriptions`, etc.) were hermes subcommands and are no longer available. Check `~/.drewgent/scripts/` for any standalone pipeline scripts.

- User asks "why didn't I get a summary for today's meeting?" → check pipeline logs and job status files.
- User asks "is setup working?" → check Graph token status and subscription files.
- User asks "re-run summary for meeting X" → check for replay scripts.
- User asks "add meeting X to the pipeline" → usually you don't — the pipeline is subscription-driven, not per-meeting.

## Critical pitfall: Graph subscriptions expire in 72 hours

Microsoft Graph caps webhook subscriptions at 72 hours and **will not auto-renew them**. If `maintain-subscriptions` is not scheduled, meeting notifications silently stop arriving 3 days after any manual subscription creation.

When the user reports "the pipeline worked yesterday but nothing is arriving today":
1. Check subscription status files — if all entries show `expirationDateTime` in the past, that's the cause.
2. Recreate subscriptions via the Graph API directly or through available scripts.
3. **Set up automated renewal immediately** via launchd cron, a systemd timer, or plain crontab. The operator runbook at `/docs/guides/operate-teams-meeting-pipeline#automating-subscription-renewal-required-for-production` has all three options. 12-hour interval is safe (6x headroom against the 72h limit).

## Other pitfalls

- **Transcript not available yet.** Teams takes some time after a meeting ends to generate the transcript artifact. `fetch --meeting-id` on a just-ended meeting may return empty. Wait 2-5 minutes and retry, or let the Graph webhook drive ingestion naturally.
- **Delivery mode mismatch.** If summaries are produced (`list` shows success) but nothing lands in Teams, check `platforms.teams.extra.delivery_mode` and the matching target config (`incoming_webhook_url` OR `chat_id` OR `team_id`+`channel_id`). The writer reads these from config.yaml or `TEAMS_*` env vars.
- **Graph app permissions.** A token acquires cleanly (`token-health` passes) but Graph API calls return 401/403 when permissions were added but admin consent wasn't re-granted. Have the user revisit the app registration in the Azure portal and click "Grant admin consent" again.

## Related docs

Point the user to these when they need more depth than this skill covers:
- Azure app registration walkthrough: `/docs/guides/microsoft-graph-app-registration`
- Full pipeline setup: `/docs/user-guide/messaging/teams-meetings`
- Operator runbook (renewal automation, troubleshooting, go-live checklist): `/docs/guides/operate-teams-meeting-pipeline`
- Webhook listener setup: `/docs/user-guide/messaging/msgraph-webhook`
