#!/usr/bin/env python3
"""vault — cross-platform encrypted secrets manager for {{AGENT_NAME}}.

Usage:
  vault init              Create master key in OS keyring
  vault set KEY [VALUE]   Encrypt & store (VALUE from arg or stdin)
  vault get KEY           Decrypt & print to stdout (never logs)
  vault list              List stored keys
  vault delete KEY        Remove a key
  vault env               Print shell export statements
  vault scan              Find plaintext keys in config files
  vault migrate [--dry-run]  Scan → encrypt → replace with {env:VAR}
"""

import argparse
import base64
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

# Discover additional site-packages from brew/manual installs
import site as _site
_stdlib_sitepkgs = _site.getusersitepackages()
# Also try common alternative paths
for _alt in ["/opt/homebrew/lib/python3.14/site-packages"]:
    _p = Path(_alt)
    if _p.exists() and str(_p) != _stdlib_sitepkgs and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

try:
    from cryptography.fernet import Fernet
except ImportError:
    sys.exit("cryptography not installed. Run: pip install cryptography")

VAULT_DIR = Path.home() / ".config" / "{{AGENT_NAME_LOWER}}"
VAULT_FILE = VAULT_DIR / "vault.enc"
KEYRING_SERVICE = "{{AGENT_NAME_LOWER}}-vault"


def _ensure_dir():
    VAULT_DIR.mkdir(parents=True, exist_ok=True)


def _vault_path():
    return VAULT_FILE


def _get_master_key():
    try:
        import keyring
        key = keyring.get_password(KEYRING_SERVICE, "master")
        if key:
            return key
    except Exception:
        pass
    # Fallback: file-based key
    fallback = VAULT_DIR / "vault.key"
    if fallback.exists():
        return fallback.read_text().strip()
    return None


def _set_master_key(key):
    try:
        import keyring
        keyring.set_password(KEYRING_SERVICE, "master", key)
        return
    except Exception:
        pass
    fallback = VAULT_DIR / "vault.key"
    fallback.write_text(key)
    fallback.chmod(0o600)


def _load_vault():
    path = _vault_path()
    if not path.exists():
        return {}
    key = _get_master_key()
    if not key:
        return {}
    f = Fernet(key.encode() if isinstance(key, str) and not key.endswith("=") else key.encode())
    return json.loads(f.decrypt(path.read_bytes()).decode())


def _save_vault(data):
    path = _vault_path()
    key = _get_master_key()
    if not key:
        sys.exit("No master key found. Run 'vault init' first.")
    f = Fernet(key.encode() if isinstance(key, str) and not key.endswith("=") else key.encode())
    path.write_bytes(f.encrypt(json.dumps(data, indent=2).encode()))
    path.chmod(0o600)


# ---- Commands ----

def cmd_init():
    _ensure_dir()
    existing = _get_master_key()
    if existing:
        # Verify existing key works
        try:
            Fernet(existing.encode())
            print("Vault already initialized. Master key exists.")
            return
        except Exception:
            pass
    raw = os.urandom(32)
    key = base64.urlsafe_b64encode(raw).decode()
    _set_master_key(key)
    if not _vault_path().exists():
        _save_vault({})
    print("Vault initialized. Master key stored in OS keyring.")


def cmd_set(key_name, value=None):
    _ensure_dir()
    if value is None:
        value = sys.stdin.read().strip()
    data = _load_vault()
    data[key_name] = value
    _save_vault(data)
    print(f"vault: stored {key_name}")


def cmd_get(key_name):
    data = _load_vault()
    val = data.get(key_name)
    if val is None:
        sys.exit(f"vault: key not found: {key_name}")
    print(val, end="" if val.endswith("\n") else "\n")


def cmd_list():
    data = _load_vault()
    for k in sorted(data.keys()):
        print(k)


def cmd_delete(key_name):
    data = _load_vault()
    if key_name not in data:
        sys.exit(f"vault: key not found: {key_name}")
    del data[key_name]
    _save_vault(data)
    print(f"vault: deleted {key_name}")


def cmd_env():
    data = _load_vault()
    for k, v in sorted(data.items()):
        escaped = shlex.quote(v)
        print(f"export {k}={escaped}")


SECRET_PATTERNS = [
    re.compile(r'(export\s+(\w+)=["\']?([^"\'\n#]+))', re.M),
    re.compile(r'"(DISCORD_TOKEN|OPENCODE_API_KEY|OPENAI_API_KEY|ANTHROPIC_API_KEY|GROQ_API_KEY|MINIMAX_API_KEY|LAZYWEB_API_KEY|_[A-Z_]+KEY[A-Z_]*|_[A-Z_]+TOKEN[A-Z_]*)":\s*"([^"]+)"'),
    re.compile(r'(?<!")([A-Z][A-Z0-9_]+(?:KEY|TOKEN|SECRET|API_KEY|PASSWORD))=(.+)$', re.M),
]

SCAN_PATHS = [
    Path.home() / ".zshrc",
    Path.home() / ".bashrc",
    Path.home() / ".bash_profile",
    Path.home() / ".profile",
    Path.home() / ".config" / "opencode" / "opencode.jsonc",
    Path.home() / ".config" / "opencode" / "opencode.json",
]

