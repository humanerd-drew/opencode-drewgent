---
title: Project Code Audit
name: project-code-audit
description: Systematic methodology for analyzing a project's file structure, mapping dependency graphs, identifying dead/orphan code, and removing it safely with local verification.
type: skill
space: outcome
tags: [audit, refactoring, cleanup, dead-code, methodology]
created: 2026-06-10
links:
  - "[[software-development/requesting-code-review]]"
  - "[[software-development/codebase-refactoring]]"
  - "[[software-development/codebase-structure-audit]]"
  - "[[software-development/codebase-consolidation]]"
  - "[[software-development/incremental-refactoring]]"
  - "[[@identity/brain/rules]]"
---

# Project Code Audit — Dead Code Detection & Safe Cleanup

## When to Use

- User asks to "clean up", "remove unused files", or "audit the project"
- Before a refactoring push — first understand what's actually alive
- When you encounter files that "look unused" — verify systematically, don't guess
- When the project has no clear file ownership map
- **Always check for AGENTS.md first** — if one exists, read it before any audit step

## Core Principle

**Incremental + Verified.** Never delete in bulk without testing. Change one thing, verify it works, move to the next. A big-bang cleanup is a big-bang breakage risk.

*This user prefers incremental, test-each-step changes. Start with zero-risk deletions, test immediately, only then discuss medium-risk restructuring.*

## Step 0 — AGENTS.md (Project Navigation Map)

**Before any audit, create or read AGENTS.md.** This is the single file every AI agent reads first to understand the project.

### What AGENTS.md contains

- Directory structure overview (depth 2-3)
- File naming convention (e.g. verb-noun.kebab-case.ts)
- "What to search for" table — maps user intent to file paths
- Current migration status (what's done, what's pending)

### When to create one

- Project has no clear structure documentation
- You're about to do a multi-phase restructuring
- You found yourself searching for files by guessing names
- User complained about "not being able to find things"

### AGENTS.md template

```
# Project Agent Map

> Read this first. Defines directory structure, file naming, and navigation.

## Directory structure
src/
├── domain-a/    (what this contains)
├── domain-b/    (what this contains)
├── api/         (thin route layer)
└── utils/       (shared utilities)

## File naming
- `verb-noun.kebab-case.ts` — search by verb first
- Example: `verify-payment.ts`, `get-daewoon.ts`, `oauth-naver.ts`

## Quick lookup
| Search term | File |
|---|---|
| login/oauth | src/user/oauth-*.ts |
| payment verify | src/payment/verify-payment.ts |

## Current status
- ✅ Phase completed
- 🚧 Phase in progress
- ⬜ Phase planned
```

### Placement
- **Project root**: `./AGENTS.md`
- **Subdirectory**: `./src/AGENTS.md` for large monorepos

This skill's Steps 1-5 assume AGENTS.md has already been consulted as the orientation step.

## Core Principle

**Incremental + Verified.** Never delete in bulk without testing. Change one thing, verify it works, move to the next. A big-bang cleanup is a big-bang breakage risk.

*This user prefers incremental, test-each-step changes. Start with zero-risk deletions, test immediately, only then discuss medium-risk restructuring.*

## Step 1 — Map Every Source File

```bash
find . -type f \( -name '*.ts' -o -name '*.js' -o -name '*.html' -o -name '*.css' \
  -o -name '*.json' -o -name '*.sql' \) \
  -not -path './node_modules/*' -not -path './dist/*' -not -path './.git/*' \
  -not -path './build/*' | sort
```

Group by layer: backend, frontend SPA, CSS, migrations, config, templates.

## Step 2 — Trace Every Import and Reference

Three parallel grep passes:

```bash
# JS/TS imports
grep -rn "import " --include='*.ts' --include='*.js' \
  --exclude-dir=node_modules --exclude-dir=dist . | sort

# HTML resource references (scripts, stylesheets, images)
grep -rn 'src=\|href=' --include='*.html' \
  --exclude-dir=node_modules . | sort

# CSS @import chains
grep -rn '@import' --include='*.css' \
  --exclude-dir=node_modules . | sort
```

Cross-reference: for each candidate dead file, search its basename across ALL source:

```bash
grep -rn "suspected-file" --include='*.{ts,js,html,css}' --exclude-dir=node_modules .
```

**Zero references across all three passes = dead code.**

## Step 3 — Classify Dead Code by Risk

| Type | Signal | Risk | Action |
|------|--------|------|--------|
| Orphan file | Nobody imports it | Zero | `rm` directly |
| Duplicate resource | Same file loaded two ways (HTML+CSS) | Zero | Remove one reference |
| Dead config key | Defined but never read | Zero | `patch` it out |
| Unused mock data | DEV fixture in source tree | Zero | Delete |
| Duplicate module | Two files exporting same data | Low | Merge + update imports |
| Legacy route | Handler exists, no UI links to it | Low | Comment out, verify |

## Step 4 — Remove & Verify

### Zero-risk (can batch):
```bash
rm -v orphan1.ts orphan2.js
# Use patch to remove duplicate HTML/CSS references
```

Restart dev server and verify entry points immediately after the batch.

### Low-risk (one at a time):
1. Make change → restart → test → next

## Step 5 — HTTP Verification

```bash
# Start dev server
npm run dev &
sleep 8

# Check entry points
for path in "/" "/app/" "/other"; do
  echo -n "$path => "; curl -sSL -o /dev/null -w "%{http_code}" "http://localhost:8787$path"; echo
done

# Verify deleted files return 404
curl -sSL -o /dev/null -w "%{http_code}" "http://localhost:8787/path/to/deleted.js"

# Verify remaining modules resolve
for mod in "app.js" "utils.js" "style.css"; do
  echo -n "/$mod => "; curl -sSL -o /dev/null -w "%{http_code}" "http://localhost:8787/$mod"; echo
done
```

## Common Pitfalls

- **`curl -s` vs `-sSL`**: Dev servers redirect `/path` to `/path/`. Without `-L` you get 307, not content.
- **ESM imports need `./` prefix**: `from './module.js'` works; bare `from 'module.js'` resolves differently.
- **CSS loaded twice**: Check BOTH `<link>` in HTML AND `@import` in CSS — same file may load via both.
- **Synology Drive corrupts symlinks**: `node_modules/.bin/*` may be XSym metadata stubs. Run `file` to detect.
- **Cache-busting `?v=` params**: Cross-reference by filename, not URL — they may mask CSS source identity.

## Related

- [[software-development/requesting-code-review]] — pre-commit git-diff verification (complementary; this skill is for existing-project analysis)
