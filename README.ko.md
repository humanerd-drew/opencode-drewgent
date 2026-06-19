# opencode-drewgent

[🇺🇸 English](README.md)

**Drewgent**는 [opencode](https://opencode.ai) 위에서 동작하는 **자율 소프트웨어 엔지니어링 에이전트 시스템**입니다. 전문화된 서브에이전트들을 칸반 기반 파이프라인으로 오케스트레이션하고, 단계 간 맥락을 구조화된 형태로 자동 전달하며, 실패를 추적하고 백그라운드 자동화를 수행합니다.

독립형 에이전트 프레임워크가 아닙니다. — 에이전트 프로필, 스킬, 스크립트, 툴, 자동화로 구성된 **설정 및 확장 레이어**입니다.

---

## 철학

### 왜 "Drewgent"인가?

**Drew** + A**gent**. 당신의 이름, 당신의 규칙, 당신의 워크플로우.

대부분의 에이전트 시스템은 범용입니다 — 모두에게 맞추려다 누구에게도 안 맞습니다. Drewgent는 정반대의 전제에서 시작합니다: **에이전트는 그걸 만드는 사람만큼 고유해야 한다.** 이름은 그 정체성의 첫 번째 선언입니다. Fork하고, 이름을 바꾸고, 당신 것으로 만드세요. `rename-drewgent` 스킬이 2000개 이상의 파일을 직접 수정하지 않아도 되게 해줍니다.

### 왜 7-레이어 뇌 구조인가?

대부분의 에이전트 아키텍처는 평평합니다: 하나의 모델, 하나의 컨텍스트 윈도우, 하나의 프롬프트. Drewgent는 **인간 뇌의 계층 구조**를 모델링합니다 — 유행 따라서가 아니라, 실제 문제를 해결하기 위해서입니다: **기억하고, 스스로 통제하고, 시간이 지나면서 성장하는 에이전트**를 어떻게 만들 것인가?

```
P0-brainstem    → 생존. 절대 무시할 수 없는 규칙.
P1-limbic       → 가치관. 어조, 페르소나, 커뮤니케이션 스타일.
P2-hippocampus  → 기억. 세션 지속성, 지식 베이스.
P3-sensors      → 입력. 툴 라우팅, 스킬 디스패치, 게이트웨이.
P4-cortex       → 성장. 패턴 인식, 학습, 취향.
P5-ego          → 정체성. 셀프 모델, 캘리브레이션, 자기 인식.
P6-prefrontal   → 전략. 계획, 제안, 장애 분석.
```

계층은 **무엇이 무엇을 오버라이드하는가**에서 나옵니다:

- **상향식** (감각 → 행동): P3가 입력 감지 → P2가 맥락 로드 → P4가 패턴 인식 → P5와 P6가 결정
- **하향식** (정체성이 행동을 지배): P5가 "나는 꼼꼼한 에이전트다" → P1이 어조 결정 → P3가 신중한 툴 선택 → P0가 위험한 작업 차단
- **P0가 항상 이긴다**: `禁rm_rf_root` 같은 뇌간 규칙은 상위 레이어가 아무리 논리적으로 우회하려 해도 차단됩니다.

이건 문서가 아닙니다. **실행 시 강제되는 제약 조건**입니다. — `P0-brainstem/`의 `.neuron` 파일들은 런타임에 로드되어 실제로 행동을 게이트합니다.

### 왜 지식 그래프가 Obsidian인가?

에이전트에게는 지속적인 기억이 필요합니다:
1. **재시작에도 유지** — 매 세션이 "백지 상태"가 아니어야 함
2. **인간과 에이전트 모두가 질의 가능** — 같은 파일을 Obsidian에서 열 수 있어야 함
3. **구조가 있음** — 평범한 텍스트 더미가 아니라 연결된 그래프
4. **버전 관리 가능** — git이 모든 변경과 결정과 장애를 추적

데이터베이스는 1과 2를 할 수 있습니다. **위키링크가 있는 파일**만 네 가지를 모두 할 수 있습니다.

P-레이어 디렉토리들은 그 자체로 **Obsidian 볼트**입니다. 모든 파일에는 YAML frontmatter, 타입 태그, 그리고 다른 파일로의 `[[wikilink]]`가 있습니다:
- 에이전트는 `gbrain_query("리프레시 토큰 정책이 뭐야?")`로 지식 그래프에서 순위가 매겨진 답을 얻습니다
- 인간은 같은 디렉토리를 Obsidian에서 열어 정확히 같은 그래프를 백링크, 그래프 뷰, 로컬 그래프와 함께 볼 수 있습니다
- git이 누가, 언제, 왜 변경했는지 추적합니다 — 모든 아키텍처 결정의 전체 감사 추적

### 파일시스템이 진실이다 (Filesystem = Truth)

대부분의 에이전트 시스템은 상태를 일시적인 컨텍스트 윈도우나 불투명한 데이터베이스에 저장합니다. Drewgent의 원칙: **파일시스템이 표준 출처다.**

- 칸반 보드? `P2-hippocampus/kanban/state/drewgent_tasks.db` SQLite 파일
- 세션 기록? FTS5 전문 검색이 가능한 SQLite
- 에이전트 프로필? `agents/`의 `.md` 파일
- 스킬? `skills/`의 `.md` 파일
- 아키텍처 결정? `P6-prefrontal/proposals/`의 `.md` 파일
- 거버넌스 규칙? `P0-brainstem/`의 `.neuron` 파일

중요한 것은 디스크에 있습니다. 디스크에 있는 것은 git에 있거나(또는 의도적으로 gitignored). 불투명한 상태는 없습니다. "에이전트가 기억할 거야"라고 믿을 필요가 없습니다.

### 코드로서의 거버넌스 (Governance as Code)

Drewgent의 규칙은 조언 프롬프트가 아닙니다 — **`P0-brainstem/`에 `.neuron` 파일로 작성된 강제 제약 조건**입니다. 각 규칙은 시그널 프로세서가 런타임에 검사하는 독립적인 제약입니다:

```
禁blind_write         → 읽지 않은 파일을 쓸 수 없음
禁task_qa_gate        → 검증 없이 완료 선언 불가
禁secrets_in_code     → 코드에서 API 키 발견 → 차단
禁karpathy_coding     → 과도한 엔지니어링, 사변적 추상화 → 플래그
```

이것은 "모범 사례"가 아닙니다. **게이트입니다** — 시그널 프로세서가 `turn.end`에서 위반을 감지하고, 인식 리포터가 이를 표면화하며, 에이전트가 "이번에는 조심할게"라고 말해도 우회할 수 없습니다.

### 볼륨보다 취향 (Taste Over Volume)

Drewgent는 **출력 양보다 결정 품질**을 우선시합니다. 모든 칸반 태스크에는 레버리지 점수가 포함됩니다: "이 작업이 잘 해결되면, 다른 문제 몇 개가 자동으로 사라지는가?"

| 점수 | 의미 | 예시 |
|------|------|------|
| 5 | 근본 원인, 전체 클래스 제거 | 아키텍처 변경으로 전체 모듈 제거 |
| 4 | 여러 하위 문제를 한 번에 해결 | 공통 유틸리티로 N개 중복 제거 |
| 3 | 명확한 개선 + 1-2개의 부수 효과 | 설정 정리로 수동 단계 제거 |
| 2 | 국소적 개선, 파급 효과 없음 | 버그 수정 |
| 1 | 표면적 변경, 최소한의 영향 | 오타, 문서 업데이트 |

낮은 레버리지 작업(점수 1-2)은 거부되지 않습니다 — 하지만 높은 레버리지 작업 뒤로 우선순위가 밀립니다. 시스템은 **가장 레버리지가 높은 다음 작업**을 찾도록 설계되었고, 잡일을 생성하지 않습니다.

### 출처 기록 컨벤션 (Provenance Convention)

이 레포의 모든 아키텍처 결정은 **왜 내려졌는지**를 기록합니다:

- 스킬 frontmatter에는 `trigger`와 `provenance` 필드가 있습니다
- 제안서에는 `tier`, `leverage_score`, 세션 컨텍스트가 포함됩니다
- 칸반 태스크에는 기원, 세션, 결정 근거가 포함됩니다

원칙: **프롬프트가 출력보다 유용하다.** 6개월 후에 완료된 제안서를 읽을 때, 출처 기록이 *무엇을* 했는지뿐만 아니라 *왜* 했는지를 알려줍니다.

---

## 빠른 시작

```bash
# 1. opencode 설치
curl -fsSL https://opencode.ai/install | sh

# 2. 이 레포를 Drewgent 디렉토리로 클론
git clone git@github.com:humanerd-drew/opencode-drewgent.git ~/.drewgent

# 3. API 키 설정
cd ~/.drewgent
cp .env.example .env
# .env 파일에 LLM 제공자 API 키 입력

# 4. opencode 실행
opencode
```

### 요구 사항

- **macOS** 또는 **Linux**
- **opencode** CLI (v1.x+)
- **Python** 3.11+
- **LLM 제공자 API 키** (OpenRouter, MiniMax 등)

---

## 목차

- [아키텍처 개요](#아키텍처-개요)
  - [7-레이어 뇌 아키텍처](#7-레이어-뇌-아키텍처)
  - [멀티-에이전트 파이프라인](#멀티-에이전트-파이프라인)
  - [복잡도 계층](#복잡도-계층)
- [에이전트 프로필](#에이전트-프로필)
  - [Flash 계층](#flash-계층)
  - [Pro 계층](#pro-계층)
  - [Max 계층](#max-계층)
  - [핸드오프 컨트랙트](#핸드오프-컨트랙트)
- [파이프라인 단계](#파이프라인-단계)
- [서브에이전트 시스템](#서브에이전트-시스템)
  - [delegate_task](#delegate_task)
  - [칸반 파이프라인 자동 분해](#칸반-파이프라인-자동-분해)
  - [컨텍스트 핸드오프 프로토콜](#컨텍스트-핸드오프-프로토콜)
  - [ESCALATE 메커니즘](#escalate-메커니즘)
  - [포니테일 원칙](#포니테일-원칙)
- [설정](#설정)
  - [opencode.jsonc](#opencodejsonc)
  - [MCP 서버](#mcp-서버)
- [크론 및 자동화](#크론-및-자동화)
- [스킬](#스킬)
- [Discord 연동](#discord-연동)
- [저장소 구조](#저장소-구조)
  - [레포에 포함된 것](#레포에-포함된-것)
  - [레포에 포함되지 않은 것 (개인 데이터)](#레포에-포함되지-않은-것-개인-데이터)
- [Obsidian 볼트](#obsidian-볼트)
- [이름 짓기 컨벤션](#이름-짓기-컨벤션)
- [관련 프로젝트](#관련-프로젝트)
- [라이선스](#라이선스)

---

## 아키텍처 개요

### 7-레이어 뇌 아키텍처

Drewgent는 인간 뇌의 계층 구조를 모델링합니다:

```
P6-prefrontal  전략      장기 계획, 제안서, 장애 보고서
P5-ego         정체성    셀프 모델, 자기 인식, 캘리브레이션
P4-cortex      성장      학습, 패턴 인식, 취향 개발
P3-sensors     입력      툴 라우팅, 게이트웨이 연동, 스킬 디스패치
P2-hippocampus 기억      세션 지속성, 지식 베이스, 칸반 상태
P1-limbic      가치관    페르소나, 어조, 글쓰기 스타일, SOUL
P0-brainstem   생존      절대 규칙(禁), 코드로서의 거버넌스
```

**상향식 흐름:** P3 입력 감지 → P2 맥락 로드 → P4 패턴 인식 → P5 통합 → P6 결정

**하향식 흐름:** P5 행동 결정 → P1 어조 영향 → P3 툴 선택 → P0 위반 차단

**P0가 모든 것을 오버라이드합니다:** 뇌간 규칙(`.neuron` 파일)은 런타임에 강제되며 상위 레이어가 우회할 수 없습니다.

### 멀티-에이전트 파이프라인

Drewgent의 핵심 워크플로우는 칸반 기반 파이프라인으로, 각 단계를 전문화된 에이전트가 처리합니다:

```python
kanban_create(
    title="로그인 검증 추가",
    pipeline=["explorer", "implementer", "tester", "reviewer", "archiver"],
)
```

5개의 순차적 태스크가 의존성과 함께 자동 생성됩니다:

```
explorer ──→ implementer ──→ tester ──→ reviewer ──→ archiver
    │              │            │           │            │
    │  findings    │  changes   │  tests    │  review    │  docs
    └──────┬───────┴─────┬──────┴─────┬─────┴──────┬─────┘
           │             │            │            │
           ↓             ↓            ↓            ↓
     이전 단계의 컨텍스트가 자동으로 프롬프트에 주입:
     **Findings:** auth code in src/auth/*.ts
     **Risks:** no refresh token rotation
     **Next:** implement token refresh
```

**핵심 속성:**
- **자동 컨텍스트 전달**: 각 단계가 이전 단계의 `findings`, `risks`, `next`를 구조화된 JSON으로 수신
- **실패 추적**: 파싱 불가능한 핸드오프는 `handoff_failed` 이벤트를 기록하고 프롬프트에 시각적 표시
- **Fan-in 지원**: 여러 부모가 있는 태스크는 모든 부모의 컨텍스트를 병합
- **Worker-side 해결**: Worker가 런타임에 부모 결과를 읽음 — DB 마이그레이션 불필요

### 복잡도 계층

| 계층 | 파이프라인 | 사용 사례 |
|------|-----------|-----------|
| **1** (단순) | Implementer → Archiver | 오타 수정, 설정 변경 |
| **2** (보통) | Explorer → Implementer ↔ Tester → Archiver | 새 함수, 중간 규모 기능 |
| **3** (복잡) | Planner → Explorer → Implementer ↔ Tester → Reviewer → Security → Archiver | 아키텍처 변경, 보안 관련 |

---

## 에이전트 프로필

14개의 전문화된 서브에이전트 역할. 각 역할은 모델, 제공자, 툴셋, 시스템 명령어를 정의합니다. `delegate_task(agent_profile="<name>", goal="...")`로 호출합니다.

### Flash 계층

OpenCode Go 구독 (호출당 $0). 빠름, 일상 작업용.

| 프로필 | 모델 | 역할 | ESCALATE |
|--------|------|------|----------|
| **explorer** | deepseek-v4-flash | 읽기 전용 코드 분석 | ✅ |
| **implementer** | deepseek-v4-flash | 코드 구현 | ✅ |
| **tester** | deepseek-v4-flash | 테스트 작성 및 검증 | ✅ |
| **archiver** | deepseek-v4-flash | 문서화, 변경 로그 | ❌ |
| **designer** | deepseek-v4-flash | UI/UX 목업, SVG 에셋 | ✅ |
| **sre** | deepseek-v4-flash | 인프라, 장애 대응 | ✅ |
| **analyst** | deepseek-v4-flash | 데이터 분석, 칸반/git 질의 | ❌ |

### Pro 계층

더 강력한 추론, 품질이 중요한 단계용.

| 프로필 | 모델 | 역할 |
|--------|------|------|
| **reviewer** | deepseek-v4-pro | 코드 리뷰 (로직, 엣지 케이스, 스타일) |
| **editor** | deepseek-v4-pro | 콘텐츠 QA, 한국어 품질 |
| **content-manager** | deepseek-v4-pro | CMO 에이전트 — 작업 관찰, 멀티 포맷 콘텐츠 생성 |

### Max 계층

깊은 추론, 아키텍처, 계획, 보안용.

| 프로필 | 모델 | 역할 |
|--------|------|------|
| **planner** | qwen3.7-max | 태스크 분해, 파이프라인 설계 |
| **reviewer-critical** | qwen3.7-max | 아키텍처 수준 리뷰 |
| **security-reviewer** | qwen3.7-max | 보안 감사 (인증, 암호, 인젝션) |
| **orchestrator** | qwen3.7-max | 작업 분해 및 파이프라인 오케스트레이션 |

### 핸드오프 컨트랙트

모든 파이프라인 참여 프로필에는 구조화된 핸드오프 섹션이 포함됩니다. 파이프라인 태스크 완료 시, 에이전트는 `result`를 JSON으로 구조화합니다:

```python
kanban_complete(
    task_id="t_xxx",
    summary="사람이 읽는 완료 보고서",
    result=json.dumps({
        "findings": ["발견 또는 생성된 것"],
        "risks": ["다음 단계가 알아야 할 위험"],
        "next": ["권장 다음 작업"],
    }),
)
```

모든 필드는 선택 사항입니다. `result`가 유효한 JSON이 아니면, 시스템이 `handoff_failed` 이벤트를 기록하고, stdout에 경고를 출력하며, 프롬프트에 시각적 표시를 남깁니다.

---

## 파이프라인 단계

| 단계 | 역할 | 핸드오프 출력 |
|------|------|---------------|
| **Explorer** | 코드 분석, 패턴 발견 | `findings`: 파일 경로, 패턴. `risks`: 우려사항. `next`: 구현 추천 |
| **Implementer** | 코드 작성, 패치 생성 | `findings`: 변경 파일, 접근법. `risks`: 엣지 케이스. `next`: 테스트 집중 영역 |
| **Tester** | 테스트 작성 및 실행 | `findings`: 테스트 결과, 발견된 버그. `risks`: 불안정한 테스트. `next`: 리뷰어 주의점 |
| **Reviewer** | 코드 품질 검토 | `findings`: 심각도별 이슈. `risks`: 차단 이슈. `next`: APPROVE/CHANGES_REQUESTED |
| **Security** | 보안 감사 | `findings`: 취약점. `risks`: CRITICAL/HIGH. `next`: 필요 수정사항 |
| **Archiver** | 문서화 | `findings`: 생성된 문서. `risks`: 문서 격차. `next`: 향후 문서 필요사항 |
| **Planner** | 태스크 그래프 설계 | `findings`: 계획 구조. `risks`: 복잡도. `next`: 실행 순서 |
| **Designer** | 목업, SVG 생성 | `findings`: 디자인 결정. `risks`: 접근성. `next`: 개발 인계 |
| **Editor** | 콘텐츠 다듬기 | `findings`: 수정사항. `risks`: 남은 문제. `next`: ACCEPT/REJECT |
| **Content Manager** | 멀티 포맷 초안 생성 | `findings`: 생성된 콘텐츠. `risks`: 시기. `next`: 편집자 집중 영역 |

---

## 서브에이전트 시스템

### delegate_task

세션 내에서 서브에이전트를 호출하는 기본 메커니즘:

```python
delegate_task(
    agent_profile="reviewer",
    goal="src/auth/*.ts의 인증 변경사항 리뷰",
)
```

`agent_profile` 파라미터:
1. `~/.drewgent/agents/<name>.md`에서 프로필 파일을 읽음
2. 프로필의 frontmatter에서 model/provider/toolsets를 오버라이드
3. 프로필의 시스템 명령어를 서브에이전트 컨텍스트 앞에 추가
4. 서브에이전트를 격리된 세션에서 실행

### 칸반 파이프라인 자동 분해

크래시에 강하고 인간 검토가 가능한 멀티-스테이지 작업:

```python
kanban_create(
    title="로그인 검증 추가",
    pipeline=["explorer", "implementer", "tester", "reviewer", "archiver"],
)
```

태스크들이 `task_links`를 통해 연결된 N개의 순차적 태스크가 생성됩니다:
- 첫 번째 태스크는 `ready`로 시작
- 각 후속 태스크는 `todo`로 시작 (부모를 기다림)
- 부모 완료 시, 의존성 엔진이 모든 부모 완료를 확인 → 자식을 `ready`로 승격
- 각 태스크는 별도의 worker 프로세스로 디스패치

### 컨텍스트 핸드오프 프로토콜

자식 태스크가 시작되면 worker(`scripts/run_kanban_worker.py`)가 자동으로:

1. `task_links`에서 부모 태스크 ID 조회
2. 각 부모의 `tasks.result` 읽기
3. JSON 파싱 시도 — 유효한 dict이면 구조화된 markdown으로 포맷
4. 유효한 JSON이 아니면 `handoff_failed` 이벤트 + 경고 + 시각적 표시
5. 컨텍스트 블록을 현재 태스크 본문 앞에 추가

런타임에 worker에서 발생 — DB 마이그레이션 제로, 스키마 변경 제로, 100% 하위 호환.

### ESCALATE 메커니즘

Flash 계층 프로필은 태스크가 자신의 능력을 초과한다고 신호를 보낼 수 있습니다:

```
ESCALATE: 이 리팩토링은 크로스-모듈 의존성 분석이 필요합니다.
planner + reviewer로 라우팅 추천.
```

호출자가 이 패턴을 감지하고 Max 계층 모델로 재라우팅합니다.

### 포니테일 원칙

코드를 작성하기 전에, 모든 에이전트는 최소화 체크리스트를 적용합니다:
1. 이 코드가 정말 필요한가? (YAGNI) → 아니오: 작성하지 않음
2. 표준 라이브러리에 이미 있나? → 사용
3. 네이티브 플랫폼 기능으로 되나? → 사용 (`<input type="date">` 등)
4. 이미 설치된 의존성이 해결하나? → 사용 (새 의존성 금지)
5. 한 줄로 가능한가? → 한 줄
6. 그래도 필요하면 최소한만.

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
      "~/.drewgent/P3-sensors/skills",
      "~/.config/opencode/skills"
    ]
  },
  "mcp": {
    "gbrain": {
      "type": "local",
      "command": ["gbrain", "serve"],
      "enabled": true,
      "timeout": 120000
    },
    "lazyweb": {
      "type": "remote",
      "url": "https://www.lazyweb.com/mcp",
      "enabled": true,
      "headers": { "Authorization": "Bearer {env:LAZYWEB_API_KEY}" },
      "timeout": 60000
    },
    "specification-website": {
      "type": "remote",
      "url": "https://mcp.specification.website/mcp",
      "enabled": true,
      "timeout": 60000
    }
  }
}
```

### MCP 서버

| 서버 | 타입 | 용도 | 인증 |
|------|------|------|------|
| **gbrain** | local (stdio) | 개인 지식 베이스 하이브리드 검색. 벡터 + 키워드, 코드 콜 그래프, 엔티티 추적 | `OPENAI_API_KEY` |
| **lazyweb** | remote (HTTP) | 28만+ 실제 앱 스크린샷. UI 디자인 참조, 전환율 최적화 리서치 | `LAZYWEB_API_KEY` |
| **specification-website** | remote (HTTP) | 웹 스펙 체크리스트: SEO, 접근성, 보안, 성능 | 없음 (공개) |

---

## 크론 및 자동화

launchd 기반 60초 틱이 `scripts/drewgent_cron.py`를 디스패치합니다. 스케줄러(`cron/scheduler.py`)가 `cron/jobs.json`을 읽고 예약된 간격으로 작업을 실행합니다.

| 간격 | 작업 | 설명 | 스크립트 |
|------|------|------|----------|
| 2분 | trend-evaluate | 수집된 트렌드를 철학 필터로 평가 | n8n_trigger_runner.py |
| 5분 | launchd watchdog | 모든 서비스 작동 확인 | shell |
| 5분 | dashboard push | 에이전트 상태를 Cloudflare 대시보드에 푸시 | agent_dashboard_push.py |
| 15분 | gbrain watchdog | gbrain 뇌 동기화 상태 확인 | shell |
| 6시간 | trend-collect | GitHub 트렌딩 레포 스크랩 | cron_trend_harvester.py |
| 6시간 | seo-harvester | RSS 피드에서 SEO 기사 수집 | cron_seo_harvester.py |
| 매일 04:00 | log rotation | 로그 로테이션 및 압축 | shell |
| 매일 06:00 | usage watch | 토큰 사용량 및 비용 추적 | minimax_usage.py |
| 매일 09:00 | harmony check | 볼트 그래프 무결성 검증 | shell |
| 매일 12:00 | seo-analyze | 수집된 SEO 기사 분석 | n8n_trigger_runner.py |
| 매일 20:00 | daily retro | 일일 작업 요약 생성 | n8n_trigger_runner.py |
| 매월 | trend-retire | 오래된 평가 트렌드 정리 | n8n_trigger_runner.py |
| 매월 | seo-trend report | SEO 트렌드 리포트 생성 | n8n_trigger_runner.py |
| 화/금 10:00 | taste review | 고품질 툴 심층 분석 | n8n_trigger_runner.py |

---

## 스킬

스킬은 YAML frontmatter가 있는 Markdown 파일로, 특정 작업을 위한 전문화된 명령어를 제공합니다. `skill()` 도구로 로드합니다.

포함된 카테고리 (~100개 이상의 스킬):

| 카테고리 | 설명 | 예시 스킬 |
|----------|------|-----------|
| `ui/` | UI 품질 기준, 디자인 시스템 | baseline-ui (12 우선순위 계층) |
| `devops/` | 인프라 및 배포 | kanban-orchestrator, cron-script-fastpath |
| `software-development/` | 엔지니어링 실천법 | ponytail, subagent-profiles, payment-integration |
| `creative/` | 시각 및 오디오 콘텐츠 | baoyu-infographic, sketch, comfyui |
| `mlops/` | ML 학습 및 추론 | axolotl, unsloth, vllm, gguf |
| `brain/` | 에이전트 시스템 유지보수 | memory-md-cleanup, daily-retro |
| `content/` | 콘텐츠 제작 파이프라인 | content-pipeline, wordpress-cms |
| `mcp/` | MCP 서버 연동 | gbrain-integration, native-mcp |
| `autonomous-ai-agents/` | 에이전트 아키텍처 패턴 | acp-thinking-spinner, hermes-agent |

---

## Discord 연동

`scripts/discord_bot.py`가 Discord 채널을 opencode 에이전트에 연결합니다:

- opencode의 `--attach` 모드로 연결 (포트 8642)
- 각 대화마다 스레드 생성
- 파일 첨부 지원 (이미지, 문서, 코드)
- 긴 메시지 청크 분할 전송
- launchd 서비스로 구성 (`ai.drewgent.discord-bot`) — 자동 복구

---

## 저장소 구조

### 레포에 포함된 것

```
~/.drewgent/
│
├── opencode.jsonc              opencode 설정 (모델, MCP, 스킬 경로)
├── AGENTS.md                   opencode가 로드하는 시스템 명령어
├── .env.example                API 키 설정 템플릿
├── .gitignore                  개인 런타임 데이터 제외
│
├── agents/                     14개 서브에이전트 프로필
│   ├── explorer.md             읽기 전용 분석 (flash)
│   ├── implementer.md          코드 구현 (flash)
│   ├── tester.md               테스트 작성 (flash)
│   ├── reviewer.md             코드 리뷰 (pro)
│   ├── reviewer-critical.md    아키텍처 리뷰 (max)
│   ├── security-reviewer.md    보안 감사 (max)
│   ├── planner.md              태스크 분해 (max)
│   ├── orchestrator.md         파이프라인 오케스트레이션 (max)
│   ├── designer.md             UI/UX 디자인 (flash)
│   ├── editor.md               콘텐츠 편집 (pro)
│   ├── content-manager.md      콘텐츠 제작 (pro)
│   ├── archiver.md             문서화 (flash)
│   ├── sre.md                  인프라 (flash)
│   ├── analyst.md              데이터 분석 (flash)
│   └── README.md
│
├── skills/                     스킬 디렉토리 (~100개)
├── P3-sensors/skills/          추가 아키텍처 스킬
├── scripts/                    39개 자동화 스크립트
├── tools/                      57개 툴 구현체
├── cron/                       예약 작업 정의
├── hooks/                      이벤트 훅
├── P0-brainstem/               생존 계층 — 거버넌스 규칙 + 禁 뉴런
├── P1-limbic/                  정체성 계층 — SOUL, 글쓰기 스타일
├── P2-hippocampus/             기억 계층 (README만 — 데이터는 gitignored)
├── P3-sensors/                 입력 계층 — 스킬, 게이트웨이 문서
├── P4-cortex/                  성장 계층 — 지식, UX 위키, 템플릿
├── P5-ego/                     정체성 계층 — SELF_MODEL
├── P6-prefrontal/              전략 계층 — 제안서, 장애 보고서, 계획
└── .github/workflows/          CI: 테스트, Docker, 문서 검사
```

### 레포에 포함되지 않은 것 (개인 데이터)

런타임에 `~/.drewgent`에 존재하지만 git에서 제외된 디렉토리들:

| 디렉토리 | 내용 | 제외 이유 |
|----------|------|-----------|
| `P2-hippocampus/kanban/` | 칸반 태스크 보드 SQLite | 개인 태스크 데이터 |
| `P2-hippocampus/knowledge/` | SEO 기사 수집 | 개인 리서치 |
| `P2-hippocampus/memories/` | 세션 인사이트 | 개인 학습 |
| `P4-cortex/content/` | 브랜드 가이드, 내러티브 | 개인 브랜딩 |
| `P5-ego/config/` | API 키, 시크릿 | 보안 |
| `config.yaml` | 개인 설정 | API 키, 경로 |
| `kanban.db` | 칸반 데이터베이스 | 개인 태스크 |
| `.db`, `.log`, `cache/` | 런타임 데이터 | 생성된 상태 |

---

## Obsidian 볼트

`~/.drewgent/` 전체는 **Obsidian 볼트**입니다. P0부터 P6까지는 위키링크(`[[Page Name]]`), YAML frontmatter, 타입 태그로 연결된 위키를 형성합니다.

```
~/.drewgent/               ← Obsidian 볼트 루트
├── P0-brainstem/          ← 거버넌스 규칙
├── P1-limbic/             ← 정체성과 페르소나
├── P2-hippocampus/        ← 기억과 지식 (런타임)
├── P3-sensors/            ← 스킬과 게이트웨이 문서
├── P4-cortex/             ← 성장, 참조, 계획
├── P5-ego/                ← 셀프 모델
├── P6-prefrontal/         ← 전략, 제안서, 장애
└── AGENTS.md              ← 에이전트 시스템 가이드 (볼트 문서)
```

### 레이어 간 위키링크

파일들은 `[[wikilink]]`를 통해 레이어 간에 참조됩니다:

- `AGENTS.md` → `[[P5-ego/SELF_MODEL]]`, `[[P0-brainstem/brain/rules]]`, `[[P1-limbic/persona/SOUL]]`
- `P0-brainstem/brain/rules.md` → 특정 `.neuron` 제약 파일
- 스킬 파일 → 아키텍처 문서와 다른 스킬
- 제안서 → 장애 보고서와 계획

### Obsidian 컨벤션

- **Frontmatter**: 모든 `.md` 파일에는 `title`, `type`, `space`, `tags`, `links`가 있는 YAML frontmatter
- **이름**: kebab-case, 볼트 전체에서 고유 (위키링크 모호성 방지)
- **태그**: 교차 분류에 사용 (`concept`, `guide`, `incident`, `proposal`)
- **볼트 제외**: 런타임 데이터 디렉토리 — `.obsidian/`에서 설정

### 볼트 질의

에이전트는 gbrain(MCP 서버)으로 볼트를 질의합니다:

```
gbrain_query("auth 패턴")             → 의미 + 키워드 검색
gbrain_get_backlinks("P5-ego/SELF_MODEL") → 참조하는 모든 페이지
gbrain_find_orphans()                  → 인바운드 링크 없는 페이지 찾기
```

---

## 이름 짓기 컨벤션

**Drewgent** = **Drew** + A**gent**.

이름은 이것이 개인화된 에이전트 시스템임을 반영합니다 — 당신의 이름, 당신의 규칙, 당신의 워크플로우. 포크를 위한 설계:

```
<yourname>gent
```

예시:
- `drewgent` (Drew + agent) — 이 레포
- `alexgent` (Alex + agent)
- `devgent` (Dev + agent)

### 이름 바꾸기

포크 후 자신의 이름으로 바꾸려면:

```
skill("rename-drewgent")
```

또는 직접 실행:

```bash
bash ~/.drewgent/scripts/rename-drewgent.sh "alexgent"
```

2000개 이상의 참조에서 "drewgent"를 "alexgent"로 교체하고, 디렉토리 이름을 변경하며, 설정 경로를 업데이트합니다.

---

## 기여하기

[CONTRIBUTING.md](CONTRIBUTING.md) 참조 — PR당 하나의 변경, 새 의존성 금지, 출처 포함.

## 보안

[SECURITY.md](SECURITY.md) 참조 — 취약점은 공개 이슈가 아닌 이메일로 보고.

## 관련 프로젝트

- [opencode](https://opencode.ai) — Drewgent가 동작하는 CLI 에이전트 플랫폼
- [gbrain](https://github.com/anomalyco/gbrain) — 하이브리드 검색을 위한 로컬 PGLite 뇌 서버
- [lazyweb](https://lazyweb.com) — 28만+ 실제 앱 스크린샷 UI 디자인 참조
- [specification.website](https://specification.website) — 웹 스펙 체크리스트

## 라이선스

MIT — [LICENSE](LICENSE) 참조
