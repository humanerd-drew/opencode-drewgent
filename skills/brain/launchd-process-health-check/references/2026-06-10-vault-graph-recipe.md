# Drewgent Vault Graph — 2026-06-10 Implementation Recipe

## What this is

Drewgent's memory + skill + incident vault, with a lightweight GBrain-style
graph traversal layer on top. Implemented 2026-06-10 19:30 during the
incident-response + memory-compression sweep.

## Why we did this

- 12+ memory entries had grown past the 8,000-char cap, all written as
  raw incident reports ("date, symptom, fix"). Hard to look up *what to
  do* in 30 seconds when the next incident hits.
- Karpathy's [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
  insight: "raw sources still require the AI to do the synthesis work live,
  during your query, under time pressure." Better to *compile* once.
- GBrain's 4-pillar model ([garrytan/gbrain](https://github.com/garrytan/gbrain))
  fits Drewgent's vault shape almost 1:1, with one big difference: GBrain
  is a separate service, while we adopt the pattern **inside the vault
  itself** (no extra service to install).

## The 4 pillars (Drewgent-flavored)

| Pillar | GBrain tool | Drewgent equivalent | Status |
|---|---|---|---|
| 1. Repo | git-versioned knowledge | `~/.drewgent/P2-hippocampus/memories/MEMORY.md` + skills + incidents | ✓ had this |
| 2. Synthesis | LLM compiles raw → wiki | memory entries rewritten as compiled procedures with wikilinks (12 → 9 entries, 21% size reduction) | ✓ applied 6/10 |
| 3. Graph traversal | typed-edge walk | `~/.hermes/scripts/drewgent_graph_lookup.sh` (wikilink walker) | ✓ implemented 6/10 |
| 4. Gap analysis | auto-detect missing edges | `~/.hermes/scripts/drewgent_graph_gap_analysis.sh` (dangling + missing) | ✓ implemented 6/10 |

## File map

```
~/.drewgent/
├── P2-hippocampus/memories/MEMORY.md          # 9 compiled procedures, vault-wikilinked
├── P6-prefrontal/incidents/                    # canonical reference docs
│   ├── launchd-mass-failure-20260610.md        # 4-6 day outage
│   ├── gateway-scheduler-double-fire-20260610.md
│   ├── acp-spinner-attempts-20260602.md
│   ├── cron-jobs-stalled-20260601.md
│   ├── cron-runner-launchd-detached-20260601.md
│   ├── cron-job-failure-20260518.md
│   └── content-pipeline-publish-leak-20260602.md
├── P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁*.neuron  # 13禁 rules
└── skills/                                       # 48 skills

~/.hermes/scripts/
├── drewgent_graph_lookup.sh          # Pillar 3
├── drewgent_graph_gap_analysis.sh    # Pillar 4
├── drewgent_harmony_check.sh         # Layer 3.5 mtime drift detector (catches Sub-pattern 9)
├── drewgent_launchd_watchdog.sh      # 5-min launchd health poll
├── drewgent_log_rotate.sh            # daily 04:00 log rotation
└── customize_smoke_test.sh           # weekly: T5/T6/T7/T8 in one script
```

## Karpathy compile rule (the synthesis principle)

**Before**: a memory entry reads like
> "2026-06-10 16:35 KST — **launchd mass-failure, 4-6일 undetected**.
> gateway 6/6 13:10 cron ticker stopped, n8n 6/4 16:41 SIGTERM..."

**After** (compiled procedure):
> ## Launchd Hardening (procedures)
> → vault: [[P6-prefrontal/incidents/launchd-mass-failure-20260610]]
>
> **All launchd plists MUST use**:
> ```xml
> <KeepAlive><dict><SuccessfulExit>false/><ThrottleInterval>10</dict>
> ```
> **Pitfalls**: bare `<true/>` (no restart on exit 0), bare `<false/>` (no restart ever)...

The compiled form is *immediately actionable*. The raw form requires re-derivation at lookup time (which is the original problem).

## How to use the graph tools

```bash
# Find all files related to a topic (direct hits + wikilinks)
bash ~/.hermes/scripts/drewgent_graph_lookup.sh "launchd"
# Returns: memory.md, 3 incident docs, 1 protocol doc, + outgoing wikilinks

# Find dangling wikilinks and orphan vault files
bash ~/.hermes/scripts/drewgent_graph_gap_analysis.sh
# Returns: ⚠ dangling (none when clean) + ⚠ not referenced (expected; not all P0 neurons need memory entries)

# Run only one direction
bash ~/.hermes/scripts/drewgent_graph_gap_analysis.sh --dangling-only
bash ~/.hermes/scripts/drewgent_graph_gap_analysis.sh --missing-links

# Weekly smoke test (cron: f0b39d211970, Sun 10:00 KST)
bash ~/.hermes/scripts/customize_smoke_test.sh
# Runs T5 (hermes wrapper) + T6 (customize layer) + T7 (regression grep) + T8 (graph integrity)
```

