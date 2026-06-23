---
title: Agents
type: guide
space: concept
tags: [concept, agent-guide]
created: 2026-05-20
updated: 2026-06-21
links:
  - "[[@identity/SELF_MODEL]]"
  - "[[@identity/brain/rules]]"
  - "[[@identity/persona/SOUL]]"
---

# Drewgent — Agent Guide

AI agent를 위한 Drewgent 프로젝트 구조·규칙·컨벤션 가이드.

---

## Current Architecture (2026-06-18)

Drewgent는 **opencode** 중심으로 운영한다. Hermes-Agent 제거됨, n8n 제거됨 (2026-06-18 launchd cron + opencode run 대체).

### Native Agent System

6개 merged subagent profiles가 `agents/*.md`에 opencode native 형식으로 정의됨.
TUI에서 `@agent-name` 으로 호출, 또는 `opencode run --agent <name>` 으로 CLI 호출.
자세한 목록은 `agents/` 참조.

```
~/.config/opencode/              # opencode 설정
  opencode.jsonc                   # 메인 설정 (+ MCP 서버: gbrain/discord/wordpress/gajae-code)
  skills/                          # opencode 스킬
  agents/                          # 6개 merged native agent 프로필 (opencode format)

~/.drewgent/                     # Drewgent 작업 디렉토리
  .well-known/                     # ARD ai-catalog.json
  scripts/                         # Python/bash 스크립트
    n8n_trigger_runner.py          # LLM 트리거 (파일체크 → kanban INSERT)
    discord_send.py                # Discord 메시지 청크 분할 전송
    discord_bot.py                 # Discord ↔ opencode 게이트웨이 봇 (--attach 사용)
    agent_dashboard_push.py        # Cloudflare 대시보드 푸셔
    ard_query.py                   # ARD Registry 검색 클라이언트
    opencode_health_check.py       # LLM health check (launchd cron)
  kanban.db                        # kanban 작업 DB
  logs/
  @-*/                             # Obsidian vault (@identity, @memory, @action)

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
~/.YOURAGENT/                    # 작업 디렉토리 + Obsidian vault (@-*)
  .well-known/                     # ARD ai-catalog.json
  scripts/                         # Python/bash/Node.js 스크립트
  @identity/                       # rules, persona, self model
  @memory/                         # raw archive, compiled wiki
  @action/                         # skills, sensors, plans
  config.yaml                      # 레거시 설정 (일부)
  AGENTS.md                        # ↔ 이 파일
```

### MCP Servers (`opencode.jsonc`)

| Server | Type | URL / Command | Auth |
|--------|------|--------------|------|
| `codebase-memory-mcp` | command (stdio) | `codebase-memory-mcp` | 없음 (로컬) |
| `discord` | command (stdio) | `discord-mcp` | `DISCORD_BOT_TOKEN` in opencode.jsonc |
| `gajae-code` | command (stdio) | `gjc mcp-serve coordinator` | `OPENCODE_API_KEY` in opencode.jsonc |
| `wordpress` | command (stdio) | `node .../wordpress-mcp-server.js` | 없음 (로컬) |

**Note:** gbrain MCP tools are built into the opencode platform — no separate daemon needed. gbrain CLI reads the local PGLite database directly.

**GJC Coordinator MCP** — Gajae-Code의 외부 컨트롤러 인터페이스. `gjc_delegate_*` 툴들은 GJC Coordinator MCP를 통해 주입된다.

### Config

- **Primary**: `~/.config/opencode/opencode.jsonc` — opencode 설정
- **Legacy**: `~/.YOURAGENT/config.yaml` — 일부 설정

---

## Agent Navigation Guide

### 이 파일들을 참조하라

| 파일 | 용도 |
|------|------|
| `@identity/brain/rules.md` | 禁 Critical Rules |
| `@identity/SELF_MODEL.md` | 셀프 모델, 정체성 |
| `@identity/persona/SOUL.md` | 성격, 어조, voice |
| `@identity/persona/writing-style-guide.md` | 글쓰기 컨벤션 |
| `@action/skills/<category>/SKILL.md` | 각 스킬 가이드 |

### 절대 수정 금지 (read-only)

- `~/.config/opencode/skills/` — opencode 번들 스킬
- `agents/*.md` — agent 프로필
- `~/.YOURAGENT/` 아래 개인 데이터 — 명시적 요청 없이 수정 금지

### 일반 작업 시 탐색 순서

