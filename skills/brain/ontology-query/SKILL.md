---
title: ontology-query — OpenCrab Graph Query Tool
type: document
space: concept
tags: [concept]
created: 2026-05-21
updated: 2026-05-20
links:
  - "[[@memory/growth/open-crab-ontology-drewgent-implementation]]"
  - "[[@memory/knowledge/NEURONFS_RULES]]"
  - "[[@memory/knowledge/OPENCRAB_ONTOLOGY]]"
  - "[[@memory/scripts/ontology_frontmatter_sync.py]]"
  - "[[@identity/brain/rules]]"---



# ontology-query — OpenCrab Graph Query Tool

Query the P0-brainstem ontology graph exported as JSONL.

## Script Location
```
~/.drewgent/P4-cortex/scripts/ontology_query.py
```

## Commands

```bash
# 1. List all nodes
python3 P4-cortex/scripts/ontology_query.py list

# 2. Show space distribution
python3 P4-cortex/scripts/ontology_query.py spaces

# 3. Get a specific rule
python3 P4-cortex/scripts/ontology_query.py rule <rule_id>
# 例: python3 P4-cortex/scripts/ontology_query.py rule 禁karpathy_coding_principles

# 4. Show links in/out for a rule
python3 P4-cortex/scripts/ontology_query.py links <rule_id>

# 5. Show full graph connections (1st + 2nd degree)
python3 P4-cortex/scripts/ontology_query.py graph <rule_id>

# 6. Search by title or rule_source
python3 P4-cortex/scripts/ontology_query.py search <query>
# 例: python3 P4-cortex/scripts/ontology_query.py search karpathy

# 7. Find orphan nodes (no links)
python3 P4-cortex/scripts/ontology_query.py orphans

# 8. Filter by space
python3 P4-cortex/scripts/ontology_query.py space <space>
# 例: python3 P4-cortex/scripts/ontology_query.py space policy
```

## Output Examples

### spaces
```
Space Distribution:
  policy               13
Total: 13 nodes
```

### links <rule_id>
```
Links FROM 禁karpathy_coding_principles:
  → P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁/禁brain_obsidian_graph
  → P0-brainstem/brain/rules
  → P5-ego/SELF_MODEL

Links TO 禁karpathy_coding_principles:
  (none — orphan candidate)
```

### orphans
```
No orphan nodes found. All nodes have at least one connection.
```

## Ontology File
```
~/.drewgent/P0-brainstem/p0-brain-ontology.jsonl
```
13 nodes exported as JSONL. Updated manually when new .neuron files are created.

## Related
- [[@memory/growth/open-crab-ontology-drewgent-implementation]] — Phase 1+2 implementation report
- [[@memory/knowledge/OPENCRAB_ONTOLOGY]] — 9-Space mapping to Drewgent P-layers
- [[@memory/scripts/ontology_frontmatter_sync.py]] — Auto frontmatter sync (cron)
