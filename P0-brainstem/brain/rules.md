---
title: P0 Brainstem Rules
type: document
space: concept
tags: [concept]
created: 2026-05-14
updated: 2026-05-20
links:
  - "[[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁/brain-graph-orphan-remediation-20260520]]"
  - "[[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁/禁brain_obsidian_graph.neuron]]"
  - "[[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁/禁kanban_hallucination.neuron]]"
  - "[[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁/禁kanban_worker_accountability.neuron]]"
  - "[[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁rebac_integration.neuron]]"
  - "[[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁rebac_kanban.neuron]]"
  - "[[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁auto_validate.neuron]]"
  - "[[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁blind_write.neuron]]"
  - "[[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁console_log.neuron]]"
  - "[[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁filesystem_truth.neuron]]"
  - "[[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁karpathy_coding_principles.neuron]]"
  - "[[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁rm_rf_root.neuron]]"
  - "[[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁secrets_in_code.neuron]]"
  - "[[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁subagent_verify.neuron]]"
  - "[[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁task_qa_gate.neuron]]"
  - "[[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁tool_integration_3file.neuron]]"
  - "[[P1-limbic/persona/SOUL]]"
  - "[[P3-sensors/gateway/loragent-architecture-dataflow]]"
  - "[[P5-ego/SELF_MODEL]]"
  - "[[禁auto_validate.neuron]]"
  - "[[禁blind_write.neuron]]"
  - "[[禁brain_obsidian_graph.neuron]]"
  - "[[P4-cortex/growth/INTEGRATION_PROTOCOL]]"
  - "[[P2-hippocampus/memories/SCHEMA]]"
  - "[[P4-cortex/knowledge/NEURONFS_RULES]]"
---


# P0 Brainstem — Critical Rules

Loragent의 절대 규칙. P0-brainstem 규칙은 어떤 상위 레이어보다 우선한다.

## 禁 Rules (Never-Do)

| Rule | 설명 |
|------|------|
| [[禁rm_rf_root.neuron]] | `rm -rf /`, `rm -rf ~`, `rm -rf ./*` 금지 |
| [[禁blind_write.neuron]] | 파일 읽기 없이 쓰기 금지 |
| [[禁task_qa_gate.neuron]] | QA 검증 없이 작업 완료 금지 |
| [[禁secrets_in_code.neuron]] | API 키/토큰 하드코딩 금지 |
| [[禁auto_validate.neuron]] | 위험 명령 자동 검증 금지 |
| [[禁console_log.neuron]] | production에서 console.log 금지 |
| [[禁subagent_verify.neuron]] | subagent 출력 검증 없이 수락 금지 |
| [[禁filesystem_truth.neuron]] | 외부 도구 대신 직접 파일 읽기 우선 |
| [[禁karpathy_coding_principles.neuron]] | 4대 Karpathy 코딩 원칙 위반 금지 |
| [[禁tool_integration_3file.neuron]] | 도구 통합 시 3개 파일 미완성 금지 |
| [[禁kanban_hallucination.neuron]] | 가짜 task ID로 kanban_complete 금지 |
| [[禁kanban_worker_accountability.neuron]] | worker TTL/heartbeat enforcement |
| [[禁rebac_integration.neuron]] | INTEGRATION_PROTOCOL 미참조 통합 작업 금지 |
| [[禁rebac_kanban.neuron]] | KANBAN_INDEX 미참조 kanban 작업 금지 |
| [[禁brain_obsidian_graph.neuron]] | P-layer/memories .md 파일 wikilink 연결 누락 금지 |
| [[禁no_linear_workflow]] | Linear workflow 통합 금지 |

> Note: 위 링크는 NeuronFS .neuron 규칙 파일을 직접 가리킨다. (`P0-brainstem/brain/Loragent-brain/P0-brainstem/禁/`)

## 4 Karpathy Coding Principles

1. **Think Before Coding** — 가정 명시, 불확실하면 질문, 모르면 모른다고 말하기
2. **Simplicity First** — 최소 코드, 200줄을 50줄로 줄일 수 있으면 줄이기
3. **Surgical Changes** — 요청한 것만 변경, orphan은 제거, 나머진 방치
4. **Goal-Driven Execution** — 성공 기준 명시, 테스트 우선, 루프 돌기

## Related

- [[P5-ego/SELF_MODEL]] — P5-Ego self-awareness model (P0 규칙 Enforcement 권한)
- [[P1-limbic/persona/SOUL]] — P1-Limbic identity & voice
- [[P3-sensors/gateway/loragent-architecture-dataflow]] — P3-Sensors architecture
- [[禁brain_obsidian_graph.neuron]] — P0 Brain rule for graph integrity enforcement
- [[禁no_linear_workflow]] — P0 Brain rule for Linear workflow deprecation

## Links
- [[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁/brain-graph-orphan-remediation-20260520]]
- [[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁/禁brain_obsidian_graph.neuron]]
- [[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁/禁kanban_hallucination.neuron]]
- [[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁/禁kanban_worker_accountability.neuron]]
- [[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁rebac_integration.neuron]]
- [[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁rebac_kanban.neuron]]
- [[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁auto_validate.neuron]]
- [[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁blind_write.neuron]]
- [[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁console_log.neuron]]
- [[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁filesystem_truth.neuron]]
- [[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁karpathy_coding_principles.neuron]]
- [[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁rm_rf_root.neuron]]
- [[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁secrets_in_code.neuron]]
- [[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁subagent_verify.neuron]]
- [[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁task_qa_gate.neuron]]
- [[P0-brainstem/brain/Loragent-brain/P0-brainstem/禁tool_integration_3file.neuron]]
