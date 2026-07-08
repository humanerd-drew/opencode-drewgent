---
title: P0 Brainstem Rules
type: document
space: concept
tags: [concept]
created: 2026-05-14
updated: 2026-05-20
links:
  - "[[@identity/brain/Loragent-brain/P0-brainstem/禁/brain-graph-orphan-remediation-20260520]]"
  - "[[@identity/brain/Loragent-brain/P0-brainstem/禁/禁brain_obsidian_graph.neuron]]"
  - "[[@identity/brain/Loragent-brain/P0-brainstem/禁/禁kanban_hallucination.neuron]]"
  - "[[@identity/brain/Loragent-brain/P0-brainstem/禁/禁kanban_worker_accountability.neuron]]"
  - "[[@identity/brain/Loragent-brain/P0-brainstem/禁rebac_integration.neuron]]"
  - "[[@identity/brain/Loragent-brain/P0-brainstem/禁rebac_kanban.neuron]]"
  - "[[@identity/brain/Loragent-brain/P0-brainstem/禁auto_validate.neuron]]"
  - "[[@identity/brain/Loragent-brain/P0-brainstem/禁blind_write.neuron]]"
  - "[[@identity/brain/Loragent-brain/P0-brainstem/禁console_log.neuron]]"
  - "[[@identity/brain/Loragent-brain/P0-brainstem/禁filesystem_truth.neuron]]"
  - "[[@identity/brain/Loragent-brain/P0-brainstem/禁karpathy_coding_principles.neuron]]"
  - "[[@identity/brain/Loragent-brain/P0-brainstem/禁rm_rf_root.neuron]]"
  - "[[@identity/brain/Loragent-brain/P0-brainstem/禁secrets_in_code.neuron]]"
  - "[[@identity/brain/Loragent-brain/P0-brainstem/禁subagent_verify.neuron]]"
  - "[[@identity/brain/Loragent-brain/P0-brainstem/禁task_qa_gate.neuron]]"
  - "[[@identity/brain/Loragent-brain/P0-brainstem/禁tool_integration_3file.neuron]]"
  - "[[@identity/persona/SOUL]]"
  - "[[@action/gateway/drewgent-architecture-dataflow]]"
  - "[[@identity/SELF_MODEL]]"
  - "[[禁auto_validate.neuron]]"
  - "[[禁blind_write.neuron]]"
  - "[[禁brain_obsidian_graph.neuron]]"
  - "[[@memory/growth/INTEGRATION_PROTOCOL]]"
  - "[[@memory/memories/SCHEMA]]"
  - "[[@memory/knowledge/NEURONFS_RULES]]"
---


# P0 Brainstem — Critical Rules

{{AGENT_NAME}}의 절대 규칙. P0-brainstem 규칙은 어떤 상위 레이어보다 우선한다.

## 禁 Rules (Never-Do)

| Rule | 설명 |
|------|------|
| [[禁rm_rf_root.neuron]] | `rm -rf /`, `rm -rf ~`, `rm -rf ./*` 금지 |
| [[禁blind_write.neuron]] | 파일 읽기 없이 쓰기 금지 |
| [[禁config_format_guess.neuron]] | 설정파일 포맷 확인 없이 신규 생성 금지 (2026-06-20 추가) |
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

## Manufacturing Bridge — 6대 패턴 (3-tier enforcement)

**trigger:** "2026-07-02 agent-wiki 검토 — 실행 중인 패턴에 이름을 붙여 설명 비용 제로화"
**decision:** "참조 문서 → graded enforcement로 승격. Tier 1(행동규칙) / Tier 2(lint WARNING) / Tier 3(禁 P1)"
**정본:** [[harness/patterns/manufacturing-bridge]] — patterns registry, 파일별 구현체 매핑, 태그 참조

### Tier 1: 행동 규칙 (bridge-lint WARNING)
모든 provenance 기록에 `manufacturing-bridge:<패턴id>` 태그 포함. 태그 누락 시 bridge-lint가 WARNING 출력.

| 패턴 | 태그 | 적용 |
|------|------|------|
| 점진제동 | `andon` | launchd/cron 장애 대응 4단계 |
| 구조적 불가능 | `poka-yoke` | watcher exclude, chmod 600, vault_cli, ponytail |
| 자동정지+HITL | `jidoka` | AskUserQuestion, kanban_block, prod-write guard |
| flaky vs systematic | `spc` | cron 실패 분류, 재발방지 |
| 두눈 실증 | `3-hyun` | build-green ≠ live-works, D1/knowledge.db 직접 쿼리 |
| 사전 위험 식별 | `fmea` | 신규 cron/skill pre-mortem, RPN |

