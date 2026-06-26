---
title: reference-gap-assessment
name: reference-gap-assessment
description: Evaluate the user's system/expertise against an external article, framework, book, or paper. Extracts the reference's conceptual framework, maps each dimension to the user's context, and delivers an evidence-based scored assessment with actionable gaps.
type: skill
domain: assessment
tags: [skill, assessment, framework, gap-analysis, evaluation]
created: 2026-06-11
updated: 2026-06-11
links:
  - "[[@identity/persona/writing-style-guide]]"
  - "[[skills/harsh-critic]]"
  - "[[skills/software-development/codebase-structure-audit]]"
  - "[[@identity/brain/rules]]"---

# reference-gap-assessment

When the user shares an external article, paper, framework, or book and asks **"how am I doing against this?"** or **"evaluate my system against this"**, use this skill.

## Trigger Conditions

- User shares a URL or reference and asks for assessment ("어떻게 보니?", "어느 정도 반영되고 있나?")
- User describes a framework and asks to be evaluated against it
- Session goal involves comparing user's work against an external standard

## Core Principle

> **Extract → Map → Score → Gap.**

The user values **honest partial scores**, not blanket "looks good." Every dimension gets a concrete score with evidence. Every gap gets a specific recommendation. The output format follows the user's preference for **evidence-based assessment** with a clear "what's good / what's missing / what's next" structure.

## User Preference Embedding

- **"정직한 부분-점수 답변" 선호**: Score each dimension separately (e.g. 7/10), never give a vague overall "looks good." Every score must have supporting evidence.
- **옵션 + "내 추천" framing**: After presenting gaps, offer 1-2 concrete improvement ideas with "내 추천" label.
- **근거 우선**: Claims must be backed by specific examples from the user's system (code, files, previous decisions, memory records). "I think" without evidence is weak.
- **최종 요약**: End with a compact table (dimension | score | evidence) for quick scanability.

## Workflow

### Phase 1: Extract the Framework

1. **Read the full reference** — fetch the article/paper/book. If the content is blocked or paywalled, search for summaries, translations, or discussions.
2. **Identify the core framework** — most articles have 3-7 organizing concepts. Extract them as named dimensions. Example: `recognition taste / compass taste / vision taste`, `zone 1-5`.
3. **Note the author's key evidence** — what examples does the author use? These are the benchmarks.
4. **Separate signal from noise** — not every paragraph is a dimension. Ignore filler.

Output of this phase: A clear list of assessment dimensions with definitions and reference examples.

### Phase 2: Map to User's System

For each dimension:

1. **Search for evidence in the user's system**:
   - Code/config files in `~/.drewgent/` and `~/.hermes/`
   - Memory entries (signal patterns, past decisions)
   - Skill library (what skills exist, what conventions are encoded)
   - Architecture decisions (P0-P6 layers, customize layer, kanban board)
   - Session history for past decisions and corrections

2. **Classify alignment**:
   - **Strong match** — explicit implementation or design choice that embodies the dimension
   - **Partial match** — some elements present but not fully systematic
   - **Gap** — absent, or the user's approach contradicts the dimension
   - **Not applicable** — the dimension doesn't apply to the user's context

3. **Collect concrete evidence** for each classification:
   - Strong match: `"customize layer at ~/.drewgent/customize/ proxies hermes_cli — compass taste"`
   - Partial match: `"3-phase QA exists but no PR-prompt coupling — partial zone 3"`
   - Gap: `"no AGENTS.md equivalent — gap in zone 5"`

### Phase 3: Score and Structure

For each dimension, assign a score (0-10 scale):

| Score | Meaning |
|-------|---------|
| 9-10 | Fully embodied; would serve as example for others |
| 7-8 | Strong; minor refinement possible |
| 5-6 | Present but not systematic; significant room |
| 3-4 | Early stage; surface-level only |
| 1-2 | Barely present |
| 0 | Absent or contradictory |

Output format per dimension:

> **{Dimension name} — {Score}/10**
> **Evidence**: {specific files, decisions, patterns}
> **Assessment**: {analysis in 2-3 sentences}
> **Gap**: {what's missing, if anything}

### Phase 4: Synthesize with Honest Assessment

1. **Start with the strongest dimensions** — the user's system has real strengths. Lead with what's working.
2. **Present gaps honestly** — use "표면적 작동 + N개 미해결" format.
3. **End with practical next steps** — 1-2 "내 추천" items that are concrete, not abstract.

Final output shape:

```
## 전반적 평가: {summary}

{Strengths paragraph}

### Dimension-by-Dimension

| Dimension | Score | Key Evidence |
|-----------|-------|-------------|
| Recognition taste | 9/10 | 리팩토링 원칙, root cause 추적 |
| ... | ... | ... |

### 내 추천 ({N}개)
1. {specific recommendation} — {why it matters}
2. {specific recommendation} — {why it matters}
```

## Reference Material Format

When saving external frameworks as reference files under `references/`, use:

```markdown
# {Reference Name} — Framework Summary

**Source**: {URL}
**Author**: {Name}
**Published**: {Date}

## Core Framework

### Dimension 1: {name}
**Definition**: {1-2 sentences}
**Author's benchmark**: {specific example from reference}

### Dimension 2: {name}
...

## Key Examples from Reference

| Example | What it demonstrates | Dimension |
|---------|---------------------|-----------|
| Codex chose Rust | Team culture effects of language choice | Recognition taste |

## Vocabulary
- {Term} — {definition, source context}
```

## Related

- [[skills/harsh-critic]] — completion bias defense (complementary, focuses on agent output)
- [[skills/software-development/codebase-structure-audit]] — code-level audit methodology
- [[@identity/persona/writing-style-guide]] — communication tone for Korean assessments
