# opencode-drewgent

[English](README.md)

[opencode](https://opencode.ai) 위에서 동작하는 개인 AI 에이전트 템플릿입니다.

이 레포는 자신만의 AI 에이전트를 만들기 위한 **스타터 킷**입니다. subagent 오케스트레이션, 스킬 시스템, cron 자동화, 지식 관리 구조 등 솔로 개발자가 매일 처음부터 구축해야 하는 패턴들을 템플릿화했습니다. fork해서 이름을 바꾸고 커스터마이징하세요.

---

## 퀵 스타트

```bash
# 1. opencode 설치
curl -fsSL https://opencode.ai/install | sh

# 2. GitHub에서 이 레포를 fork한 뒤 클론
git clone git@github.com:YOUR_USERNAME/opencode-drewgent.git ~/.youragent
cd ~/.youragent

# 3. 의존성 설치 및 .env 생성
bash scripts/setup.sh

# 4. "drewgent"를 당신의 에이전트 이름으로 변경
#    (opencode 내에서 실행:)
skill("rename-drewgent")

# 5. opencode 실행
opencode
```

---

## 아키텍처

### 에이전트 시스템

opencode의 내장 `task(subagent_type="...")`로 멀티스텝 작업을 위임하고, 필요 시 GJC Coordinator MCP로 격리된 worktree에서 병렬 실행합니다. 주요 에이전트 프로필은 `.opencode/agents/*.md`에 정의:

| 프로필 | 모델 | 역할 |
|--------|------|------|
| implementer | flash | 코드 생성, 파일 수정 |
| reviewer | pro | 코드 리뷰, 품질 게이트 |
| explorer | flash | 코드베이스 탐색, 리서치 |
| planner | pro/max | 작업 분해, 계획 |
| sre | flash | 인프라, 모니터링 |
| architect | pro | 아키텍처 결정 |

### 볼트 구조 (P0-P6)

Obsidian 호환 폴더 구조로 에이전트의 정체성, 지식, 메모리를 계층화:

| 레이어 | 경로 | 내용 |
|-------|------|------|
| **P0-brainstem** | `@identity/brain/` | 규칙, 제약, 禁 규칙 |
| **P1-limbic** | `@identity/persona/` | 성격, 어조, 글쓰기 스타일 |
| **P2-hippocampus** | `P2-hippocampus/` | 원본 아카이브 — 세션, 메모리, 지식 |
| **P3-sensors** | `@action/` | 툴 통합, 게이트웨이 설정 |
| **P4-cortex** | `skills/` | 스킬 정의, 성장 기록 |
| **P5-ego** | `@identity/SELF_MODEL.md` | 자기 인식, 컴파일된 위키 |
| **P6-prefrontal** | `P6-prefrontal/` | 인시던트, 회고, 계획 |

### MCP 서버

`opencode.jsonc`에 예시 MCP 서버 설정 포함:

| 서버 | 타입 | 용도 |
|------|------|------|
| `codebase-memory-mcp` | local stdio | 코드베이스 지식 그래프 |
| `gajae-code` | local stdio | GJC Coordinator 격리 위임 |
| `safari` | local stdio | 웹 브라우징 |
| `astryx` | remote HTTP | Meta Astryx 디자인 시스템 |
| `discord` | local stdio | Discord 연동 |

### 스킬 시스템

스킬은 `skill("name")`으로 로드하는 특화 명령어 파일입니다. 템플릿에는 100+ 스킬이 포함:

- `skills/software-development/` — 코딩 패턴, 리팩토링, 테스팅
- `skills/devops/` — 인프라, 배포, 모니터링
- `skills/mlops/` — ML 학습, 추론, 파인튜닝
- `skills/creative/` — 디자인, 아키텍처 다이어그램, 콘텐츠
- `skills/productivity/` — 외부 툴 연동
- `skills/seo/` — SEO 및 콘텐츠 최적화

### Cron 자동화

`scripts/drewgent_cron.py` 스케줄러가 `cron/jobs.json`을 읽어 주기적 작업을 실행합니다. 예시 job은 `cron/jobs.json` 참조.

### Kanban 작업 파이프라인

SQLite 기반 kanban 보드(`kanban.db`)로 작업을 추적합니다. 각 task는 subagent 파이프라인(explorer → implementer → reviewer)과 leverage score를 가질 수 있습니다.

---

## 커스터마이징 가이드

### 1. 에이전트 이름 변경

전체 repo에서 "drewgent"를 당신의 에이전트 이름으로 변경:

```bash
# 방법 A: opencode 내에서
skill("rename-drewgent")

# 방법 B: 수동 find/replace
find ~/.youragent -type f -name "*.md" -o -name "*.py" -o -name "*.sh" -o -name "*.json" | \
  xargs sed -i '' 's/drewgent/youragent/g'
```

### 2. 정체성 설정

다음 파일을 수정하여 에이전트의 성격을 정의:

- `@identity/SELF_MODEL.md` — 목적, 역할, 핵심 지시
- `@identity/persona/SOUL.md` — 어조, 목소리, 커뮤니케이션 스타일
- `@identity/persona/writing-style-guide.md` — 글쓰기 컨벤션
- `@identity/brain/rules.md` — 행동 규칙과 제약

### 3. MCP 서버 설정

`opencode.jsonc`를 수정하여 필요한 MCP 서버 추가:
- Discord 봇 (`DISCORD_BOT_TOKEN` 필요)
- Gajae-Code coordinator (`OPENCODE_API_KEY` 필요)
- WordPress MCP 서버 (콘텐츠 관리)
- Safari 웹 브라우징 (macOS 전용)

### 4. Cron 작업 설정

`cron/jobs.json`을 수정하여 자동화 작업 추가. 예시:

```json
{
  "id": "my-job",
  "name": "내 작업",
  "enabled": true,
  "schedule": { "kind": "cron", "expr": "0 6 * * *" },
  "deliver": { "kind": "script", "script": "scripts/my_script.py" },
  "workdir": "~/",
  "max_runtime": 600
}
```

### 5. 스킬 라이브러리 구축

필요 없는 스킬을 제거하고, 자신만의 스킬을 추가하세요. 각 스킬은 `skills/` 아래 디렉토리 + `SKILL.md` 파일로 구성됩니다.

```bash
ls skills/*/SKILL.md
```

---

## 주요 개념

### 위임 패턴

- **`task(subagent_type="reviewer", ...)`** — 같은 모델 서브태스크. 가볍고 빠름.
- **`gjc_delegate_execute(...)`** — 격리된 worktree + tmux. 무거운 격리, 병렬 실행.
- **`gjc_delegate_team(...)`** — 병렬 멀티 에이전트 오케스트레이션.

### 연혁 기록 (Provenance)

모든 artifact는 생성 동기를 기록:

```yaml
trigger: "무슨 문제/요청에서 시작되었는가"
provenance:
  session: "YYYY-MM-DD 주제"
  decision: "왜 이렇게 설계했는가, 어떤 대안이 있었는가"
```

### 계층적 자율성 (Tiered Autonomy)

| 계층 | 범위 | 권한 |
|------|------|------|
| 1 | 오타, 사소한 수정 | 자율. 완료 후 보고. |
| 2 | 기존 패턴 내 작업 | 자율. 연혁 포함. |
| 3 | 구조 변경 | 제안 → 승인 대기. |
| 4 | 아키텍처/방향 | 제안만. 사람이 결정. |

### 중요 정책

- **Filesystem = truth** — 상태와 설정은 디스크에 저장, 컨텍스트에 보관 금지
- **QA 게이트** — 검증 없이 완료 선언 금지
- **빅뱅 리팩토링 금지** — 한 번에 하나씩 변경, 중간마다 검증
- **Ponytail 원칙** — YAGNI, 표준 라이브러리 우선, 불필요한 의존성 금지
- **Answer-first** — CLI 출력은 결론 먼저, 과정은 그 다음

---

## 생성 콘텐츠 저작권 표시

공개 홍보용 콘텐츠(블로그, X 스레드, 데모)에만 추가:

```
Built with [opencode-drewgent](https://github.com/humanerd-drew/opencode-drewgent)
```

---

## 알려진 문제

### Python 3.14: json scope 버그
큰 함수 내에서 `except json.JSONDecodeError:`를 쓰면 `json.loads()`가 `UnboundLocalError`. 해결: `__import__('json').loads()` 또는 별도 wrapper 함수 사용.

### macOS bash 3.2
associative array 없음. `date -j -f` 필요. `set -u` 주의.

### Launchd plist 패턴
모든 서비스: `KeepAlive { SuccessfulExit: false, ThrottleInterval: 10 }`. `<true/>`나 `<false/>` 쓰지 말 것.

### 토큰/비용 데이터 = SQLite
opencode stderr 로그는 `tokens.input=0`으로 표시됨. 실제 데이터는 `~/.local/share/opencode/opencode.db`에 있음.

---

## 라이선스

MIT — fork 시 원하는 라이선스로 변경하세요.
