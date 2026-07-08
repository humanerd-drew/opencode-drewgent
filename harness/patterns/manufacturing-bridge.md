---
title: manufacturing-bridge
description: "6대 패턴(점진제동/구조적불가능/자동정지-HITL/flaky-vs-systematic/두눈실증/사전위험식별)의 Drewgent 동형매핑 정본 + enforcement"
type: reference
space: concept
tags: [concept, harness, quality, enforcement]
created: 2026-07-02
updated: 2026-07-02
patterns:
  - id: andon
    maturity: PROVEN
    tags: [andon, 점진제동, graduated-remediation]
    enforced_by: "check-all bridge-lint (Tier 2), rules.md (Tier 1)"
  - id: poka-yoke
    maturity: PROVEN
    tags: [poka-yoke, 포카요케, 구조적-불가능]
    enforced_by: "rules.md (Tier 1), ponytail skill"
  - id: jidoka
    maturity: PROVEN
    tags: [jidoka, 자동정지-hitl, jidoka]
    enforced_by: "rules.md (Tier 1), AskUserQuestion"
  - id: spc
    maturity: PROVEN
    tags: [spc, flaky-systematic]
    enforced_by: "rules.md (Tier 1)"
  - id: 3-hyun
    maturity: PROVEN
    tags: [3현, 두눈-실증]
    enforced_by: "rules.md (Tier 3, 禁, P1 결함)"
  - id: fmea
    maturity: DRAFT
    tags: [fmea, rpn, pre-mortem]
    enforced_by: "kanban task template (WIP), rules.md (Tier 1)"
inspired_by: "lazymac2x/agent-wiki (MIT) — 제조↔에이전트 동형사상 개념 검토 및 Taste Review 계기"
links:
  - "[[@identity/brain/rules]]"
  - "[[@identity/SELF_MODEL]]"
  - "[[skills/software-development/ponytail]]"
  - "[[scripts/bridge-lint.sh]]"
---

# Manufacturing Bridge — 6대 패턴 (Drewgent 정본)

일관된 의사결정을 위한 6개 패턴. 새 메커니즘/가드레일을 설계하기 전에 이 표를 먼저 참조한다.
패턴은 provenance 태그로 추적되고, enforcement tier별로 강제된다.

---

## 1. 점진제동 (graduated remediation)

**원리:** 장애 대응을 4단계로 분리. 처음부터 멈추지 않고 단계별로 강도를 높인다.
즉시 kill -9는 마지막 수단. 선행신호 → 조이기 → 늦추기 → 세우기 순서.

**Drewgent 구현체:**

| 단계 | 동작 | 파일 | 트리거 조건 |
|------|------|------|-----------|
| 先경고 | 알림만, 멈추지 않음 | `scripts/discord_send.py`, `cron_state.json WARN` | 1회 실패, latency spike, 비정상 로그 |
| 조이기 | 재시도 + backoff | launchd ThrottleInterval 10s | 연속 2-3회 실패 |
| 늦추기 | 큐 적체, 속도 제한 | `cron_runner.py` skip logic, office-autopilot sequential | 반복 실패, resource exhaustion |
| 세우기 | 완전 정지 + HITL | `kanban_block`, `AskUserQuestion` | 치명적 오류, 데이터 불일치, 보안 위반 |

**enforcement:** bridge-lint (Tier 2) — provenance에 `andon` 태그 확인. rules.md (Tier 1) — 점진제동 원칙 명시.

**태그:** `manufacturing-bridge:andon`

---

## 2. 구조적 불가능 (structural impossibility / poka-yoke)

**원리:** "하지 마" 규칙이 아니라 구조적으로 불가능하게 만든다.
검사로 막는 게 아니라, 접근 경로 자체를 차단하거나, 틀린 입력이 애초에 들어오지 않게 설계.

**Drewgent 구현체:**

| 포카요케 | 방지 대상 | 메커니즘 | 파일 |
|----------|-----------|----------|------|
| watcher exclude | vault.key, secrets_vault.json 읽기 | opencode.jsonc watcher 경로 제외 | `~/.config/opencode/opencode.jsonc` |
| chmod 600 | DB/Admin credential 노출 | 파일 권한으로 읽기 원천 차단 | `~/.drewgent/wordpress/.wp-env` |
| knowledge.db isolation | knowledge.db 직접 탐색 | CLI-only 접근, MCP로는 불가 | chmod 600, watcher exclude |
| vault_cli.py 의무화 | API 키 평문 저장 | set/get 외 저장 경로 없음 | `~/.drewgent/scripts/vault_cli.py` |
| 禁 blind_write | 파일 읽기 없는 쓰기 | tool 설계상 Read 선행 필수 + P0 규칙 | rules.md 禁 rule |
| launchd KeepAlive 패턴 | 잘못된 재시작 조건 | `SuccessfulExit: false` 고정 | 모든 `ai.drewgent.*.plist` |

