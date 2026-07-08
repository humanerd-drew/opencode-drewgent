---
title: - skills/project/kis-autonomous-bot-debug/SKILL
type: skill
space: outcome
tags: [outcome]
created: 2026-05-20
updated: 2026-05-20
links:
  - "[[@action/skills/SKILL-INDEX]]"
---

space: outcome
type: document

# Brain Dashboard System

Drewgent의 NeuronFS Brain 상태를 실시간으로 모니터링하는 통합 시스템.

## 아키텍처

```
┌─────────────────────────────────────────────────────┐
│                  Drewgent Brain                      │
│                                                     │
│  ┌─────────────┐  ┌──────────────────────────────┐ │
│  │ Brain Rules │  │   Scripts (~/.drewgent/scripts) │ │
│  │  .neuron    │──│  brain_nodes.py (ASCII 뇌)     │ │
│  │  files      │  │  brain_html_dashboard.py (WEB) │ │
│  └─────────────┘  │  brain_rule_monitor.py        │ │
│                   │  session_end_hook.py          │ │
│                   └──────────────────────────────┘ │
│                              │                        │
│         ┌────────────────────┼────────────┐         │
│         ▼                    ▼            ▼         │
│  ┌────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │ Cron 6h    │  │ Cron 5min    │  │ Discord   │  │
│  │ Growth Rep │  │ Session End  │  │ Alert     │  │
│  └────────────┘  └──────────────┘  └───────────┘  │
└─────────────────────────────────────────────────────┘
```

## 핵심 스크립트

### 1. brain_nodes.py (ASCII 뇌 시각화)
```bash
python3 ~/.drewgent/scripts/brain_nodes.py
```
실제 뇌 해부학 구조를 반영한 ASCII 아트:
- P6 Prefrontal (맨 위/앞) → P0 Brainstem (맨 아래) 
- Synapse Signal Flow: P0→P1→P2→P3→P4→P5→P6
- Spinal Cord 포함
- Stats + Growth delta 표시

### 2. brain_html_dashboard.py (웹 대시보드)
```bash
python3 ~/.drewgent/scripts/brain_html_dashboard.py
```
출력: `~/.drewgent/brain_dashboard.html`
- SVG 뇌 시각화 (애니메이션 시냅스 신호)
- Stats 카드 4개 (Brain Rules, Skills, Knowledge, Sessions)
- Layer Detail 테이블
- Skills 라이브러리
- 5분 자동 리프레시

### 3. brain_rule_monitor.py (성장 모니터)
```bash
python3 ~/.drewgent/scripts/brain_rule_monitor.py        # 실행
python3 ~/.drewgent/scripts/brain_rule_monitor.py --check # 상태 확인
```
- brain_rule_state.json 와 비교하여 신규 규칙 탐지
- 새 규칙 발견 시 Discord 알림 (webhook)
- Discord 설정: `~/.drewgent/config/discord.json` (webhook_url 필요)

### 4. session_end_hook.py (세션 종료 감시)
```bash
python3 ~/.drewgent/scripts/session_end_hook.py          # 실행
python3 ~/.drewgent/scripts/session_end_hook.py --check   # 상태 확인
```
- session_checkpoint.json 수정시간 감시
- 세션 종료 (5분 이상 비활성 후 재접속) 감지
- Dashboard 자동 실행 → ~/.drewgent/logs/ 저장

## Cron Jobs

| Job | Schedule | Script | Deliver |
|-----|----------|--------|---------|
| Brain Growth Monitor | 6h 마다 | brain_rule_monitor.py + brain_html_dashboard.py | Discord #n8n-cotroltower |
| Session End Hook | 5min 마다 | session_end_hook.py | origin (Discord thread) |

## 상태 파일

| File | 용도 |
|------|------|
| `~/.drewgent/brain_snapshot.json` | brain_nodes.py 성장 delta 저장 |
| `~/.drewgent/brain_rule_state.json` | brain_rule_monitor.py 신규 규칙 탐지용 |
| `~/.drewgent/.last_hook_run` | session_end_hook.py 마지막 실행 시간 |
| `~/.drewgent/brain_dashboard.html` | 웹 대시보드 출력 |

## Discord Notification 설정

Discord webhook URL을 `~/.drewgent/config/discord.json`에 저장:
```json
{
  "webhook_url": "https://discord.com/api/webhooks/..."
}
```

## 실행 예시

```bash
# 전체 대시보드 실행 (콘솔)
python3 ~/.drewgent/scripts/brain_nodes.py

# 웹 대시보드 생성
python3 ~/.drewgent/scripts/brain_html_dashboard.py

# 성장 모니터 수동 실행
python3 ~/.drewgent/scripts/brain_rule_monitor.py

# 세션 종료 감지 확인
python3 ~/.drewgent/scripts/session_end_hook.py --check
```

## 성장 알림 동작

1. brain_rule_monitor.py가 6시간마다 실행
2. brain_rule_state.json의 layers vs 현재 .neuron 파일 비교
3. 신규 규칙 발견 → Discord Embed 알림:
   - Layer별 신규 규칙 목록
   - 총 규칙 수
   - Dashboard 시놉시스

## 확장

- **P0 Brainstem 규칙** (禁*): 안전 관련 규칙으로 다른 레이어보다 우선
- **새 규칙 추가 시**: 새 .neuron 파일을 `~/.drewgent/brain/Drewgent-brain/<layer>/`에 추가하면 자동 탐지
- **Layer 추가 시**: `LAYER_ORDER` 배열에 새 layer ID 추가하면 자동 반영

## Related
- [[@action/skills/SKILL-INDEX]]
