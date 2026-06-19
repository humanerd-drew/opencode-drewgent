---
name: llm-cost-audit
title: Drewgent LLM Cost Audit
description: Drewgent의 LLM 호출 작업을 inventory하고 cost optimization 후보를 도출하는 표준 절차
domain: devops
space: growth
type: skill
tags: [devops, cost, llm, audit, optimization]
created: 2026-06-02
updated: 2026-06-02
links:
  - "[[P4-cortex/knowledge/NEURONFS_RULES]]"
  - "[[P5-ego/SELF_MODEL]]"
  - "[[P0-brainstem/brain/rules]]"
  - "[[skills/devops/minimax-usage]]"
  - "[[skills/software-development/token-compression-headroom]]"
  - "[[skills/software-development/llm-model-migration]]"
---

# Drewgent LLM Cost Audit

Drewgent의 LLM 호출 작업을 inventory하고 cost optimization 후보를 도출하는 표준 절차.

## When to use

- Model flip 후 (M2.7→M3 같은 catalog change)
- Cron job 신규 등록 후
- Monthly token bill review
- Token 사용 spike 감지 시
- Smart routing 설정 변경 후
- Acp / Kanban / Cron architecture 변경 후

## 핵심 발견 (2026-06-02 audit)

**Finding #1 — Smart routing misconfig**:
config.yaml의 `smart_model_routing.cheap_model.model`이 main `model.model`과 같으면 (예: 둘 다 M3) cost saving 효과 0. 단순 prompt도 M3로 라우팅됨.

**Finding #2 — Kanban worker ≠ 결정론적**:
`run_kanban_worker.py:140`은 tempfile script로 `AIAgent(model='MiniMax-M3')` 인스턴스화. KANBAN_WORKER_MODE=1 환경변수는 결정론적 shell이 아님을 나타내지 않음. ready task spawn마다 LLM 1회. KANBAN-REVIEW-20260520.md의 "결정론적 shell script" 기술은 부정확.

**Finding #3 — Scheduler dispatches all jobs as LLM**:
`cron/scheduler.py:596`의 `run_job()`은 jobs.json의 모든 prompt를 `AIAgent(...)`로 실행. prompt가 단순 shell command만 있어도 (cron-output-cleanup, kanban-maintenance 등) LLM이 1번 거침.

## 5-Step Audit Framework

### Step 1 — jobs.json inventory

```bash
cat ~/.drewgent/cron/jobs.json | jq '.jobs[] | {id, name, schedule: .schedule.expr, enabled, model, prompt_len: (.prompt | length)}'
```

분류:
- enabled/disabled
- prompt 길이 (단순 shell ≈ <500 chars, LLM reasoning 필요 ≈ >1500 chars)
- LLM 호출 vs 결정론적 shell

### Step 2 — Dispatcher / worker LLM grep

```bash
grep -n "AIAgent\|chat\.completions\|messages\.create" ~/.drewgent/scripts/run_kanban_worker.py
grep -n "AIAgent" ~/.drewgent/scripts/dispatch_once_*.py
```

예상:
- dispatch_once_*.py → LLM 호출 0건 (sqlite3 + subprocess.Popen only)
- run_kanban_worker.py → AIAgent 1+ 건 (KANBAN_WORKER_MODE=1도 LLM)

### Step 3 — Entry point LLM grep

```bash
grep -rn "AIAgent\|chat\.completions\|call_llm" \
  ~/.drewgent/source/drewgent-agent/acp_adapter/ \
  ~/.drewgent/source/drewgent-agent/gateway/run.py \
  ~/.drewgent/source/drewgent-agent/cli.py 2>/dev/null
```

| Entry | Pattern | LLM? |
|-------|---------|------|
| acp_adapter/server.py:758 | agent.run_conversation | ✅ |
| acp_adapter/session.py:473 | AIAgent(**kwargs) | ✅ |
| gateway/run.py | (분해 후 AIAAgent 호출) | ✅ |
| cli.py | AIAgent 인스턴스화 | ✅ |

### Step 4 — Aux LLM caller inventory

```bash
grep -rn "call_llm" ~/.drewgent/source/drewgent-agent/agent/ | grep -v test
```

확인 위치:
- title_generator.py:38 — max_tokens=30, background thread
- context_compressor.py:364 — summary 생성 (M3 1M이라 거의 안 옴)
- web_tools.py — web extract
- vision tools — 이미지 분석
- session_search, skills_hub, mcp, flush_memories — auxiliary.* config 사용

### Step 5 — config.yaml model audit

```bash
grep -A2 "model:\|provider:\|cheap_model:\|summary_provider:\|fallback_model" ~/.drewgent/config.yaml | head -50
```

핵심 check:
1. `model.model` vs `smart_model_routing.cheap_model.model` — 같으면 효과 0
2. `auxiliary.compression.model` — 비어있으면 auto chain
3. `auxiliary.session_search.model` — 명시적 cheap model
4. `fallback_model.model` — main이 죽을 때 fallback

## 5 LLM-Calling Categories (Inventory Template)

