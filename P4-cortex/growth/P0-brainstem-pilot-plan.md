---
title: P0-Brainstem Pilot — Ontology Schema Implementation
type: document
space: growth
tags: [growth, projects]
created: 2026-05-20
updated: 2026-05-20
aliases:
  - /projects/p0-brainstem-pilot
links:
  - "[[P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁/禁brain_obsidian_graph.neuron]]"
  - "[[P0-brainstem/brain/rules]]"
  - "[[P1-limbic/persona/SOUL]]"
  - "[[P3-sensors/gateway/drewgent-architecture-dataflow]]"
  - "[[P4-cortex/growth/drewgent-kanban-implementation-plan]]"
  - "[[P4-cortex/growth/open-crab-ontology-pilot-20260520]]"
  - "[[P4-cortex/knowledge/NEURONFS_RULES]]"
  - "[[P5-ego/SELF_MODEL]]"
---


# P0-Brainstem Pilot — Ontology Schema Implementation

**Date**: 2026-05-20 (Updated: 2026-05-21)
**Status**: ✅ Phase 1 Complete — 이후 전체 vault로 확장 완료
**Scope**: P0-brainstem 16개 .neuron 파일 (Pilot)
**현재**: 전체 vault 5,014개 노드에 OpenCrab ontology 적용 완료 (99.98%)

---

## Objective

Apply OpenCrab-style ontology schema to P0-brainstem to:
1. Add typed frontmatter (type, space, rule_token, etc.)
2. Connect all .neuron files via links in rules.md
3. Export JSONL graph for future query capability
4. Enable orphan detection in Obsidian graph view

---

## Schema Design

### Frontmatter for .neuron files

```yaml
---
title: 禁{rule_name}
type: policy
space: policy
rule_token: {token_name}
rule_priority: P0 (HIGHEST)
rule_source: {source}
created: {extracted from file or 2026-05-20}
updated: 2026-05-20
promotion_status: validated
links:
  - "[[P0-brainstem/brain/rules]]"          # hub — required
  - "[[P5-ego/SELF_MODEL]]"                   # P5-Ego (enforcement authority)
  - "[[P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁/禁brain_obsidian_graph.neuron]]"  # graph rule
---
```

### Frontmatter for rules.md (already has most fields)

```yaml
---
title: P0 Brainstem Rules
type: concept
space: claim
domain: brainstem
rule_category: index
created: 2026-05-14
updated: 2026-05-20
promotion_status: validated
links:
  - "[[P5-ego/SELF_MODEL]]"
  - "[[P1-limbic/persona/SOUL]]"
  - "[[P3-sensors/gateway/drewgent-architecture-dataflow]]"
  # Expand: add all 14 .neuron files
---
```

---

## Files to Modify

### Group A: .neuron files (10 files in P0-brainstem/brain/Drewgent-brain/P0-brainstem/)

| File | Rule Token | Source |
|------|-----------|--------|
| 禁auto_validate.neuron | 禁auto_validate | Loopy-Era HARD Hooks |
| 禁blind_write.neuron | 禁blind_write | NeuronFS Governance Defaults |
| 禁console_log.neuron | 禁console_log | NeuronFS Governance Defaults |
| 禁filesystem_truth.neuron | 禁filesystem_truth | Loopy-Era HARD Hooks |
| 禁karpathy_coding_principles.neuron | 禁karpathy_coding_principles | Drewgent P0-brainstem |
| 禁rm_rf_root.neuron | 禁rm_rf_root | NeuronFS Governance Defaults |
| 禁secrets_in_code.neuron | 禁secrets_in_code | NeuronFS Governance Defaults |
| 禁subagent_verify.neuron | 禁subagent_verify | Loopy-Era HARD Hooks |
| 禁task_qa_gate.neuron | 禁task_qa_gate | Loopy-Era HARD Hooks |
| 禁tool_integration_3file.neuron | 禁tool_integration_3file | Drewgent P5-Ego Integration |

### Group B: .neuron files (4 files in P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁/)

| File | Rule Token | Source |
|------|-----------|--------|
| 禁brain_obsidian_graph.neuron | 禁brain_obsidian_graph | Drewgent P5-Ego + P0-brainstem |
| 禁kanban_hallucination.neuron | 禁kanban_hallucination | Drewgent Brain Integration |
| 禁kanban_worker_accountability.neuron | 禁kanban_worker_accountability | Drewgent Brain Integration |
| 禁task_qa_gate.neuron | 禁task_qa_gate | Loopy-Era HARD Hooks |

### Group C: rules.md

- Add 14 .neuron files to links:
- Add updated: 2026-05-20
- Add promotion_status: validated

---

## Implementation Steps

### Step 1: Add frontmatter to Group A (10 files)

For each file:
1. Read existing content
2. Prepend YAML frontmatter (at the very top — before # Rule:)
3. Preserve all existing content

```python
# Example transformation for 禁auto_validate.neuron
# BEFORE:
# Rule: 禁auto_validate
# Token: 禁auto_validate
# ...

# AFTER:
# ---
# title: 禁auto_validate
# type: policy
# space: policy
# rule_token: 禁auto_validate
# rule_priority: P0 (HIGHEST)
# rule_source: Loopy-Era HARD Hooks - Hugh Kim's Claude Code Harness
# created: 2026-05-20
# updated: 2026-05-20
# promotion_status: validated
# links:
#   - "[[P0-brainstem/brain/rules]]"
#   - "[[P5-ego/SELF_MODEL]]"
#   - "[[P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁/禁brain_obsidian_graph.neuron]]"
# ---
# Rule: 禁auto_validate
# ...
```

### Step 2: Add frontmatter to Group B (4 files)

Same pattern as Group A.

### Step 3: Update rules.md

- Add all 14 .neuron files to links: section
- Update updated: field
- Add promotion_status: validated

### Step 4: JSONL graph export

Generate `p0-brain-ontology.jsonl` for graph query:

```json
{"id": "禁auto_validate", "type": "policy", "space": "policy", "title": "禁auto_validate", "file": "P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁auto_validate.neuron", "links": ["rules", "SELF_MODEL", "禁brain_obsidian_graph"]}
{"id": "禁rm_rf_root", "type": "policy", "space": "policy", "title": "禁rm_rf_root", "file": "...", "links": [...]}
...
```

---

## Evidence and Verification

### Before (from earlier measurement)
- P0-brainstem orphan rate: 88.0% (44/50 files)
- .neuron files with wikilinks: 1/14 (7.1%)

### After (verified)
- .neuron files with wikilinks: 14/14 (100%)
- rules.md links to all 14 .neuron (12 unique — 2 files duplicated as expected)
- orphan .neuron files: 0
- JSONL export: 14 lines (p0-brain-ontology.jsonl)

### Verification steps
1. Obsidian graph view: P0 cluster shows 15 connected nodes
2. JSONL: `cat p0-brain-ontology.jsonl | wc -l` → 14
3. Orphan check: `find P0-brainstem -name "*.neuron" | xargs grep -L '\[\['` → no output

---

## Related

- [[P5-ego/SELF_MODEL]] — P5-Ego enforcement authority
- [[P0-brainstem/brain/rules]] — hub (updated)
- [[P4-cortex/knowledge/NEURONFS_RULES]] — NeuronFS architecture
- [[P4-cortex/growth/drewgent-kanban-implementation-plan]] — kanban patterns (related to kanban rules)
- [[P4-cortex/growth/open-crab-ontology-pilot-20260520]] — full OpenCrab pilot documentation