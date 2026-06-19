---
name: neuron-fs-brain
description: NeuronFS-style brain governance for Drewgent. Manages filesystem-based AI constraints via folder structure and special tokens (vorq, 禁).
version: 1.0.0
author: drewgent-core
license: MIT
metadata:
  drewgent:
    tags: [neuronfs, brain, governance, constraints, filesystem, vorq, brain-management]
    category: brain
links:
  - "[[P3-sensors/skills/SKILL-INDEX]]"
  - "[[neuronfs-governance-defaults]]"
  - "[[neuronfs-subsumption-ordering]]"
  - "[[P4-cortex/knowledge/NEURONFS_RULES]]"
  - "[[P0-brainstem/brain/rules]]"
  - "[[brain/vault-naming-convention]]"
---

# NeuronFS Brain Governance

This skill implements NeuronFS-style brain governance for Drewgent, treating the filesystem as a constraint engine where folder structure and special tokens force AI behavior.

## Overview

NeuronFS (Neuron Filesystem) is a governance pattern where:
- **Folders = Constraints** — Directory structure defines rules
- **Files = Rules** — `.neuron` files contain rule definitions
- **Naming = Enforcement** — Special prefixes trigger behavior

## Key Concepts

### The vorq Harness

`vorq` = "value-or-lookup" — When the AI encounters an unknown governance token, it MUST look up the definition before proceeding.

Example:
```
禁console_log 必vorq
```

This means: "The token `禁console_log` requires lookup before any action involving console.log"

### The 禁 Micro-Opcode

`禁` (Chinese character for "forbid") = NEVER_DO directive

- Single Chinese character carries 8 characters of meaning
- Forces AI to recognize forbidden patterns instantly
- Example: `禁secrets` → "NEVER do this: hardcoded secrets"

### 7-Layer Subsumption

The brain is organized in 7 layers with strict priority:

| Priority | Layer | Purpose |
|----------|-------|---------|
| **1 (HIGHEST)** | P0-brainstem | Survival, safety, NEVER-DO rules |
| 2 | P1-limbic | Values, tone, emotional constraints |
| 3 | P2-hippocampus | Memory patterns, context |
| 4 | P3-sensors | Tool routing, platform hints |
| 5 | P4-cortex | Skills, workflows, learning |
| 6 | P5-ego | Identity, personality |
| 7 (LOWEST) | P6-prefrontal | Strategy, planning |

**Critical**: P0 rules OVERRIDE all other layers. The brainstem doesn't negotiate.

## Brain Structure

```
~/.drewgent/brain/<name>/
├── P0-brainstem/           # CRITICAL: never-do rules
│   ├── 禁/                # Forbidden pattern subdirectories
│   │   ├── secrets_in_code/
│   │   │   └── rule.neuron
│   │   └── rm_rf_root/
│   │       └── rule.neuron
│   ├── bomb.neuron        # Kill switches for entire layers
│   └── imperatives.neuron # Must-do rules
├── P1-limbic/            # Values and style
│   └── values.neuron
├── P2-hippocampus/       # Memory constraints
│   └── memory.neuron
├── P3-sensors/           # Tool routing
│   └── routing.neuron
├── P4-cortex/            # Patterns and skills
│   ├── patterns.neuron
│   └── workflows.neuron
├── P5-ego/               # Identity
│   └── identity.neuron
└── P6-prefrontal/         # Strategy
    └── strategy.neuron
```

## Brain Management Commands

### Initialize a Brain
```
/brain init <name>
```

Creates a new brain with the 7-layer structure.

Example:
```
/brain init myproject
```

### Activate a Brain
```
/brain activate <name>
```

Sets the active brain that will be loaded into the system prompt.

### List Brains
```
/brain list
```

Shows all available brains with their stats.

### Emit Brain
```
/brain emit
```

Displays the current active brain's content.

### Fire (Strengthen) a Neuron
```
/brain fire <path>
```

Increments the weight of a neuron, making its rules stronger.

Example:
```
/brain fire P0-brainstem/禁secrets_in_code
```

### Bomb (Kill) a Neuron
```
/brain bomb <path>
```

Creates a kill switch that disables a neuron path.

Example:
```
/brain bomb P4-cortex/patterns/bad_pattern
```

