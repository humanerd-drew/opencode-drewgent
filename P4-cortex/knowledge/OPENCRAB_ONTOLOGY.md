---
title: OpenCrab Ontology — Loragent 9-Space Mapping
status: published
type: concept
space: concept
tags: [concept]
created: 2026-05-20
updated: 2026-05-20
aliases:
  - /insights/opencrab-ontology
links:
  - "[[P0-brainstem/brain/rules]]"
  - "[[P3-sensors/resolver/RESOLVER]]"
  - "[[P4-cortex/growth/INTEGRATION_PROTOCOL]]"
  - "[[P4-cortex/growth/open-crab-ontology-pilot-20260520]]"
  - "[[P4-cortex/knowledge/NEURONFS_RULES]]"
  - "[[P5-ego/SELF_MODEL]]"
---


# OpenCrab Ontology — Loragent 9-Space Mapping

OpenCrab의 9-space ontology를 Loragent 7-layer subsumption architecture에 매핑한 문서.

## 9 Spaces (OpenCrab)

| Space | Role | Loragent Layer | Enforcement |
|-------|------|----------------|-------------|
| `identity` | Core identity and self-model | P5-ego, P1-limbic | P5 Override P1 |
| `claim` | Plans, incidents, strategic assertions | P6-prefrontal | High priority |
| `concept` | Ideas, principles, knowledge | P4-cortex/knowledge | Pattern-based |
| `policy` | Absolute rules (FORBIDDEN/GUARD) | P0-brainstem | P0 overrides all |
| `workflow` | Step-by-step procedures | P4-cortex/growth (protocol) | Execution path |
| `resource` | Memory, sessions, persistent state | P2-hippocampus | Context window |
| `resolver` | Context routing tables | P3-sensors/resolver | On-demand load |
| `outcome` | Gateway, tools, skills, results | P3-sensors | Execution layer |
| `growth` | Growth patterns, learning, plans | P4-cortex/growth | Evolution track |

## Type Taxonomy

Loragent의 document type taxonomy (OpenCrab-inspired):

| Type | Used in | Description |
|------|---------|-------------|
| `index` | rules.md, SKILL-INDEX.md, SCHEMA.md | Registry / hub document |
| `identity` | SOUL.md, SELF_MODEL.md | Core self description |
| `policy` | .neuron files in P0 | FORBIDDEN/GUARD rules |
| `workflow` | INTEGRATION_PROTOCOL.md | Multi-step procedures |
| `guide` | writing-style-guide.md, KANBAN-USER-GUIDE.md | How-to documents |
| `plan` | growth-2026.md, implementation plans | Planning documents |
| `incident` | cron-job-failure-20260518.md | Incident reports |
| `report` | stabilization_report.md, path-integrity-*.md | Status/analysis reports |
| `concept` | NEURONFS_RULES.md, architecture-dataflow.md | Conceptual explanations |
| `review` | KANBAN-REVIEW-20260520.md, garry-tan-*-review.md | Evaluation documents |
| `resolver` | RESOLVER.md | Context routing table |
| `schema` | SCHEMA.md | Data/memory schema |
| `template` | KANBAN_INCIDENT_TEMPLATE.md | Reusable templates |
| `protocol` | cron-self-healing-protocol.md | Protocol definitions |
| `principle` | obsidian-vault-site-principle.md | Architectural principles |
| `document` | (default) | Generic documents |

## P-Layer → Space Mapping

```
P0-brainstem  → space: policy   (all .neuron files)
P1-limbic     → space: identity  (SOUL, writing-style, persona)
P2-hippocampus → space: resource (memories, sessions, kanban state)
P3-sensors    → space: outcome   (gateway, tools, skills)
P3-sensors    → space: resolver  (RESOLVER.md only)
P4-cortex     → space: growth   (growth/, knowledge/, plans/)
P5-ego        → space: identity  (SELF_MODEL, config)
P6-prefrontal → space: claim    (plans, incidents, strategy)
```

## Exemptions (No OpenCrab schema)

These directories are exempt from ontology injection because their content is externally sourced or auto-generated:

- `P2-hippocampus/memories/insights/` — monthly log, scraped content
- `P2-hippocampus/memories/concepts/` — knowledge wiki
- `P2-hippocampus/memories/entities/` — user/entity pages (already have schema)
- `P2-hippocampus/knowledge/seo-articles/` — scraped SEO content (heritage frontmatter preserved)
- `P3-sensors/cron/output/` — auto-generated cron job outputs
- `P0-brainstem/_agent/MEMORY/archive/` — old session archives

## Runtime Injection (Prompt Builder)

When the agent loads P-layer documents, space/type metadata is used to inject awareness:

```python
SPACE_GUIDANCE = {
    "policy":   "이 문서는 절대 규칙입니다. FORBIDDEN/GUARD 구조를 enforcement합니다.",
    "identity": "이 문서는 Loragent의 정체성입니다. voice와 tone에 영향을 줍니다.",
    "resolver": "이 문서는 컨텍스트 라우팅 테이블입니다. 키워드 매칭에 사용됩니다.",
    "growth":   "이 문서는 성장 패턴입니다. 학습과 패턴 인식에 사용됩니다.",
    "resource": "이 문서는 리소스입니다. 메모리/세션 관련 정보입니다.",
    "outcome":  "이 문서는 결과/출력물입니다. gateway, tools, skills 관련입니다.",
    "concept":  "이 문서는 개념입니다. 설명과 분석에 사용됩니다.",
    "claim":    "이 문서는 주장입니다. 계획과 사고에 사용됩니다.",
}
```

## Obsidian Graph Cluster Behavior

With OpenCrab ontology applied:
- `space: policy` cluster — P0-brainstem rules, tightly interconnected
- `space: identity` cluster — SOUL, SELF_MODEL, writing-style
- `space: growth` cluster — plans, protocols, reviews
- `space: resource` cluster — memories, SCHEMA, kanban index

Each cluster is visually separated in Obsidian graph view while maintaining cross-cluster wikilinks.

## Heritage Content Preservation

SEO articles with existing `heritage: true` frontmatter are preserved unchanged. Their metadata (source_url, keyword, 신뢰도 등급, etc.) is kept as-is. Only non-heritage P-layer files receive space/type injection.

## Related

- [[P5-ego/SELF_MODEL]] — P5-Ego self-awareness (space: identity)
- [[P4-cortex/knowledge/NEURONFS_RULES]] — NeuronFS architecture
- [[P3-sensors/resolver/RESOLVER]] — Context routing (space: resolver)
- [[P0-brainstem/brain/rules]] — P0 Brainstem rules (space: policy)
- [[P4-cortex/growth/INTEGRATION_PROTOCOL]] — Tool/skill integration (space: workflow)
- [[P4-cortex/growth/open-crab-ontology-pilot-20260520]] — P0-brainstem pilot report

---
*Generated by Loragent — 2026-05-20 (OpenCrab ontology full rollout)*