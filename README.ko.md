# opencode-drewgent

**AI 에이전트를 위한 템플릿 — 포크해서 나만의 에이전트를 만드세요**

opencode-drewgent는 `opencode` 위에서 동작하는 개인 AI 에이전트 시스템의 **템플릿 저장소**입니다. 단순한 설정 모음이 아니라, 진화하는 지식베이스, 멀티 에이전트 오케스트레이션, 자동화된 크론 작업, 체계적인 회고 파이프라인을 포함한 **운영 가능한 에이전트 시스템**을 바로 시작할 수 있습니다.

---

## 빠른 시작

```bash
# 1. 포크 후 클론
git clone git@github.com:YOUR_USER/opencode-YOURAGENT.git
cd opencode-YOURAGENT

# 2. 업스트림 등록 (향후 업데이트 수신)
git remote add upstream git@github.com:YOUR_GITHUB_USER/YOUR_REPO_NAME.git

# 3. 이름 변경 (drewgent → youragent)
bash scripts/rename-drewgent.sh "youragent"

# 4. 실행
opencode --config opencode.jsonc
```

자세한 내용은 아래 **[포크 & 커스터마이징 가이드](#포크--커스터마이징-가이드)** 참고.

---

## 한 줄 요약

> **opencode + agent profiles + LLM Wiki + kanban + cron = 당신만의 AI 에이전트 운영체제**

---

## 아키텍처 (v0.8)

```
opencode CLI
    │
    ├── AGENTS.md  (시스템 문서 — 정체성, 규칙, 워크플로우)
    ├── opencode.jsonc  (MCP 서버, 모델, 스킬 경로)
    ├── agents/  (6개 통합 subagent 프로필)
    ├── skills/  (100+ 스킬 — 온디맨드 로딩)
    ├── @identity/  (셀프 모델, persona, 금지 규칙)
    ├── @action/  (크론 작업, 인시던트, 계획)
    └── cron/jobs.json  (20개 자동화 작업)
```

### 레이어 구조 (7-layer → 3-layer)

| 레이어 | 역할 | 디렉토리 |
|--------|------|----------|
| **정체성** | 셀프 모델, 규칙, persona, voice | `@identity/` |
| **지식** | 메모리, 세션, 학습 (런타임 데이터) | `@memory/` (git 제외) |
| **액션** | 스킬, 크론, 계획, 인시던트 | `@action/` |

### 디렉토리 구조

```
opencode-drewgent/
├── opencode.jsonc           # 메인 설정 (모델, MCP, 스킬)
├── AGENTS.md                # 시스템 문서 (에이전트 가이드)
├── agents/                  # 6개 통합 subagent 프로필
│   ├── explorer             # 읽기 전용 분석 + 데이터 분석
│   ├── implementer          # 구현 + 테스트 (kimi-k2.7-code)
│   ├── reviewer             # 코드 리뷰 + 콘텐츠 검수
│   ├── reviewer-critical    # 중요 변경 심층 리뷰 + 보안
│   ├── planner              # 계획 + 오케스트레이션 + SRE
│   └── archiver             # 문서화 + 콘텐츠 관리
├── @identity/               # 에이전트 정체성
│   ├── SELF_MODEL.md        # 아키텍처 인식
│   ├── SOUL.md              # 핵심 persona
│   ├── brain/rules.md       # P0-brainstem 금지 규칙
│   └── persona/             # voice, writing style
├── @action/                 # 액션 레이어
│   ├── skills/              # 확장 스킬
│   ├── plans/               # 실행 계획
│   └── incidents/           # 장애 보고서
├── cron/
│   ├── jobs.json            # 크론 작업 정의
│   └── scheduler.py         # 스케줄러 엔진
├── scripts/                 # 유틸리티 스크립트
└── skills/                  # 100+ 온디맨드 스킬
```

### subagent 프로필 (6개 통합)

| 프로필 | 모델 | 역할 | 통합됨 |
|--------|------|------|--------|
| explorer | deepseek-v4-flash | 읽기 전용 분석, 데이터 분석 | analyst |
| implementer | kimi-k2.7-code | 구현, 테스트 | tester |
| reviewer | deepseek-v4-pro | 코드 리뷰, 콘텐츠 검수 | editor |
| reviewer-critical | qwen3.7-plus | 중요 리뷰, 보안 감사 | security-reviewer |
| planner | qwen3.7-max | 계획, 오케스트레이션, SRE | orchestrator, sre |
| archiver | deepseek-v4-flash | 문서화, 콘텐츠 관리 | content-manager |

---

## 주요 기능

### 1. 멀티 에이전트 파이프라인

kanban 기반 3단계 파이프라인 (explore → implement → review). archiver는 완료 후 자동 실행.

```
kanban_create(title="Add login", pipeline=["explorer","implementer","reviewer"])
    → explorer 가 분석
    → implementer 가 구현
    → reviewer 가 리뷰
    → archiver 가 자동 문서화 (post-hook)
```

### 2. LLM Wiki (Karpathy 컴파일 패턴)

RAG와 달리, 지식을 **미리 컴파일**해서 계속 축적:

```
@memory/ (원시 데이터) → wiki-compile cron → P5-ego/wiki/compiled/ (컴파일드 지식)
```

조회 우선순위:
1. 컴파일드 지식 (최우선)
2. gbrain 벡터 검색
3. 원시 데이터 (최후의 수단)

### 3. 크론 작업 자동화

launchd 데몬이 60초마다 `cron/jobs.json`을 읽어 작업 실행:

| 작업 | 주기 | 설명 |
|------|------|------|
| Office Autopilot | 5분 | kanban 태스크 자동 처리 |
| Trend Harvester | 6시간 | AI 트렌드 수집/평가 |
| SEO Article Harvester | 6시간 | SEO 기사 수집/분석 |
| Wiki Compile | 주간 | 지식 컴파일 |
| Daily Retro | 매일 20:00 | 작업 회고 |

### 4. MCP 서버 통합

| 서버 | 용도 | 기본 활성화 |
|------|------|------------|
| gbrain | 지식 그래프 (벡터 검색) | ✅ |
| lazyweb | UI 디자인 참고 | ❌ (온디맨드) |
| specification-website | 웹 스펙 체크리스트 | ❌ (온디맨드) |

---

## 포크 & 커스터마이징 가이드

이 저장소는 **템플릿**입니다. 포크해서 나만의 에이전트로 커스터마이징하세요.

### 사전 준비

- **[opencode](https://opencode.ai)** CLI 설치: `brew install anomalyco/tap/opencode` 또는 [GitHub Releases](https://github.com/anomalyco/opencode/releases)
- **Git** (SSH 키 등록)
- **Python 3.11+** (스크립트 실행용)
- **(선택) [gbrain](https://github.com/garrytan/gbrain)** — 지속적 지식 그래프 (MCP 서버)

### 1단계: 포크

```bash
# GitHub에서 포크: https://github.com/YOUR_GITHUB_USER/YOUR_REPO_NAME → Fork
# 그 다음 클론:
git clone git@github.com:YOUR_USER/opencode-YOURAGENT.git
cd opencode-YOURAGENT

# 업스트림 등록 (향후 업데이트 받기):
git remote add upstream git@github.com:YOUR_GITHUB_USER/YOUR_REPO_NAME.git
git fetch upstream
```

### 2단계: 이름 변경

두 가지 방법이 있습니다.

#### 방법 A: 자동 스크립트 (권장)

```bash
bash scripts/rename-drewgent.sh "youragent"
```

이 스크립트는 2000개 이상의 파일에서 모든 `drewgent` 참조를 교체합니다:

| 항목 | 변경 예시 |
|------|----------|
| 디렉토리명 | `~/.drewgent/` → `~/.youragent/` |
| 설정 경로 | `~/.drewgent/skills` → `~/.youragent/skills` |
| 환경변수 | `DREW_HOME` → `YOURAGENT_HOME` |
| 프로젝트명 | `Drewgent` → `Youragent` (대문자 유지) |
| 코드 참조 | 모든 inline 경로의 `drewgent` → `youragent` |
| 스크립트 헤더 | `Drewgent agent system` → `Youragent agent system` |
| `opencode.jsonc` | 스킬 경로, MCP 명령어 업데이트 |
| `AGENTS.md` | 모든 참조 다시 쓰기 |

실행 후 검증:
```bash
grep -r "drewgent" . --include="*.md" --include="*.py" --include="*.json" --include="*.jsonc" 2>/dev/null | head -5
# 아무것도 나오지 않아야 정상 (모두 교체됨)
```

**macOS 사용자 참고:** 내장 `sed`가 BSD 문법을 사용합니다. GNU sed가 필요하면:
```bash
brew install gnu-sed
```

#### 방법 B: 수동 설정

스크립트가 맞지 않는 경우, 다음 파일들을 직접 수정하세요:

- **`opencode.jsonc`** — `model`, skill `paths`, MCP server `command` 변경
- **`AGENTS.md`** — 프로젝트명, 링크, 정체성 참조 업데이트
- **`cron/jobs.json`** — `deliver` 필드의 Discord 채널 ID 설정
- **`@identity/`** — `SELF_MODEL.md`, `SOUL.md`, `brain/rules.md`를 당신의 에이전트 persona에 맞게 재작성
- **`scripts/`** — 쉘 스크립트의 하드코딩된 경로 업데이트

### 3단계: 핵심 파일 설정

#### `opencode.jsonc`

| 필드 | 설정값 |
|-------|--------|
| `model` | 기본 모델, 예: `opencode-go/deepseek-v4-flash` |
| `small_model` | 간단한 작업용 fallback 모델 |
| `skills.paths` | opencode가 스킬을 찾는 디렉토리 목록 |
| `mcp.gbrain` | gbrain MCP 서버 명령어 (사용 안 하면 `enabled: false`) |
| `mcp.lazyweb` | UI 디자인 MCP — 사용 안 하면 `enabled: false` |
| `mcp.specification-website` | 웹 스펙 MCP — 사용 안 하면 `enabled: false` |

#### `cron/jobs.json`

파일을 열고 모든 `discord:YOUR_*_CHANNEL_ID`를 실제 Discord 채널 ID로 교체하세요. `"deliver": "local"`인 작업은 Discord 없이 로컬에서만 실행됩니다.

주요 작업:
- `kanban-dispatcher` — 1분마다 kanban 태스크 확인 (자동 활성화)
- `trend-collect` — GitHub 트렌딩 수집 (Discord 채널 필요)
- `seo-article-harvester` — RSS 피드 모니터링 (Discord 채널 필요)
- `wiki-compile` / `wiki-lint` — 주간 위키 컴파일
- `daily retro` — 매일 작업 요약 (Discord 채널 필요)

#### `AGENTS.md`

이 파일이 당신 에이전트의 **헌법**입니다. 당신의 persona에 맞게 재작성:
- 말투: 간결? 상세? 캐주얼?
- 규칙: P0-brainstem 금지 사항 (절대 하면 안 되는 것)
- 정체성: 에이전트가 자신에 대해 아는 것
- 스킬: 기본 로딩할 스킬
- kanban 파이프라인: 작업 흐름 정의

#### `@identity/` (에이전트 정체성)

| 파일 | 목적 |
|------|------|
| `SELF_MODEL.md` | 에이전트가 자신에 대해 아는 것 (아키텍처, 능력) |
| `SOUL.md` | 핵심 성격, 말투, voice |
| `brain/rules.md` | P0-brainstem 절대 금지 규칙 |
| `persona/writing-style-guide.md` | 글쓰기 컨벤션 |

### 4단계: 실행

```bash
# 설정 파일로 opencode 실행:
opencode --config opencode.jsonc
```

당신의 에이전트는 다음을 로드합니다:
1. `AGENTS.md`를 시스템 명령어로
2. 설정된 경로의 모든 스킬
3. MCP 서버 (gbrain, 선택적 서버)
4. `cron/jobs.json`의 크론 작업 (cron 활성화 시)

### 업데이트 유지

```bash
git pull upstream main
```

이 명령으로 템플릿의 최신 v0.8+ 업데이트를 받습니다. 충돌이 발생하면:

```bash
# 업스트림 변경 수용 (당신의 커스터마이징 포기):
git checkout --theirs opencode.jsonc
# 또는 내 버전 유지:
git checkout --ours opencode.jsonc
# 그 다음 머지 커밋:
git commit
```

**중요:** `rename-drewgent.sh`, `README.md`는 업스트림이 덮어쓰도록 설계되었습니다. 당신의 개인 설정은 `opencode.jsonc`, `cron/jobs.json`, `AGENTS.md`, `@identity/`에 보관하세요.

### 문제 해결

| 문제 | 해결책 |
|------|--------|
| `opencode` 명령어 없음 | opencode 설치: `brew install anomalyco/tap/opencode` 또는 [releases](https://github.com/anomalyco/opencode/releases) |
| `gbrain` 명령어 없음 | [garrytan/gbrain](https://github.com/garrytan/gbrain) 설치 또는 `opencode.jsonc`에서 `"enabled": false` |
| macOS `sed` 오류 | GNU sed 설치: `brew install gnu-sed` |
| 크론 작업 실행 안 됨 | `cron/jobs.json`의 `"enabled": true` 확인. `drewgent_cron.py` 스케줄러가 실행 중이어야 함 |
| 업스트림 풀 충돌 | `git checkout --ours <file>`로 내 버전 유지, `--theirs`로 업스트림 수용 |

---

## 문제 해결

### cron 데몬이 동작하지 않음

```bash
launchctl list | grep ai.drewgent.cron
# PID가 없으면:
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.drewgent.cron.plist
```

### kanban 태스크가 처리되지 않음

```bash
cd ~/.drewgent && bash scripts/office_autopilot.sh
cat logs/office-autopilot.log
```

---

## 라이선스

MIT — [YOUR_PROJECT_NAME](https://your-domain.example)
