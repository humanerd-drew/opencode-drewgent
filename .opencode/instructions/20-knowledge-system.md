# Knowledge System

## Architecture

```
knowledge.db (SQLite + FTS5 + Ollama embeddings)
├── knowledge (entries)
├── embeddings (vectors)
├── entities (ontology nodes, typed)
└── relations (ontology edges, typed)
```

## Tools

| Tool | What it does |
|------|-------------|
| `recall(query)` | Hybrid search (semantic + FTS5) |
| `remember(fact, type)` | Store + embed + extract entities |
| `graph-explore(query)` | Find entity + 2-hop neighbors |
| `graph-trace(query)` | Entity path tracing |
| `graph-rca(query)` | Root cause analysis report |

## Entity Extraction

`remember()` automatically:
1. Stores the fact with embedding
2. Extracts entities (LLM or fallback regex)
3. Creates relations to known entities
4. Links to instruction files via topic keywords

## Inference Engine

```
python3 scripts/inference.py transitive --entity <name> --type depends_on
python3 scripts/inference.py backtrace --entity <entity>
python3 scripts/inference.py contradictions
python3 scripts/inference.py all
```

## PRD System (Optional)

`skill("prd-agent")` — Product Requirements Documentation.
3 phases: Create → Regression test → Drift detection.

## Relationship Constraints

| Relation | Allowed Source → Target |
|----------|------------------------|
| depends_on | any → tool/script |
| fixed_by | incident → pattern/decision |
| caused | decision/pattern → incident |
| led_to | decision/pattern → decision/pattern |
| cites | paper → paper |
| contradicts | decision/pattern → decision/pattern |
| references, relates_to | any → any |
