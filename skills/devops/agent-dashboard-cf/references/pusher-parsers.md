# Hermes CLI Output Parser Patterns

## collect_cron() — `hermes cron list`

### 출력 포맷
```
┌─────────────────────────────────────────────────────────┐
│                         Scheduled Jobs                   │
└─────────────────────────────────────────────────────────┘

  <job_id> [active|paused]
    Name:      <job name>
    Schedule:  <cron expr>
    Repeat:    ∞
    Next run:  <ISO timestamp>
    Deliver:   <target>
    Script:    <path>
    Mode:      no-agent (...)
    Last run:  <ISO timestamp>  ok|error: <detail>
```

### 파싱 전략
1. Box-drawing chars (`─ ┌ └ │`)를 건너뜀
2. `<job_id> [state]` 라인 감지 → 새 job 객체 생성
3. `Name:`, `Schedule:`, `Last run:` 키-값 파싱
4. `Last run:` 라인의 `ok` / `error:` 접두사로 상태 판별

### 주의사항
- `error:` 뒤에 콜론이 붙음 → `parts[1] == "error:"`가 아니라 `parts[1].startswith("error")`로 체크
- `Last run:`이 없는 job도 있음 (taste-review-trigger 등 최초 실행 전)
- `[active]`만 표시됨. Paused job은 CLI에 안 나옴 (tool 출력에는 나옴)

### 분류 로직
```python
def _cron_classify(job, active, errors, paused):
    if job.get("last_status") == "error":
        errors.append(job)
    elif job.get("state") == "paused":
        paused.append(job)
    else:
        active.append(job)
```

## collect_kanban() — `hermes kanban list`

### 출력 포맷
```
⊘ t_7cdcfa91  blocked   default               [Orchestrator] m-log-v2 전체 구조 개편
◻ t_05c40c8f  todo      default               Phase 1: src/ 도메인 폴더 생성
▶ t_6d0f88df  ready     content-manager       [cmo] 2026-W24 — First content batch
```

### 파싱 전략
- `split()` 결과 컬럼: `[0]=icon, [1]=id, [2]=status_text, [3]=assignee, [4:]=title`
- 아이콘 매핑: `⊘=blocked`, `◻=todo`, `▶=ready`, `●=running`, `✓=done`, `◼=done`
- `parts[2]` (status_text)는 아이콘 매핑과 중복이므로 무시할 것
- `assignee = parts[3]`, `title = " ".join(parts[4:])`

## collect_sessions() — `hermes sessions list`

간단한 split 파싱. 포맷이 변하기 쉬우므로 fallback 처리가 중요.

## 일반 원칙

1. `subprocess.run(..., shell=True, env=env)` 사용 — cron 환경에선 PATH 보강 필수
2. 모든 CLI 명령어에 `2>/dev/null` 추가 — stderr 무시
3. 출력이 없으면 빈 리스트 반환 (예외 발생시키지 않음)
4. `timeout` 인자 필수 — CLI가 멈출 경우 대비 (기본 15초)
