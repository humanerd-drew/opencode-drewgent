---
title: quality-patterns
description: "6대 패턴(점진제동/구조적불가능/자동정지-HITL/flaky-vs-systematic/두눈실증/FMEA)의 Agent 정본. Layer 0(구조적) / Layer 1(원칙) / Layer 2(프로세스) 구조."
type: reference
space: concept
tags: [concept, quality, governance]
created: 2026-07-02
updated: 2026-07-11
patterns:
  - id: poka-yoke
    maturity: PROVEN
    tags: [poka-yoke, 포카요케, 구조적-불가능]
    layer: 0
  - id: andon
    maturity: PROVEN
    tags: [andon, 점진제동, graduated-remediation]
    layer: 1
  - id: jidoka
    maturity: PROVEN
    tags: [jidoka, 자동정지-hitl]
    layer: 1
  - id: spc
    maturity: PROVEN
    tags: [spc, flaky-systematic]
    layer: 1
  - id: 3-hyun
    maturity: PROVEN
    tags: [3현, 두눈-실증]
    layer: 1
  - id: fmea
    maturity: DRAFT
    tags: [fmea, rpn, pre-mortem]
    layer: 2
links:
  - "[[@identity/brain/rules]]"
  - "[[@identity/SELF_MODEL]]"
  - "[[skills/software-development/ponytail]]"
  - "[[scripts/bridge-lint.sh]]"
---

# Agent Quality Patterns

일관된 의사결정을 위한 6개 패턴. 3개 Layer로 구성.

```
Layer 0 — 구조적 (항상 ON, overhead 0)
Layer 1 — 원칙 (항상 ON, wisdom만 있으면 됨)
Layer 2 — 프로세스 (OFF by default, 필요할 때만 ON)
```

---

## Layer 0: 구조적 (Structural)

항상 활성화. overhead 제로. OS/파일시스템 단에서 강제되므로 에이전트의 판단이 필요 없음.

### poka-yoke (구조적 불가능)

**원리:** "하지 마" 규칙이 아니라 구조적으로 불가능하게 만든다.

| 포카요케 | 방지 대상 | 메커니즘 |
|----------|-----------|----------|
| watcher exclude | vault 파일 읽기 | opencode.jsonc watcher 경로 제외 |
| chmod 600 | credential 노출 | 파일 권한으로 읽기 원천 차단 |
| vault_cli.py 의무화 | API 키 평문 저장 | set/get 외 저장 경로 없음 |
| 禁 blind_write | 파일 읽기 없는 쓰기 | tool 설계 + P0 규칙 |

**ponytail 관계:** ponytail의 6단계 체크리스트는 poka-yoke의 코드 레벨 인스턴스.

---

## Layer 1: 원칙 (Principles)

항상 활성화. enforcement 불필요 — system prompt에 내장. wisdom 레벨.

### 점진제동 (graduated remediation)

**원리:** 장애 대응을 4단계로. 처음부터 kill -9 하지 않는다.

| 단계 | 동작 |
|------|------|
| 先경고 | 경고만, 멈추지 않음 |
| 조이기 | 재시도 + backoff |
| 늦추기 | 큐 적체, 속도 제한 |
| 세우기 | 완전 정지 + HITL |

### 자동정지 + HITL (jidoka)

**원리:** guardrail 감지 시 자동 정지, 판단은 인간에게.

| Guardrail | 조건 | 판단자 |
|-----------|------|--------|
| prod-write 접근 | production DB/API 쓰기 | AskUserQuestion |
| kanban_block | task 분류 불가 | 인간 |
| rm -rf root | 파괴적 명령어 | 자동차단 |
| confidence < 80% | LLM 불확실 | AskUserQuestion |

### flaky vs systematic 분류 (SPC)

**원리:** 단발성은 무시, 반복성은 근본수정.

### 두눈 실증 (3현)

**원리:** CI-green ≠ live-works. 현장/현물/현실 중 2가지 직접 확인.

---

## Layer 2: 프로세스 (Process)

**OFF by default.** `DREWGENT_MODE=lab`이면 Layer 2 전부 침묵.
협업/공개 레포 환경에서만 켜는 게 적절.

### FMEA (사전 위험 식별)

**원리:** RPN = 심각도 × 발생 × 검출 로 위험 점수화.

| RPN | 등급 | 요구 조치 |
|-----|------|----------|
| ≤ 10 | Low | 모니터링만 |
| 11-50 | Medium | guardrail + 알림 |
| ≥ 51 | High | pre-mortem, HITL gate |

### bridge-lint (태그 검증)

명시적 호출만:

```bash
bash scripts/bridge-lint.sh
DREWGENT_MODE=production bash scripts/bridge-lint.sh
```

---

## 태그 참조

| 패턴 | 태그 | Layer | maturity |
|------|------|-------|----------|
| 구조적 불가능 | `poka-yoke` | 0 | PROVEN |
| 점진제동 | `andon` | 1 | PROVEN |
| 자동정지+HITL | `jidoka` | 1 | PROVEN |
| flaky vs systematic | `spc` | 1 | PROVEN |
| 두눈 실증 | `3-hyun` | 1 | PROVEN |
| 사전 위험 식별 | `fmea` | 2 | DRAFT |
