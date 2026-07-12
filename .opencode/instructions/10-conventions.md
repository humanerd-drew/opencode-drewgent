# Conventions & Policies

## Provenance Convention

Every artifact records its trigger and decision context:

```
---
title: my-skill
trigger: "Why this was created"
provenance:
  session: "YYYY-MM-DD topic"
  decision: "Why this design, what alternatives considered"
---
```

## Tiered Autonomy

| Tier | Scope | Agent Authority |
|------|-------|----------------|
| 1 | Typos, docs, comments | Autonomous, report after |
| 2 | Within existing patterns | Autonomous, include provenance |
| 3 | Structural changes | Propose → approve → execute |
| 4 | Architecture/direction | Propose only, human decides |

## Ponytail — Lazy Senior Dev Mode

Before writing code:
1. Is this code really needed? (YAGNI)
2. Does stdlib already have it?
3. Does the platform already support it?
4. Does an existing dependency handle it?
5. Can it be one line?
6. If still needed: minimum implementation.

## Answer-First Communication

- Conclusion first, process only if needed
- `[Summary]` → `[Details]` → `[Appendix]`
- Exception: debugging → process-first is correct

## Important Policies

- **Filesystem = Truth**: verify subagent output against actual files
- **No big-bang refactoring**: change → verify → confirm → next
- **Add less, remove more**: every new dependency must justify itself

## Ontology Integrity

- Run `ontology_setup.py` after schema changes
- Housekeeper validates type hierarchy + relation constraints daily
- Contradiction detection via `inference.py contradictions`
