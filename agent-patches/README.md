# Agent Core Patches

These files are reference snapshots of the `drewgent-agent` pip package source
with behavioral fixes applied.  They are NOT the canonical source — the pip
package is built from the private `agent/` and `tools/` directories.

## Changes included

| File | Fix |
|------|-----|
| `run_agent.py` | semantic FTS5 fallback, credential state injection, pre-LLM skill matching, key auto-detection, `_fts_safe_query` cross-language fix |
| `auto_learn.py` | removed `_detect_implicit_style` (noise source), restricted `_ANTI_PATTERNS`, removed over-broad `_ENV_PATTERNS` tool match, knowledge.db bridge |
| `prompt_builder.py` | delegation policy MUST-level, SKILLS_GUIDANCE extended with load instruction |
| `model_tools.py` | added `tools.credential_tool` to module discovery |
| `toolsets.py` | added `credential_provision` to core tools |
| `memory_tool.py` | add/replace → knowledge.db bridge (FTS5 write) |
| `credential_tool.py` | **NEW** — credential provisioning tool + auto-detection |

## To apply

```bash
# These files go into your drewgent-agent package source.
# For pip-installed users, copy the relevant sections manually:
# - run_agent.py: _fts_safe_query, _read_credential_state, injection blocks
# - auto_learn.py: _ANTI_PATTERNS, _ENV_PATTERNS, _detect_implicit_style removal
# - prompt_builder.py: build_skills_system_prompt header, SKILLS_GUIDANCE
# - tools/memory_tool.py: _write_to_knowledge_db calls
# - tools/credential_tool.py: entire new file
```
