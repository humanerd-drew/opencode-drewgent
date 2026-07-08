---
title: qa-cycle
description: Contract-First QA pipeline - implements 3-phase QA (contract → micro-QA → full-QA) using P2-hippocampus qa-evidence system
trigger conditions:
  - Task involves building or modifying software
  - User requests test, QA, or verification
  - Task completion needs acceptance criteria
space: outcome
type: document
tags: [qa, testing, contract-first, verification]
links:
  - "[[@action/skills/qa/DESCRIPTION]]"
  - "[[@action/skills/SKILL-INDEX]]"
source: Hugh Kim's Loopy-Era Harness, Drewgent P2-hippocampus
---

# qa-cycle — Contract-First QA Pipeline

## Purpose

Runs 3-phase QA pipeline for any task:
1. **CONTRACT** — Define acceptance criteria before implementation
2. **MICRO-QA** — Verify each step as it's completed
3. **FULL-QA** — Final gate check before delivery

## How It Works

Uses the `QAEvidenceManager` in `P2-hippocampus/qa-evidence/` to:
- Create a `contract.json` with acceptance criteria
- Record `micro-qa_*.json` after each step
- Run `full-qa.json` before delivery
- Generate `.qa-evidence.json` manifest

## Usage

```
skill: qa-cycle
task_id: {optional, auto-generated if omitted}
action: create_contract | record_micro | run_full_qa | status
```

## Workflow

### 1. Create Contract (Before Implementation)
```python
qa = QAEvidenceManager()
qa.create_contract(
    task_id="my-task-001",
    acceptance_criteria=[
        {"id": "c1", "description": "Feature X works", "priority": "P0"},
        {"id": "c2", "description": "Tests pass", "priority": "P0"},
    ]
)
```

### 2. Record Micro-QA (After Each Step)
```python
qa.record_micro_qa(
    task_id="my-task-001",
    step_id="step_1",
    step_description="Implemented feature X",
    evidence={"files": ["feature_x.py"]},
    verification={"passed": True, "score": 1.0}
)
```

### 3. Run Full-QA (Before Delivery)
```python
result = qa.run_full_qa(
    task_id="my-task-001",
    criteria_verification=[...],
    overall_score=0.95
)
if not result["ready_for_delivery"]:
    # revision loop
```

## Hugh Kim's Contract-First QA Principle

From the Loopy-Era Harness:
- Phase 2.5 시나리오 확정 → 구현 → micro-QA → full-QA
- `.qa-evidence.json` 증거 필수
- FILESYSTEM = TRUTH: 파일에서 직접 읽어 Specialist에게 전달

## Integration

- **P2-hippocampus/qa-evidence/** — Evidence storage
- **P4-cortex/growth/orchestrator/** — Orchestrator calls qa-cycle
- **HARD hook: task_qa_gate** — Blocks delivery without QA

## Verification Checklist

Before marking QA complete, verify:
- [ ] All acceptance criteria have test results
- [ ] No blocker-level issues remain
- [ ] Filesystem = Truth: re-read files to confirm changes
- [ ] Evidence manifest is complete

## Related
- [[@action/skills/SKILL-INDEX]]
- [[@action/skills/qa/DESCRIPTION]]
