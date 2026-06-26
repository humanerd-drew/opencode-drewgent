## Skill Cross-Linking Technique

~80 new wikilinks added across 5 clusters (software-development refactoring/planning/debugging, brain NeuronFS, mlops training).

### Technique: related_skills Metadata → wikilinks

Many skills had `related_skills` arrays in their `metadata.hermes` section but no actual `links:` frontmatter, so the relationships existed only as machine-readable metadata — not as Obsidian graph edges.

**Detection**:
```bash
# Find skills with related_skills but no links section
grep -l 'related_skills' ~/.drewgent/skills/software-development/*/SKILL.md | while read f; do
  has_links=$(grep -c '^links:' "$f")
  related=$(grep -A1 'related_skills:' "$f" | tail -1)
  [ "$has_links" -eq 0 ] && echo "$(basename $(dirname $f)): $related"
done
```

**Conversion**: For each related_skills entry, add a `links:` section with actual wikilink paths.

### Cluster-Specific Additions

| Cluster | Skills | Avg Links (before → after) |
|---------|--------|---------------------------|
| SD refactoring | codebase-refactoring, incremental-refactoring, codebase-structure-audit, codebase-consolidation, simplify-code, project-code-audit | 0 → 7.0 |
| SD planning | tdd, requesting-code-review, writing-plans, plan, spike | 1 → 6.4 |
| SD debugging | systematic-debugging, python-debugpy, node-inspect-debugger | 1 → 3.0 |
| brain NeuronFS | neuron-fs-brain, neuronfs-governance-defaults, neuronfs-subsumption-ordering | 0 → 5.0 |
| mlops training | axolotl, unsloth, peft, trl-fine-tuning, grpo-rl-training, pytorch-fsdp | 0 → 3.3 |
| creative | architecture-diagram, baoyu-infographic, claude-design, comfyui, design-md, humanizer, pretext, sketch, touchdesigner-mcp | 0 → 5.0 |
| mlops/inference | gguf, guidance, obliteratus, outlines, vllm | 0 → 5.0 |
| mcp | mcporter, native-mcp, gbrain-integration-drewgent | 0 → 5.0 |
| social-media | xitter, xurl | 0 → 5.0 |
| apple | macos-computer-use | 0 → 4.0 |

### Skills → P-Layer Rules Mapping

After cluster cross-linking, all 121 SKILL.md files received `[[@identity/brain/rules]]` in their frontmatter `links:` section (71 newly added, 50 already present). This creates a universal governance link from every skill to the P0 rules that constrain it.

### Fix: related_skills Metadata → Actual Links

Many Hermes-bundled skills had `metadata.hermes.related_skills` arrays that never created graph edges. The fix:

### Broken Link Discovered

When verifying `[[@memory/memories/insights/index]]`, the file didn't exist (referenced by SCHEMA.md but never created). Created `insights/index.md` to resolve.

### YAML Frontmatter Note

Some SKILL.md files have `links: []` followed by a second `links:` — YAML uses the last value, so only the second takes effect. This is harmless but should be cleaned up when editing the file.
