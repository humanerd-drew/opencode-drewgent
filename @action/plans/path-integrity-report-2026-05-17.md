---
title: Path Integrity Report 2026 05 17
type: plan
space: claim
tags: [claim]
created: 2026-05-20
updated: 2026-05-20
links:
  - "[[@memory/growth/INTEGRATION_PROTOCOL]]"
  - "[[@memory/knowledge/obsidian-vault-site-principle]]"
  - "[[@action/migrations/drewgent-root-consolidation-20260506]]"
  - "[[@action/plans/growth-2026]]"
---



# Drewgent Path Integrity Report - 2026-05-17

Scope: `~/.drewgent` runtime layout, active NeuronFS/Obsidian layers, and `source/drewgent-agent` path references. This report intentionally excludes broad archive/session-log cleanup from automatic fixes.

## Summary

- Core runtime data flow is connected:
  - `~/.drewgent/brain` -> `P0-brainstem/brain`
  - `~/.drewgent/memories` -> `P2-hippocampus/memories`
  - `~/.drewgent/sessions` -> `P2-hippocampus/sessions`
  - `~/.drewgent/logs` -> `P6-prefrontal/logs`
- Active brain is `Drewgent-brain`.
- `brain_load()` returns governance content and includes `禁task_qa_gate` and `禁karpathy_coding_principles`.
- Gateway logs show the gateway started successfully with 3 platforms after the last restart.
- One broken symlink was found:
  - `~/.drewgent/humanerd-site/content/scripts` -> `~/.drewgent/P4-cortex/scripts/`

## Runtime Path Findings

### OK

- Session storage is routed through the hippocampus layer.
- Logs are routed through the prefrontal layer.
- Memory wiki is routed through the hippocampus layer.
- Active brain symlinks P1-P6 into the active brain tree.
- QA evidence now resolves under `~/.drewgent/P2-hippocampus/qa-evidence`.

### Needs Cleanup

1. `humanerd-site/content/scripts` has a missing target.
   - Impact: site/content graph only; not core agent runtime.
   - Low-risk fix: create `~/.drewgent/P4-cortex/scripts`.

2. Some runtime helpers still compute default state paths with `Path.home() / ".drewgent"` instead of the shared `get_drewgent_home()`.
   - Impact: default profile works, but named/custom profiles may write state to the wrong home.
   - Low-risk candidates:
     - `source/drewgent-agent/model_tools.py`
     - `source/drewgent-agent/agent/model_metadata.py`
     - `source/drewgent-agent/agent/models_dev.py`
     - `source/drewgent-agent/agent/auto_learn.py`

3. Config is duplicated as real files:
   - `~/.drewgent/config.yaml`
   - `~/.drewgent/P5-ego/config/config.yaml`
   - Impact: potential drift.
   - Recommendation: do not auto-fix yet. First determine whether P5 copy is intended as identity-layer snapshot or stale migration artifact.

## Wikilink Findings

Narrow active-layer scan, excluding archive/session/cron output noise:

- Checked files: 144
- Wikilinks seen: 209
- Unresolved candidates: 137

Most unresolved candidates are not runtime blockers. They fall into these buckets:

- placeholder links in governance examples
- filename-only links where the target exists under a subfolder
- imported knowledge graph links in `P4-cortex/knowledge/laws-of-ux-wiki`
- external source paths that are not present in the current active vault
- generated memory text containing malformed wiki syntax

Recommendation: wikilinks should be handled in a separate graph hygiene pass, not mixed with runtime path cleanup.

## Safe Cleanup Plan

1. Create missing `~/.drewgent/P4-cortex/scripts` directory.
2. Replace simple profile-unsafe state path defaults with `get_drewgent_home()`.
3. Re-run:
   - broken symlink scan
   - Python compile for touched files
   - targeted tests that cover path/profile behavior if available
4. Leave config deduplication and wikilink rewrites for a reviewed follow-up.

## Related
- [[@action/plans/growth-2026]]
- [[@action/migrations/drewgent-root-consolidation-20260506]]
- [[@memory/knowledge/obsidian-vault-site-principle]]

## Links
- [[@memory/growth/INTEGRATION_PROTOCOL]]