1. **코드 분석** → `search_graph` / `trace_path` / `query_graph` 우선 (codebase-memory-mcp, 인덱싱된 모든 파일)
2. **지식 검색** → `@memory/wiki/compiled/` 우선, 없으면 `@memory/raw/` fallback ([[#LLM Wiki — Karpathy Compile Pattern]] 참조)
3. **설정 변경** → `~/.config/opencode/opencode.jsonc`
4. **스킬 생성/수정** → `@action/skills/<category>/SKILL.md` (skill_manage 툴 사용)
5. **메모리 저장** → `memory()` 툴 (target: memory 또는 user)
6. **규칙 추가** → `@identity/brain/rules.md` (禁 규칙은 별도 .neuron 파일)
7. **오류 진단** → `@memory/incidents/` 참조

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

## Vault Structure (@-*)

```
~/.YOURAGENT/
├── @identity/            # rules, persona, self model
├── @memory/              # raw archive + compiled wiki
├── @action/              # skills, sensors, plans
└── scripts/              # Python/bash/Node.js scripts
```

각 @-* 폴터는 Obsidian vault의 그래프 노드. 파일 간 wikilink로 연결된다.

## LLM Wiki — Karpathy Compile Pattern (2026-06-21)

**원칙:** Raw data = @memory/raw (read-only archive). Compiled knowledge = @memory/wiki (query target).

### Architecture

```
@memory/raw/            ← Raw Archive (unstructured, agent fingers off)
  memories/               Raw memory files
  sessions/               Raw session logs
  knowledge/              Raw collected knowledge

@memory/wiki/           ← Compiled Wiki (structured, query first)
  compiled/               Weekly-compiled wiki pages
  queries/                Saved query patterns
  index.md                Wiki index + routing rules
  lint-report.md          Daily health status
```

### Query Routing (strict priority)

1. **`@memory/wiki/compiled/`** — compiled pages first
2. **`@memory/raw/memories/`** — raw memory (fallback)
3. **`@memory/raw/knowledge/`** — raw knowledge (fallback)
4. **`@memory/raw/sessions/`** — raw session logs (last resort)

If you had to go beyond step 1, note what was missing — the wiki-compile job should cover it next run.

### Cron Jobs

| Job | Schedule | Profile | Action |
|-----|----------|---------|--------|
| wiki-compile | Sun 03:00 | archiver | Compile new @memory/raw data → @memory/wiki pages |
| wiki-lint | daily 04:00 | explorer | Check wiki health, report issues |

### Provenance

```
trigger: "Karpathy compile from system-overhaul 2026-06-21"
decision: "@memory/raw is pure storage; structured knowledge lives in @memory/wiki"
```

---

## Tiered Autonomy (신규)

작업 유형별 AI agent의 판단 권한 레벨. 불필요한 확인 요청을 줄이고, 위험한 결정은 반드시 인간을 거치게 한다.

| Tier | 범위 | 내 판단 권한 | 예시 |
|------|------|------------|------|
| 1 | 문서/코멘트/오타 | **Autonomous.** 완료 후 간단히 보고 | 오타 수정, README 업데이트, `memory()` 저장, skill 문서화 개선 |
| 2 | 기존 패턴 내 작업 | **Autonomous.** 단, provenance 포함 + 검증 | 기존 스킬 패치, 규칙에 명시된 config 변경, AGENTS.md 업데이트 |
| 3 | 구조 내 변경 | **제안 → 승인 후 실행.** draft + 옵션 제시 | customize layer 변경, 새 메커니즘 도입, skill 구조 변경 |
| 4 | 아키텍처/방향 | **사전 제안만.** 결정은 인간 | @-* vault 구조 변경, 새 전략 도입, fork/repot 결정 |

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
| 분석 저장 | `@action/taste-reviews/YYYY-MM-DD-slug.md` |

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

## ARD — Agentic Resource Discovery (2026-06-22)

Google/Microsoft 주도로 개발 중인 [ARD Spec](https://agenticresourcediscovery.org) (v0.9 Draft)을 Drewgent에 적용.

### Catalog

Drewgent의 6개 subagent를 `ai-catalog.json`으로 publish:

```
~/.drewgent/.well-known/ai-catalog.json   # catalog manifest
```

- URN 형식: `urn:air:drewgent.ai:agent:<slug>`
- Media type: `application/opencode-subagent+json`
- 각 agent: `capabilities`, `representativeQueries`, `metadata` (model/temperature) 포함
- 호스팅 필요: GitHub Pages 또는 CF Worker에서 `/.well-known/ai-catalog.json` serve

### Agent Profile Frontmatter

각 `agents/*.md`에 `ard:` 섹션 추가:
```yaml
ard:
  identifier: urn:air:drewgent.ai:agent:explorer
  type: application/opencode-subagent+json
  capabilities:
    - code-exploration
    - research
    - pattern-discovery
```

### Registry Query Client

`~/.drewgent/scripts/ard_query.py`:
```bash
python3 ard_query.py https://agentfinder.github.com/api/v1 "weather mcp server"
python3 ard_query.py https://ai-catalog.outshift.io "flight booking" --limit 5
```

### 등록된 ARD Registry (테스트 완료)

| Registry | Endpoint | 인증 |
|----------|----------|------|
| GitHub Agent Finder | `POST /api/v1/search` | 없음 (public) |
| Cisco AGNTCY | `GET /v1/agents?filter=...` | 없음 (public) |
| Hugging Face Discover | `POST /search` | 없음 (public) |

### 향후 계획

- [ ] CF Worker로 `/.well-known/ai-catalog.json` 호스팅 (`drewgent.ai` 도메인)
- [ ] `ard_query.py`를 `opencode.jsonc` MCP 서버로 등록 (runtime tool discovery)
- [ ] Kanban pipeline에 ARD discovery step 추가 — orchestrator가 필요 시 registry 검색
- [ ] `trustManifest` 추가 (SPIFFE 또는 DID 기반 workload identity)

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

### Agent Delegation (2026-06-23)

GJC Coordinator MCP가 OMO (opencode subagent profiles + delegate.ts)를 대체한다.

#### 호출 방식 (2계층)

| 방식 | 명령 | 모델 | 언제? |
|------|------|------|-------|
| **같은 세션** (빠름) | `task(subagent_type="reviewer", ...)` | 부모 모델 상속 | 프로필 모델이 부모와 같거나 상관없을 때 |
| **다른 모델** (정확) | `delegate(name="implementer", prompt="...")` | **프로필 모델 적용** | 프로필 고유 모델이 필요할 때 |

delegate()는 **GJC Coordinator MCP** `gjc_delegate_execute` 툴로 대체되었다. worktree isolation, tmux 병렬 실행이 필요할 때 사용한다.

```
# 같은 모델이면 task (가볍고 빠름)
task(
    subagent_type="explorer",
    description="Analyze auth code",
    prompt="Analyze the existing auth implementation..."
)

# 격리/병렬 실행이 필요하면 GJC (worktree + tmux)
gjc_delegate_execute(
    goal="Refactor auth module",
    worktree="refactor-auth",
    acceptance=["all tests pass", "API compatible"]
)

# 병렬 팀 실행
gjc_delegate_team(
    goals=[
        { id: "A", desc: "..." },
        { id: "B", desc: "..." },
        { id: "C", desc: "..." },
    ]
)
```

#### 모델 라우팅 (GJC)

GJC는 `OPENCODE_API_KEY`로 opencode-go/opencode-zen 모델 풀에 접근:

| Tier | 모델 | GJC alias | 용도 |
|------|------|-----------|------|
| **Flash** | `deepseek-v4-flash` | `--smol` / default | 분석, 간단 구현, 문서 |
| **Pro** | `deepseek-v4-pro`, `glm-5.2` | `--model deepseek-v4-pro` | 일반 작업, 코드 리뷰 |
| **Code** | `kimi-k2.7-code` | `--model kimi-k2.7-code` | 코드 생성 특화 |
| **Max** | `qwen3.7-max`, `qwen3.7-plus` | `--slow` | 복잡한 추론, 계획, 심층 리뷰 |

#### 프로필 목록

`agents/*.md` (opencode auto-discover)

| Profile | Model | Role | 비고 |
|---------|-------|------|------|
| explorer | deepseek-v4-flash | 읽기 전용 분석 + 데이터 분석 (ESCALATE 가능) | analyst 통합 |
| implementer | **kimi-k2.7-code** | 구현 + 테스트 (ESCALATE 가능) | tester 통합 |
| reviewer | deepseek-v4-pro | 코드 리뷰 + 콘텐츠 검수 | editor 통합 |
| reviewer-critical | **qwen3.7-plus** | 중요 변경 심층 리뷰 + 보안 감사 | security-reviewer 통합 |
| planner | qwen3.7-max | 태스크 분해 + 오케스트레이션 + SRE | orchestrator/sre 통합 |
| archiver | deepseek-v4-flash | 문서화/기록 + 콘텐츠 관리 | content-manager 통합 |

### Kanban Pipeline (2026-06-13)

```
kanban_create(
    title="Add login",
    pipeline=["explorer","implementer","reviewer"],
    # archiver runs automatically on completion (post-hook)
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
                  └─ N pending → gjc_delegate_execute(goal="Process pending kanban tasks", model="qwen3.7-max")
                       ├─ task 분류 → task() / gjc_delegate_execute
                       ├─ explorer / implementer / reviewer / planner / archiver
                      ├─ kanban_complete on success
                      └─ Discord summary
```

**규칙:**
- SILENT 기본값. 할 게 없으면 아무 일도 안 일어남.
- 비싼 모델(qwen3.7-max)는 작업이 있을 때만 호출됨.
- 모호한 task는 `kanban_block` → 사람 검토.
- 결과는 Discord #growth 채널로 요약.

### Linear Bridge (2026-06-13)

kanban_complete → post_tool_call hook → Linear issue upsert.

- Hook: `~/.YOURAGENT/hooks/kanban-linear-sync.py`
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
@action/skills/ui/baseline-ui/SKILL.md
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

- [[@identity/SELF_MODEL]]
- [[@identity/brain/rules]]
- [[@identity/persona/SOUL]]
- [[@identity/persona/writing-style-guide]]
