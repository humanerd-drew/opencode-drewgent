---

name: semblent-search
description: Semantic code search using Semble — find code by intent rather than exact matches. Use when exploring unfamiliar codebases or searching for patterns that are hard to express as regex.
version: 1.0.0
category: research
space: outcome
type: document
tags: [code-search, research, debugging, exploration]
links: [[@action/skills/SKILL-INDEX]]]
links:
  - "[[@action/skills/SKILL-INDEX]]"
---


# Semble Semantic Code Search

Semble indexes codebases and answers natural-language queries about code.
It returns ranked results with file locations and relevance scores.

## Available Tools

### `semble_search`
Search using natural language intent.

```
semble_search(query="authentication flow", path="/repo", top_k=5)
semble_search(query="where is cache invalidation", path=".", top_k=5)
semble_search(query="how does delegate_task spawn subagents", path=".", top_k=3)
```

### `semble_find_related`
Find similar code given a file:line from a prior result.

```
semble_find_related(file_path="tools/delegate_tool.py", line=287, path=".", top_k=5)
```

## Decision Matrix: When to Use Semble

| Situation | Tool |
|-----------|------|
| Find code by **what it does** (intent) | `semble_search` |
| Find code by **exact pattern** (regex) | `search_files` (grep) |
| Find code by **filename** | `search_files` (glob) |
| Need full file **context** | `read_file` |
| Explore **unfamiliar codebase** | `semble_search` first |
| **Debugging** "where did this error come from" | `semble_search` |
| **Refactoring** related code | `semble_search` + `semble_find_related` |

## Workflow

1. Start with `semble_search` to find relevant chunks by describing intent
2. Use `semble_find_related` with promising results to discover related implementations
3. Use `read_file` only when you need full context of a specific file
4. Use `search_files` (grep) only for exact string matches or exhaustive searches

## Index Location

Semble indexes are stored at `~/.semble/`. Indexes persist across sessions — no re-indexing needed on each query.

## Limitations

- Index updates happen on-demand (server-side, no local control)
- Very large codebases may take longer to return results
- Best for exploratory queries, not exhaustive searches

## Examples

**Find where AIAgent is initialized:**
```
semble_search(query="AIAgent __init__ constructor", path=".", top_k=5)
```

**Find workflow/integration patterns:**
```
semble_search(query="workflow integration P0 P1 brain", path=".", top_k=3)
```

**Find related delegate tool code:**
```
semble_find_related(file_path="tools/delegate_tool.py", line=287, path=".", top_k=5)
```

## Related
- [[@action/skills/SKILL-INDEX]]
