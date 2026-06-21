---
title: Agents
type: guide
space: concept
tags: [concept, agent-guide]
created: 2026-05-20
updated: 2026-06-21
links:
  - "[[P5-ego/SELF_MODEL]]"
  - "[[P0-brainstem/brain/rules]]"
  - "[[P1-limbic/persona/SOUL]]"
---

# Drewgent — Agent Guide

AI agent를 위한 Drewgent 프로젝트 구조·규칙·컨벤션 가이드.

---

## Current Architecture (2026-06-18)

Drewgent는 **opencode** 중심으로 운영한다. Hermes-Agent 제거됨, n8n 제거됨 (2026-06-18 launchd cron + opencode run 대체).

### Native Agent System

14개 subagent profiles가 `~/.config/opencode/agents/*.md`에 opencode native 형식으로 정의됨.
TUI에서 `@agent-name` 으로 호출, 또는 `opencode run --agent <name>` 으로 CLI 호출.
자세한 목록은 `~/.config/opencode/agents/` 참조.

```
~/.config/opencode/              # opencode 설정
  opencode.jsonc                   # 메인 설정 (+ MCP 서버: gbrain/lazyweb/spec/discord)
  skills/                          # opencode 스킬
  agents/                          # 14개 native agent 프로필 (opencode format)

~/.drewgent/                     # Drewgent 작업 디렉토리
  scripts/                         # Python/bash 스크립트
    n8n_trigger_runner.py          # LLM 트리거 (파일체크 → kanban INSERT)
    discord_send.py                # Discord 메시지 청크 분할 전송
    discord_bot.py                 # Discord ↔ opencode 게이트웨이 봇 (--attach 사용)
    agent_dashboard_push.py        # Cloudflare 대시보드 푸셔
    opencode_health_check.py       # LLM health check (launchd cron)
  kanban.db                        # kanban 작업 DB
  logs/
  P0-P6/                           # Obsidian vault

~/Library/LaunchAgents/          # launchd 서비스 (재부팅/크래시 자동 복구)
  ai.drewgent.opencode.plist       # opencode serve (:8642, headless daemon)
  ai.drewgent.discord-bot.plist    # Discord ↔ opencode 게이트웨이 (--attach, WaitForNetworkInterface)
  ai.drewgent.cron.plist           # cron dispatcher (60초)
```

### Self-Healing

- launchd **KeepAlive**: 크래시 시 10초 후 자동 재시작
- launchd **RunAtLoad**: 재부팅 후 로그인 시 자동 실행
- **Drewgent launchd watchdog**: 5분마다 서비스 상태 체크 (cron → drewgent_launchd_watchdog.sh)

### Launchd Cron (2026-06-18, n8n 대체)

1개 launchd plist (`ai.drewgent.cron`)가 60초마다 `drewgent_cron.py` 실행. 상태는 `~/.drewgent/logs/cron_state.json`에 저장.

| 주기 | 작업 | 방식 |
|------|------|------|
| 2분 | trend-evaluate | n8n_trigger_runner.py |
| 5분 | launchd watchdog, dashboard push | shell/python 스크립트 |
| 15분 | gbrain watchdog | shell 스크립트 |
| 6시간 | trend-collect, seo-harvester | Python/shell |
| 매일 04:00 | log rotation, wiki-lint | shell / explorer agent |
| 매일 06:00 | usage watch | Python |
| 매일 09:00 | harmony check | shell |
| 매일 12:00 | seo-analyze | n8n_trigger_runner.py |
| 매일 20:00 | daily retro | n8n_trigger_runner.py |
| 월 03:00 | wiki-compile | archiver agent |
| 월 10:00 | trend-retire | n8n_trigger_runner.py |
| 월 14:00 | seo-trend report | n8n_trigger_runner.py |
| 화/금 10:00 | taste review | n8n_trigger_runner.py |

### Discord 알림 파이프

| 구분 | 채널 | 방식 |
|------|------|------|
| launchd cron → webhook | SEO/Trend/Retro/Content/Health | n8n_trigger_runner.py + curl |
| Discord 봇 | 모든 채널 (스레드 생성) | discord_bot.py → opencode run --attach :8642 |

