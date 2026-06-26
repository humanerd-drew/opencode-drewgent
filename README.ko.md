# opencode-drewgent

**AI 에이전트를 위한 오픈소스 개인 비서 프레임워크**

opencode-drewgent는 `opencode` 위에서 동작하는 개인 AI 에이전트 시스템의 **아키텍처 레퍼런스**입니다. subagent 오케스트레이션, kanban 기반 파이프라인, 크론 자동화, 지식 그래프를 포함한 **운영 가능한 에이전트 시스템**입니다.

---

## 철학

### 왜 "Drewgent"?

**Drew** + A**gent**. 당신의 이름, 당신의 규칙, 당신의 워크플로우.

대부분의 에이전트 시스템은 범용적입니다. Drewgent는 반대 전제에서 시작합니다: **에이전트는 그것을 만드는 사람만큼이나 고유해야 한다.**

### 왜 7-레이어 브레인?

플랫한 아키텍처로는 해결할 수 없는 문제가 있습니다: **어떻게 에이전트가 기억하고, 스스로 통제하며, 성장하게 할 것인가?**

```
P0-brainstem    → 생존. 절대 규칙, 재정의 불가
P1-limbic       → 가치관. 어조, 페르소나, 스타일
P2-hippocampus  → 기억. 세션 지속성, 지식베이스
P3-sensors      → 입력. 툴 라우팅, 게이트웨이 통합
P4-cortex       → 성장. 패턴 인식, 학습, taste
P5-ego          → 정체성. 셀프모델, 캘리브레이션
P6-prefrontal   → 전략. 계획, 제안, 사후 분석
```

**P0는 항상 우선:** `.neuron` 파일로 작성된 뇌간 규칙은 런타임에 강제되며, 어떤 상위 레이어도 우회할 수 없습니다.

### 왜 Obsidian을 지식 그래프로?

에이전트가 필요한 지속적인 기억:
1. **재시작에도 유지** — 매 세션 처음부터 시작하지 않음
2. **인간과 에이전트 모두 질의 가능** — Obsidian에서 동일 파일 열기
3. **구조를 가짐** — 평범한 텍스트 더미가 아닌 연결된 그래프
4. **버전 관리 가능** — git이 모든 결정과 변경 추적

P-레이어 디렉토리 자체가 Obsidian 볼트입니다. gbrain을 통한 하이브리드 검색으로 에이전트가 질의하고, 인간은 Obsidian에서 그래프 뷰로 탐색합니다.

### Filesystem = Truth

대부분의 에이전트 시스템은 상태를 휘발성 컨텍스트나 불투명한 DB에 저장합니다. Drewgent의 원칙: **파일시스템이 표준 소스다.**

- kanban 보드? SQLite 파일
- 세션 기록? FTS5 풀텍스트 검색
- 에이전트 프로필? `agents/*.md`
- 스킬? `skills/*/SKILL.md`
- 아키텍처 결정? `@action/proposals/`
- 거버넌스 규칙? `P0-brainstem/`의 `.neuron` 파일

중요한 것은 모두 디스크에, 디스크에 있는 것은 git에 추적됩니다.

### Governance as Code

규칙은 권고사항이 아닌 **강제 제약**입니다. `.neuron` 파일로 작성되어 런타임에 확인됩니다:

```
禁blind_write         → 읽지 않고 파일 쓰기 차단
禁task_qa_gate        → 검증 없이 완료 선언 차단
禁secrets_in_code     → 코드 내 API 키 탐지 → 차단
禁ponytail_violation  → 과도한 엔지니어링 플래그
```

### Taste Over Volume

Drewgent는 출력 양보다 **의사결정 품질**을 우선시합니다. 모든 kanban task에는 leverage score가 포함됩니다: "이 작업이 잘 해결되면, 얼마나 많은 다른 문제가 사라지는가?"

| Score | 의미 | 예시 |
|-------|------|------|
| 5 | 근본 원인 해결, 전체 클래스 제거 | 아키텍처 변경으로 모듈 전체 제거 |
| 4 | 여러 하위 문제 동시 해결 | 공통 유틸로 N개 중복 제거 |
| 3 | 명확한 개선 + 1-2개 부수 효과 | 설정 정리로 수동 단계 제거 |
| 2 | 국소적 개선, 확산 없음 | 버그 수정 |
| 1 | 표면적 변경, 최소 영향 | 오타, 문서 업데이트 |

### Provenance Convention

모든 결정은 **왜** 만들어졌는지를 기록합니다:

- 스킬 프론트매터: `trigger`, `provenance` 필드
- 제안서: `tier`, `leverage_score`, 세션 컨텍스트
- Kanban task: origin, session, decision rationale

---

## 퀵 스타트

```bash
# 1. opencode 설치
curl -fsSL https://opencode.ai/install | sh

# 2. 이 레포를 Drewgent 디렉토리로 클론
git clone git@github.com:humanerd-drew/opencode-drewgent.git ~/.drewgent

# 3. opencode 실행
cd ~/.drewgent
opencode
```

### 요구사항

- **macOS** 또는 **Linux**
- **opencode** CLI (v1.x+)
- **Python** 3.11+
- **모델 구독** (opencode-go 또는 bring-your-own)

---

## 포크 가이드

이 레포는 **fork해서 커스터마이징**하도록 설계되었습니다.

### 1. GitHub에서 Fork

[humanerd-drew/opencode-drewgent](https://github.com/humanerd-drew/opencode-drewgent)를 fork하세요.

### 2. 포크 클론

```bash
git clone git@github.com:YOUR_USERNAME/opencode-drewgent.git ~/.drewgent
```

### 3. 이름 변경 (권장)

모든 `drewgent` 참조를 당신의 에이전트 이름으로 변경:

```bash
# opencode 내에서 rename 스킬 실행
skill("rename-drewgent")

# 또는 init 스크립트 직접 실행
bash scripts/init-template.sh --name yourname
```

### 4. @identity/ 커스터마이징

`@identity/` 디렉토리의 파일을 수정하여 에이전트 성격 정의:

| 파일 | 내용 |
|------|------|
| `@identity/SELF_MODEL.md` | 에이전트 이름, 목적, 핵심 지시사항 |
| `@identity/persona/SOUL.md` | 어조, 스타일, 가치관 |
| `@identity/persona/writing-style-guide.md` | 글쓰기 규칙 |
| `@identity/brain/rules.md` | P0 거버넌스 규칙 |

### 템플릿 vs 개인 파일

| 레포에 포함 (템플릿) | gitignore됨 (개인 데이터) |
|----------------------|--------------------------|
| P0-P6 레이어 구조 | `@memory/` — 세션 로그, 성장 데이터 |
| 스킬 정의 | `@action/incidents/` — 개인 사고 기록 |
| 에이전트 프로필 | `P5-ego/config/` — API 키, 시크릿 |
| 스크립트 & cron 예제 | `config.yaml`, `kanban.db` |
| `@identity/` (템플릿) | `agent-dashboard-state.json` |

---

## 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                      사용자 입력                          │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│  오케스트레이션                                          │
│  task() / gjc_delegate_execute() / gjc_delegate_team()  │
│  opencode 내장 subagent + GJC Coordinator MCP           │
├────────────────────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │explorer  │ │implement │ │reviewer  │ │planner   │  │
│  │(리서치)   │ │(구현)    │ │(리뷰)    │ │(계획)    │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
└────────────────────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│  지식 계층 (LLM Wiki + gbrain)                           │
│                                                        │
│  P5-ego/wiki/compiled/  ← 컴파일된 지식 (최우선 조회)    │
│  gbrain MCP             ← 벡터 + 키워드 하이브리드 검색  │
│  codebase-memory-mcp    ← 코드베이스 지식 그래프         │
│  @memory/               ← 원시 데이터 (최후의 수단)       │
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

### 에이전트 프로필

| 티어 | 프로필 | 모델 | 역할 |
|------|--------|------|------|
| **Flash** | explorer | deepseek-v4-flash | 읽기 전용 코드 분석 |
| | implementer | deepseek-v4-flash | 코드 구현 |
| | archiver | deepseek-v4-flash | 문서화 |
| | designer | deepseek-v4-flash | UI/UX 디자인 |
| | analyst | deepseek-v4-flash | 데이터 분석 |
| **Pro** | reviewer | deepseek-v4-pro | 코드 리뷰 |
| | editor | deepseek-v4-pro | 콘텐츠 QA |
| | content-manager | deepseek-v4-pro | CMO 에이전트 |
| | orchestrator | deepseek-v4-pro | 워크 오케스트레이션 |
| | sre | deepseek-v4-pro | 인프라 관리 |
| **Max** | planner | qwen3.7-max | 태스크 분해 |
| | reviewer-critical | qwen3.7-max | 아키텍처 리뷰 |
| | security-reviewer | qwen3.7-max | 보안 감사 |

### 서브에이전트 위임 (2계층)

| 방식 | 명령 | 모델 | 언제? |
|------|------|------|-------|
| **같은 세션** (빠름) | `task(subagent_type="reviewer", ...)` | 부모 모델 상속 | 간단한 작업, 프로필 모델이 부모와 같을 때 |
| **다른 모델** (격리) | `gjc_delegate_execute(worktree="...")` | 프로필 모델 적용 | 격리/병렬 실행 필요 시 |

---

## 주요 기능

### 1. 서브에이전트 오케스트레이션

opencode 내장 `task()` + GJC Coordinator MCP 조합으로 작동:

```python
# 같은 모델 (가볍고 빠름)
task(
    subagent_type="explorer",
    description="인증 코드 분석",
    prompt="src/auth/*.ts의 기존 구현 분석...",
)

# 격리 실행 (워크트리 + tmux)
gjc_delegate_execute(
    goal="인증 모듈 리팩토링",
    worktree="refactor-auth",
    acceptance=["모든 테스트 통과", "API 호환성 유지"],
)
```

### 2. Kanban 파이프라인

크래시에도 살아남는 멀티스테이지 워크플로우:

```python
kanban_create(
    title="로그인 검증 추가",
    pipeline=["explorer", "implementer", "reviewer"],
    body="이메일+비밀번호 로그인, JWT 토큰, 리프레시 토큰 구현",
)
```

완료 시 archiver가 자동 실행 (post-hook).

### 3. LLM Wiki (Karpathy 컴파일 패턴)

RAG와 달리, 지식을 미리 컴파일해서 축적:

```
@memory/ (원본) → wiki-compile cron → P5-ego/wiki/compiled/ (지식)
```

조회 우선순위:
1. `P5-ego/wiki/compiled/` — 컴파일드 지식 (최우선)
2. `gbrain query` — 벡터 검색
3. `codebase-memory-mcp` — 코드베이스 지식 그래프
4. `@memory/` — 원시 데이터

### 4. 크론 작업 자동화

launchd 기반 60초 틱, `cron/jobs.json`에서 작업 정의:

| 작업 | 주기 | 방식 |
|------|------|------|
| Office Autopilot | 5분 | kanban 태스크 자동 처리 |
| 대시보드 푸시 | 5분 | Cloudflare 대시보드 업데이트 |
| Housekeeper | 60분 | 브레인 펄스 체크 |
| Content Manager | 3시간 | 자동 콘텐츠 생성 |
| Trend 수집 | 6시간 | GitHub 트렌드 수집 (8병렬) |
| Trend 평가 | 매일 10:00 | kanban 태스크 생성 |
| Daily Retro | 매일 20:00 | 일일 회고 |
| Wiki Compile | 주간 일 03:00 | 지식 컴파일 |
| Taste Review | 화/금 10:00 | 고품질 툴 심층 분석 |

### 5. Discord 통합

**Discord Bot** — `scripts/discord_bot.py`가 opencode `--attach` 모드로 연결:
- 대화별 스레드 생성
- 파일 첨부 지원 (이미지, 문서, 코드)
- 2000자 초과 메시지 분할 전송
- launchd 서비스로 자동 복구

**Discord MCP** — `discord-mcp` stdio 서버로 직접 툴 접근:
- 메시지 전송/수정/삭제, 리액션, 파일 업로드
- 채널 히스토리, 검색, 첨부파일 다운로드

---

## 설정

### opencode.jsonc

```jsonc
{
  "model": "opencode-go/deepseek-v4-flash",
  "small_model": "opencode-go/deepseek-v4-pro",
  "instructions": ["AGENTS.md"],
  "skills": {
    "paths": [
      "~/.drewgent/skills",
      "~/.drewgent/@action/skills",
      "~/.config/opencode/skills"
    ]
  },
  "mcp": {
    "discord": {
      "type": "local",
      "command": ["discord-mcp"],
      "env": { "DISCORD_TOKEN": "{env:DISCORD_BOT_TOKEN}" }
    },
    "wordpress": {
      "type": "local",
      "command": ["node", "scripts/wordpress-mcp-server.js"]
    },
    "gajae-code": {
      "type": "local",
      "command": ["gjc", "mcp-serve", "coordinator"],
      "env": { "OPENCODE_API_KEY": "{env:OPENCODE_API_KEY}" }
    },
    "gbrain": {
      "type": "local",
      "command": ["gbrain", "serve"],
      "env": { "OPENAI_API_KEY": "ollama-local" },
      "timeout": 120000
    }
  }
}
```

### MCP 서버

| 서버 | 타입 | 용도 |
|------|------|------|
| codebase-memory-mcp | stdio | 코드베이스 지식 그래프 |
| discord | stdio | Discord 메시지/채널 관리 |
| wordpress | stdio | WordPress 포스트 관리 |
| gajae-code | stdio | GJC Coordinator (워크트리 격리, tmux 병렬) |
| portone | stdio | 포트원 결제 게이트웨이 |
| gbrain | stdio | 개인 볼트 하이브리드 검색 |

---

## 디렉토리 구조

```
~/.drewgent/
├── opencode.jsonc              opencode 설정
├── AGENTS.md                   시스템 문서 (에이전트 가이드)
├── agents/                     16개 subagent 프로필
├── skills/                     60+ 카테고리, 100+ 스킬
├── @action/                    액션 레이어 (스킬, 제안, 계획, 인시던트)
├── @memory/                    메모리/성장 데이터 (git 제외)
├── scripts/                    27개 자동화 스크립트
├── cron/                       jobs.json + scheduler.py
├── P0-brainstem/               거버넌스 규칙 (.neuron)
├── P1-limbic/                  정체성/페르소나
├── P2-hippocampus/             기억 레이어 (stub)
├── P3-sensors/                 게이트웨이/샌드박스
├── P4-cortex/                  성장/콘텐츠/지식
├── P5-ego/                     셀프모델 + wiki
└── P6-prefrontal/              전략 (→ @action/로 이전)
```

---

## 모델 라우팅

| 티어 | 모델 | 용도 |
|------|------|------|
| **Flash** | deepseek-v4-flash | 분석, 간단 구현, 문서 |
| **Pro** | deepseek-v4-pro, glm-5.2 | 일반 작업, 코드 리뷰 |
| **Code** | kimi-k2.7-code | 코드 생성 특화 |
| **Max** | qwen3.7-max, qwen3.7-plus | 복잡 추론, 계획, 심층 리뷰 |

---

## 트러블슈팅

| 문제 | 해결 |
|------|------|
| `opencode`를 찾을 수 없음 | 설치: `curl -fsSL https://opencode.ai/install \| sh` 또는 `brew install anomalyco/tap/opencode` |
| `gbrain`을 찾을 수 없음 | [github.com/garrytan/gbrain](https://github.com/garrytan/gbrain)에서 설치하거나 `opencode.jsonc`에서 `"enabled": false` 설정 |
| rename 스크립트가 macOS `sed`에서 실패 | macOS `sed`는 BSD 문법 사용. `brew install gnu-sed`로 GNU sed 설치 |
| Cron 작업이 실행되지 않음 | `cron/` 디렉토리 존재 확인, `jobs.json`에 `"enabled": true` 설정, `drewgent_cron.py` 스케줄러 실행 필요 |
| `@identity/` 플레이스홀더가 그대로 보임 | `@identity/SELF_MODEL.md`, `@identity/persona/SOUL.md`, `writing-style-guide.md`를 에이전트에 맞게 수정 |

## 크레딧

| 프로젝트 | 저자 | 용도 |
|---------|------|------|
| [opencode](https://opencode.ai) | [Anomaly](https://github.com/anomalyco) | AI 코딩 에이전트 플랫폼 |
| [gbrain](https://github.com/garrytan/gbrain) | Garry Tan | 지식 그래프 & 하이브리드 검색 |
| [codebase-memory-mcp](https://github.com/anomalyco/opencode) | Anomaly | 코드베이스 지식 그래프 |
| [Gajae-Code](https://gajae-code.com) | — | GJC Coordinator MCP |
| [discord-mcp](https://github.com/anomalyco/discord-mcp) | Anomaly | Discord MCP 서버 |
| [PortOne](https://developers.portone.io) | PortOne | 한국 결제 게이트웨이 SDK |
| [Cloudflare Agents SDK](https://developers.cloudflare.com/agents) | Cloudflare | Workers 기반 상태유지 에이전트 |
| [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) | Andrej Karpathy | 컴파일 패턴 지식베이스 개념 |
| [Ponytail](https://github.com/DietrichGebert/ponytail) | Dietrich Gebert | 코드 최소화 체크리스트 |
| [NeuronFS](https://github.com/rhino-acoustic/NeuronFS) | [rhino-acoustic](https://github.com/rhino-acoustic) | 뇌 기반 거버넌스 시스템 |
| [ARD Spec](https://agenticresourcediscovery.org) | Google/MS | Agentic Resource Discovery |

---

## 라이선스

MIT