| Category | Where | Frequency | Cost lever |
|----------|-------|-----------|------------|
| 24/7 gateway/ACP | acp_adapter/server.py:758, session.py:473 | user message마다 | prompt_cache, max_iter cap |
| Cron jobs (LLM dispatch) | cron/scheduler.py:596 | 6h~1주 주기 | 단순 shell은 LLM 우회 (H2) |
| Background thread | title_generator.py:38 | session 1개당 1회 | smaller model (H4) |
| Kanban worker | run_kanban_worker.py:140 | ready task spawn마다 | 결정론적 재작성 (H3) |
| Direct user turn | AIAgent.run_conversation | user input마다 | prompt_cache, max_iter cap |

## Cost Optimization Candidates (8 options)

| ID | 변경 | Risk | 가성비 |
|----|------|------|--------|
| H1 | smart_routing.cheap_model을 더 작은 모델로 (예: M2.5) | 낮음 | ★★★★★ |
| H2 | 단순 shell cron을 scheduler bypass로 직접 실행 | 중 | ★★★★ |
| H3 | run_kanban_worker.py를 진짜 결정론적으로 재작성 | 높음 | ★★ |
| H4 | title_generator/context_compressor를 더 작은 모델로 | 낮음 | ★★★★ |
| H5 | disabled job 재활성화 검토 | — | — |
| H6 | prompt_caching 활성화 강화 (Anthropic cache) | 낮음 | ★★★ |
| H7 | max_iterations 90 → 50 | 중 (큰 작업 잘림) | ★ |
| H8 | (cost와 무관, skip) | — | — |

## 3 Critical Misconfig Checks (must verify)

1. **Smart routing cheap = main model** (Finding #1)
   ```bash
   grep -E "model:|cheap_model:" ~/.drewgent/config.yaml
   ```
   cheap_model.model이 main model.model과 같으면 효과 0. 즉각 변경 후보.

2. **Kanban worker 결정론적 여부** (Finding #2)
   ```bash
   grep -n "AIAgent" ~/.drewgent/scripts/run_kanban_worker.py
   ```
   KANBAN_WORKER_MODE 환경변수가 있어도 LLM 호출하면 결정론적이 아님.
   KANBAN_REVIEW 같은 과거 review 문서의 "결정론적" 기술 신뢰 금지.

3. **Cron scheduler LLM dispatch** (Finding #3)
   ```bash
   grep -n "AIAgent" ~/.drewgent/source/drewgent-agent/cron/scheduler.py
   ```
   jobs.json prompt가 단순 shell이라도 LLM 1회 거침. scheduler.py가
   shell-only path 지원하면 cron 단순 shell job은 LLM 우회 가능.

## Verification (ROI 측정)

실측 데이터 없이 추정만 하지 말 것. 다음 절차:

1. `display.show_cost: true` 켜기 (`~/.drewgent/config.yaml`)
2. 1~2주 baseline 수집 (LLM call count, input/output tokens)
3. H1/H2 등 1개씩 적용 → 1주 측정
4. 절감률 계산 (전월 baseline 대비)

memory 6/1: "Token Plan credits 기반 (per-call 정액제 → 입력/출력 단가 기반)"
→ cost는 per-call 정액제가 아닌 token 단가 기반. 즉 큰 모델이 더 비쌈.
M3 1M은 M2.5보다 비싸다. simple prompt도 M3로 보내면 손해.

## Pitfalls

- **memory note의 "결정론적" 기술을 그대로 믿지 말 것** — grep으로 확인
- **scheduler.py의 LLM dispatch 가정을 잊지 말 것** — 단순 shell job도 cost 발생
- **auxiliary.compression.provider=auto** — OpenRouter/Nous/Anthropic fallback chain
  작동, M3 외 다른 provider가 fallback으로 잡힐 수 있음
- **show_cost: false 기본값** — 비용 안 보임, ROI 측정 전에 켜야 함
- **display.compact: false + tool_preview_length: 0** — UI verbose mode,
  tool output이 prompt에 그대로 들어감. compact mode + preview_length
  조정으로 input token 절감 가능 (별도 cost lever)

## Related skills

- `token-compression-headroom` — tool output 4-layer cap, headroom_ai POC
- `llm-model-migration` — M2.7→M3 같은 provider flip
- `minimax-usage` — MiniMax Token Plan 사용량 확인 (ZSH RPROMPT 통합)
- `cron-jobs-stalled` — cron 정지 incident 진단
- `external-tool-evaluation` — 외부 도구 POC 패턴 (headroom_ai 평가에 사용)

## Verification

- [ ] jobs.json 10개 inventory + LLM 호출 여부 분류 완료
- [ ] dispatcher/worker LLM grep 결과 확인
- [ ] 4 entry point LLM call site 모두 식별
- [ ] aux 8 task (call_llm caller) 모두 식별
- [ ] config.yaml model/smart_routing 3 check 모두 pass
- [ ] 8 cost candidates 우선순위 매트릭스 작성
- [ ] user-facing report (H1~H8 가성비) 제출
- [ ] show_cost 활성화 + 1~2주 baseline 시작 (next turn)