```
~/.hermes/                      # Hermes-Agent 설치 (plain, NOT forked)
  config.yaml                   # 메인 설정
  .env                          # API keys (chmod 600)
  skills/                       # Hermes 기본 스킬 (읽기 전용)
  profiles/                     # Hermes 프로필
  plugins/                      # Hermes 플러그인

~/.drewgent/                    # Drewgent 커스터마이징 + Obsidian vault (P0-P6)
  customize/                    # PYTHONPATH override 레이어
    sitecustomize.py            # Python startup hook
    hermes_cli/gateway.py       # launchd label override (ai.drewgent.*)
    hermes_cli/cron.py          # cron pid resolution
  skills/                       # Drewgent 전용 스킬 (100+)
  P0-brainstem/                 # 룰, 禁 규칙
  P1-limbic/                    # 정체성, persona, voice
  P2-hippocampus/               # Raw Archive (read-only) — 메모리, 세션, 지식
  P3-sensors/                   # 게이트웨이, 툴
  P4-cortex/                    # 스킬 색인, 성장 기록
  P5-ego/                       # 셀프 모델 + wiki/compiled (쿼리 대상)
  P6-prefrontal/                # 인시던트, 회고
  config.yaml                   # 레거시 설정 (일부)
  AGENTS.md                     # ↔ 이 파일

~/.local/bin/hermes             # Wrapper: PYTHONPATH 패치, unset PYTHONPATH 제거
                                # 원본은 hermes.bak
```

### Customize Layer 작동 방식

1. `~/.zshrc`에서 `export PYTHONPATH=~/.drewgent/customize:$PYTHONPATH`
2. Python이 `from hermes_cli.gateway import ...` 할 때 customize/ 디렉토리를 먼저 탐색
3. customize/hermes_cli/ 아래에 같은 모듈이 있으면 그게 우선 적용
4. Gateway plist에도 동일 PYTHONPATH 설정

### MCP Servers (`opencode.jsonc`)

| Server | Type | URL / Command | Auth |
|--------|------|--------------|------|
| `codebase-memory-mcp` | command (stdio) | `/Users/drew/.local/bin/codebase-memory-mcp` | 없음 (로컬) |
| `discord` | command (stdio) | `discord-mcp` | `DISCORD_BOT_TOKEN` in opencode.jsonc |
| `lazyweb` | remote (Streamable HTTP) | `https://www.lazyweb.com/mcp` | `Bearer {env:LAZYWEB_API_KEY}` (via `~/.zshrc`; launchd plist에 등록 필요) |
| `specification-website` | remote | `https://mcp.specification.website/mcp` | 없음 (public) |

**Note:** gbrain MCP tools are built into the opencode platform — no separate daemon needed. gbrain CLI reads the local PGLite database directly.

**Lazyweb** — 디자인 참고용 MCP. 281k+ 실제 앱 스크린샷 검색/비교.
- 설치: `plugins/lazyweb-skill/` (GitHub `aboul3ata/lazyweb-skill`)
- 토큰: `~/.zshrc`에 `LAZYWEB_API_KEY`로 등록 (free/no-billing bearer token)
- 용도: UI 디자인 작업 전 참고 스크린샷 검색, A/B 테스트 리서치, 플로우 분석
- **주의:** launchd 환경에 `LAZYWEB_API_KEY` 없음. opencode serve plist에 env 추가 필요 (MCP 재활성화 시)

### 현재 적용된 override

| Hermes 기본값 | Drewgent override | 파일 |
|--------------|-------------------|------|
| `ai.hermes.gateway` | `ai.drewgent.gateway` | `customize/hermes_cli/gateway.py` |
| `ai.hermes.cron-runner` | `ai.drewgent.cron-runner` | `customize/hermes_cli/gateway.py` |
| macOS Sonoma+ plist 파싱 | pid 추출 보정 | `customize/hermes_cli/gateway.py` |

### Config

- **Primary**: `~/.hermes/config.yaml` — Hermes-Agent 표준 설정
- **Legacy**: `~/.drewgent/config.yaml` — 일부 Drewgent 설정 (점진적 마이그레이션 중)

