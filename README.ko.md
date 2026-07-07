# opencode-drewgent

[![Built for opencode](https://img.shields.io/badge/Built%20for-opencode-8A2BE2)](https://opencode.ai)

**opencode 기반 개인 AI 에이전트를 위한 밑그림입니다.**

이 레포지토리는 프레임워크가 아닌 **출발점**입니다. [opencode](https://opencode.ai) 위에서 동작하는 개인 AI 에이전트를 구축하기 위한 컨벤션, 도구, 인프라 패턴을 제공합니다. Fork해서 자신만의 에이전트로 만들어보세요.

---

## 시작하기

```bash
git clone https://github.com/humanerd-drew/opencode-drewgent.git my-agent
cd my-agent
# 1. @identity/ 수정 — 이름, 규칙, 페르소나 설정
# 2. .env.example → .env 복사, OPENAI_API_KEY 입력
# 3. 실행: opencode
```

전체 가이드는 [AGENTS.md](AGENTS.md)를 참조하세요.

---

## 구성

```
@identity/            → 에이전트 정체성 (SELF_MODEL, 규칙, 페르소나)
@action/              → 스킬, 제안, 마이그레이션 기록
.opencode/            → 에이전트 프로필, MCP 도구
launchd/              → macOS 서비스 템플릿
cron/                 → 예약 작업 디스패처
harness/patterns/     → 품질 패턴 (manufacturing-bridge)
skills/               → 100+ 스킬 정의
scripts/              → 설치, 동기화, 하우스키핑
```

---

## 핵심 개념

**7-레이어 브레인 (P0-P6):** 에이전트 의사결정 계층 구조. `P0-brainstem/`의 규칙이 모든 것을 재정의합니다. `P5-ego/`의 정체성이 행동을 지배합니다.

**Obsidian Vault = 지식 그래프:** P-레이어 디렉토리는 에이전트의 장기 기억입니다. 에이전트는 `recall()`로, 사용자는 Obsidian에서 직접 질의할 수 있습니다.

**Governance as Code:** 규칙은 권고가 아닌 강제 제약(`.neuron`)입니다. `harness/patterns/manufacturing-bridge.md`에 6가지 품질 패턴이 문서화되어 있습니다.

**계층적 자율성:** 에이전트가 자율적으로 처리할 일(Tier 1-2), 제안 후 승인(Tier 3), 인간의 결정 필요(Tier 4)로 구분됩니다.

---

## 커스터마이징

| 단계 | 방법 |
|------|------|
| 이름 변경 | `bash scripts/rename-drewgent.sh YourAgentName` |
| 정체성 | `@identity/SELF_MODEL.md`, `@identity/persona/SOUL.md` 수정 |
| 규칙 | `@identity/brain/rules.md` 수정 |
| MCP 서버 | `opencode.jsonc` 수정 |
| Cron 작업 | `cron/jobs.json` 수정 |
| Launchd 서비스 | `launchd/*.plist.example` → `~/Library/LaunchAgents/` 복사 |

---

## 라이선스

MIT