def _resolve_patterns(content, patterns):
    found = []
    for pattern in patterns:
        for m in pattern.finditer(content):
            if len(m.groups()) >= 2:
                key = m.group(2) if len(m.groups()) > 1 else m.group(1)
                val = m.group(len(m.groups()))  # last group = value
                # Heuristic: skip obvious non-secrets
                if len(val) < 8 or re.match(r'^(true|false|yes|no|\d+)$', val, re.I):
                    continue
                found.append((key, val, pattern))
    return found


def cmd_scan():
    found_any = False
    for path in SCAN_PATHS:
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        matches = _resolve_patterns(content, SECRET_PATTERNS)
        if matches:
            found_any = True
            print(f"\n=== {path} ===")
            for key, val, _ in matches:
                masked = val[:6] + "..." + val[-4:] if len(val) > 12 else "***"
                print(f"  {key} = {masked}")
    if not found_any:
        print("No plaintext secrets found.")


REPLACE_PATTERNS = [
    (re.compile(r'export\s+(DISCORD_TOKEN|OPENCODE_API_KEY|OPENAI_API_KEY|ANTHROPIC_API_KEY|GROQ_API_KEY|MINIMAX_API_KEY|LAZYWEB_API_KEY|_[A-Z_]+KEY[A-Z_]*|_[A-Z_]+TOKEN[A-Z_]*)="?([^"\'\n#]+)"?'), True),
    (re.compile(r'"(DISCORD_TOKEN|OPENCODE_API_KEY|OPENAI_API_KEY|ANTHROPIC_API_KEY|GROQ_API_KEY|MINIMAX_API_KEY|LAZYWEB_API_KEY|[a-zA-Z_]+(?:KEY|TOKEN|API_KEY))":\s*"([^"]+)"'), False),
]


def cmd_migrate(dry_run=False):
    vault_data = _load_vault()
    modified_files = []

    for path in SCAN_PATHS:
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        original = content
        matches = _resolve_patterns(content, SECRET_PATTERNS)
        if not matches:
            continue

        for key, val, _ in matches:
            # Likely already migrated or non-secret
            if val.startswith("{env:") or val.startswith("$env:") or val.startswith("$"):
                continue
            if key not in vault_data:
                vault_data[key] = val

            # Replace in content
            if path.suffix in (".jsonc", ".json"):
                old = f'"{key}": "{val}"'
                new = f'"{key}": "{{env:{key}}}"'
                content = content.replace(old, new)
            elif path.suffix in (".zshrc", ".bashrc", ".bash_profile", ".profile", ""):
                # Shell file — remove or comment out the export
                for line in content.split("\n"):
                    stripped = line.strip()
                    if re.match(rf'^export\s+{re.escape(key)}\b', stripped):
                        if not stripped.startswith("#"):
                            content = content.replace(line, f"# {line}  # migrated to vault")
                            break

        if content != original:
            modified_files.append((path, content))

    _save_vault(vault_data)

    if dry_run:
        print("DRY RUN — would modify:")
        for path, new_content in modified_files:
            print(f"  {path}")
        return

    for path, new_content in modified_files:
        path.write_text(new_content)
        print(f"  migrated: {path}")

    print(f"\nVault now has {len(vault_data)} keys.")


def cmd_status():
    key = _get_master_key()
    if key:
        print(f"Master key: {'✓ found' if key else '✗ missing'}")
        vault = _vault_path()
        if vault.exists():
            data = json.loads(Fernet(key.encode()).decrypt(vault.read_bytes()).decode())
            print(f"Vault file:  ✓ {vault} ({len(data)} keys)")
            for k in sorted(data.keys()):
                print(f"  - {k}")
        else:
            print("Vault file:  ✗ not found")
    else:
        print("Master key: ✗ missing (run 'vault init')")
    print(f"Keyring:     {'keyring' if _has_keyring() else 'file fallback'}")


def _has_keyring():
    try:
        import keyring
        return True
    except ImportError:
        return False


def main():
    parser = argparse.ArgumentParser(description="{{AGENT_NAME}} vault — encrypted secrets manager")
    parser.add_argument("command", choices=["init", "set", "get", "list", "delete", "env", "scan", "migrate", "status"])
    parser.add_argument("args", nargs="*", help="key [value]")
    parser.add_argument("--dry-run", action="store_true", help="For migrate: preview only")
    args = parser.parse_args()

    if args.command == "init":
        cmd_init()
    elif args.command == "status":
        cmd_status()
    elif args.command == "scan":
        cmd_scan()
    elif args.command == "list":
        cmd_list()
    elif args.command == "env":
        cmd_env()
    elif args.command == "migrate":
        cmd_migrate(dry_run=args.dry_run)
    elif args.command == "set":
        if len(args.args) < 1:
            sys.exit("Usage: vault set KEY [VALUE]")
        cmd_set(args.args[0], args.args[1] if len(args.args) > 1 else None)
    elif args.command == "get":
        if len(args.args) < 1:
            sys.exit("Usage: vault get KEY")
        cmd_get(args.args[0])
    elif args.command == "delete":
        if len(args.args) < 1:
            sys.exit("Usage: vault delete KEY")
        cmd_delete(args.args[0])


if __name__ == "__main__":
    main()
