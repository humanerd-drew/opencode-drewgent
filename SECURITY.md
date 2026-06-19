---
title: Security
type: guide
space: concept
tags: [concept, security]
---

# Security Policy

## Reporting a Vulnerability

This repo contains **configuration and tooling** — agent profiles, skills, scripts. It does not handle user data directly, but it does orchestrate LLM calls and file operations.

**If you find a security issue:**

1. **Do not open a public issue.**
2. Email the maintainer at the address listed in the git commit history.
3. Provide a clear description, reproduction steps, and impact assessment.

## What We Consider a Vulnerability

- Prompt injection paths that could leak API keys or secrets
- Shell injection via agent tool calls
- Unauthorized file access through agent operations
- Exposure of credentials in logs or error messages
- Bypass of P0-brainstem governance rules (`禁` neurons)

## What Is NOT a Vulnerability

- The agent making a mistake in its reasoning
- A skill producing incorrect output for a specific input
- Missing documentation
- Not supporting a particular LLM provider

## Response Timeline

- **CRITICAL**: 24 hours to acknowledge, 7 days to fix
- **HIGH**: 48 hours to acknowledge, 14 days to fix
- **MEDIUM/LOW**: Next release cycle

## Security Practices

- API keys go in `.env` (gitignored), never in committed files
- P0-brainstem rules actively block common vulnerability patterns
- `禁secrets_in_code` detects and blocks hardcoded credentials
- All runtime databases are gitignored by default