### Tier 2: lint gate (WARNING)
`scripts/bridge-lint.sh`가 변경된 .md 파일의 frontmatter 태그를 검증.
- 태그 누락: WARNING (Tier 1 위반)
- 미등록 태그: WARNING (확장 감지)
- registry 기반이므로 패턴 추가 시 lint 자동 반영

### Tier 3: 禁 rule (P1 결함)
| 패턴 | 위반 조건 | 결함 등급 |
|------|----------|-----------|
| 두눈 실증 (3-hyun) | 검증 없이 완료 선언 | **P1** — task_qa_gate.neuron 참조 |
| (향후) 자동정지+HITL | 정지만 하고 인간 판단 없이 진행 | P1? |

## 4 Karpathy Coding Principles

1. **Think Before Coding** — 가정 명시, 불확실하면 질문, 모르면 모른다고 말하기
2. **Simplicity First** — 최소 코드, 200줄을 50줄로 줄일 수 있으면 줄이기
3. **Surgical Changes** — 요청한 것만 변경, orphan은 제거, 나머진 방치
4. **Goal-Driven Execution** — 성공 기준 명시, 테스트 우선, 루프 돌기

## Related

- [[@identity/SELF_MODEL]] — P5-Ego self-awareness model (P0 규칙 Enforcement 권한)
- [[@identity/persona/SOUL]] — P1-Limbic identity & voice
- [[@action/gateway/drewgent-architecture-dataflow]] — P3-Sensors architecture
- [[禁brain_obsidian_graph.neuron]] — P0 Brain rule for graph integrity enforcement
- [[禁no_linear_workflow]] — P0 Brain rule for Linear workflow deprecation

## Links
- [[@identity/brain/Loragent-brain/P0-brainstem/禁/brain-graph-orphan-remediation-20260520]]
- [[@identity/brain/Loragent-brain/P0-brainstem/禁/禁brain_obsidian_graph.neuron]]
- [[@identity/brain/Loragent-brain/P0-brainstem/禁/禁kanban_hallucination.neuron]]
- [[@identity/brain/Loragent-brain/P0-brainstem/禁/禁kanban_worker_accountability.neuron]]
- [[@identity/brain/Loragent-brain/P0-brainstem/禁rebac_integration.neuron]]
- [[@identity/brain/Loragent-brain/P0-brainstem/禁rebac_kanban.neuron]]
- [[@identity/brain/Loragent-brain/P0-brainstem/禁auto_validate.neuron]]
- [[@identity/brain/Loragent-brain/P0-brainstem/禁blind_write.neuron]]
- [[@identity/brain/Loragent-brain/P0-brainstem/禁console_log.neuron]]
- [[@identity/brain/Loragent-brain/P0-brainstem/禁filesystem_truth.neuron]]
- [[@identity/brain/Loragent-brain/P0-brainstem/禁karpathy_coding_principles.neuron]]
- [[@identity/brain/Loragent-brain/P0-brainstem/禁rm_rf_root.neuron]]
- [[@identity/brain/Loragent-brain/P0-brainstem/禁secrets_in_code.neuron]]
- [[@identity/brain/Loragent-brain/P0-brainstem/禁subagent_verify.neuron]]
- [[@identity/brain/Loragent-brain/P0-brainstem/禁task_qa_gate.neuron]]
- [[@identity/brain/Loragent-brain/P0-brainstem/禁tool_integration_3file.neuron]]

## m-log 수정 검증 규칙 (2026-06-21)
trigger: "m-log streaming 수정에서 implementer 결과물을 검증 안 하고 import 경로 오류를 놓친 사건"
provenance:
  session: "2026-06-21 m-log-streaming-fix"
  decision: "매번 같은 실수를 반복하므로, 규칙으로 박아서 절대 건너뛰지 못하게 함"

### implementer 결과 검증 필수 단계:
1. implementer가 반환한 diff를 반드시 직접 읽을 것
2. 모든 import 경로를 `ls`로 실제 파일 존재 확인
3. `frontend/`와 `public/` 디렉토리 구조 차이를 확인하고 sync 필요 여부 판단
4. TypeScript는 `npx tsc --noEmit`, JS는 `node --check`로 각 파일 검증
5. 위 단계를 모두 통과해야만 "완료"라고 보고할 것

### m-log 프로젝트 특수사항:
- Worker가 서빙하는 건 `public/` 디렉토리, 소스는 `frontend/`
- `npm run dev` / `npm run deploy` 할 때 `sync:local`이 `frontend/` → `public/` 복사
- implementer 태스크에는 반드시 "frontend/ 수정 후 public/에도 동일하게 적용"을 포함