**ponytail 관계:** ponytail의 6단계 체크리스트(구현 전 YAGNI→stdlib→native→dep→oneline→min)는 구조적 불가능의 **코드 레벨 인스턴스**. 체크리스트를 통과하면 불필요한 코드가 애초에 생성되지 않는다. → [[skills/software-development/ponytail]]

**enforcement:** rules.md (Tier 1) — 구조적 불가능 원칙. ponytail auto-load — 코딩 작업 시 체크리스트 강제.

**태그:** `manufacturing-bridge:poka-yoke`

---

## 3. 자동정지 + 인간판단 (automatic stop + HITL / jidoka)

**원리:** guardrail이 감지되면 자동으로 정지. 판단은 인간에게 넘긴다.
정지까지는 자동, 재가동 결정은 반드시 사람. 자동정지만 있고 인간지혜가 없으면 무음 fail이 된다.

**Drewgent 구현체:**

| Guardrail | 자동정지 조건 | 판단자 | 비가역 | 파일 |
|-----------|-------------|--------|--------|------|
| prod-write 접근 | production DB/API 쓰기 감지 | AskUserQuestion | 비가역 | gateway/ |
| kanban_block | task 분류 불가/모호 | Discord 알림 → 인간 | 가역 | `kanban.py` |
| rm -rf root | 파괴적 명령어 | agent routine (자동차단) | 비가역 | 禁 rule |
| budget exceed | 월간 한도 초과 | agent 또는 인간 | 조건부 | cron monitor |
| confidence < 80% | LLM 자체 불확실 | AskUserQuestion | 조건부 | run_agent.py |

**규칙:** prod-write, 비가역, confidence < 80%는 어느 루프든 자동정지 + HITL. 정지만 하고 HITL 없이 넘어가는 건 "무음 fail" = P1 결함.

**enforcement:** rules.md (Tier 1) — 자동정지+HITL 원칙. AskUserQuestion — 시스템 차원의 HITL 메커니즘.

**태그:** `manufacturing-bridge:jidoka`

---

## 4. flaky vs systematic 분류 (special cause vs common cause / SPC)

**원리:** 실패를 패턴으로 분류한다. 단발성(flaky)은 무시해도 되고, 반복성(systematic)은 근본수정이 필요하다.
이 구분 없이 모든 실패에 똑같이 대응하면 flaky에 과잉대응하거나 systematic을 방치하게 된다.

**Drewgent 구현체:**

| 관측 | 분류 | 조치 | 대상 파일 |
|------|------|------|----------|
| 1회 단발, 패턴 없음 | **flaky** | retry + ignore | `logs/cron_state.json` |
| 반복, 동일 조건 | **systematic** | 근본수정 + 재발방지 문서 | `P6-prefrontal/logs/`, `cron_health_check.py` |
| 특정 조건에서만 발생 | 층별 분석 | 조건 분리 후 재현 테스트 | launchd plist, macOS 버전 |
| 점진적 증가 추세 | 先경고 (점진제동) | 모니터링 강화, 용량 계획 | `discord_send.py` |

**규칙:** cron 실패 진단 시 항상 SPC 분류를 먼저. "그냥 flaky겠지"는 금지 (실제로는 systematic인 경우가 더 많다).

**enforcement:** rules.md (Tier 1) — flaky-vs-systematic 원칙.

**태그:** `manufacturing-bridge:spc`

---

## 5. 두눈 실증 (gemba-genbutsu-genjitsu / 3현)

**원리:** CI-green ≠ live-works. checksum이나 테스트 통과만 믿고 "됐다"고 단정하지 않는다.
실제 실행 환경(현장), 실제 상태 덤프(현물), 실제 결과(현실) 중 최소 2가지를 직접 확인해야 QA 통과.

**Drewgent 구현체:**

| 3현 | 의미 | 검증 방법 | 적용 파일 |
|-----|------|-----------|----------|
| 현장 | 실제 실행 환경 | `launchd list`, `docker ps`, `ps aux`, process list | 배포/디버그 시 |
| 현물 | 실제 상태 | D1 직접 SELECT, recall query, `cron_state.json` 파일 읽기 | QA 단계 |
| 현실 | 실제 결과 | HTTP response status, terminal output, screenshot capture | 최종 확인 |