### Visualize Brain
```
/brain diag
```

Displays the brain structure as a tree diagram.

## Creating Rule Files

### Basic Rule Structure

Create `.neuron` files anywhere in the brain structure:

```markdown
# Rule: 禁console_log
# Token: 禁console_log
# Priority: P0

FORBIDDEN: console.log, print, System.out in production code

REASON: 
- Pollutes production logs
- Leaks debugging info
- Performance impact

EXCEPTIONS:
- Test files (*.test.js, *_test.py)
- Development-only code under #ifdef DEBUG

REPLACEMENT:
- Use structured logging: logging.info(), winston.info(), etc.
- Log levels: DEBUG < INFO < WARN < ERROR

ENFORCEMENT:
- Check for console.log before any file save
- Suggest logging library import if missing
```

### vorq Token Rules

For tokens that require lookup:

```
TOKEN: 禁my_pattern
TYPE: vorq
CONDITION: Before any action matching "my_pattern"
ACTION: 
1. Check ~/.drewgent/brain/active/禁/my_pattern/
2. Load rule.neuron content
3. Verify conditions are met
4. Proceed only if rules pass
DEFAULT: If no rule found, FORBID the action
```

## Governance Constants

These are hard-coded runes (constants) that cannot be overridden:

### Forbidden Micro-Opcodes
- `禁` — NEVER_DO prefix
- `禁secrets` — Never hardcode secrets
- `禁rm_rf` — Never recursive delete root
- `禁blind_write` — Never write without reading

### Mandate Micro-Opcodes
- `命` — MUST_DO prefix
- `命secure_defaults` — Security is mandatory
- `命verify` — Verify before action
- `命log` — Log significant actions

### Value Micro-Opcodes
- `值` — PREFERENCE prefix
- `值clarity` — Prefer clear over clever
- `值brevity` — Be concise
- `値documentation` — Document non-obvious code

## Wikilink Naming Convention

Obsidian vault에서 P-layer 간 wikilink는 **full canonical path**를 사용해야 한다. 이는 NeuronFS의 두 가지 원칙을 지키기 위함이다.

### 원칙 1: Layer Identity 보존

NeuronFS에서 P-layer는 단순한 폴더 경로가 아니라 **우선순위와 정체성**이다:

```
[[P0-brainstem/brain/rules]]     ← P0, brainstem layer
[[P1-limbic/persona/SOUL]]      ← P1, limbic layer
[[P5-ego/SELF_MODEL]]           ← P5, ego layer
[[P4-cortex/knowledge/NEURONFS_RULES]] ← P4, cortex layer
```

short name(`[[rules]]`, `[[SOUL]]`)은 layer 정보를 소멸시킨다 — `[[SOUL]]`이 P1인지 P5인지 알 수 없다.

### 원칙 2: 이름 충돌 회피

Drewgent vault에는 중복 파일명이 존재한다:

| Short name | 중복 수 | Canonical path (올바른 링크) |
|------------|---------|------------------------------|
| `[[SOUL]]` | **4** | `[[P1-limbic/persona/SOUL]]` |
| `[[index]]` | **29** | `[[P2-hippocampus/memories/index]]` |
| `[[SCHEMA]]` | **3** | `[[P2-hippocampus/memories/SCHEMA]]` |
| `[[SKILL]]` | **316** | 사용 금지 — `[[skills/<category>/<name>/SKILL]]` 사용 |

Obsidian은 short name `[[SOUL]]`에 대해 **일관된 해석을 보장하지 않는다** — 같은 vault에서도 상황에 따라 다른 파일로 연결될 수 있다.

### 적용 규칙

1. **P-layer wikilink는 반드시 full canonical path 사용**:
   ```
   ✅ [[P0-brainstem/brain/rules]]
   ❌ [[rules]]
   
   ✅ [[P1-limbic/persona/writing-style-guide]]
   ❌ [[writing-style-guide]]
   ```

2. **스킬 SKILL.md 링크는 카테고리 포함**:
   ```
   ✅ [[skills/devops/kanban-worker/SKILL]]
   ❌ [[SKILL]]  (316개 중복 — 절대 금지)
   ```

