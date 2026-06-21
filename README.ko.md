# opencode-drewgent

**AI 에이전트를 위한 오픈소스 개인 비서 프레임워크**

opencode-drewgent는 `opencode` 위에서 동작하는 개인 AI 에이전트 시스템의 **아키텍처 레퍼런스**입니다. 단순한 설정 모음이 아니라, 진화하는 지식베이스, 다중 에이전트 오케스트레이션, 자동화된 크론 작업, 체계적인 회고 파이프라인을 포함한 **운영 가능한 에이전트 시스템**입니다.

---

## 한 줄 요약

> **opencode + OmO + LLM Wiki + kanban + cron = 당신만의 AI 에이전트 운영체제**

---

## 사전 준비

| 도구 | 버전 | 설치 |
|------|------|------|
| [opencode](https://opencode.ai) | ≥ 1.4.0 | `curl -fsSL https://opencode.ai/install \| bash` |
| [bun](https://bun.sh) | ≥ 1.0 | `curl -fsSL https://bun.sh/install \| bash` |
| [oh-my-openagent](https://github.com/code-yeongyu/oh-my-openagent) | latest | `bunx oh-my-openagent install` |

**선택 사항:**
- tmux (팀 모드 시각화) — `brew install tmux`
- sqlite3 (kanban DB) — macOS 기본 내장

---

## 설치

### 1. opencode 설치 및 설정

```bash
curl -fsSL https://opencode.ai/install | bash
opencode auth login  # 원하는 LLM provider 선택
```

### 2. OmO 설치

```bash
bunx oh-my-openagent install --no-tui \
  --platform=opencode \
  --claude=yes \
  --openai=yes
```

> 자신의 구독 상황에 맞게 `--claude`, `--openai`, `--gemini`, `--opencode-go` 등을 조정하세요.
> 자세한 옵션은 [OmO 설치 가이드](https://github.com/code-yeongyu/oh-my-openagent) 참고.

### 3. opencode-drewgent 클론

```bash
git clone https://github.com/humanerd-drew/opencode-drewgent.git ~/.drewgent
cd ~/.drewgent
# AGENTS.md를 프로젝트 루트에 심링크
ln -sf ~/.drewgent/AGENTS.md ./AGENTS.md
```

### 4. 에이전트 프로필 복사

```bash
cp ~/.drewgent/agents/*.md ~/.config/opencode/agents/
```

### 5. (선택) cron 데몬 설정

launchd를 통해 60초마다 cron 디스패처 실행:

```bash
cp ~/.drewgent/hooks/ai.drewgent.cron.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.drewgent.cron.plist
```

---

## 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                      사용자 입력                         │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│  OmO Sisyphus (Orchestrator)                           │
│  멀티 에이전트 워크플로우 자동 분배                      │
├────────────────────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │explorer  │ │implement │ │sre       │ │planner   │  │
│  │(리서치)   │ │(구현)    │ │(인프라)   │ │(계획)    │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
└────────────────────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│  지식 계층 (LLM Wiki)                                   │
│                                                        │
│  P5-ego/wiki/compiled/  ← 컴파일된 지식 (최우선 조회)    │
│  P5-ego/wiki/queries/   ← 캐시된 질문-답변              │
│  gbrain MCP             ← 벡터 검색                     │
│  P2-hippocampus/        ← 원시 데이터 (최후의 수단)      │
└────────────────────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│  인프라 계층                                            │
│                                                        │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────┐  │
│  │ cron        │  │ kanban.db   │  │ launchd        │  │
│  │ (jobs.json) │  │ (태스크 관리)│  │ (서비스 관리)   │  │
│  └─────────────┘  └─────────────┘  └────────────────┘  │
└────────────────────────────────────────────────────────┘
```

### 레이어 설명

| 레이어 | 역할 | 핵심 기술 |
|--------|------|-----------|
| **오케스트레이션** | 사용자 요청 → 적절한 에이전트 분배 | OmO Sisyphus, Team Mode |
| **에이전트** | 역할별 전문화된 subagent 15종 | opencode native agent profiles |
| **지식** | Karpathy 컴파일 패턴 기반 LLM Wiki | P5-ego/wiki/, gbrain |
| **인프라** | 백그라운드 작업, 태스크 관리, 서비스 | cron/jobs.json, kanban.db, launchd |

### 디렉토리 구조

```
~/.drewgent/
├── AGENTS.md              # 시스템 문서 (에이전트 가이드)
├── agents/                # 15개 subagent 프로필 (→ ~/.config/opencode/agents/)
│   ├── sre.md             # Site Reliability Engineering
│   ├── implementer.md     # 코드 구현
│   ├── planner.md         # 태스크 분해/계획
│   └── ...
├── cron/
│   ├── jobs.json          # 크론 작업 정의 (단일 소스)
│   ├── scheduler.py       # 크론 스케줄러 엔진
│   └── jobs.py            # 작업 저장/관리
├── scripts/
│   ├── drewgent_cron.py   # launchd 데몬 (60초 틱)
│   ├── office_autopilot.sh # kanban → OmO 디스패처
│   ├── cron_health_check.py # 전체 크론 상태 검증
│   ├── n8n_trigger_runner.py # 레거시 트리거 어댑터
│   └── discord_send.py    # Discord 알림 전송
├── P5-ego/wiki/           # LLM Wiki (컴파일드 지식)
│   ├── index.md           # 마스터 인덱스
│   ├── compiled/          # 17개 주제별 지식 페이지
│   └── lint-report.md     # 위키 건강 상태
└── hooks/                 # launchd plist 템플릿
```

---

## 주요 기능

### 1. 멀티 에이전트 오케스트레이션 (OmO)

OmO Sisyphus가 15개의 전문화된 subagent를 조정합니다.

| 명령 | 효과 |
|------|------|
| `ultrawork: ...` | 모든 에이전트 병렬 활성화 |
| `/team 3:executor "..."` | 팀 모드 (병렬 작업) |
| `@implementer ...` | 특정 subagent 직접 호출 |

### 2. LLM Wiki (Karpathy 컴파일 패턴)

RAG와 달리, 지식을 미리 컴파일해서 계속 축적합니다.

```
P2-hippocampus/ (원본) → wiki-compile cron → P5-ego/wiki/compiled/ (지식)
```

조회 우선순위:
1. `P5-ego/wiki/compiled/` — 컴파일드 지식 (최우선)
2. `gbrain query` — 벡터 검색
3. `P2-hippocampus/` — 원시 데이터

### 3. 크론 작업 자동화

60초마다 launchd 데몬이 `jobs.json`을 읽어 작업 실행.

| 작업 | 주기 | 방식 |
|------|------|------|
| Office Autopilot | 5분 | OmO Sisyphus가 kanban 태스크 처리 |
| Wiki Compile | 주간 일 03:00 | P2 → P5-ego/wiki/ 지식 컴파일 |
| Wiki Lint | 매일 04:00 | 위키 일관성 검사 |
| Cron Health Check | 매일 05:00 | 전체 크론 상태 검증 |
| Trend Harvester | 6시간 | AI 트렌드 수집 |
| Content Pipeline | 매일 12:00 | 자동 콘텐츠 생성 |

### 4. kanban 태스크 관리

SQLite 기반 kanban 시스템으로 작업 추적.

```bash
# 태스크 생성
sqlite3 ~/.drewgent/kanban.db "INSERT INTO tasks(id,title,status) VALUES ('my-task','내 작업','todo');"

# 태스크 조회
sqlite3 ~/.drewgent/kanban.db "SELECT id, title, status FROM tasks;"
```

---

## 시작하기 - 권장 워크플로우

### 새 기능 개발

```
/start-work "로그인 페이지 리팩토링"
```

1. Prometheus가 요구사항 인터뷰
2. Atlas가 실행 계획 수립
3. implementer가 코드 구현
4. sre가 배포

### 버그 수정

```
ultrawork: fix #42 — 유저 프로필 이미지가 안 보임
```

### 지식 검색

```
llm wiki: cron jobs.json 설정 방법
```

1. P5-ego/wiki/compiled/cron-operations.md 조회
2. 없으면 gbrain 벡터 검색
3. 없으면 P2 원시 데이터 검색

---

## 커스터마이징

### 나만의 subagent 추가

```bash
# 1. 프로필 생성
cat > ~/.config/opencode/agents/my-agent.md << 'EOF'
---
description: My custom agent
mode: subagent
model: opencode-go/deepseek-v4-flash
permission:
  read: allow
  bash: allow
  edit: allow
---
You are my custom agent. Do specific things.
EOF

# 2. AGENTS.md에 등록
echo "- @my-agent — 설명" >> AGENTS.md
```

### 나만의 크론 작업 추가

```bash
# jobs.json에 등록
# drewgent_cron.py가 자동으로 읽어서 실행
```

### Wiki 컴파일 범위 조정

`cron/jobs.json`의 `wiki-compile` job 프롬프트를 수정하여 컴파일할 소스 변경.

---

## trouble shooting

### OmO가 응답하지 않음

```bash
bunx oh-my-openagent doctor
```

### cron 데몬이 동작하지 않음

```bash
launchctl list | grep ai.drewgent.cron
# PID가 없으면:
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.drewgent.cron.plist
```

### kanban 태스크가 처리되지 않음

```bash
# 수동 트리거
cd ~/.drewgent && bash scripts/office_autopilot.sh
# 로그 확인
cat logs/office-autopilot.log
```

---

## 크레딧

opencode-drewgent은 아래 오픈소스 프로젝트들을 기반으로 동작합니다. 감사합니다.

| 프로젝트 | 저자 | 용도 | 라이선스 |
|---------|------|------|---------|
| [opencode](https://opencode.ai) | [Anomaly](https://github.com/anomalyco) | AI 코딩 에이전트 플랫폼 | MIT |
| [oh-my-openagent](https://github.com/code-yeongyu/oh-my-openagent) | [code-yeongyu](https://github.com/code-yeongyu) | 멀티 에이전트 오케스트레이션 (Sisyphus, ultrawork) | SUL-1.0 |
| [oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode) | [Yeachan-Heo](https://github.com/Yeachan-Heo) | 팀 모드 멀티 에이전트 패턴 참고 | MIT |
| [gbrain](https://github.com/garry-example/gbrain) | — | MCP 기반 지식 그래프 | — |
| [codebase-memory-mcp](https://github.com/anomalyco/opencode) | Anomaly | 코드베이스 지식 그래프 | MIT |
| [lazyweb](https://lazyweb.com) | — | UI 디자인 참고 MCP | — |
| [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) | Andrej Karpathy | 컴파일 패턴 지식베이스 개념 | — |
| [Ponytail](https://github.com/DietrichGebert/ponytail) | Dietrich Gebert | 코드 최소화 체크리스트 | — |
| [NeuronFS](https://github.com/drewgent/neuronfs) | — | 뇌 기반 거버넌스 시스템 | — |
| [specification.website](https://specification.website) | — | 웹 스펙 체크리스트 MCP | — |

이 프로젝트들은 각각의 라이선스를 따릅니다. 코드를 직접 포함하지 않으며, 설정/참조로만 사용됩니다.

---

## 라이선스

MIT
