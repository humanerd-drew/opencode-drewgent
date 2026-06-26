---
name: yaml-config-patch-drewgent
description: Patch Drewgent config.yaml safely — handles the dual-config pattern (~/.drewgent/config.yaml + P5-ego/config/config.yaml) and avoids mcp_patch YAML gotchas
links:
  - "[[@action/skills/SKILL-INDEX]]"
  - "[[@identity/brain/rules]]"
---

# YAML Config Patch — Drewgent Dual-Config Pattern

Drewgent는 config.yaml을 **두 곳에 중복**으로 유지한다. compression이나
auxiliary 같은 task-specific routing 변경 시 **두 파일 모두** 손대야 하고,
각 파일 내에서도 nested section 구조를 정확히 이해하고 patch해야 한다.

이 skill은 2026-06-03 cost optimization (H3 — M3 → M2.5 routing) 작업 중
두 차례 patch 실수로 얻은 운영 노하우를 정리한다.

---

## 1. Dual-Config Pattern (CRITICAL)

Drewgent는 두 개의 config.yaml을 운영한다:

| File | Used by | What it has |
|---|---|---|
| `~/.drewgent/config.yaml` | gateway, CLI, cron scheduler, run_kanban_worker | `auxiliary.compression` (provider/model) 만 |
| `~/.drewgent/P5-ego/config/config.yaml` | P5-ego layer (identity snapshot) | `compression:` (summary_*) + `auxiliary.compression:` (provider/model) 둘 다 |

**P5-ego 파일의 compression 섹션이 두 군데**:
- root-level `compression:` (line 43-50 근처) — `summary_provider`, `summary_model`, `summary_base_url`
- `auxiliary.compression:` (line 72-77 근처) — `provider`, `model`, `base_url`, `api_key`, `timeout`

이 둘은 **다른 dict**. P5-ego의 의도는 P5 layer가 자기 config를 가진 것.
path-integrity-report-2026-05-17에서는 "do not auto-fix yet" 결정.

**변경 시 두 파일 + P5-ego는 두 section 모두** 손봐야 할 수 있다.
auxiliary.compression만 보면 P5-ego의 root-level compression이 stale로 남는다.

---

## 2. mcp_patch YAML Gotcha

`mcp_patch`로 YAML을 patch할 때 **partial old_string이 sibling section을
복제하는 사고**를 내기 쉽다.

### 발생 패턴 (실제 사고 사례, 2026-06-03)

원본:
```yaml
compression:        ← root-level
  enabled: true
  threshold: 0.9
  summary_model: ''
  summary_provider: minimax
```

잘못된 patch — old_string이 `summary_model: ''` 부분만 잡고 new_string이
compression:으로 다시 시작:
```yaml
compression:        ← root-level (line 43)
  enabled: true
compression:        ← DUPLICATE (line 45) — 잘못된 새 키
  enabled: true     ← DUPLICATE (line 46)
  threshold: 0.9
  ...
```

YAML이 broken. 두 개의 `compression:`이 같은 level에 있어서 parser가
후자만 인식하거나 error.

### Prevention Rule

1. **Always read the file first** — 정확한 indentation, sibling section
   위치, 부모 key까지 확인 후 patch
2. **Match enough context** — old_string에 부모 key + 첫 child 1~2줄 +
   target key 1~2줄 포함. target만 매치하면 부모가 ambiguous
3. **Verify after every patch** — 즉시 `python3 -c "import yaml; yaml.safe_load(open(p))"`
   + 출력으로 scope 확인
4. **If duplication appears, read file** → 정확한 라인 파악 → 다시 patch
   (이미 있는 `compression:` 줄을 기준으로 작업)

### Recommended verification script

```bash
python3 -c "
import yaml
for p in [
    '~/.drewgent/config.yaml',
    '~/.drewgent/P5-ego/config/config.yaml',
]:
    with open(p) as f:
        c = yaml.safe_load(f)
    print(p)
    for k, v in c.get('auxiliary', {}).items():
        prov = v.get('provider','?') if isinstance(v,dict) else '?'
        mod = v.get('model','?') if isinstance(v,dict) else '?'
        print(f'  aux.{k:18} provider={prov} model={mod!r}')
    comp = c.get('compression', {})
    if comp:
        print(f'  compression:      summary_provider={comp.get(\"summary_provider\")} summary_model={comp.get(\"summary_model\")!r}')
"
```

출력에서 의도한 변경만 적용됐는지, 다른 auxiliary task가 unchanged인지
scope 확인.

---

## 3. Model Routing Change Checklist (예: H3 M3 → M2.5)

`call_llm(task="compression")`이 사용하는 routing logic:
- `auxiliary_client.py:1700-1770` `resolve_provider_for_task()`
- 우선순위: explicit arg > env var > `auxiliary.{task}` > root `compression.summary_*`
- `auxiliary.compression.provider="minimax"`이면 `compression.summary_provider`
  fallback은 안 탐 (line 1732 조건: cfg_provider가 None 또는 "auto"일 때만)

**변경 위치 3곳**:
1. `~/.drewgent/config.yaml` `auxiliary.compression.{provider, model}`
2. `~/.drewgent/P5-ego/config/config.yaml` `auxiliary.compression.{provider, model}`
3. `~/.drewgent/P5-ego/config/config.yaml` `compression.{summary_provider, summary_model}`

각 파일의 5-line block (provider/model/base_url/api_key/timeout) 전체가
auxiliary.compression의 한 묶음. patch 시 이 5줄을 단위로.

---

## 4. P0 Brainstem 禁karpathy_coding_principles 적용

config 변경도 surgical change 원칙 적용:
- 변경할 task만: compression (또는 변경하는 한 auxiliary task)
- 다른 auxiliary task는 unchanged 유지
- 위에 3번의 verification script로 scope 확인
- QA evidence: contract + micro (yaml valid) + full (실제 call_llm이 새 model로 라우팅)

---

## 5. Common Pitfalls (5/30~6/3 운영 중 발견)

1. **path-integrity-report-2026-05-17**: 두 config는 의도된 중복
   (P5-ego layer의 identity snapshot). 자동 dedup 시 의도 무너질 수 있음
2. **config.yaml의 smart_model_routing.cheap_model**: M3면 cheap 효과 0
   (cheap=smart=main). H1 작업 시 main model과 다른 모델로 설정 필요
3. **auxiliary.compression.provider=auto + model 명시**: OpenRouter chain
   따라가서 M2.5 매칭 provider 못 찾으면 fail. provider=minimax 명시가
   direct + 가장 robust
4. **mcp_patch "include" 누락**: old_string이 match 여러 곳 있으면
   ambiguous. `replace_all=true` 또는 더 큰 context로 매치
5. **6/1 M2.7 follow-up 메모리**: source/_agent/orchestrator/bot.py의
   M2.7 호출은 별도 scope — config routing 변경으로 안 잡힘. 직접 patch 필요

---

## 6. Related

- `~/.drewgent/P6-prefrontal/plans/path-integrity-report-2026-05-17` — config 중복 의도
- `~/.drewgent/P4-cortex/knowledge/token-compression-headroom-20260602` — cost 결과 패턴
- `skills/software-development/llm-model-migration` — model default swap
- `skills/software-development/python-nested-import-nameerror` — Python import gotcha
- `agent/auxiliary_client.py:1700-1770` — call_llm task routing logic
- `~/.drewgent/source/drewgent-agent/agent/model_metadata.py:130` — MiniMax-M2.5 catalog entry (204800, legacy)

---

*Generated 2026-06-03 after H3 cost optimization Round 1 — two patch recoveries and one full config recovery taught this pattern.*
