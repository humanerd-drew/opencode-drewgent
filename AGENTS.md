---
title: Agents
type: guide
space: concept
tags: [concept, agent-guide]
created: 2026-05-20
updated: 2026-07-02
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

### YOUR_DOMAIN — WordPress Security & SEO (2026-06-27)

WordPress 사이트(YOUR_DOMAIN) 보안 및 SEO 정리 내역:

**보안**
- `humanerd-security.php` MU 플러그인으로 모든 보안/SEO/디자인 관리
- HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy 응답 헤더
- wp-admin: 로그인 세션 없으면 301 차단. 로그인 사용자는 정상 접근.
- wp-login.php: 일반 접근 가능. 무차별 대입 방어 (3초 지연 + IP당 5회 실패 시 1h lockout)
- xmlrpc.php, readme.html, install.php: 301 차단
- REST API `/wp/v2/users` 엔드포인트 제거 (사용자 열거 방지)
- DISALLOW_FILE_EDIT = true. WP_DEBUG_DISPLAY = false

**SEO**
- `computer.md` 없음 — `humanerd-security.php`에서 `<meta description>`, OG tags, Twitter cards 자동 생성
- Schema.org JSON-LD: WebSite + Organization (전체), BlogPosting (포스트별)
- `llms.txt` — AI 크롤러용 동적 콘텐츠 목록 (카테고리별 모든 발행글)
- `/.well-known/ai-catalog.json` — ARD v1.0 규격, 15개 agent 등록
- wp-sitemap.xml — WordPress 내장 (posts + pages + categories + tags)

**포스트 slug 컨벤션**
- 모든 slug 영문 kebab-case로 변경 (예: `model-routing-architecture`, `14-to-6-agents`)
- content-manager agent가 새 글 생성 시 영문 slug 사용하도록 강제
- 기존 URL은 자동 301 → 새 slug

**내부 링킹 (CGE)**
- `content-graph-engine`이 매일 06:00에 TF-IDF + taxonomy 기반 내부 링크 추천 → 상위 3개 자동 적용
- 스크립트: `content_graph_builder.py` (build + apply)

**디자인**
- 제목/본문 Noto Sans KR 통일 (sans-serif only, serif 제거)
- 카드 스타일 (rounded + 미세 그림자 + 호버 효과)
- 댓글 스타일 (rounded input, 포커스 링, 브라운 버튼)
- 푸터 GeneratePress 크레딧 제거

**정리**
- Hello Dolly 삭제, Akismet 5.7 업데이트 + 활성화
- 모든 태그 삭제 (일관성 없어 무의미)
- 작성자 누락 버그 수정: MCP 서버에 `--post_author=1` 추가
- content-manager agent 프로필에 slug/category 컨벤션 명시

### Agent System

Drewgent는 **opencode**의 내장 `task()` + **GJC Coordinator MCP** 조합으로 작동.

- **`task(subagent_type="...")`** — opencode 내장. 복잡한 멀티스텝 작업을 별도 세션에 위임. subagent 타입은 opencode built-in.
- **`gjc_delegate_*`** — GJC Coordinator MCP 툴. worktree isolation, tmux 병렬 실행, structured workflow (deep-interview/ralplan/ultragoal)가 필요할 때 사용.
- **직접 실행** — 단순/일반 작업. subagent 없이 내가 직접 처리.

