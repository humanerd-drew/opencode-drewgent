---
title: OpenCrab Ontology Pilot — P0-brainstem Schema Implementation
type: document
space: growth
tags: [growth, projects]
created: 2026-05-20
updated: 2026-05-20
aliases:
  - /projects/ontology-pilot
links:
  - "[[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁/禁brain_obsidian_graph.neuron]]"
  - "[[P0-brainstem/brain/rules]]"
  - "[[P0-brainstem/p0-brain-ontology.jsonl]]"
  - "[[P4-cortex/growth/INTEGRATION_PROTOCOL]]"
  - "[[P4-cortex/growth/P0-brainstem-pilot-plan]]"
  - "[[P4-cortex/knowledge/NEURONFS_RULES]]"
  - "[[P5-ego/SELF_MODEL]]"
---



# OpenCrab Ontology Pilot — P0-brainstem Schema Implementation

**Date**: 2026-05-20
**Status**: Phase 1 Complete
**Source**: [AlexAI-MCP/OpenCrab](https://github.com/AlexAI-MCP/OpenCrab)

---

## Background: What is OpenCrab

OpenCrab은 MetaOntology OS의 public integration repository이다.
LocalCrab(로컬 온톨로지 팩토리) + OpenCrab SaaS(에코시스템 배포)로 구성된다.

핵심 개념: **9 Space Ontology** — 모든 노드를 semantic space로 분류하여 그래프 구조를 형성한다.

### OpenCrab 9-Space

| Space | Role |
|-------|------|
| subject | Actors with identity, agency, roles, permissions |
| resource | Documents, datasets, tools, APIs, files, projects |
| evidence | Raw observations, logs, text units, parser/OCR outputs |
| concept | Entities, concepts, topics, classes, domain abstractions |
| claim | Derived assertions grounded by evidence |
| community | Clusters and summaries of related concepts or actors |
| outcome | KPIs, risks, impacts, measurable results |
| lever | Tunable controls that affect outcomes or concepts |
| policy | Access, sensitivity, approval, governance rules |

### 핵심 도구 (MCP Tools)

- `ontology_manifest` — grammar 전체 반환
- `ontology_add_node` — grammar 검증된 노드 추가
- `ontology_add_edge` — grammar 검증된 엣지 추가
- `ontology_query` — hybrid vector + BM25 + graph query
- `ontology_impact` — I1-I7 impact analysis
- `ontology_rebac_check` — relationship-based access check
- `ontology_ingest` — local ontology store에 텍스트 ingestion
- `harness_promotion_apply` — CrabHarness promotion package 적용

### Pack v1 Format

```
manifest.json
graph/nodes.jsonl
graph/edges.jsonl
evidence/index.jsonl
quality/report.json
neo4j/import.cypher
neo4j/opencrab_ingest.jsonl
neo4j/export_status.json
README.md
sample_queries.json
community_reports.json
```

---

## Loragent Pilot: What Was Applied

### Phase 1 (완료 — 2026-05-20)

P0-brainstem의 `.neuron` 파일 14개에 typed frontmatter schema 도입:

```yaml
---
title: 禁{rule_name}
type: policy
space: policy
rule_token: {token_name}
rule_priority: P0 (HIGHEST)
rule_source: {source}
created: 2026-05-20
updated: 2026-05-20
promotion_status: validated
links:
  - "[[P0-brainstem/brain/rules]]"
  - "[[P5-ego/SELF_MODEL]]"
  - "[[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁/禁brain_obsidian_graph.neuron]]"
---
```

### 적용된 파일 (14개)

**Group A (10개)**: `P0-brainstem/brain/Loragent-brain/P0-brainstem/`
- 禁auto_validate.neuron
- 禁blind_write.neuron
- 禁console_log.neuron
- 禁filesystem_truth.neuron
- 禁karpathy_coding_principles.neuron
- 禁rm_rf_root.neuron
- 禁secrets_in_code.neuron
- 禁subagent_verify.neuron
- 禁task_qa_gate.neuron
- 禁tool_integration_3file.neuron

**Group B (4개)**: `P0-brainstem/brain/Loragent-brain/P0-brainstem/禁/`
- 禁brain_obsidian_graph.neuron
- 禁kanban_hallucination.neuron
- 禁kanban_worker_accountability.neuron
- 禁task_qa_gate.neuron

**rules.md** 업데이트 (links 확장, promotion_status 추가)

### Graph Export

`P0-brainstem/p0-brain-ontology.jsonl` — 14개 노드의 그래프 표현:

```json
{"id": "禁rm_rf_root", "type": "policy", "space": "policy", "title": "禁rm_rf_root", "file": "brain/Loragent-brain/P0-brainstem/禁rm_rf_root.neuron", "links": ["P0-brainstem/brain/rules", "P5-ego/SELF_MODEL", "P0-brainstem/brain/Loragent-brain/P0-brainstem/禁/禁brain_obsidian_graph"], "rule_priority": "P0 (HIGHEST)", "rule_source": "NeuronFS Governance Defaults"}
```

### Bidirectional Linking 검증

- 모든 .neuron → rules (hub), SELF_MODEL, 禁brain_obsidian_graph 연결
- rules.md → 12개 wikilink (.neuron 14개 참조, 중복 제외 12개 고유)
- orphan .neuron: 0개

---

## Current Loragent Schema

### Frontmatter Fields

| Field | Source | Description |
|-------|--------|-------------|
| title | OpenCrab-inspired | Neuron 파일명 |
| type | OpenCrab-inspired | policy / concept / resource 등 |
| space | OpenCrab (9-space) | 모든 P0 규칙은 `space: policy` |
| rule_token | Loragent native | 고유 규칙 식별자 |
| rule_priority | Loragent native | P0 (HIGHEST) |
| rule_source | Loragent native | 규칙 출처 |
| created | Loragent native | 생성일 |
| updated | Loragent native | 수정일 |
| promotion_status | Loragent native | validated / draft / deprecated |
| links | Loragent native | wikilink 연결 목록 |

### space 분류 (현재)

Loragent Pilot Phase 1에서는 모든 P0 규칙을 `space: policy`로統一.

향후 확장을 위해 제안된 분류:
- `space: policy` — 금지/강제 규칙 (禁*)
- `space: concept` — 원칙/가이드 (karpathy_coding_principles)
- `space: evidence` — QA 증거/로그 (qa-evidence)
- `space: resource` — 도구/스킬 정의
- `space: claim` — rules.md (규칙 인덱스)

---

## Phase 2: 완료된 작업 (전체 vault로 확장)

### Phase 2-A: 9-Space 확장 ✅ 완료

규칙을 semantic space로 세분화 완료:
- `禁karpathy_coding_principles` → space: concept
- `禁task_qa_gate` (2개) → space: evidence
- 나머지 11개 → space: policy

전체 vault (P0-P6 + skills + memories 등): 5,014개 노드 중 5,013개 (99.98%) space: 보유

### Phase 2-B: ontology_query tool ✅ 완료

`P4-cortex/scripts/ontology_query.py` + `skills/brain/ontology-query/SKILL.md` 생성됨.

8개 명령: `list`, `spaces`, `rule`, `links`, `graph`, `search`, `orphans`, `space`

### Phase 2-C: ReBAC enforcement ✅ 완료

- `禁rebac_integration` — INTEGRATION_PROTOCOL 참조 없이 tool/skill 통합 시 awareness.integrity event
- `禁rebac_kanban` — KANBAN_INDEX 참조 없이 kanban 작업 시 awareness.integrity event

```yaml
# 예: 禁karpathy_coding_principles
space: concept  # 원칙/가이드

# 예: 禁rm_rf_root
space: policy  # 금지 규칙 (유지)

# 예: 禁task_qa_gate
space: evidence  # QA 증거/프로세스
```

### Phase 2-B: ontology_query tool (선택)

JSONL 기반 그래프 쿼리:
- `space:policy`인 모든 규칙 조회
- 특정 rule_token으로 노드 조회
- links 기반 그래프 탐색

### Phase 2-C: ReBAC enforcement (선택)

OpenCrab의 relationship-based access check 패턴 적용:
- `禁tool_integration_3file` → INTEGRATION_PROTOCOL 참조 시에만 도구 추가 허용
- `禁kanban_*` → KANBAN_INDEX 참조 시에만 kanban 작업 허용

---

## Verification Checklist

```bash
# 1. 모든 .neuron에 frontmatter 존재
find ~/.loragent/P0-brainstem -name "*.neuron" | wc -l
# → 14 (Group A 10 + Group B 4)

# 2. 모든 .neuron에 space: 필드 존재
grep -l "space:" ~/.loragent/P0-brainstem/brain/Loragent-brain/P0-brainstem/*.neuron | wc -l
# → 10

# 3. orphan .neuron 없음
for f in ~/.loragent/P0-brainstem/brain/Loragent-brain/P0-brainstem/*.neuron; do
  grep -q '\[\[' "$f" || echo "ORPHAN: $f"
done
# → (출력 없음)

# 4. JSONL 라인 수
wc -l ~/.loragent/P0-brainstem/p0-brain-ontology.jsonl
# → 14
```

---

## Related Documentation

- [[P0-brainstem/brain/rules]] — P0 Brainstem Rules hub
- [[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁/禁brain_obsidian_graph.neuron]] — Graph integrity rule
- [[P4-cortex/growth/P0-brainstem-pilot-plan]] — Original pilot plan
- [[P0-brainstem/p0-brain-ontology.jsonl]] — Graph export (14 nodes)
- [[P4-cortex/knowledge/NEURONFS_RULES]] — NeuronFS architecture

---

## Source

- OpenCrab GitHub: https://github.com/AlexAI-MCP/OpenCrab
- MetaOntology OS: OpenCrab에 내장된 grammar/schema 시스템
- CrabHarness: evidence collection control plane

---

*Generated by Loragent — 2026-05-20*

## Links
- [[P4-cortex/growth/INTEGRATION_PROTOCOL]]
