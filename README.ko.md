# opencode-drewgent

[English](README.md)

[opencode](https://opencode.ai) 위에서 동작하는 AI 에이전트 **스타터 키트**입니다. fork해서 당신의 에이전트로 만드세요.

---

## 1. 설치 (2분)

**필요한 것:** 터미널 + GitHub 계정.

```bash
# 1. opencode 설치 (이미 설치했다면 생략)
curl -fsSL https://opencode.ai/install | sh

# 2. 이 레포를 클론
git clone git@github.com:humanerd-drew/opencode-drewgent.git ~/.youragent
cd ~/.youragent

# 3. 실행 (설치 + 실행을 한 번에)
bash scripts/setup.sh && opencode
```

opencode가 열리면:

```
# 4. 이름을 바꾸세요
/rename "내 에이전트"
```

이제 에이전트가 명령을 기다립니다. `"내 프로젝트에 로그인 기능을 추가해줘"` 같은 걸 말해보세요.

## 2. 이 키트가 주는 것

| 사용법 | 결과 |
|--------|------|
| `remember("portone v2로 전환")` | 결정이 영구 저장됩니다. `recall("portone")`로 언제든 검색 가능 |
| `recall("결제 오류")` | 지난 세션의 관련 내용을 찾아줍니다 |
| `graph-rca("배포 실패")` | 문제의 원인을 추적해 리포트를 만듭니다 |
| `"코드 리뷰해줘"` | 전담 리뷰어 에이전트가 검토합니다 |
| `"코드 분석해줘"` | 탐색 전담 에이전트가 아키텍처를 분석합니다 |
| `"이거 계획을 세워줘"` | 플래너 에이전트가 단계별 계획을 만듭니다 |

## 3. 시작 후 할 일

1. **이름 바꾸기** — `@identity/`와 `@action/` 폴더에 에이전트의 이름, 성격, 규칙이 있음
2. **API 키 등록** — `.env` 파일에 LLM 제공자 키를 추가
3. **맞춤 설정** — `skills/` 폴더에 새로운 능력을 추가할 수 있음

> opencode 안에서 `"이 프로젝트 구조가 어떻게 돼?"`라고 물어보세요.

## 설계 철학 — 왜 이렇게 만들었나

### P0-P6 볼트 구조

볼트는 에이전트의 장기 기억이자 정체성입니다. **뇌의 은유**를 사용한 이유는, 에이전트에게도 인간의 뇌와 같은 층위(본능, 성격, 기억, 감각, 추론, 자의식, 계획)가 필요하기 때문입니다.

| 레이어 | 경로 | 용도 |
|--------|------|------|
| **P0 — Brainstem** | `@identity/brain/` | 규칙, 제약, 불변 조건 |
| **P1 — Limbic** | `@identity/persona/` | 성격, 어조, 글쓰기 스타일 |
| **P2 — Hippocampus** | `P2-hippocampus/` | 원시 아카이브 — 세션, 기억 (읽기 전용) |
| **P3 — Sensors** | `@action/` | 도구 통합, 게이트웨이 설정 |
| **P4 — Cortex** | `skills/` | 스킬 정의, 성장 기록 |
| **P5 — Ego** | `@identity/SELF_MODEL.md` | 자의식, 컴파일된 위키 |
| **P6 — Prefrontal** | `P6-prefrontal/` | 인시던트, 회고, 계획 |

P0 규칙이 모든 것을 재정의합니다. "공손함"(P1)과 "시크릿 노출 금지"(P0)가 충돌하면 P0이 이깁니다.

### 서브에이전트 프로필

하나의 에이전트가 모든 것을 잘하려고 하면 컨텍스트와 비용만 낭비됩니다. 대신 **각 프로필은 전문화된 전문가**입니다:

- **implementer** — flash 모델, 파일 편집, 코드 생성
- **reviewer** — pro 모델, 코드 품질 게이트
- **planner** — max 모델, 작업 분해
- **explorer** — flash 모델, 읽기 전용 코드 탐색
- **sre** — flash 모델, 인프라 모니터링
- **analyst** — 읽기 전용, 데이터 질의

### 결정 맥락 기록 (Provenance)

AI 어시스턴트의 가장 큰 문제는 **휘발성 컨텍스트**입니다. 세션 중에는 훌륭한 결정을 내리지만, 세션이 끝나면 그 결정은 사라집니다. 모든 artifact에 기원 이야기를 기록함으로써 해결합니다:

```yaml
trigger: "무슨 문제에서 비롯되었는가"
provenance:
  session: "YYYY-MM-DD 주제"
  decision: "왜 이 방법을 선택했는가, 어떤 대안이 있었는가"
```

나중에 `recall("decision: ...")`로 전체 맥락을 복구할 수 있습니다.

### 계층적 자율성 (Tiered Autonomy)

| 티어 | 범위 | 권한 |
|------|------|------|
| **1** | 오타, 사소한 수정 | 자율 실행. 완료 후 보고. |
| **2** | 확립된 패턴 내 작업 | 자율 실행. provenance 포함. |
| **3** | 구조적 변경 | 제안 → 승인 후 실행. |
| **4** | 아키텍처 결정 | 제안만. 인간이 결정. |

명시적 티어는 에이전트가 불확실성을 판단해야 하는 부담을 없앱니다.

### 스킬 시스템

스킬은 **실행 가능한 지식**입니다. 작업이 트리거와 일치할 때 필요시 로드됩니다:

```python
skill("portone-payment-integration")
# → PortOne V2 SDK 패턴, KG이니시스 설정, 웹훅 처리 로드
```

각 스킬은 `SKILL.md` 파일이 있는 디렉토리입니다. 에이전트가 모든 것을 미리 알 필요가 없게 합니다.

### 위임 패턴

- **`task(...)`** — 같은 모델, 같은 세션. 빠르고 저렴.
- **`gjc_delegate_execute(...)`** — 격리된 worktree + tmux. 병렬/위험 작업용.

5분 미만이고 격리가 필요 없으면 `task()`. 아니면 `gjc_delegate_*`.

### 크론 자동화

스케줄러(`scripts/drewgent_cron.py`)가 에이전트를 반응형에서 능동형으로 바꿉니다. `cron/jobs.json`에 정의된 작업이 사용자 개입 없이 정해진 시간에 실행됩니다.

### 칸반

작업 지속성을 위한 도구입니다. 에이전트가 작업 중 크래시되어도 칸반에 추적된 작업은 사라지지 않습니다. 각 작업에는 파이프라인(explorer → implementer → reviewer)과 영향도 점수가 있습니다.

### 증상에서 해결까지

```
이름 붙이기 → 추적하기 → 패턴 매칭 → 결정 → 수정 → 아카이브
```

대부분의 에이전트는 2-4단계를 건너뛰고 같은 버그를 반복해서 발견합니다.

## MCP 서버

| 서버 | 타입 | 용도 |
|------|------|------|
| `codebase-memory-mcp` | local | 코드베이스 지식 그래프 |
| `gajae-code` | local | GJC Coordinator — 격리 실행 |
| `safari` | local | 웹 브라우징 (macOS Safari TP 필요) |
| `astryx` | remote | Meta 디자인 시스템 |
| `discord` | local | Discord 연동 (봇 토큰 필요) |
| `wordpress` | local | WordPress 콘텐츠 관리 |

## 알려진 문제

- **Python 3.14**: `except json.JSONDecodeError:` → `UnboundLocalError`. 해결: `__import__('json').loads()`
- **macOS bash 3.2**: 연관 배열 없음. `date -j -f` 사용
- **Launchd plist**: `KeepAlive { SuccessfulExit: false, ThrottleInterval: 10 }` 사용
- **토큰 데이터**: stderr가 아닌 `~/.local/share/opencode/opencode.db`에 있음
- **이름 변경 필수**: 변경 없이 실행하면 에이전트가 자신을 "Drewgent"라고 생각함

## 생성 콘텐츠 저작권 표시

공개 콘텐츠(블로그, 트윗, 데모)에만:

```
Built with [opencode-drewgent](https://github.com/humanerd-drew/opencode-drewgent)
```

## Credits

opencode-drewgent는 다음 오픈소스 프로젝트들의 아이디어와 구조를 참고했습니다:

| Project | Author | Contribution | License |
|---------|--------|-------------|---------|
| [opencode](https://opencode.ai) | [Anomaly](https://github.com/anomalyco) | AI 코딩 에이전트 플랫폼 | MIT |
| [codebase-memory-mcp](https://github.com/anomalyco/opencode) | Anomaly | 코드베이스 지식 그래프 | MIT |
| [Gajae-Code](https://github.com/Yeachan-Heo/gajae-code) | [Yeachan-Heo](https://github.com/Yeachan-Heo) | GJC Coordinator — worktree 격리, tmux 병렬 | — |
| [discord-mcp](https://github.com/anomalyco/discord-mcp) | Anomaly | Discord MCP 서버 | MIT |
| [PortOne](https://developers.portone.io) | PortOne | 한국 결제 게이트웨이 SDK | — |
| [Cloudflare Agents SDK](https://developers.cloudflare.com/agents) | Cloudflare | 상태 기반 에이전트 프레임워크 | MIT |
| [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) | Andrej Karpathy | 컴파일 패턴 지식베이스 개념 | — |
| [Ponytail](https://github.com/DietrichGebert/ponytail) | Dietrich Gebert | 코드 최소화 체크리스트 | — |
| [NeuronFS](https://github.com/rhino-acoustic/NeuronFS) | [rhino-acoustic](https://github.com/rhino-acoustic) | 뇌 기반 거버넌스 시스템 | — |
| [specification.website](https://specification.website) | [Joost de Valk](https://github.com/jdevalk) | 웹 스펙 체크리스트 MCP | — |
| [ARD Spec](https://agenticresourcediscovery.org) | Google/MS | Agentic Resource Discovery 표준 | — |
| [agent-wiki](https://github.com/lazymac2x/agent-wiki) | lazymac2x | 제조↔에이전트 하네스 동형성 개념 | MIT |
| [opencrab](https://github.com/opencrab/opencrab) | opencrab | AI 에이전트용 지식 그래프 시스템 | Apache 2.0 |

## License

MIT — fork 시 자신의 라이선스로 교체하세요.
