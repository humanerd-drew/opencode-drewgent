---
title: P0-Brainstem Governance System — Compiled
type: wiki-compiled
tags: [compiled, governance, p0-brainstem, rules, neurons, rebac]
trigger: "wiki-compile 2026-06-21 — compiled from P0-brainstem and P4-cortex knowledge"
provenance:
  session: "2026-06-21 wiki-compile"
  decision: "Consolidate governance rules, 禁 neurons, and ReBAC enforcement"
created: 2026-06-21
updated: 2026-06-21
links:
  - "P5-ego/wiki/compiled/agent-architecture"
  - "P5-ego/wiki/compiled/taste-decisions"
  - "P0-brainstem/brain/rules"
---

# P0-Brainstem Governance System — Compiled

## Core Decisions

### 1. P-Layer Subsumption Architecture
**What:** 7-layer brain hierarchy with strict subsumption ordering. P0-brainstem rules override ALL other layers. P6-prefrontal is ephemeral reflection.
**Why:** AI agents need unambiguous rule priority. Higher layers cannot contradict lower layers.
**Order:**
- P0: Absolute rules + 禁 neurons (immutable)
- P1: Identity, persona, voice
- P2: Raw archive (read-only)
- P3: Gateways, tools, signal system
- P4: Skills index, growth records
- P5: Self model + compiled wiki (query target)
- P6: Incidents, retrospectives, long-term plans
**Status:** Active. All 7 layers operational.

### 2. 禁 Neurons (Critical Rules)
**What:** Micro-opcode constraint files in P0-brainstem with special `禁` prefix. Key active neurons:
- `禁incident_aware` — 6 trigger conditions for system anomalies
- `禁rebac_integration` / `禁rebac_kanban` — relationship-based access control
- `禁filesystem_truth` — always read directly from filesystem
- `禁task_qa_gate` — 3-phase QA (contract → micro → full)
- `禁karpathy_coding_principles` — pre-coding ritual
- `禁tool_integration_3file` — every tool requires 3 files: code, schema, toolset registration
**Why:** Machine-enforceable constraints that cannot be overridden by higher layers.
**Status:** Active. 14 `.neuron` files created during OpenCrab Ontology pilot.

### 3. OpenCrab Ontology (9-Space Semantics)
**What:** 9-space ontology mapped to 7-layer Drewgent architecture:
- identity (P1, P5), claim (P6), concept (P0), policy (P0), workflow (P3, cron)
- resource (P2), resolver (P3), outcome (P3), growth (P4)
**Why:** Typed frontmatter (`space:`, `type:`, `rule_token:`) enables ontology-driven queries.
**Coverage:** 5,014 vault nodes, 99.98% have `space:` field.
**Status:** Phase 1-2 complete (2026-05-20/21). `ontology_query.py` script with 8 commands available.

### 4. ReBAC (Relationship-Based Access Control)
**What:** 禁tools/skills/kanban rules require `INTEGRATION_PROTOCOL` / `KANBAN_INDEX` reference. Integration Protocol mandates 3-file pattern for any new tool/skill.
**Why:** Every integration must be registered and cross-referenced. Prevents orphan tools.
**Status:** Active. Gadfly rule: cross-reference with existing files before adding.

### 5. 3-Phase QA Gate
**What:** Phase 1 (Contract) — verify function signature and return shape. Phase 2 (Micro) — test edge cases. Phase 3 (Full) — integration test.
**Why:** Catches issues at the earliest phase. Contract failures block delivery (P0 signal).
**Status:** Active. `qa.gate.contract.placeholder_detected` → delivery blocked.

### 6. Tiered Autonomy (T1-T4)
**What:** (See taste-decisions.md for detail) T1 docs → T2 patterns → T3 propose → T4 human only.
**Why:** Remove unnecessary confirmation friction for safe changes.
**Status:** Active. Enforced by agent profiles.

### 7. Knowledge Bus (5-Module Singleton)
**What:** Bus.py connects NeuronFS, VerificationEngine, GrowthEngine, RevisionLoop. JSON persistence.
**Why:** Central governance enforcement across all modules.
**Status:** Active.

## Rationale
Governance borrowed from NeuronFS (filesystem-based AI constraints) + Garry Tan's "Thin Harness, Fat Skills" philosophy. P0 rules are the immutable constitution; everything else can be changed with proper process.

## Current Status
All governance rules active. OpenCrab ontology covers 99.98% of vault. 3-phase QA gate enforced. ReBAC applies to tools/skills/kanban. 14 禁 neurons active. Daily harmony check verifies compliance.
