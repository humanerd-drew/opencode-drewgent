# pass (Unix Password Store) Setup on macOS

## When to Use

The user asks you to store API keys, tokens, or credentials using `pass`. This is common when they want secrets managed with GPG encryption rather than plaintext files.

## Quick Setup

### 1. Generate a GPG key (if none exists)

```bash
# Check existing keys
gpg --list-keys

# Batch-generate a no-passphrase key for pass use
cat > /tmp/gpg-batch.conf << 'EOF'
%no-protection
%transient-key
Key-Type: RSA
Key-Length: 2048
Name-Real: <name> pass
Name-Email: <email>
Expire-Date: 0
EOF
gpg --batch --generate-key /tmp/gpg-batch.conf
```

- `RSA` is safer for compatibility across GPG versions (ed25519 may fail on older GPG)
- `%no-protection` — no passphrase required (for terminal automation)
- `%transient-key` — no on-disk key storage beyond GPG's own DB
- `Expire-Date: 0` — no expiration

### 2. Initialize pass

```bash
KEYID=$(gpg --list-keys --with-colons 2>/dev/null | grep '^pub:' | cut -d: -f5)
pass init "$KEYID"
```

### 3. Store secrets

```bash
# Single-line secret
echo "sk-abc...xyz" | pass insert -m <path>/<name>

# Verify
pass show <path>/<name>
pass ls
```

## Naming Convention

Organize by project context:

```
Password Store
└── <project>/
    ├── deepseek-api-key
    ├── nvidia-nim-key
    ├── nvidia-nim-key-fallback
    └── nvidia-nim-key-fallback-2
```

**Avoid** generic names like `api-key` or `secret` — be specific enough that you can tell what the key is for at a glance next session.

## Common Pitfalls

- **`pass insert -m` reads from stdin, but it's interactive by default.** Use `echo "value" | pass insert -m <name>` to pipe. The `-m` flag (multi-line) accepts piped input.
- **GPG version compatibility:** macOS may have an older `gpg` from LibreSSL or a modern one from Homebrew. Check with `gpg --version`. If `ed25519` key type fails, fall back to `RSA`.
- **pass is not git-initialized by default.** The default `pass init` creates just a local password store. If the user wants git sync, they'd need `pass git init`.
- **No way to update a single key without re-inserting.** `pass insert` overwrites. There's no in-place edit.
