---

title: Pass Zero Secret Store
type: skill
space: outcome
tags: [outcome]
created: 2026-05-20
updated: 2026-05-22
links: []
links:
  - "[[P3-sensors/skills/SKILL-INDEX]]"
  - "[[P0-brainstem/brain/rules]]"---




# pass-zero — Secret Store Skill

Drewgent manages credentials using pass-zero: a GPG-free encrypted store.

## Architecture

```
~/.drewgent/.master_pass          ← Master key (NOT synced to cloud)
SynologyDrive-drewgent/drewgent/secrets/  ← Encrypted .enc files (synced)
  github/token.enc
  github/username.enc
  notion2web/notion-token.enc
  cloudflare/api-token.enc
  ...
```

## Core Commands

```bash
# Get a secret (used by agent internally)
python3 ~/Library/CloudStorage/SynologyDrive-drewgent/drewgent/secrets/pass-zero.py get <service> <key>

# Store a secret
python3 ~/Library/CloudStorage/SynologyDrive-drewgent/drewgent/secrets/pass-zero.py set <service> <key> "<value>"

# List services
python3 ~/Library/CloudStorage/SynologyDrive-drewgent/drewgent/secrets/pass-zero.py services

# List keys in a service
python3 ~/Library/CloudStorage/SynologyDrive-drewgent/drewgent/secrets/pass-zero.py list <service>
```

## Agent Behavior Rules

### When USER shares a credential:
1. IMMEDIATELY store it with `pass-zero set` — never in memory or logs
2. Never repeat the value back to the user
3. Acknowledge only that it's saved

### When agent needs a credential:
1. Retrieve it with `pass-zero get` at the moment of use
2. Use it directly in the command/API call
3. Never mention the value in the response

### Credential patterns that trigger auto-store:
- GitHub token, Notion token, Cloudflare API key
- Any `ghp_`, `ntc_`, `cf_` prefix
- Passwords, secrets, API keys mentioned in context

## Credential Rotation Workflow

When user provides a new credential (token, key, password) for an existing service:

### Step 1 — Store immediately
```bash
pass-zero set <service> <key> "<new_value>"
```

### Step 2 — Update config.yaml
Replace the credential value in `~/.drewgent/config.yaml` at the relevant path.

### Step 3 — Restart affected service
Restart the gateway or relevant service to apply the new credential.

### Discord Token Rotation Example (2026-05-22)

User provided new Discord bot token → token rotation completed:

1. **Store** — `pass-zero set discord token "MTQ3..."`
2. **Update** — `config.yaml` → `platforms.discord.token`
3. **Restart** — `launchctl stop ai.custom-agent.gateway && launchctl start ai.custom-agent.gateway`

### Credential Update Pattern

```python
# 1. Store in pass-zero (encrypted, synced)
pass-zero.py set <service> <key> "<new_value>"

# 2. Update config.yaml
config['platforms']['<service>']['token'] = "<new_value>"

# 3. Restart service
launchctl stop <label> && launchctl start <label>
```

## Related
- [[P3-sensors/skills/SKILL-INDEX]]
