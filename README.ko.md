# opencode-{agent-name}

[opencode](https://opencode.ai) 위에서 동작하는 개인 AI 에이전트 템플릿입니다.

이 레포는 자신만의 에이전트 시스템을 만드는 출발점입니다. subagent 프로필, 스킬 라이브러리, cron 자동화, P0–P6 볼트 구조를 포함합니다. fork해서 이름을 바꾸고 커스터마이징하세요.

## 퀵 스타트

```bash
# 1. opencode 설치
curl -fsSL https://opencode.ai/install | sh

# 2. GitHub에서 이 레포를 fork한 뒤 클론
git clone git@github.com:YOUR_USERNAME/opencode-drewgent.git ~/.youragent
cd ~/.youragent

# 3. 셋업 실행
bash scripts/setup.sh

# 4. opencode 실행
opencode
```

## 최소 구조

```
~/.youragent/
├── AGENTS.md                   # opencode가 로드하는 시스템 가이드
├── opencode.jsonc              # 모델, MCP 서버, 스킬 경로
├── .opencode/agents/*.md       # subagent 프로필 템플릿
├── skills/                     # 스킬 라이브러리
├── cron/jobs.json              # cron 작업 예시
├── launchd/*.plist.example     # macOS 데몬 템플릿
├── scripts/                    # 자동화 스크립트
└── P0-brainstem/ ... P6-prefrontal/  # 볼트 레이어
```

## 커스터마이징

1. repo 전체에서 `drewgent` → `youragent`로 이름 변경 (`skill("rename-drewgent")` 또는 find/replace 사용).
2. `@identity/SELF_MODEL.md`, `@identity/persona/SOUL.md`, `@identity/persona/writing-style-guide.md`를 에이전트 정체성에 맞게 수정.
3. `skills/` 아래에서 필요한 스킬을 추가/제거.
4. 자동화 필요에 맞게 `cron/jobs.json` 수정.

전체 가이드는 [AGENTS.md](AGENTS.md)를 참조하세요.

## 라이선스

MIT — fork 시 원하는 라이선스로 변경하세요.