```
~/.config/opencode/              # opencode 설정
  opencode.jsonc                   # 메인 설정 (+ MCP 서버: gbrain/discord/wordpress/gajae-code)
  skills/                          # opencode 스킬

~/.drewgent/                     # Drewgent 작업 디렉토리
  .well-known/                     # ARD ai-catalog.json (source, deployed via MU plugin)
  wordpress/                       # WordPress (Docker compose + theme/plugin overrides)
    docker-compose.yml
    .wp-env                        # DB/Admin credentials (chmod 600)
    wp-content/themes/generatepress/
    wp-content/plugins/
  scripts/                         # Python/bash/Node.js 스크립트
    n8n_trigger_runner.py          # LLM 트리거 (파일체크 → kanban INSERT)
    discord_send.py                # Discord 메시지 청크 분할 전송
    discord_bot.py                 # Discord ↔ opencode 게이트웨이 봇 (--attach 사용)
    agent_dashboard_push.py        # Cloudflare 대시보드 푸셔
    ard_query.py                   # ARD Registry 검색 클라이언트
    trend_scorer.py                # Heuristic trend scoring (LLM-free, cron script fastpath)
    wordpress-mcp-server.js        # WordPress MCP server (wp-cli via docker exec)
    opencode_health_check.py       # LLM health check (launchd cron)
  kanban.db                        # kanban 작업 DB
  logs/
  P0-P6/                           # Obsidian vault
  @memory/growth/trend-harvester/  # Trend harvester output (collected/→scored→analyzed/keep/, evaluated/, applied/)

~/Library/LaunchAgents/          # launchd 서비스 (재부팅/크래시 자동 복구)
  ai.drewgent.opencode.plist       # opencode serve (:8642, headless daemon)
  ai.drewgent.discord-bot.plist    # Discord ↔ opencode 게이트웨이 (--attach, WaitForNetworkInterface)
  ai.drewgent.cron.plist           # cron dispatcher (60초)
  ai.YOUR_AGENT.cloudflared-wp.plist # Cloudflare Tunnel → YOUR_DOMAIN (WordPress)
```

### Self-Healing

- launchd **KeepAlive**: 크래시 시 10초 후 자동 재시작
- launchd **RunAtLoad**: 재부팅 후 로그인 시 자동 실행
- **Drewgent launchd watchdog**: 5분마다 서비스 상태 체크 (cron → drewgent_launchd_watchdog.sh)

### Launchd Cron (2026-06-18, n8n 대체)

1개 launchd plist (`ai.drewgent.cron`)가 60초마다 `drewgent_cron.py` 실행. 상태는 `~/.drewgent/logs/cron_state.json`에 저장.

**Known trap:** jobs.json schedule 필드가 string이면 `parse_schedule()` crash. 항상 `{"kind": "cron", "expr": "..."}` 형식 사용.

| 주기 | 작업 | 방식 |
|------|------|------|
| 5분 | launchd watchdog, dashboard push | shell/python 스크립트 |
| 15분 | gbrain watchdog | shell 스크립트 |
| 매시간 | **housekeeper** (pulse) | drewgent_housekeeper.py → Discord Bot API |
| 3시간 | **content-curator** | content_curator.py ($0, Python) — 모든 소스 heuristic curation → kanban INSERT |
| 5분 | **office-autopilot** | 1개 task씩 순차 처리 (token 폭주 방지) |
| 12:00 / 20:00 | **content-editor** | opencode run (agent) — 사후 QA |
| 일 10:00 | **content-weekly** | opencode run (agent) — 주간 요약 포스트 |
| 6시간 | trend-collect (parallel, 8 workers) → **trend-scorer** (30분 후, heuristic) | Python/shell |
| 매일 03:00 | seo-analyze | seo_analyzer.sh |
| 매일 04:00 | **housekeeper** (deep clean), log rotation, wiki-lint, QA evidence digest, gbrain wiki sync | drewgent_housekeeper.py |
| 매일 05:00 | **content-taste-diff** | content_diff_analyzer.py |
| 매일 05:00 | cron health check | cron_health_check.py |
| 매일 06:00 | usage watch | trend_usage_watch.py |
| 월 06:00 | seo-ontology-builder | seo_ontology_builder.py → LLM 증분 온톨로지 업데이트 |
| 매일 09:00 | harmony check | drewgent_harmony_check.sh |
| 매일 20:00 | daily retro | opencode run |
| 매일 03:00 | wiki-compile (archiver) | opencode run |

**추가/변경 (2026-07-01):**
- `content-curator` 🆕 — 기존 6개 job(content-manager-periodic, content-news/insight/series-trigger, content-planner, trend-evaluate-trigger)을 1개 Python 스크립트로 통합. $0 heuristic curation.
- `content-weekly` 🆕 — 주간 요약 digest (일 10:00)
- `content-editor-periodic` — 2h → **12:00/20:00**로 축소 (불필요한 QA 호출 제거)
- `content-taste-diff` 제거 (content-curator와 중복)
- `taste-review-trigger` **비활성화** (n8n zombie)
- `trend-evaluate-legacy` (every 2m, n8n trigger) → **비활성화** (n8n 제거됨)
- `kanban-dispatcher` (cron_runner.py) → **비활성화** (Hermes 제거됨, office-autopilot가 대체)
- `content-graph-engine` (daily 06:00) → **build + apply** — TF-IDF + taxonomy 링크 추천 → 상위 3개 자동 적용
  - `content_graph_builder.py`가 `build` + `apply --limit 3` 실행
  - 데이터 위치: `content-graph-engine/`, 결과: `P4-cortex/content/content-graph.json`

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
| `gajae-code` | command (stdio) | `gjc mcp-serve coordinator` | `OPENCODE_API_KEY` in opencode.jsonc |
| `wordpress` | command (stdio) | `node .../wordpress-mcp-server.js` | 없음 (로컬) |
| `astryx` | remote (HTTP) | `https://astryx.atmeta.com/mcp` | 없음 (공개) — Meta Astryx design system MCP (search + get) |

