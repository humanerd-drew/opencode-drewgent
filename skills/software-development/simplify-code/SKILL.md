---
name: simplify-code
description: "Parallel 3-agent cleanup of recent code changes."
version: 1.0.0
author: Hermes Agent (inspired by Claude Code /simplify)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [code-review, cleanup, refactor, delegation, subagent, parallel, simplify]
    related_skills: [requesting-code-review, test-driven-development, plan]
links:
  - "[[P3-sensors/skills/SKILL-INDEX]]"
  - "[[software-development/codebase-refactoring]]"
  - "[[software-development/incremental-refactoring]]"
  - "[[software-development/requesting-code-review]]"
  - "[[software-development/test-driven-development]]"
  - "[[software-development/plan]]"
  - "[[P0-brainstem/brain/rules]]"
---

# Simplify Code — Parallel Review & Cleanup

Review your recent code changes with three focused reviewers running in
parallel, aggregate their findings, and apply the fixes worth applying.

**Core principle:** Three narrow reviewers beat one broad reviewer. Each one
deeply searches the codebase for a single class of problem — reuse, quality,
efficiency — without diluting its attention across all three. They run
concurrently, so you pay the latency of one review, not three.

## When to Use

Trigger this skill when the user says any of:

- "simplify" / "simplify my changes" / "simplify these changes"
- "review my code" / "review my recent changes" / "clean up my changes"
- "/simplify" (if they're carrying the Claude Code habit over)

Optional modifiers the user may add — honor them:

- **Focus:** "simplify focus on efficiency" → run only the efficiency reviewer
  (or weight the aggregation toward it). Recognized focuses: `reuse`,
  `quality`, `efficiency`.
- **Dry run:** "simplify but don't change anything" / "just report" → run the
  three reviewers, present findings, apply NOTHING. Ask before applying.
- **Scope:** "simplify the last commit" / "simplify staged" / "simplify
  src/foo.py" → narrow the diff source accordingly (see Phase 1).

Do NOT auto-run this after every edit. It costs three subagents' worth of
tokens — invoke it only when the user explicitly asks.

## The Process

### Phase 1 — Identify the changes

Capture the diff to review. Pick the source by what the user asked for, in
this default order:

```bash
# 1. Default: uncommitted working-tree changes (tracked files)
git diff

# 2. If that's empty, include staged changes
git diff HEAD

# 3. Scoped variants the user may request:
git diff --staged                 # "staged changes"
git diff HEAD~1                    # "the last commit"
git diff main...HEAD              # "this branch" / "my PR"
git diff -- src/foo.py            # specific file(s)
```

If `git diff` and `git diff HEAD` are both empty and there's no git repo or no
changes, fall back to the files the user explicitly named or that were
recently created/edited in this session. If you genuinely can't find any
changed code, say so and stop — there's nothing to simplify.

Capture the full diff text. Note its size: if it's very large (say >2000
changed lines), warn the user that three subagents each carrying the full diff
will be token-heavy, and offer to scope it down (per-directory, per-commit)
before proceeding.

### Phase 2 — Launch three reviewers in parallel

Use `delegate_task` **batch mode** — pass all three tasks in one `tasks`
array so they run concurrently. Three is the right fan-out for this pattern;
it's well within the `delegation.max_concurrent_children` budget on any
default install.

Give **every** reviewer the **complete diff** (not fragments — cross-file
issues hide in the gaps) plus the absolute repo path so they can search the
wider codebase. Each reviewer gets `terminal`, `file`, and `search`
toolsets (so they can `git`, `read_file`, and `search_files`/grep).