**규칙:** implementer 출력 검증 시 3현 의무화. "빌드 통과했다" = 완료 아님. P1 결함.

**enforcement:** rules.md (Tier 3, 禁, P1 결함). `task_qa_gate.neuron` — QA 검증 없이 완료 금지.

**태그:** `manufacturing-bridge:3-hyun`

---

## 6. 사전 위험 식별 (risk scoring / FMEA)

**원리:** 작업 시작 전에 잠재 고장 모드를 점수화한다. RPN = 심각도 × 발생 × 검출.
모든 위험을 막을 순 없으니 점수로 우선순위를 정하고, 높은 것만 집중 방어.

**Drewgent 구현체:**

| RPN | 등급 | 요구 조치 |
|-----|------|----------|
| ≤ 10 | Low | 모니터링만 |
| 11-50 | Medium | guardrail + 알림 |
| ≥ 51 | High | pre-mortem 필수, HITL gate, kanban_block fallback |

**RPN 기준:**
- **심각도:** 1(불편) → 5(데이터 손실) → 10(보안/금전)
- **발생:** 1(연1회) → 5(월1회) → 10(매일)
- **검출:** 1(즉시감지) → 5(로그분석) → 10(사용자신고)

**적용 대상:** `cron/jobs.json` 신규 job, `skills/` 신규 skill, `scripts/` 신규 스크립트, kanban task 생성 시.

**enforcement:** rules.md (Tier 1) — 원칙 명시. kanban task template (WIP) — RPN 필드 추가 예정.

**태그:** `manufacturing-bridge:fmea`

---

## 규칙 (enforcement tier별)

### Tier 1: AGENTS.md 행동 규칙 (bridge-lint WARNING)
- 모든 provenance 기록에 `manufacturing-bridge:<패턴id>` 태그를 포함한다
- 새 메커니즘/가드레일 설계 전 위 6개 패턴 중 해당하는 것이 있는지 확인한다
- 태그 미포함 시 bridge-lint가 WARNING을 출력한다

### Tier 2: check-all bridge-lint (WARNING)
- 변경된 .md 파일의 frontmatter에서 patterns registry 기준 태그 검증
- 누락 태그: WARNING
- 미등록 태그: WARNING
- registry에 패턴 추가만으로 검증 대상 확장 가능

### Tier 3: 禁 rule (P1 결함)
- **3현 위반:** 검증 없이 완료 선언 = P1 결함. `task_qa_gate.neuron` 참조.
- (향후 추가: 점진제동 先경고 없이 세우기 = P1?)

---

---

## Enforcement Review Schedule

이 파일의 enforcement를 언제 활성화할지 에이전트가 판단해서 보고한다.

| 단계 | 조건 | 동작 | 예정일 |
|------|------|------|--------|
| 1차 검토 | 브리지 태그를 5회 이상 실제 의사결정에 사용한 기록 | bridge-lint를 check-all.sh에 연결 제안 | 2026-07-16 (2주) |
| 2차 검토 | 3현 위반 사례를 발견한 경우 | Tier 3 enforcement 활성화 제안 | 발견 시 즉시 보고 |
| 3차 검토 | FMEA 태그 3회 이상 사용 | FMEA maturity를 DRAFT→PROVEN 승격 + kanban 템플릿 연결 제안 | 2026-08-01 |

**에이전트 규칙:** 위 조건 중 하나라도 만족하면, 별도 요청 없이 사용자에게 보고한다.
"manufacturing-bridge enforcement review: 조건 N 충족. 제안: ..."

## 태그 참조

| 패턴 | 태그 문자열 | 등록일 | maturity |
|------|-----------|--------|----------|
| 점진제동 | `manufacturing-bridge:andon` | 2026-07-02 | PROVEN |
| 구조적 불가능 | `manufacturing-bridge:poka-yoke` | 2026-07-02 | PROVEN |
| 자동정지+HITL | `manufacturing-bridge:jidoka` | 2026-07-02 | PROVEN |
| flaky vs systematic | `manufacturing-bridge:spc` | 2026-07-02 | PROVEN |
| 두눈 실증 | `manufacturing-bridge:3-hyun` | 2026-07-02 | PROVEN |
| 사전 위험 식별 | `manufacturing-bridge:fmea` | 2026-07-02 | DRAFT |