**Note:** gbrain MCP tools are built into the opencode platform — no separate daemon needed. gbrain CLI reads the local PGLite database directly.

**GJC Coordinator MCP** — Gajae-Code의 외부 컨트롤러 인터페이스. `gjc_delegate_plan`, `gjc_delegate_execute`, `gjc_delegate_team` 툴 제공. worktree isolation, tmux 병렬 실행, structured workflow (deep-interview/ralplan/ultragoal) 지원.

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
| wiki-compile | daily 03:00 | archiver | Compile new P2 data → wiki pages |
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

## ARD — Agentic Resource Discovery (2026-06-22)

Google/Microsoft 주도로 개발 중인 [ARD Spec](https://agenticresourcediscovery.org) (v0.9 Draft)을 Drewgent에 적용.

### Catalog

Drewgent의 MCP 서버 툴을 `ai-catalog.json`으로 publish:

```
~/.drewgent/.well-known/ai-catalog.json   # catalog manifest (source)
→ WordPress MU plugin으로 serve → https://YOUR_DOMAIN/.well-known/ai-catalog.json
```

- 각 MCP 툴: `capabilities`, `representativeQueries`, `metadata` 포함
- 호스팅: WordPress MU plugin (`YOUR_AGENT-ard.php`)이 `/.well-known/ai-catalog.json` 인터셉트

### GJC Coordinator MCP Tools

`gjc_delegate_*` 툴들은 GJC Coordinator MCP를 통해 주입된다:
- `gjc_delegate_plan` — deep-interview + ralplan 워크플로
- `gjc_delegate_execute` — ultragoal 워크플로 (worktree + tmux)
- `gjc_delegate_team` — 병렬 tmux worker 오케스트레이션

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

## File Access Policy

### 절대 읽지 말 것 (vault/secret 파일)
다음 파일은 절대 Read tool로 읽지 않는다:
- `~/.config/drewgent/vault.key` — vault 암호화 키 (`~/.drewgent` 외부에 보관)
- `secrets_vault.json` — secrets 저장소
- `secrets_registry.json` — secrets 레지스트리
- `.env` (있는 경우) — 환경변수
- `keys/` 아래 모든 파일

이 파일들은 opencode watcher에서도 제외되어 있다. 명시적으로 요청받아도 읽지 않는다.

### Vault Secrets 규칙 (vault_cli.py)
사용자가 API 키/토큰/secret을 건네면:
1. 절대 평문으로 파일에 쓰지 않는다 (`.zshrc`, `.env`, `opencode.jsonc` 등)
2. `vault set KEY_NAME <value>` 로 즉시 암호화 저장
3. config 변경이 필요하면 `{env:KEY_NAME}` 참조만 사용
4. 기존 평문 발견 시 `vault migrate`로 일괄 이관

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


OpenCode GO 구독 모델 풀 (2026-06-28 cost analysis 기준, per-call 비용):
- **Flash** ($0.00038/call): deepseek-v4-flash — 메인 세션, 실행 작업, 간단 분석
- **Pro** ($0.0035/call, 9.2x flash): deepseek-v4-pro, glm-5.2, minimax-m3 — 코드 리뷰, 계획
- **Code** ($0.012/call, 32x flash): kimi-k2.7-code — ~~코드 생성 특화~~ (32배 비용 대비 flash로 대체)
- **Max** ($0.0356/call, 94x flash): qwen3.7-max, qwen3.7-plus — 복잡 추론, 심층 검토

### Agent Profile Model Assignment (성능 최적화 → 비용 최적화)

**원칙:** 계획/검증=고급모델(max/pro), 수행=저급모델(flash). 글쓰기/코드생성은 수행에 해당.

| Profile | 성능 최적화 (기존) | 비용 최적화 (현재) | 근거 |
|---------|-------------------|-------------------|------|
| **implementer** | `kimi-k2.7-code` ($0.012) | `deepseek-v4-flash` ($0.00038) | 코드 생성=수행. kimi 32x 비용 대비 효과 미미 |
| **content-manager-periodic** | — | **제거됨** (content-curator.py로 대체) | 2026-07-01: $0 Python 스크립트로 통합 |
| **wiki-compile** | `deepseek-v4-pro` ($0.0035) | `deepseek-v4-flash` ($0.00038) | 문서 컴파일=수행. cron jobs.json override |
| **reviewer** | `deepseek-v4-pro` ($0.0035) | `deepseek-v4-pro` | 유지 — 검증은 pro 적정 |
| **content-planner** | — | **제거됨** (content-curator.py로 대체) | 2026-07-01: $0 Python 스크립트로 통합 |
| **planner** | `qwen3.7-max` ($0.0356) | `qwen3.7-max` | 유지 — 계획은 max 적정 |
| **reviewer-critical** | `qwen3.7-max` ($0.0356) | `qwen3.7-max` | 유지 — critical 검토는 max 적정 |
| **메인 세션** | `deepseek-v4-flash` | `deepseek-v4-flash` | 유지 |

| Metric | 성능 최적화 (6/27) | 비용 최적화 (예상) | 절감 |
|--------|-------------------|-------------------|------|
| 주간 예상 소모 | $30.07/2일 (한도 100%) | ~$10.46/2일 ($5/일) | **65%** |
| 실행 작업 모델 | kimi/pro → flash로 통일 | |

Groq Free Tier 모델 풀 (내부 작업 전용):
- **openai/gpt-oss-20b** (1000 t/s, 30 RPM, 1K RPD, structured_outputs, reasoning) — 내부 작업 주력
- **openai/gpt-oss-120b** (500 t/s, 30 RPM, 1K RPD, 120B, reasoning) — 복잡 분석
- **qwen/qwen3-32b** (400 t/s, **60 RPM**, 1K RPD, reasoning) — RPM 2배, 대안
- **llama-3.1-8b-instant** (560 t/s, 30 RPM, **14.4K RPD**) — 고처리량 단순 작업  # RPD만 유일하게 여유
- **whisper-large-v3-turbo** (STT, 20 RPM, 2K RPD) — 음성→텍스트

실제 한도 (60 concurrent burst 테스트 검증):
- **RPM**: 30 (Qwen3-32b만 60). 모든 모델 공통.
- **RPD**: 1,000 대부분. llama-3.1-8b만 14,400으로 예외.
- **TPM**: 모델별 상이 (8K~30K)
- 30 RPM = 2초에 1회. 연속 호출 시 429 발생. 반드시 exponential backoff 필요.

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
| **Code** | `kimi-k2.7-code` | `--model kimi-k2.7-code` | 코드 생성 특화 (비용 주의: flash 32배) |
| **Max** | `qwen3.7-max`, `qwen3.7-plus` | `--slow` | 복잡한 추론, 계획, 심층 리뷰 |

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

`office_autopilot.sh`가 cron으로 5분마다 kanban DB를 확인, pending task가 있으면 orchestrator task를 통해 자율 처리.

```
cron (60s tick)
  └─ drewgent_cron.py
       └─ office-autopilot (300s)
            └─ sqlite3 check kanban.db
                 ├─ 0 pending → silent
                 └─ N pending → opencode run --attach :8642
                      ├─ task 분류 → gjc_delegate_execute / 직접 처리
                      ├─ kanban_complete on success
                      └─ Discord summary
```

**규칙:**
- SILENT 기본값. 할 게 없으면 아무 일도 안 일어남.
- 비싼 모델(qwen3.7-max)은 작업이 있을 때만 호출됨.
- 모호한 task는 `kanban_block` → 사람 검토.
- 결과는 Discord #growth 채널로 요약.
- **중복 spawn 방지**: `pgrep -f "opencode run.*ultrawork"`로 이미 실행 중인 세션 감지 → 있으면 skip.

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

### Generated Content Attribution (2026-07-02)

모든 생성물(블로그, X 스레드, 아티팩트, 리포트, HTML, SVG)의 말미에 푸터를 추가한다:

```
Built with [opencode-drewgent](https://github.com/humanerd-drew/opencode-drewgent)
```

**규칙:**
- 포스트 내용에 통합 (별도 "광고" 영역 금지. 마지막 줄로 자연스럽게)
- 한국어 생성물: `opencode-drewgent로 제작됨`
- Xitter 짧은 글: 해시태그 `#opencode #drewgent`
- UI/HTML 아티팩트: 화면 하단 고정 푸터로 렌더링 (눈에 띄지 않게)

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

### 토큰/비용 데이터 = SQLite, not stderr log
opencode CLI의 stderr 로그에는 토큰/비용 정보가 없음 (`tokens.input=0`만 기록).
**실제 데이터는 `~/.local/share/opencode/opencode.db`의 `message` 테이블**에 있음.
`agent_dashboard_push.py`에서 `collect_model_usage()`는 반드시 SQLite를 우선 조회하고, 실패 시에만 로그 fallback.

이걸 몰라서 2026-07-02에 추정치로 때웠다가, user가 KV 얘기를 꺼내서 실제 DB 발견. **항상 `opencode.db`를 먼저 확인할 것 — stderr 로그 파싱은 call count fallback용.**

### 변경 전 KV/storage 영향 확인 (Repeat-Request Trap)
예전에 논의/변경한 사항을 잊고 다시 요청하는 케이스 방지:
- `agent_dashboard_push.py` 의존성 변경(log→SQLite, endpoint URL 등) 전에는 KV/스토리지 영향부터 체크
- `wrangler kv key list --binding AGENT_DASHBOARD`로 현황 확인
- history 데이터 일별 사이즈 체크 (`GET /api/history?date=YYYY-MM-DD`)
- payload 사이즈 변화량 확인
- "한 번 user가 바꾸라고 한 적 있는 패턴"이면 반드시 `git log --oneline`이나 AGENTS.md Known Pitfalls 확인 후 진행

---

---

## Template Push Workflow

Drewgent의 공개 템플릿(`humanerd-drew/opencode-drewgent`)에 변경사항을 공유할 때 사용.

### Trigger

사용자가 "공개 템플릿에 올려줘" 또는 "push-template" 요청.

### How it works

`scripts/push-template.sh` 자동 실행:

1. `.last-template-push`에 기록된 SHA 이후 변경사항 탐지
2. 개인 데이터 자동 제외:
   - `agent/`, `cron/jobs.json`, `config.yaml`, `.env`, `kanban.db` — runtime state
   - `@memory/`, `@action/incidents/` — 개인 세션/사고 기록
   - `plans/`, `nix/`, `website/`, `scripts/archive/` — 개인 계획/인프라
3. 인격정보 자동 치환: `YOUR_DOMAIN` → `YOUR_DOMAIN`, `your-email@example.com` → `your-email@example.com`, `YOUR_DOCKER_USER/` → `YOUR_DOCKER_USER/`
4. `public/main`에 워크트리 생성 → 복사 → 커밋 → 푸시
5. `.last-template-push` 업데이트 (다음 증분 push 기준)

### 수동 확인 사항

스크립트 실행 후에도 다음은 직접 확인:
- `@identity/` 파일에 개인 데이터가 남아있지 않은지
- 새로 추가된 skill/script에 personal domain 참조가 없는지
- README 한글/영문 모두 업데이트되었는지

---

## Public Template Boundary

| 레포에 포함 (아키텍처 + 템플릿) | gitignored/제외 (개인 데이터) |
|--------------------------------|------------------------------|
| P0-P6 레이어 구조 + @action/ | `@memory/` — 세션, 성장 데이터 |
| `@identity/` (템플릿) | `@action/incidents/` — 사고 기록 |
| skill 정의 (100+) | `agent/` — 런타임 에이전트 |
| agent profiles (ARD identifier) | `cron/jobs.json` — 실제 작업 |
| scripts/ | `config.yaml`, `kanban.db`, `.env` |
| cron 예제 | `plans/`, `nix/`, `website/` |

---

## Links

- [[@identity/SELF_MODEL]]
- [[@identity/brain/rules]]
- [[@identity/persona/SOUL]]
- [[@identity/persona/writing-style-guide]]