3. **금지 패턴**: 어떤 P-layer 파일도 short name만으로 링크하지 않는다. Obsidian이 추측하게 놔두지 않는다.

4. **검증**: wikilink 추가 후 `grep -r '\[\[SOUL\]\]'` 등으로 short name 사용 잔여를 확인하고 수정한다.

## Subsumption Enforcement

Rules are enforced in strict priority order:

1. **Check P0 first** — If P0 forbids, stop immediately
2. **Check P1-P4** — Apply constraints in order
3. **Check P5-P6** — Apply as guidelines only
4. **Log all decisions** — Track rule applications

Example decision flow:
```
User asks: "Write a function that logs to console"

1. Check P0: Any 禁console_* rules?
   → Found: 禁console_log_production
   → Action: FORBID (unless in test/dev context)
   
2. Result: Block console.log, suggest logging library
```

## Integration with Drewgent

The brain is loaded into the system prompt via:

1. `/brain activate <name>` sets the active brain
2. `brain_load()` in `agent/prompt_builder.py` reads active brain
3. Brain content is rendered after `SESSION_SEARCH_GUIDANCE`
4. P0 rules appear first in the prompt (highest priority)

## Example Brain Setup

### Step 1: Initialize
```bash
/brain init myproject
```

### Step 2: Add Rules
Create files in the appropriate layers:
```
~/.drewgent/brain/myproject/P0-brainstem/禁secrets_in_code.neuron
~/.drewgent/brain/myproject/P1-limbic/professional_tone.neuron
~/.drewgent/brain/myproject/P4-cortex/python_patterns.neuron
```

### Step 3: Activate
```bash
/brain activate myproject
```

### Step 4: Verify
```bash
/brain diag
```

## Best Practices

1. **Start with P0 rules** — Define safety constraints first
2. **Use specific tokens** — `禁secrets_in_code` > `禁secrets`
3. **Document exceptions** — Not everything is absolute
4. **Fire frequently-used rules** — Strengthen common patterns
5. **Use bombing sparingly** — It's a kill switch, not a delete

## Troubleshooting

### Brain not loading?
- Check `/brain list` shows the brain
- Run `/brain activate <name>`
- Verify `~/.drewgent/brain/active_brain.txt` exists

### Rules not enforced?
- Rules must be in `.neuron`, `.md`, or `.rule` files
- Check for `bomb.neuron` disabling the path
- Verify P0 rules are loaded first

### Need to disable a rule temporarily?
```bash
/brain bomb P4-cortex/my_temp_rule
```

To re-enable:
```bash
/brain unbomb P4-cortex/my_temp_rule
```

---

## Agent Navigation & Provenance

NeuronFS brain governance 외에도, Drewgent의 **에이전트 내비게이션과 결정 맥락 기록**은 `AGENTS.md`에 통합되어 있다.

### AGENTS.md

`~/.drewgent/AGENTS.md`는 현재 아키텍처, 파일 구조, 에이전트가 참조해야 할 문서들을 정의한 **agent-first navigation guide**다. 이 파일은 세션 시작 시 컨텍스트에 자동 로드된다.

핵심 내용:
- Current architecture (customize layer, NOT fork)
- Agent navigation guide (what to read, what not to touch)
- Provenance convention (결정 맥락 기록 규칙)
- Kanban leverage score convention
- Known pitfalls (Python 3.14 json bug, macOS bash, launchd plist)

### Provenance Convention

모든 artifact(skill, memory, config 변경) 생성 시 **trigger/context**를 frontmatter나 content에 기록한다:

```
---
title: skill-name
trigger: "why this skill exists"
provenance:
  session: "YYYY-MM-DD topic"
  decision: "design rationale"
---
```

자세한 규칙은 `AGENTS.md` 참조.

### Taste Framework Reference

`references/taste-framework.md`는 Pratik Bhavsar의 "How to Be a 30x AI Engineer with a Taste"를 요약한 참고 자료다. Recognition/Compass/Vision taste의 세 가지 형태와 5가지 가치 창출 영역을 정의하며, Drewgent의 아키텍처 결정을 평가하는 프레임워크로 사용할 수 있다.

---

## Related Skills

- `neuronfs-governance-defaults` — Default security rules
- `neuronfs-subsumption-ordering` — Layer priority explanation