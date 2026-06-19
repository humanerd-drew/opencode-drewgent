# M-LOG Secrets Management

## Secrets Storage Pattern

Secrets are stored in two places:

1. **`pass` password manager** — for recovery/human access
   - Store: `pass m-log/` (various keys)
   - Access: `pass show m-log/<key-name>`
2. **Cloudflare Worker secrets** — runtime only
   - Set via: `wrangler secret put <KEY_NAME>`
   - List: `npx wrangler secret list`
   - Values can NEVER be read back after being set (Cloudflare security feature)

## Secrets Required for m-log-v2

| Secret | Where to find | pass path |
|--------|--------------|-----------|
| `DEEPSEEK_API_KEY` | pass already has it | `pass m-log/deepseek-api-key` |
| `NAVER_CLIENT_SECRET` | Naver Developers Console → m-log app | Not in pass |
| `GOOGLE_CLIENT_SECRET` | Google Cloud Console → OAuth 2.0 credentials | Not in pass |
| `PORTONE_API_SECRET` | PortOne Console → Integration Info → API Secret | Not in pass |
| `SESSION_SECRET` | Generate with `openssl rand -hex 32` | Not in pass |

## Setting Secrets

```bash
# From pass (existing values)
pass show m-log/deepseek-api-key | wrangler secret put DEEPSEEK_API_KEY

# From stdin (paste or pipe)
echo "<value>" | wrangler secret put <KEY_NAME>

# For SESSION_SECRET (generate new)
SESSION_SECRET=$(openssl rand -hex 32) && echo "$SESSION_SECRET" | wrangler secret put SESSION_SECRET
```

## Non-Secrets (wrangler.jsonc vars, OK in git)

- `BASE_URL` — public
- `NAVER_CLIENT_ID` — OAuth client ID (public by design)
- `GOOGLE_CLIENT_ID` — OAuth client ID (public by design)
- `SAJU_API_ENDPOINT` — public API URL
- `PERSONA_API_ENDPOINT` — public API URL

## PortOne Client-Side Keys (public, hardcoded in PaymentPage.svelte)

- `storeId` — PortOne store identifier (public, needed by SDK)
- `channelKey` — Per-channel key for payment routing (public, needed by SDK)

## Pitfall: Secrets per Worker

Cloudflare secrets are scoped to a specific worker name (`name` field in `wrangler.jsonc`).
`m-log` and `m-log-v2` have SEPARATE secrets. You must re-set them for each worker.
