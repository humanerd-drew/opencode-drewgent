# GBrain Implementation in Drewgent (Karpathy + GBrain hybrid, 2026-06-10)

This is a record of how we applied Karpathy's "LLM Wiki" and GBrain's 3-pillar
architecture to the existing Drewgent vault, without adopting the
external `garrytan/gbrain` service.

## Why we didn't install GBrain

`garrytan/gbrain` is a separate service (git-versioned brain repo, LLM
synthesis, graph traversal, gap analysis). Adopting it would mean:
- A new dependency to maintain
- A separate persistence layer alongside `~/.drewgent/P2-hippocampus/`
- A different tool to call for memory operations

Drewgent already has:
- A git-versioned vault (`~/.drewgent/`) with wikilinks
- `ontology-query` skill for graph traversal on P0-brainstem neurons
- LLM-synthesis capability via the agent loop

The hybrid approach below gives us 3 of 4 GBrain pillars with **zero new dependencies**.

## 3-pillar mapping

| GBrain pillar | Drewgent equivalent | Status |
|---|---|---|
| 1. Repo (git-versioned) | `~/.drewgent/` vault (Obsidian-flavored, git-versioned) | ✓ pre-existing |
| 2. Synthesis (LLM compile) | Memory entries as compiled procedures (not raw incident reports) | ✓ added 6/10 |
| 3. Graph traversal | `~/.hermes/scripts/drewgent_graph_lookup.sh` (wikilink walker) + `ontology-query` skill | ✓ added 6/10 |
| 4. Gap analysis | None — TODO | ✗ |

## Implementation: drewgent_graph_lookup.sh

A bash script that walks wikilinks across P2-hippocampus (memory), P0-brainstem
(neurons), P4-cortex (growth), P6-prefrontal (incidents).

```bash
# Usage
bash ~/.hermes/scripts/drewgent_graph_lookup.sh "launchd"
# Output:
#   ## Direct hits
#     • /Users/drew/.drewgent/P2-hippocampus/memories/MEMORY.md
#     • /Users/drew/.drewgent/P6-prefrontal/incidents/cron-jobs-stalled-20260601.md
#     • /Users/drew/.drewgent/P6-prefrontal/incidents/launchd-mass-failure-20260610.md
#     • /Users/drew/.drewgent/P6-prefrontal/incidents/cron-runner-launchd-detached-20260601.md
#     • /Users/drew/.drewgent/P4-cortex/growth/discord-token-resilience-protocol.md
#   ## Wikilink graph (incoming)
#     (no incoming wikilinks)
#   ## Outgoing from memory
#     [[ACP-spinner-attempts-20260602]]
#     [[content-pipeline-publish-leak-20260602]]
#     [[cron-jobs-stalled]]
#     ...
```

**Key insight**: "incoming" requires explicit `[[topic]]` wikilinks in *other*
files — GBrain's "self-wiring" model. If you want auto-discovery, every memory
entry must include `→ vault: [[topic]]` for related entities.

## Memory entry structure (Karpathy-compiled)

Before (raw incident report, 8568 chars total):
```
2026-06-10 16:35 KST — launchd mass-failure, 4-6일 undetected. gateway
6/6 13:10 cron ticker stopped, n8n 6/4 16:41 SIGTERM, quartz-fswatch
KeepAlive:false, cron jobs last_run_at=5/19, label mismatch. Fix: watchdog
cron `2d9a31f2b661` (5m, no_agent)...
```

After (compiled procedure, 6804 chars total):
```
## Launchd Hardening (procedures)
→ vault: [[@action/incidents/launchd-mass-failure-20260610]]

**All launchd plists for AI agent services MUST use this template**:
```xml
<key>KeepAlive</key>
<dict>
  <key>SuccessfulExit</key><false/>
  <key>ThrottleInterval</key><integer>10</integer>
</dict>
```
**Pitfalls**: bare `<true/>`, bare `<false/>`, missing key.
```

12 entries → 9 entries. 8,568 → 6,804 chars (21% reduction, 0 resolved facts lost).

## The 4th pillar: gap analysis (TODO)

GBrain detects: "X is in your brain repo, but no entry in MEMORY.md references
it." This is the "gap" — facts you have but can't recall.

Drewgent equivalent would be a script:
```bash
# Pseudo-code
for f in ~/.drewgent/P4-cortex/knowledge/*.md; do
  topic=$(basename "$f" .md)
  if ! grep -qE "\[\[$topic\]\]" ~/.drewgent/P2-hippocampus/memories/MEMORY.md; then
    echo "GAP: $topic not referenced in memory"
  fi
done
```

Not yet implemented. If memory compression starts dropping important facts, this becomes critical.

## Why this matters

A 2026-06-10 checkup discovered:
- `last_run_at` of `hermes cron list` 22 days stale
- 4 enabled jobs had `next_run_at` 22 days in the past
- The 6/1 incident doc said "복구" (recovered) — but the recovery was *transient*

This is exactly what GBrain's "compilation + graph" pattern is designed to prevent: a single canonical, graph-linked source of truth that doesn't drift from reality. We don't need GBrain-the-service to apply the principle — we have the pattern locally.

## Tradeoffs vs installing garrytan/gbrain

| Aspect | Local hybrid | Real GBrain |
|---|---|---|
| Maintenance | 0 new deps | 1 new repo to track |
| Cross-session continuity | MEMORY.md load (8K cap) | 10k+ files in brain repo |
| Graph queries | bash script + ontology-query skill | full graph DB |
| Synthesis | manual (one-time H2 compression) | automated via LLM |
| Gap analysis | TODO | built-in |
| Cost | 0 (just bash) | API calls for synthesis |

For Drewgent's scale (single user, ~10k files, manual but occasional checkups), the local hybrid is sufficient. The day a third contributor joins or MEMORY.md hits 8K cap daily, the calculation changes.
