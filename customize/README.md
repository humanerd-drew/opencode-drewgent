# Drewgent Customization Layer for Hermes

This directory contains code that **overrides** hermes-agent internals to make
hermes work for Drewgent's context (not the upstream generic hermes).

## How it works

1. `sitecustomize.py` runs at Python startup (when PYTHONPATH or `python -X` site loads it)
2. It inserts `~/.drewgent/customize/` to `sys.path[0]`
3. When hermes does `from hermes_cli.gateway import ...`, Python first checks
   `~/.drewgent/customize/hermes_cli/`
4. If a custom version exists, that wins; otherwise hermes's own loads

## Why this layer exists

Hermes's `get_launchd_label()` returns `ai.hermes.gateway` (hardcoded), but
Drewgent uses `ai.drewgent.gateway`. Override here so hermes's CLI sees the
right label for *this* environment.

## Activation

Two activation paths:
- **Gateway plist**: `EnvironmentVariables.PYTHONPATH=/Users/drew/.drewgent/customize`
- **Shell env** (for `hermes cron list` from terminal):
  `export PYTHONPATH=~/.drewgent/customize:$PYTHONPATH` in `~/.zshrc`

## Files in this layer

- `hermes_cli/__init__.py` — package marker
- `hermes_cli/gateway.py` — overrides hermes's gateway.py with our label logic
- `sitecustomize.py` — Python startup hook (auto-loads layer when on path)
