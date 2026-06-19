# Delegation Silent Fallback — Subagent가 부모 모델만 쓰는 현상의 root cause

## 증상

- 멀티에이전트/서브에이전트(`delegate_task`)를 spawn해도 dashboard의 Models 카드에 모델이 1개만 뜬다
- 4-level routing을 config에 설정해놨는데도 서브에이전트가 부모와 같은 모델을 사용한다
- "API key를 역할마다 발행하면 분배되지 않을까?"라는 잘못된 가설로 시간 낭비

## root cause (확정)

`tools/delegate_tool.py`의 `_spawn_subagent` 함수, line 1016-1018:

```python
effective_model = model or parent_agent.model
effective_provider = override_provider or getattr(parent_agent, "provider", None)
effective_base_url = override_base_url or parent_agent.base_url
```

`model` 인자가 None이면 (config의 `delegation.model`이 비어있거나 주석 처리) **silent fallback** — 경고도 로그도 없이 부모 모델을 그대로 사용. 서브에이전트는 자기 spawn 로그에 `model: <parent의 model>` 찍히고 끝남. 그래서 dashboard에 부모 모델만 카운트됨.

## 진단 절차 (전수조사 1회)

```bash
# 1. config.yaml의 delegation 블록이 model/provider를 갖고 있는지 확인
grep -nA 10 "^delegation:" ~/.hermes/config.yaml
```

**확정 조건**: `model:` 또는 `provider:` 키가 `delegation:` 블록 안에 없거나 모두 주석 처리됨.

```bash
# 2. effective config 확인
hermes doctor

# 3. 실제 spawn 시 어떤 모델이 쓰였는지 log 확인
grep -E "effective_model|Using model|delegate_task.*model=" ~/.hermes/logs/agent.log | tail -20
```

→ 전부 같은 모델이면 원인 확정.

## 흔한 오해 (반드시 교정)

| 오해 | 진실 |
|------|------|
| "API key를 역할마다 발행하면 모델이 분배된다" | **아님.** API key는 인증/과금 분리일 뿐 모델 선택과 무관. 모델은 model/provider 필드로 결정됨. |
| "provider만 다르면 모델이 다른 걸 쓴다" | **아님.** 같은 provider 안에서도 model 필드가 핵심. opencode-go에서 `deepseek-v4-flash`와 `deepseek-v4-pro`는 다른 모델. |
| "4-level routing을 설정했으니 자동 분배된다" | **부분적으로 맞음.** main/delegation/auxiliary 각 레벨에 명시적으로 설정해야 동작. 빠진 레벨은 부모 레벨로 silent fallback. |
| "서브에이전트가 spawn될 때 로그를 보면 알 수 있다" | **반만 맞음.** 로그에는 부모의 model만 찍힘. delegation.model이 비어있다는 단서 자체는 안 나옴 — config를 직접 봐야 함. |

## 해결 옵션 (옵션 → 추천 → go)

### A. config.yaml에 delegation.model 추가 ← **내 추천**

가장 단순, 즉시 적용 가능, 4-tier 라우팅 의도와 정확히 일치.

```yaml
# ~/.hermes/config.yaml
delegation:
  max_iterations: 50
  model: "deepseek-v4-pro"          # subagent용 — 부모(flash)보다 강한 모델
  provider: "opencode-go"           # provider 명시 필수 (auto-resolution 회피)
```

**검증**:
```bash
hermes doctor     # effective config 덤프에서 delegation.model 확인
# 그 다음 서브에이전트 spawn → log에서 model=deepseek-v4-pro 찍히는지 확인
```

### B. `delegate_task(agent_profile="<name>")`로 per-call override

`~/.drewgent/agents/<name>.md` 또는 `~/.hermes/agents/<name>.md` profile에 model 박혀있으면 config보다 우선. 역할별 세분화 가능.

```python
delegate_task(
    goal="Review this PR for security issues",
    agent_profile="reviewer",   # ~/.drewgent/agents/reviewer.md 사용
    context="..."
)
```

profile 파일 구조 예시:
```yaml
---
name: reviewer
model: deepseek-v4-pro
provider: opencode-go
toolsets: [file, terminal]
instructions: |
  You are a code reviewer. ...
---
```

config의 `delegation.model`보다 우선순위 높음. A와 B를 같이 쓰면: config의 delegation.model은 기본값, profile이 명시한 경우만 override.

### C. API key 분리 — **보류**

쿼터/과금 분리가 실제 필요해질 때까지 도입 가치 없음. 멀티테넌트/멀티팀 운영 단계에서 추가.

## 관련 코드 위치 (참조)

- `tools/delegate_tool.py:1016-1018` — effective_model/provider/base_url silent fallback
- `tools/delegate_tool.py:867-876` — `_spawn_subagent` 시그니처, model 파라미터
- `tools/delegate_tool.py:679-735` — `_build_parent_progress_relay` — model kwarg threading
- `~/.hermes/config.yaml` line 855+ — `delegation:` 블록
- 공식 docs: `website/docs/user-guide/features/delegation.md` line 132-143 — Model Override 섹션

## provenance

- 발견: 2026-06-16 multi-agent routing Q&A 세션
- 트리거: 사용자 "왜 모델이 하나만 쓰이고 있는건데" — `delegate_tool.py:1016`의 `or parent_agent.model` 패턴 직접 발견
- 검증: grep으로 `~/.hermes/config.yaml:855-863`의 delegation 블록 점검 → model/provider 키 부재 확인
