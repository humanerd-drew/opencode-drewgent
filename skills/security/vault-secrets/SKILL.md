---
title: vault-secrets
trigger: "User provides an API key, token, or any secret value — store it encrypted, never in plaintext"
provenance:
  session: "2026-07-01 vault-system"
  decision: "keyring (OS-native) + Fernet (cross-platform). vault_cli.py in scripts/, skill in skills/security/. Template-included for {{AGENT_NAME_LOWER}} installs."
created: 2026-07-01
---

# Vault Secrets — {{AGENT_NAME}} Encrypted Secrets Manager

## Core Rule

**Never write a secret to disk in plaintext. Ever.**

When a user gives you an API key, token, password, or any sensitive value:

1. Do NOT write it to `.zshrc`, `opencode.jsonc`, `.env`, or any file
2. Do NOT `echo "export KEY=VALUE" >> .zshrc`
3. Use `vault set KEY_NAME <value>` immediately

## Usage

```bash
# Store a key (from stdin for safety)
echo "$API_KEY" | vault set OPENAI_API_KEY

# Or pass as argument (visible in process list)
vault set DISCORD_TOKEN "MT..."

# Retrieve for debugging
vault get OPENAI_API_KEY

# List all stored keys
vault list

# Delete
vault delete OPENAI_API_KEY
```

## Shell Integration

`.zshrc` / `$PROFILE` should have:

```zsh
eval "$(python3 ~/.{{AGENT_NAME_LOWER}}/scripts/vault_cli.py env 2>/dev/null)" || true
```

This decrypts all keys at shell login. `opencode.jsonc` references them via `{env:KEY_NAME}`.

## Config File Rules

- `opencode.jsonc`: use `{env:KEY_NAME}` syntax, never hardcode values
- `.zshrc` / shell rc: use vault hook, never `export KEY=VALUE`
- `.env`: never commit, never store real secrets — use vault

## Setup for New Installs

```bash
pip install cryptography keyring
python3 ~/.{{AGENT_NAME_LOWER}}/scripts/vault_cli.py init
vault scan   # find existing plaintext keys
vault migrate  # encrypt & replace with {env:VAR}
```

## Cross-Platform

| Layer | macOS | Windows | Linux |
|-------|-------|---------|-------|
| Keyring | Keychain | Credential Manager | libsecret |
| File | `vault.enc` | `vault.enc` | `vault.enc` |
| Shell hook | `.zshrc` | `$PROFILE` | `.bashrc` |
| opencode ref | `{env:VAR}` | `{env:VAR}` | `{env:VAR}` |
