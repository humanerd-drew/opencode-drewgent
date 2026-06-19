# Discord Webhook Embed Limits

Production constraints that routinely cause 400 errors when exceeded.

## Hard Limits

| Field | Limit | Triggers |
|-------|-------|----------|
| Embeds per webhook | **10** max | 400 Bad Request |
| Embed title | 256 chars | truncated, not error |
| Embed description | 4096 chars | truncated, not error |
| Total payload | ~8MB | 413 / 400 |

## Common Pitfalls

- **Embed count > 10** — most common cause of 400. Paginate or truncate.
- **Empty embeds** — at least one of title/description/fields is required per embed.
- **Webhook URL stale** — deleted webhook returns 404, not 400.
- **Rate limit** — 5 POSTs per second per webhook, 429 response.

## Harvester Context

`harvester.py` `send_discord()` sends up to 10 embeds per webhook call. If you need more articles delivered, batch into multiple webhook calls (max 10 embeds per call) with a 1-second delay between calls.
