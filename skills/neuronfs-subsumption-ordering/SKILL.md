---
name: neuronfs-subsumption-ordering
description: Maps NeuronFS 7-layer brain architecture to Drewgent prompt layers. Explains how P0-brainstem rules override all others.
version: 1.0.0
author: drewgent-core
license: MIT
metadata:
  drewgent:
    tags: [neuronfs, subsumption, brain, architecture, layers]
    category: brain
links:
  - "[[@action/skills/SKILL-INDEX]]"
  - "[[neuron-fs-brain]]"
  - "[[neuronfs-governance-defaults]]"
  - "[[@memory/knowledge/NEURONFS_RULES]]"
  - "[[@identity/brain/rules]]"
---

# NeuronFS Subsumption Architecture

This skill explains how NeuronFS-style brain governance maps to Drewgent's prompt architecture, specifically the 7-layer subsumption hierarchy where P0 overrides all other layers.

## The Subsumption Principle

**Higher layers cannot override lower layers.** In a subsumption architecture, the lowest layer (P0-brainstem) has the highest priority. Rules at P0 must be obeyed regardless of what higher layers say.

This is modeled after biological neural architectures where the brainstem (survival center) overrides the prefrontal cortex (planning center). You don't "decide" to stop breathing when you're thinking about dinner.

## 7-Layer Mapping

| Layer | Name | Drewgent Prompt Section | Priority |
|-------|------|------------------------|----------|
| **P0** | brainstem | System prompt TOP (before identity) | **HIGHEST** |
| **P1** | limbic | Tool-use enforcement | HIGH |
| **P2** | hippocampus | Memory guidance | MEDIUM-HIGH |
| **P3** | sensors | Platform hints | MEDIUM |
| **P4** | cortex | Skills index | MEDIUM |
| **P5** | ego | SOUL.md / identity | LOW |
| **P6** | prefrontal | Context files (AGENTS.md) | LOWEST |

## Layer Descriptions

### P0-brainstem: Survival & Safety (CRITICAL)

The brainstem controls involuntary survival functions. In AI governance:

- **NEVER-DO rules** must be enforced absolutely
- **Bomb kill switches** disable entire subtrees
- **禁 (禁) tokens** mark forbidden patterns
- No exception mechanism — P0 rules are absolute

**Example rules:**
- Never commit secrets to version control
- Always validate user input
- Fail securely (deny by default)
- Never delete without confirmation

### P1-limbic: Emotional & Values (HIGH)

The limbic system handles emotional responses and values. In governance:

- Tone and style constraints
- Value-based decision rules
- Communication standards
- Brand voice enforcement

**Example rules:**
- Maintain professional tone in user communication
- Prefer constructive feedback over criticism
- Use inclusive language
- Be direct but respectful

### P2-hippocampus: Memory & Context (MEDIUM-HIGH)

The hippocampus encodes memories and context. In governance:

- Session context boundaries
- Recall patterns for past interactions
- Memory operation rules
- Context preservation

**Example rules:**
- Don't forget user preferences
- Use session_search before asking for clarification
- Preserve context across turns
- Archive significant decisions

### P3-sensors: Input & Tool Routing (MEDIUM)

Sensors route input signals. In governance:

- Tool availability detection
- Platform-specific behavior
- Input format validation
- API routing rules

**Example rules:**
- Route file operations to appropriate tools
- Detect platform (CLI vs gateway) and adapt
- Validate input formats before processing
- Use platform-appropriate commands

### P4-cortex: Learning & Patterns (MEDIUM)

The cortex handles learned patterns and skills. In governance:

- Workflow patterns
- Skill recommendations
- Code style patterns
- Common solution templates

**Example rules:**
- After complex tasks, offer to save as skill
- Follow established project patterns
- Use language-specific idioms
- Apply DRY principle to repeated code

### P5-ego: Identity & Self (LOW)

The ego represents self-identity. In governance:

- SOUL.md identity
- Personality traits
- Voice characteristics
- Communication style

**Example rules:**
- Follow SOUL.md personality directives
- Adapt voice to user preferences
- Maintain consistent identity across sessions

### P6-prefrontal: Planning & Strategy (LOWEST)

The prefrontal cortex handles high-level planning. In governance:

- AGENTS.md project context
- High-level strategy goals
- Cross-cutting concerns
- Long-term objectives

**Example rules:**
- Follow AGENTS.md project guidelines
- Pursue stated project goals
- Balance multiple objectives
- Consider long-term maintainability

## Override Examples

### Example 1: P0 overrides P5 (ego)

**P5 (ego) says:** "Be playful and use humor"

**P0 (brainstem) says:** "禁offensive_humor — Never make jokes that could be interpreted as mocking users"

**Result:** No offensive humor, even if it would be "funny" — P0 overrides P5's playfulness directive.

### Example 2: P0 overrides P6 (prefrontal)

**P6 (prefrontal) says:** "Optimize for code brevity"

**P0 (brainstem) says:** "命secure_defaults — Security is non-negotiable"

**Result:** Secure code even if verbose, even if P6 suggests brevity optimization.

### Example 3: P1 overrides P4 (cortex)

**P4 (cortex) says:** "Reuse this pattern from the codebase"

**P1 (limbic) says:** "命secure_defaults — Security by default"

**Result:** Don't reuse patterns that violate security, even if they're established in the codebase.

## Brain Loading Order

The brain is loaded layer-by-layer in ascending order (P0 first):

```
1. Load P0-brainstem rules (render first = highest priority)
2. Load P1-limbic rules
3. Load P2-hippocampus rules
4. Load P3-sensors rules
5. Load P4-cortex rules
6. Load P5-ego rules
7. Load P6-prefrontal rules
```

When rendering the system prompt:
- P0 content appears at the TOP (after identity)
- Later layers append below
- The AI reads top-to-bottom, giving earlier content more weight

## Implementation in Drewgent

```
~/.drewgent/brain/<name>/
├── P0-brainstem/     # Rendered FIRST → highest priority
│   ├── 禁/          # Forbidden patterns
│   ├── bomb.neuron  # Kill switches
│   └── imperatives.neuron  # Must-do rules
├── P1-limbic/        # Rendered SECOND
│   └── values.neuron
├── P2-hippocampus/   # Rendered THIRD
│   └── memory.neuron
├── P3-sensors/       # Rendered FOURTH
│   └── routing.neuron
├── P4-cortex/        # Rendered FIFTH
│   ├── patterns.neuron
│   └── skills.neuron
├── P5-ego/           # Rendered SIXTH
│   └── identity.neuron
└── P6-prefrontal/    # Rendered LAST → lowest priority
    └── strategy.neuron
```

## Managing Priority

### Strengthening a Rule
```bash
/brain fire P0-brainstem/禁secrets_in_code
```
Each fire increments the weight, making the rule harder to override.

### Killing a Rule (Kill Switch)
```bash
/brain bomb P4-cortex/patterns/bad_pattern
```
Bombing a path disables it entirely — no rules in that subtree apply.

### Creating New Rules
Place rules in the appropriate layer:
- Security rules → P0-brainstem
- Style/tone rules → P1-limbic
- Memory rules → P2-hippocampus
- Tool routing → P3-sensors
- Workflows → P4-cortex
- Identity → P5-ego
- Strategy → P6-prefrontal

## Key Takeaways

1. **P0 rules are absolute** — They override everything
2. **Lower priority doesn't mean unimportant** — P6 handles high-level goals
3. **Higher layers reference lower layers** — P5 might reference P0 for exceptions
4. **Bombing disables entire subtrees** — Use sparingly, for emergency shutdown
5. **Neuron firing strengthens patterns** — Frequently-used rules get higher weight