---

## Agent Navigation Guide

### 이 파일들을 참조하라

| 파일 | 용도 |
|------|------|
| `P0-brainstem/brain/rules.md` | 禁 Critical Rules (P0 우선) |
| `P5-ego/SELF_MODEL.md` | 셀프 모델, 정체성 |
| `P1-limbic/persona/SOUL.md` | 성격, 어조, voice |
| `P1-limbic/persona/writing-style-guide.md` | 글쓰기 컨벤션 |
| `skills/<category>/SKILL.md` | 각 스킬 가이드 |

### 절대 수정 금지 (read-only)

- `~/.hermes/skills/` — Hermes 기본 번들 스킬
- `~/.hermes/plugins/` — 명시적 요청 없이 수정 금지
- `customize/` 아래 파일 — 패턴을 먼저 읽고, 이해한 후에만 수정

### 일반 작업 시 탐색 순서

1. **코드 분석** → `search_graph` / `trace_path` / `query_graph` 우선 (codebase-memory-mcp, 인덱싱된 모든 파일)
2. **지식 검색** → `P5-ego/wiki/compiled/` 우선, 없으면 `P2-hippocampus/` fallback ([[#LLM Wiki — Karpathy Compile Pattern]] 참조)
3. **설정 변경** → `~/.hermes/config.yaml`
4. **스킬 생성/수정** → `~/.drewgent/skills/<category>/SKILL.md` (skill_manage 툴 사용)
5. **메모리 저장** → `memory()` 툴 (target: memory 또는 user)
6. **규칙 추가** → `P0-brainstem/brain/rules.md` (禁 규칙은 별도 .neuron 파일)
7. **오류 진단** → `P6-prefrontal/incidents/` 참조

---

## Provenance Convention (신규)

**원칙:** 모든 artifact 생성/수정 시 그 결정을 내리게 된 **trigger/context**를 함께 기록한다.

### Skill Frontmatter

```
---
title: skill-name
trigger: "이 스킬을 만든 동기 (무슨 문제/요청에서 비롯되었는가)"
provenance:
  session: "YYYY-MM-DD topic-description"
  decision: "왜 이렇게 설계했는가, 어떤 대안을 검토했는가"
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

예시:
```
---
title: drewgent-provenance-convention
trigger: "Pratik '30x AI Engineer with Taste' — 결정 맥락을 artifact에 박기 위해"
provenance:
  session: "2026-06-14 taste-discussion"
  decision: "taste 수용 결정 #1 — skill/memory/config 생성 시 trigger 기록을 의무화"
created: 2026-06-14
---
```

### Memory 저장 시

`memory()` 툴 content에 trigger 맥락 포함:
```
User preference for provenance tracking (from taste discussion 2026-06-14 — "Prompt alongside PR" 원칙)
```

### Config 변경 시

변경 이유를 commit message나 인접 문서에 기록.
직접 수정 시 `# Reason: <trigger>` 주석을 config에 추가.

### Kanban Task 생성 시

body에 provenance 포함:
```
## Origin
- Trigger: [문제/요청]
- Session: [날짜 topic]
- Decision rationale: [왜 이렇게 하는가]
```

---

## Kanban Leverage Score (신규)

**원칙:** "이 작업이 해결되면, 몇 개의 다른 문제가 자동으로 사라지는가?"

### Task 생성 시 (kanban_create)

Body에 Leverage Assessment 포함:
```
## Leverage Assessment
- 이 작업 해결 시 자동 해결되는 문제:
  1. ...
  2. ...
- Leverage Score (1-5): N
- 근거: (왜 이 점수인지 간단히)
```

### Task 완료 시 (kanban_complete)

metadata에 실제 impact 기록:
```json
{
  "leverage_score": 4,
  "problems_eliminated": ["problem A", "problem B"],
  "taste_decision": "왜 이 접근법이 최선이었는지"
}
```

### 점수 기준

| Score | 의미 | 예시 |
|-------|------|------|
| 5 | 전체 시스템의 근본 문제 해결 | 아키텍처 변경으로 클래스 전체 제거 |
| 4 | 여러 하위 문제를 한 번에 해결 | 공통 모듈 추출로 N개 중복 제거 |
| 3 | 명확한 개선 + 1-2개 부수 효과 | config 정리로 수동 스탭 제거 |
| 2 | 국소적 개선, 부수 효과 없음 | 버그 수정 |
| 1 | 표면적 변경, 영향 제한적 | 오타 수정, 문서 업데이트 |

---

## Vault Structure (P0-P6)

```
~/.drewgent/
├── P0-brainstem/         # 절대 규칙, 禁 뉴런
├── P1-limbic/            # 정체성, persona, voice, writing style
├── P2-hippocampus/       # Raw Archive (read-only) — 메모리, 세션, 지식
├── P3-sensors/           # 게이트웨이, 툴 통합, 데이터 흐름
├── P4-cortex/            # 스킬 인덱스, 성장 기록, 리팩토링 이력
├── P5-ego/               # 셀프 모델, 자기 인식 + wiki/compiled (쿼리 대상)
├── P6-prefrontal/        # 인시던트, 회고, 장기 계획
└── skills/               # 카테고리별 SKILL.md (100+)
```

각 P-layer는 Obsidian vault의 폴더. 파일 간 wikilink로 연결되어 그래프를 형성.

---

## LLM Wiki — Karpathy Compile Pattern (2026-06-21)

**원칙:** Raw data = P2-hippocampus (read-only archive). Compiled knowledge = P5-ego/wiki (query target).

### Architecture

```
P2-hippocampus/         ← Raw Archive (unstructured, agent fingers off)
  memories/               Raw memory files
  sessions/               Raw session logs
  knowledge/              Raw collected knowledge

P5-ego/wiki/            ← Compiled Wiki (structured, query first)
  compiled/               Weekly-compiled wiki pages
  queries/                Saved query patterns
  index.md                Wiki index + routing rules
  lint-report.md          Daily health status
```

### Query Routing (strict priority)

1. **`P5-ego/wiki/compiled/`** — compiled pages first
2. **`P2-hippocampus/memories/`** — raw memory (fallback)
3. **`P2-hippocampus/knowledge/`** — raw knowledge (fallback)
4. **`P2-hippocampus/sessions/`** — raw session logs (last resort)

If you had to go beyond step 1, note what was missing — the wiki-compile job should cover it next run.

### Cron Jobs

| Job | Schedule | Profile | Action |
|-----|----------|---------|--------|
| wiki-compile | Sun 03:00 | archiver | Compile new P2 data → wiki pages |
| wiki-lint | daily 04:00 | explorer | Check wiki health, report issues |

### Provenance

```
trigger: "Karpathy compile from system-overhaul 2026-06-21"
decision: "P2 is pure storage; structured knowledge lives in P5-ego/wiki"
```

---

## Tiered Autonomy (신규)

작업 유형별 AI agent의 판단 권한 레벨. 불필요한 확인 요청을 줄이고, 위험한 결정은 반드시 인간을 거치게 한다.

| Tier | 범위 | 내 판단 권한 | 예시 |
|------|------|------------|------|
| 1 | 문서/코멘트/오타 | **Autonomous.** 완료 후 간단히 보고 | 오타 수정, README 업데이트, `memory()` 저장, skill 문서화 개선 |
| 2 | 기존 패턴 내 작업 | **Autonomous.** 단, provenance 포함 + 검증 | 기존 스킬 패치, 규칙에 명시된 config 변경, AGENTS.md 업데이트 |
| 3 | 구조 내 변경 | **제안 → 승인 후 실행.** draft + 옵션 제시 | customize layer 변경, 새 메커니즘 도입, skill 구조 변경 |
| 4 | 아키텍처/방향 | **사전 제안만.** 결정은 인간 | P-layer 구조 변경, 새 전략 도입, fork/repot 결정 |

### 운영 규칙

- **Tier 1-2는 지연 없이 실행.** 굳이 "해도 될까요?" 묻지 않음.
- **Tier 3은 반드시 draft 제시:** `[제안]` prefix + 2-3개 옵션 + "내 추천"
- **Tier 4는 한 문장 요약** → 상세 논의는 결정 후
- 불확실하면 Tier 3으로 기본값. **더 위험하게 추측하지 말 것.**

### 근거 (Taste 원칙)

Codex 팀의 tiered code review system에서 영감:
- *"Non-critical code gets AI review only. Core agent code gets mandatory human review."*
- 핵심은 "어떤 코드가 critical한지 아는 것" 자체가 taste.
- 등급을 명시함으로써 판단 비용을 줄이고 일관된 수준 유지.

---

## Answer-First Communication (신규)

**원칙:** 복잡한 응답은 결과/결론을 먼저, 과정은 그 다음에.

### 구조

```
[요약/결론] — 한두 문장
[상세] — 필요한 경우에만
[부록] — 툴 출력, 로그, 참조
```

### 이유 (Taste)

기사 Month 1 연습에서: *"The good ones all do something in the first 30 seconds (usually show you the outcome before explaining the process)."*
CLI 환경에서는 특히 중요 — 사용자는 스크롤하지 않고 결과를 원함.

### 예외 사항

- 문제 진단/디버깅 맥락은 과정-먼저가 올바름 (사고 과정 공유)
- 사용자가 명시적으로 "어떻게 했어?"라고 물은 경우

---

## Taste Review (신규)

Trend Harvester keep 리스트에서 고품질 툴을 선정하여 **심층 분석**하고 taste 결정을 추출하는 주 2회 루틴.

| 항목 | 값 |
|------|-----|
| Cron job | `29ccd2c5d019` |
| 일정 | 화/금 10:00 KST |
| 채널 | Discord #growth |
| 소스 | Trend Harvester keep 리스트 (≥6.0 점수) |
| 분석 저장 | `P4-cortex/taste-reviews/YYYY-MM-DD-slug.md` |

### 분석 프레임워크 (5 Questions)

1. **One-Liner**: 이 툴을 한 문장으로?
2. **훔칠 Taste 결정**: 제작자가 내린 결정 중 Drewgent에 적용할 가치가 있는 것
3. **아키텍처 인사이트**: 구조적으로 배울 점
4. **Drewgent 적용 가능성**: 적용 가능? 어떻게?
5. **Leverage Score (1-5)**

### 원칙

- **양보다 질.** 모든 keep을 처리하는 게 목표가 아님. 진짜 가치 있는 인사이트에 집중.
- 분석 완료된 항목은 keep → applied로 이동.
- 자세한 내용: `taste-review` 스킬 참조.

---

## Important Policies

### Prompt Caching 유지

시스템 프롬프트를 세션 중간에 변경하지 않는다. 컨텍스트 압축 시에만 변경.
- 절대 `system` 메시지에 변하는 내용을 넣지 않음 (link-resolve 등)
- 스킬은 user 메시지로 주입 (system 아님)

### Filesystem = Truth

파일 시스템 상태를 canonical source로 간주한다. 단, 코드 분석은 graph tool 우선.
- **graph tool 실패 시** → search_files → file read 순서로 검증 (fallback)
- graph tool로 검증 안 되는 항목만 직접 파일 읽기
- 확인되지 않은 subagent 출력은 수락 금지

### 리팩토링 원칙

- **절대 빅뱅 금지.** change → dev server test → confirm → next
- 위험도 0% 변경부터 시작 (데드코드 제거)
- 결정 전 충분한 분석 데이터 제시 ("조치 결정 할 수 있도록")
- 옵션 → "내 추천" → user go 구조

### QA 게이트

3-phase QA: contract → micro → full. kanban task는 각 phase 통과 후 complete.

### 모델 라우팅

| 조건 | 경로 |
|------|------|
| 메인 (interactive) | opencode-go/deepseek-v4-flash |
| subagent (복잡) | opencode-go/deepseek-v4-pro |
| vision | opencode-go/mimo-v2.5-pro |
| MiniMax 직접 (fallback) | provider: minimax, model: MiniMax-M3 |

OpenCode GO 구독 모델 풀:
- **Flash**: deepseek-v4-flash, kimi-k2.7-code (코드 생성 특화)
- **Pro**: deepseek-v4-pro, glm-5.2, minimax-m3
- **Max**: qwen3.7-max, qwen3.7-plus (최신)

### Agent Office (2026-06-20)

14개 subagent profiles at `~/.config/opencode/agents/*.md` — opencode native format.

#### 호출 방식 (2계층)

| 방식 | 명령 | 모델 | 언제? |
|------|------|------|-------|
| **같은 세션** (빠름) | `task(subagent_type="reviewer", ...)` | 부모 모델 상속 | 프로필 모델이 부모와 같거나 상관없을 때 |
| **다른 모델** (정확) | `delegate(name="implementer", prompt="...")` | **프로필 모델 적용** | 프로필 고유 모델이 필요할 때 |

`delegate()`는 `~/.config/opencode/tools/delegate.ts` 커스텀 툴. 내부에서 `opencode run --agent <name> --model <model> --attach :8642` 실행 → 프로필 모델이 적용된 새 세션을 띄우고 결과 반환.

```
# 같은 모델이면 task (가볍고 빠름)
task(
    subagent_type="explorer",
    description="Analyze auth code",
    prompt="Analyze the existing auth implementation..."
)

# 다른 모델이 필요하면 delegate (새 세션)
delegate(
    name="implementer",
    prompt="Implement login validation. Files: src/auth/login.ts..."
)
```

#### 프로필 목록

`~/.config/opencode/agents/*.md` (opencode auto-discover), Custom tool: `~/.config/opencode/tools/delegate.ts`

| Profile | Model | Role |
|---------|-------|------|
| explorer | deepseek-v4-flash | 읽기 전용 분석 (ESCALATE 가능) |
| implementer | **kimi-k2.7-code** | 구현 — 코드 생성 특화 모델 (ESCALATE 가능) |
| tester | deepseek-v4-flash | 테스트 (ESCALATE 가능) |
| reviewer | deepseek-v4-pro | 일반 코드 리뷰 |
| reviewer-critical | **qwen3.7-plus** | 중요 변경 심층 리뷰 — 최상급 추론 |
| security-reviewer | **minimax-m3** | 보안 감사 — 다른 계열 모델로 다양한 시각 |
| planner | qwen3.7-max | 태스크 분해/계획 |
| orchestrator | qwen3.7-max | 작업 배정/파이프라인 조정 |
| designer | deepseek-v4-flash | UI/UX 디자인 (ESCALATE 가능) |
| sre | deepseek-v4-flash | 인프라/인시던트 (ESCALATE 가능) |
| analyst | deepseek-v4-flash | 데이터 분석 (ESCALATE 가능) |
| content-manager | deepseek-v4-pro | CMO 콘텐츠 생성 |
| editor | glm-5.2 | 콘텐츠 검수/한국어 인퓨전 |
| archiver | deepseek-v4-flash | 문서화/기록 |

### Kanban Pipeline (2026-06-13)

```
kanban_create(
    title="Add login",
    pipeline=["explorer","implementer","tester","reviewer","archiver"],
)
```

N개 sequential child task 자동 생성 + 의존성 링크.

### Office Autopilot (2026-06-20)

`office_autopilot.sh`가 cron으로 5분마다 kanban DB를 확인, pending task가 있으면 orchestrator를 호출하여 자율 처리.

```
cron (60s tick)
  └─ drewgent_cron.py
       └─ office-autopilot (300s)
            └─ sqlite3 check kanban.db
                 ├─ 0 pending → silent
                 └─ N pending → opencode run --agent orchestrator --attach :8642
                      ├─ orchestrator가 task 분류 → delegate()
                      ├─ implementer / content-manager / sre / explorer / etc.
                      ├─ kanban_complete on success
                      └─ Discord summary
```

**규칙:**
- SILENT 기본값. 할 게 없으면 아무 일도 안 일어남.
- 비싼 에이전트(orchestrator, qwen3.7-max)는 작업이 있을 때만 호출됨.
- 모호한 task는 `kanban_block` → 사람 검토.
- 결과는 Discord #growth 채널로 요약.

### Linear Bridge (2026-06-13)

kanban_complete → post_tool_call hook → Linear issue upsert.

- Hook: `~/.hermes/agent-hooks/kanban-linear-sync.py`
- Cron: 매 2시간 prune + feedback 체크
- Archive: 7일 지난 completed issue 자동 정리
- Free tier limit: 250 issues, safety margin 200

### Ponytail — Lazy Senior Dev Mode (2026-06-15)

코드를 생성하기 전, 항상 다음 체크리스트를 적용한다. 출처: [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail).

```
1. 이 코드가 정말 필요한가? (YAGNI)         → no: 작성하지 않음
2. 표준 라이브러리에 이미 있나?               → use it
3. 네이티브 플랫폼 기능으로 되나?              → use it (<input type="date"> 등)
4. 이미 설치된 디펜던시가 해결하나?            → use it (새 dep 추가 금지)
5. 한 줄로 가능한가?                           → one line
6. 그래도 필요하면 최소한만.
```

**Rules:**
- 요청되지 않은 추상화 금지. 회피 가능한 새 dep 금지.
- 보일러플레이트 금지. 추가보다 삭제. 영리함보다 단순함. 최소 파일 수.
- 단순화는 `ponytail:` 코멘트로 표시. 한계와 업그레이드 경로를 함께 명시.

**NOT lazy about (절대 타협 금지):**
- Trust boundary validation, data-loss 방지, security, a11y, hardware calibration
- 사용자가 명시적으로 요청한 사항

**Verification:**
Non-trivial 로직은 **1개의 runnable check**를 남긴다 (assert 기반, 프레임워크 금지). Trivial one-liner는 test 불필요.

자세한 내용: `skills/software-development/ponytail` 참조.

### Baseline UI — Frontend Quality Standard (2026-06-17)

모든 frontend 작업 전에 로드할 UI quality bar. ponytail과 상호보완 — ponytail은 코드 최소화, baseline-ui는 디자인 퀄리티.

12개 priority tier: Stack Defaults → HTML Semantics → Accessibility (9-tier) → Typography → Color → Layout → Motion & Animation (9-tier, FLIP/scroll-timeline 포함) → Interactive Patterns → SEO → Content Discipline → Performance → Anti-Slop.

기존 claude-design, sketch, ponytail, project-restructure, seo-audit에 분산된 UI 규칙을 1개 파일로 통합. ui-skills (ibelick) 참고하여 a11y + motion perf section depth 보강.

```
~/.drewgent/skills/ui/baseline-ui/SKILL.md
```

UI 작업 시 `skill("baseline-ui")` 로드.

---

### Cron Job Creation Checklist (2026-06-21)

새 cron job 추가 시 반드시 확인:

- [ ] `cron/jobs.json`에 job entry 추가 (unique hex ID, schedule, deliver)
- [ ] script 파일 생성 시 `scripts/` 디렉토리에 배치
- [ ] `cron_health_check.py`가 감지할 수 있도록 `enabled: true` + `state: "scheduled"` 설정
- [ ] `cron/output/` 디렉토리에 결과 파일이 쌓이는지 확인 (output 있는 job의 경우)
- [ ] Discord deliver 채널 ID 올바른지 확인
- [ ] 수동 실행 테스트: `python3 scripts/<script>.py` 또는 opencode run
- [ ] AGENTS.md Launchd Cron 테이블에 새 job 추가 (주기/작업/방식)

---

## Known Pitfalls

### Python 3.14: json scope bug
큰 함수 내에서 `except json.JSONDecodeError:`를 쓰면 `json.loads()`가 UnboundLocalError.
해결: `__import__('json').loads()` 또는 별도 wrapper 함수 사용.

### macOS bash 3.2
associative array 없음, `date -j -f` 필요, `set -u` 문제.

### Launchd plist 패턴
모든 Drewgent 서비스: `KeepAlive { SuccessfulExit: false, ThrottleInterval: 10 }`
`<true/>` (exit 0 재시작 안 함) 또는 `<false/>` (재시작 안 함) 쓰지 말 것.

---

## Links

- [[P5-ego/SELF_MODEL]]
- [[P0-brainstem/brain/rules]]
- [[P1-limbic/persona/SOUL]]
- [[P1-limbic/persona/writing-style-guide]]