## Pitfalls (the gotchas we hit)

### Bash 3.2 (macOS default) quirks
- **No associative arrays** (`declare -A` invalid). Use parallel indexed arrays.
- **No `set -u`** — dotted label arithmetic quirk. Variables with dots (e.g. `ai.drewgent.gateway`) inside `${...}` get parsed as math.
- **`date -j -f`** for date parsing (GNU `date` not available).

### Regex precision
- **Naive `grep "PYTHONPATH"`** matches `PYTHONHOME` (substring). Use anchored: `^[[:space:]]*unset[[:space:]]+PYTHONPATH[[:space:]]*$`.
- **Naive `grep -c "dangling"`** matches section headers (`## Dangling wikilinks`), not alert lines. Use the specific marker: `grep -c "⚠ dangling:"`.
- **Naive `grep -c "<error>"`** in a 9.6M-line log: 40s runtime. Use mtime + targeted grep, not full scan.

### Memory tool drift guard
- The `memory` tool refuses to `add` after direct `write_file`/`patch` to MEMORY.md. It saves `.bak.<timestamp>` and asks to reconcile. This is a *safety feature*.
- **Workaround**: if you need to do a structural memory rewrite, plan to *not* use `memory` tool afterward. Go direct-write, accept the drift, document the change elsewhere (incident doc, skill).
- **Don't** try to "preserve" the round-trip — the guard exists for safety, and bypassing it loses the guard.

### Layer 3.5 false positives
- **Double-fire (Sub-pattern 7)**: gateway scheduler may fire interval jobs 2x per minute. Layer 3.5 must NOT alert on this. The fix: only alert if `last dispatcher tick > 60s ago` (i.e., truly stalled, not double-fire within a minute).
- **Two-source duplication (Sub-pattern 8)**: if `cron-runner.plist` AND jobs.json gateway entry both run, you get 4 fires/min. Detection: count `=== ISO ===` lines per minute in `cron-runner/<date>.log`.

## The 4-pillar value (vs GBrain full install)

We *did* consider installing the full GBrain service. Decided against because:

1. **No external service to manage** — our vault *is* the brain
2. **Wikilinks are already first-class** in Obsidian-compatible formats; GBrain re-implements the graph on top of files
3. **Customize layer exists** for hermes ↔ vault interop; GBrain would be a parallel system
4. **Memory drift is observable** through the existing harmony check + smoke test; GBrain's gap detection is a single script for us, vs a whole service
5. **Single-machine, single-user** — GBrain's distributed / multi-user features are overkill for Drewgent

The 4-pillar *pattern* is what we adopt, not the implementation. Implementation lives in 4 scripts (graph_lookup, gap_analysis, harmony_check, smoke_test), all bash, all under 300 lines each.

## Future work (not in this recipe)

- **Auto-fix loop**: when gap analysis finds a dangling wikilink, *create* the target file from a template. (Skipped: 6/10 sweep manually fixed all 6 dangles, future incident may need auto-fix.)
- **gap_analysis → memory write-back**: detected missing link → suggest memory entry that links to it. (TBD, requires LLM call.)
- **Multi-vault**: if Drewgent grows to multiple repos (e.g. separate skills, separate incidents dirs), the graph_lookup needs a `-r` flag. (TBD.)

## Reference: state at end of 6/10 sweep

```bash
$ bash ~/.hermes/scripts/drewgent_graph_gap_analysis.sh
🔍 **Drewgent graph gap analysis** @ 2026-06-10 19:33:37 KST
Mode: all

## Dangling wikilinks (in MEMORY.md, target file not found)
  ✓ all wikilinks resolve

## Missing links (vault files NOT referenced from MEMORY.md)
  ⚠ not referenced: 禁tool_integration_3file
  ⚠ not referenced: 禁rm_rf_root
  ⚠ not referenced: 禁blind_write
  ⚠ not referenced: 禁secrets_in_code
  ⚠ not referenced: 禁kanban_worker_accountability
  ⚠ not referenced: 禁brain_obsidian_graph
  ⚠ not referenced: 禁kanban_hallucination
  ⚠ not referenced: 禁auto_validate
  ⚠ not referenced: 禁console_log
  ⚠ not referenced: 禁subagent_verify

---
Run graph lookup: bash ~/.hermes/scripts/drewgent_graph_lookup.sh <topic>
```

Dangling = 0. Missing = 10 (all P0 neurons, *expected* — memory entries only need cross-links to *relevant* neurons, not all of them).