Tell each reviewer to:
- Search the existing codebase for evidence (don't reason from the diff alone).
- Report findings as a concrete list: `file:line → problem → suggested fix`.
- Rank each finding `high` / `medium` / `low` confidence.
- Skip nits and style-only churn. Only flag things that materially improve
  the code.

Pass these three goals (drop any the user's focus excludes):

**Reviewer 1 — Code Reuse**
> Review this diff for code that duplicates functionality already in the
> codebase. Search utility modules, shared helpers, and adjacent files
> (use search_files / grep) for existing functions, constants, or patterns
> the new code could call instead of reimplementing. Flag: new functions
> that duplicate existing ones; hand-rolled logic that an existing utility
> already does (manual string/path manipulation, custom env checks, ad-hoc
> type guards, re-implemented parsing). For each, name the existing thing to
> use and where it lives.

**Reviewer 2 — Code Quality**
> Review this diff for quality problems. Look for: redundant state (values
> that duplicate or could be derived from existing state; caches that don't
> need to exist); parameter sprawl (new params bolted on where the function
> should have been restructured); copy-paste-with-variation (near-duplicate
> blocks that should share an abstraction); leaky abstractions (exposing
> internals, breaking an existing encapsulation boundary); stringly-typed
> code (raw strings where a constant/enum/registry already exists — check the
> canonical registries before flagging). For each, give the concrete refactor.

**Reviewer 3 — Efficiency**
> Review this diff for efficiency problems. Look for: unnecessary work
> (redundant computation, repeated file reads, duplicate API calls, N+1
> access patterns); missed concurrency (independent ops run sequentially);
> hot-path bloat (heavy/blocking work on startup or per-request paths);
> TOCTOU anti-patterns (existence pre-checks before an op instead of doing
> the op and handling the error); memory issues (unbounded growth, missing
> cleanup, listener/handle leaks); overly broad reads (loading whole files
> when a slice would do). For each, give the concrete fix and why it's faster
> or lighter.

### Phase 3 — Aggregate and apply

Wait for all three to return (batch mode returns them together).

1. **Merge** the findings into one list, deduping where reviewers overlap.
2. **Discard false positives** — you have the most context; you don't have to
   argue with a reviewer, just drop weak or wrong suggestions silently.
3. **Resolve conflicts.** Reviewers can disagree (Reviewer 1: "use existing
   util X"; Reviewer 3: "X is slow, inline it"). Default resolution order:
   **correctness > the user's stated focus > readability/reuse > micro-perf.**
   Don't apply a perf "fix" that hurts clarity unless the path is genuinely
   hot. When two suggestions are mutually exclusive and both defensible, pick
   the one that touches less code and note the alternative.
4. **Apply** the surviving fixes directly with `patch` / `write_file` — unless
   the user asked for a dry run, in which case present the list and ask first.
5. **Verify** you didn't break anything: run the project's targeted tests for
   the touched files (not the full suite), and re-run any linter/type check the
   repo uses. If a fix breaks a test, revert that one fix and report it.
6. **Summarize** what you changed: a short list of applied fixes grouped by
   reviewer category, plus any findings you deliberately skipped and why.

## Pitfalls

- **Don't fan out wider than ~3.** More reviewers means more cost and more
  conflicting suggestions to reconcile, not better coverage. Three categories
  cover the space.
- **Give the WHOLE diff to each reviewer.** Splitting the diff across reviewers
  defeats the design — cross-file duplication and N+1s only show up with the
  full picture.
- **Reviewers search, they don't guess.** A reuse finding with no pointer to
  the existing utility ("there's probably a helper for this") is noise. Require
  `file:line` evidence; drop findings that lack it.
- **Apply ≠ rewrite.** This is cleanup of the user's recent changes, not a
  license to refactor the whole module. Keep edits scoped to what the diff
  touched plus the minimal surrounding change a fix requires.
- **Respect project conventions.** If the repo has AGENTS.md / CLAUDE.md /
  HERMES.md or a linter config, fold those rules into the reviewer prompts so
  suggestions match house style instead of fighting it.
- **Large diffs blow context.** If the diff is huge, scope it down before
  delegating — three subagents each carrying a 5000-line diff is expensive and
  may truncate.

## Related

If your install has the `subagent-driven-development` skill (optional), it
covers the complementary case: parallel review *during* implementation, per
task. This skill is the standalone *after-the-fact* cleanup pass. Use
`requesting-code-review` for the pre-commit security/quality gate.

## Incremental approach

When the user prefers ONE-BY-ONE refactoring (e.g. says "하나씩") instead of
parallel review, switch to the incremental approach:

1. **Keep the dev server running.** Start or verify the dev server is live
   (npm run dev, wrangler dev, etc.). Test after each individual change.
   *   For wrangler dev: redirect output to a log file
       (`> /tmp/wrangler-dev.log 2>&1`) so you can tail it later. The server's
       stdout is often empty via process() capture; a file is more reliable.
   *   Watch for `⎔ Reloading local server...` / `⎔ Local server updated and ready`
       in the dev log before testing — this confirms the change compiled.
2. **One change at a time.** Make one atomic edit, wait for hot reload, then
   test. Do NOT batch multiple edits even if they seem safe.
3. **Verify with real HTTP calls.** After each change, use curl to hit the
   running server and confirm the endpoint still returns correct data. Do not
   just check that the server did not crash.
   *   Test both the happy path and expected error codes.
   *   For JSON APIs, pipe through `python3 -c "import sys,json; …"` for
       structured assertions.
4. **Commit only after user review.** Never commit without approval. Use
   `git add -A && git commit` only when explicitly told to. Keep changes
   unstaged so the user can `git diff --cached` at any time.
5. **Document as you go.** Keep a running status file (e.g. README.md in the
   target directory) that tracks what has been done, what is next, and what
   assumptions were verified. Update after each logical change group.

### Dead-code audit sub-pattern

Before deleting any file or config value that appears unused:

1. Search the entire project for references
   (`grep -rn "filename\|exported_name" --include='*.ts' --include='*.js' --include='*.html'`).
   Check both import statements AND HTML script/link tags.
2. If zero references exist in all source files, it is safe to delete.
3. After deletion, verify via HTTP that no 404s appear for the removed path.
4. Record the deletion with file size and reason in the status file.

### Cross-repository integration pattern

When a project has multiple copies (NAS-backed working copy + SMB original +
SynologyDrive sync), find all pieces by listing each copy's source directory:

1. List both directories side-by-side and identify files unique to each.
2. Copy missing directories from source to working copy (`cp -R`).
3. Run the dev server after each copy batch to verify nothing broke.
4. Update worker-configuration.d.ts / .env / tsconfig as needed for new
   imports (env vars for LLM keys, type declarations for new modules).
5. Never commit cross-repo copies without user review — they may have secrets.

### Worker → controller migration pattern

When a monolithic worker.ts (700+ lines with inline route handlers) needs
splitting into controllers:

1. List all route handlers in the current worker.ts
   (`grep -n "url.pathname" worker.ts | grep -v "//"`).
2. List all exported async functions in target controller files
   (`grep "^export async function" src/controllers/*.ts`).
3. Map each route to a controller function. Note parameter patterns
   (most take `(request, env, url)`, some add `ctx`).
4. Build the new worker.ts as a pure router (imports + dispatch only).
   Keep cross-cutting concerns (CORS, response enrichment like
   analysisReport) in the router layer, not in controllers.
5. Verify every route still works after migration.
6. The router file should compress to ~80-100 lines from 700+.

### LLM caller consolidation pattern

When multiple controllers independently implement the same
DeepSeek → NVIDIA fallback fetch logic with identical 3-key rotation:

1. Create `src/utils/llm.ts` with shared functions:
   *   `callDeepSeek(env, systemPrompt, userContent, maxTokens?)`
   *   `callNvidiaWithFallback(env, systemPrompt, userContent, maxTokens?)`
       — iterates 3 keys with 28s per-key timeout via AbortController.
   *   `callLLMJson(env, systemPrompt, userContent, maxTokens?, temp?)`
       — tries DeepSeek first, falls back to NVIDIA, throws on total failure.
   *   `extractJsonObject(text)` — regex-based JSON extraction.
2. Replace duplicated implementations in each controller with imports.
3. Start with the most-used caller. Leave old functions as thin shims
   that delegate to `import('../utils/llm').then(...)` during migration.
4. Verify with a real API call that produces a non-trivial response.

### Master data consolidation pattern

When the same data (e.g. domain constants, API URLs, config values) is
duplicated across 3+ locations (frontend JS, backend TS, separate worker),
the safe consolidation sequence is:

1. Create src/data/<domain>-constants.json as a single source of truth in
   plain JSON. JSON is universally readable by both JS and TS without build
   steps.
2. Backend modules import directly using relative paths. TypeScripts
   resolveJsonModule: true handles this natively.
3. Frontend keeps a standalone copy with a prominent JSDoc comment pointing
   to the master JSON. Frontend files cannot import backend JSON at runtime
   (different serving context), so a sync comment is the pragmatic safety
   measure.
4. Update each consumer one file at a time, testing with the dev server after
   each change. Start with the most independent consumer, end with the most
   coupled one.
5. Verify parity by checking that the output before and after the change is
   identical for the same input.

### Analysis engine layering

When building a server-side analysis pipeline that the frontend consumes:

  types.ts      data structures (zero dependencies)
  engine.ts     pure computation (imports types + master data only)
  worker.ts     API integration (imports engine, handles request/response)

Keep the engine pure. No fetch, no env, no request/response objects. It takes
plain data in, returns plain data out. This makes it testable independently
and deployable in any worker context.
