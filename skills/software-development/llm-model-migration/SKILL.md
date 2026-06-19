---
name: llm-model-migration
description: LLM provider가 default model을 업데이트(M2.7→M3, GPT-4→GPT-5, claude-3.5→3.7)하거나 pricing/Token Plan을 변경했을 때 코드/문서/카탈로그를 일관되게 마이그레이션하는 표준 절차. scope 분해 → grep inventory → catalog+production+docs 병렬 patch → 3단계 verification (AST, runtime, grep) → out-of-scope flagging → memory 영구 저장.
title: LLM Model Migration — Provider Default Update
domain: software-development
space: growth
type: workflow
tags: [llm, model-migration, provider-update, token-plan, drewgent]
created: 2026-06-01
updated: 2026-06-01
links:
  - "[[P4-cortex/growth/INTEGRATION_PROTOCOL]]"
  - "[[P5-ego/SELF_MODEL]]"
  - "[[P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁/禁task_qa_gate.neuron]]"
  - "[[P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁/禁blind_write.neuron]]"
  - "[[P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁/禁karpathy_coding_principles.neuron]]"
  - "[[P0-brainstem/brain/rules]]"---

# LLM Model Migration — Provider Default Update

LLM provider가 default model을 업데이트했을 때 (M2.7→M3, GPT-4→GPT-5, claude-3.5→3.7 등) 코드/문서/설정을 일관되게 마이그레이션하는 표준 절차.

## 트리거 조건

다음 중 하나라도 해당되면 이 스킬을 로드:
- Provider 모델 업데이트 발표 (new default)
- Token Plan / pricing 변경 (per-call 정액제 → input/output 단가제 등)
- 모델 context window 변경 (8K → 1M 등)
- Legacy catalog 정리 (구 모델 deprecation)

## 1단계: Scope 확정 (사용자 입력 파싱)

사용자가 제시한 scope를 명확히 분리:
- **In-scope files**: 사용자가 명시한 파일 (예: "production code 4개 파일")
- **Catalog/registry**: model_metadata.py 같은 lookup table
- **Docs**: providers.md, SKILL.md, README, ARCHITECTURE
- **Comments**: source code 주석/문서
- **Out-of-scope candidates**: scope 밖이지만 영향 받을 수 있는 파일 (orchestrator, test fixture 등)

⚠️ Scope 밖 후보는 사용자에게 **보고만 하고 변경하지 않는다** — silently 바꾸면 사용자의 의도(intent)를 무시하게 된다.

## 2단계: 재고 (Inventory) — grep으로 모든 참조 수집

```bash
# In-scope + catalog + docs
grep -rn "M2.7" --include="*.py" --include="*.md" \
  scripts/ plugins/ P0-brainstem/ agent/ \
  website/docs/ skills/ CHANGELOG.md
```

### 2-1. Multi-source file discovery (필수)

Drewgent vault는 같은 파일이 여러 위치에 복사돼있을 수 있다. catalog/config 단일 파일로 가정하면 안 됨:

```bash
# catalog 후보 파일이 몇 개 있는지 먼저 파악
find ~/.drewgent/source -name "model_metadata.py" 2>/dev/null
find ~/.drewgent/P0-brainstem -name "model_metadata.py" 2>/dev/null
find ~/.drewgent -maxdepth 6 -name "config.yaml" 2>/dev/null
```

**왜 중요한가**: 같은 `model_metadata.py`가 보통 3군데 있어:
- `source/drewgent-agent/agent/` — canonical (runtime이 import)
- `P0-brainstem/agent/` — frozen policy (catalog lookup fallback 용도, 직접 import X)
- `agent/` (top-level) — 보통 canonical의 symlink

migration이 frozen copy에만 적용되고 canonical은 안 바뀐 채로 CHANGELOG는 "Done" 찍히는 경우 자주 발생. runtime catalog lookup → 옛 모델 fallback → 새 모델 못 쓰는 상황.

체크리스트:
- [ ] 각 catalog 후보의 `mtime` 비교 (최신인지)
- [ ] `MiniMaxAI/MiniMax-M3` entry가 canonical(`source/drewgent-agent/...`)에 있는지가 1순위
- [ ] frozen copy는 통상 **변경하지 않음** — 만약 변경됐다면 잘못된 위치로 적용된 것
- [ ] provider model list (`drewgent_cli/models.py`)는 catalog와 별개 — 둘 다 migration 필요

분류해서 리스트업:
- Production code default (실제 API call에 사용)
- Catalog entry (lookup table)
- Doc references (skills, providers, README)
- Comments (소스 주석)
- Out-of-scope references (orchestrator, test, scratch) — **플래그만, 변경 X**

## 3단계: 병렬 읽기 (3-5개 파일씩)

production code + catalog + docs를 동시에 read_file. 각 파일에서 정확한 default line 위치 + 패턴 파악.

## 4단계: 변경 적용 (병렬 patch)

- **Production code**: default model string 직접 교체
- **Catalog**: 새 모델 entry 추가 (1M context 등), legacy 모델 entry는 `legacy` 주석 달고 보존
- **Docs**: default model + context window + pricing 표 업데이트
- **Comments**: "M2.7 기반" 같은 주석도 일관성 위해 업데이트
- **CHANGELOG.md**: prepend (맨 위에 추가) — migration은 visible한 history event

### Catalog 패턴 (예: model_metadata.py)

```python
# Before:
"MiniMaxAI/MiniMax-M2.5": 204800,  # legacy

# After (M3 추가):
"MiniMaxAI/MiniMax-M2.5": 204800,  # legacy — kept for backwards compat
"MiniMaxAI/MiniMax-M3": 1048576,  # Token Plan eligible; 1M context
```

→ 새 모델을 **append** (prepend 아님). M2.5 보존 = 옛 코드가 catalog lookup해도 fallback 가능.

### Production code 패턴

```python
# Before
DEFAULT_MODEL = "MiniMax-M2.7"

# After
DEFAULT_MODEL = "MiniMax-M3"  # 2026-06-01: M2.7 → M3 (Token Plan, 1M context)
```

→ 짧은 변경 사유 주석 추가 (왜 바꿨는지 1줄, 미래 추적용).

## 5단계: 신규 문서 작성 (Reference Doc)

Token Plan / pricing 변경 같은 **behavior change**가 있으면 별도 reference doc 작성:

- 경로: `website/docs/reference/{feature-name}.md`
- 내용: 이전 vs 이후 비교표, "기본 모델", "Token Plan", "credits 가이드"
- 다른 docs가 인용 가능하게 명확한 heading 구조

## 6단계: Verification (3개 모두)

### 6-1. Syntax check (AST parse)

```bash
for f in <production_files>; do
  python3 -c "import ast; ast.parse(open('$f').read())" && echo "OK: $f"
done
```

### 6-2. Model resolution (runtime test)

```python
import importlib.util
spec = importlib.util.spec_from_file_location('name', 'path/to/model_metadata.py')
mm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mm)
assert 'NewModel' in mm.DEFAULT_CONTEXT_LENGTHS
print(mm.DEFAULT_CONTEXT_LENGTHS.get('NewModel'))  # context size 확인
```

⚠️ Pitfall: dict 이름이 `MODEL_CONTEXT_LENGTHS`가 아닐 수 있다. AttributeError 나면 `dir(module)`로 실제 이름 확인 후 재시도.

### 6-3. Grep으로 미변경 reference 확인

```bash
# In-scope 파일에서만 — out-of-scope는 별도 보고
grep -l "M2.7" <in-scope-paths>
# → 모두 0건이어야 함 (단, legacy catalog 보존 entry는 예외)
```

## 7단계: Out-of-scope 보고 (사용자에게)

scope 밖에서 발견한 reference를 명확히 보고:

```
⚠️ 범위 밖 발견 (보고만, 변경 안 함):
  source/_agent/orchestrator/bot.py:213,219 — call_minimax()가 실제 API 호출에서
  model="MiniMax-M2.7" 사용 중. 사용자 4개 파일 scope에 안 들어갔고 orchestrator 계열은
  의도적 분리일 수 있어 그대로 둠. follow-up 필요하면 알려주세요.
```

→ 기본은 사용자가 "그래 그것도 바꿔" 또는 "그건 놔둬" 결정.

### 7-1. 예외: Drop-in 호환 입증 가능 시 즉시 patch

**판단 기준** (3가지 모두 충족 시 patch 진행, 사용자 결정 대기 불필요):
1. **Superset 관계**: 새 모델이 옛 모델의 superset (e.g. M3 ⊇ M2.7) → 출력/스펙 회귀 없음
2. **System prompt 불필요 변경**: 기존 prompt가 새 모델에서 그대로 유효
3. **max_tokens / 기타 파라미터 drop-in 호환**: 호출 시그니처 변경 불필요

**Patch + 보고 동시 진행**:

```
✅ 범위 밖 patch (drop-in 호환 입증, follow-up entry):
  source/_agent/orchestrator/bot.py:213,219 — M2.7 → M3 patch
  근거: M3 = M2.7 superset, system prompt / max_tokens 그대로 유효
  CHANGELOG 0.7.4에 sub-bullet follow-up entry 추가
  verification: grep M2.7 → 0건
```

**중요**: silently 바꾸는 게 아님 — **명시적 rationale과 CHANGELOG follow-up entry로 trail 남김**. 사용자가 "왜 바꿨어?" 물으면 근거 제시 가능. 이건 P2 (silent change) 위반이 아니라 P7 (justified follow-up) 패턴.

## 8단계: Memory 영구 저장

`mcp_memory(action='add', target='memory', ...)` 로:

```
2026-MM-DD: [Provider] 모델 업데이트 — [OldModel] → [NewModel] ([context]).
  소모 방식: [pricing change]. [N]개 파일 default 교체 완료.
  model_metadata.py catalog: [NewModel] = [context] 추가, [OldModel] entry는 legacy 보존.
  문서: [docs paths] 업데이트. ⚠️ 주의: [out-of-scope file]는 [reason] 그대로 둠.
```

## Pitfalls (실제 겪은 함정)

### P1: dict 이름 오타
- `model_metadata.py`의 dict는 `DEFAULT_CONTEXT_LENGTHS` (X `MODEL_CONTEXT_LENGTHS`)
- AttributeError 나면 `dir(module)`로 실제 attribute 확인

### P2: out-of-scope silent change
- 사용자 scope 밖의 파일을 silently 바꾸면 사용자의 의도(intent) 무시
- → 발견 시 항상 보고하고 결정 받기

### P3: catalog에서 legacy entry 삭제
- 옛 코드가 `model_metadata.lookup("OldModel")` 호출 중인데 catalog에서 지우면 fallback 실패
- → legacy는 **주석 달고 보존**, migrate 안 함

### P4: CHANGELOG에 append vs prepend
- Migration은 latest event이므로 **prepend** (맨 위)
- "최신 = 위" 컨벤션 유지
- **예외**: follow-up patch (out-of-scope 파일을 나중에 patch) → 기존 migration entry에 **sub-bullet** 추가 (별도 entry 만들지 않음)

### P5: Pydantic-style path
- `from P0-brainstem.agent.model_metadata import X` 안 됨 (Python은 hyphen module name 거부)
- importlib.util.spec_from_file_location()로 우회

### P6: Test fixture는 손대지 말 것
- `tests/test_model_normalize.py` 등에서 M2.7 사용 중 → backwards compat 테스트용
- → 의도적 보존, 변경 X

### P7: Justified follow-up (out-of-scope patch with rationale)
- P2 (silent change)와의 구분: silently 바꾸면 안 되지만, **drop-in 호환 입증 시 rationale 명시 + CHANGELOG follow-up entry 남기면 OK**
- 판단 기준 3가지 모두 충족 필요 (Section 7-1 참조)
- CHANGELOG sub-bullet 예시:
  ```
  - 영향 파일 14개: production code 5 + ...
    - source/_agent/orchestrator/bot.py (follow-up, 2026-MM-DD): call_minimax()의
      audit_log + client.messages.create() 두 곳을 M3로 정정. system prompt / max_tokens
      그대로 유효 (drop-in 호환).
  ```

### P8: Multi-source file copy (catalog/config가 여러 위치)
- Drewgent vault 구조상 같은 파일이 3~4개 위치에 존재 가능:
  - `source/<project>/agent/` (canonical, runtime이 import)
  - `P0-brainstem/agent/` (frozen policy, 직접 import 안 됨, catalog fallback lookup용)
  - `<project>/agent/` (top-level, 보통 symlink)
  - `build/lib/...` (setup.py build artifact, 보통 검증 제외)
- **함정**: migration이 frozen copy에만 적용되고 canonical은 그대로 → runtime catalog lookup이 옛 모델을 반환 → "migration 됐다"는 CHANGELOG와 실제 동작 불일치
- **함정 2**: top-level symlink가 옛 canonical을 가리키고 있을 수 있음 → migration은 새 canonical에 했는데 runtime은 옛 symlink를 import
- **대응 (Section 2-1 참조)**:
  - Step 2에서 `find`로 모든 복제본 위치 파악
  - Step 6-3 grep을 **모든 복제본**에 대해 수행
  - mtime 비교 — canonical이 가장 최신이어야 함
  - frozen copy는 절대 변경하지 않음 (변경됐다면 잘못된 위치로 patch된 것의 신호)

### P9: Provider model list ≠ catalog entry
- `model_metadata.py`는 **context size lookup** (기술적 capability, e.g. `1048576` = 1M)
- `drewgent_cli/models.py` (또는 provider config)는 **provider가 노출하는 모델 목록** (e.g. `["MiniMax-M3", "MiniMax-M3-highspeed"]`)
- **둘 다 migration 필요**, 하나만 해서는 안 됨:
  - catalog만 추가 → setup wizard/model picker에 안 뜸, 사용자가 못 고름
  - provider list만 추가 → context size lookup 실패 (catalog에 entry 없음) → fallback 또는 에러
- **함정**: CHANGELOG가 "model_metadata.py updated"라고만 쓰면 provider list 빠진 채 "Done" 처리
- **대응**:
  - Step 2 grep inventory에 provider list도 포함 (e.g. `drewgent_cli/models.py`, `config.yaml`의 model/provider 섹션)
  - Verification step 6-3에서 provider list grep도 별도 수행
  - Verification step 6-2 runtime test에서 setup wizard가 새 모델을 노출하는지 확인 (가능하다면)

### P13: Test file mirror drift (6-spot rule)
- **현상**: `tests/test_setup_model_selection.py` 같은 테스트 fixture는 보통 **top + source 두 곳에 mirror**됨. production flip scope에 빠져있어서 production은 M3로 flip됐는데 test는 M2.7에 pin된 채 방치되는 패턴. 같은 "M3 is default" claim이 production과 test 사이에 inconsistent.
- **왜 발생하는가**: 사용자가 "production code 14개 파일 flip" 같은 task scope를 줄 때 test 파일은 보통 빠져있음. 그러나 `git grep`이 mirror 양쪽을 모두 hit하면 한쪽만 고치고 "Done" 처리하기 쉬움.
- **6-spot rule (catalog claim 동기화 시)**:
  ```
  Production 4 spots:
    top/models.py
    top/setup.py (또는 top/drewgent_cli/setup.py)
    source/models.py
    source/setup.py

  Test 2 spots:
    top/tests/test_setup_model_selection.py
    source/tests/test_setup_model_selection.py

  → 6 spots 모두 새 모델 entry가 첫번째 또는 catalog list에 노출되는지 확인
  ```
- **대응**:
  - Step 2 grep inventory를 **mirror 양쪽**에 동시 수행:
    ```bash
    # Replace old-model-name with the actual model string being migrated
    # Example (M2.7→M3 migration):
    #   git grep -l "minimax-m2.7" -- 'source/drewgent-agent/drewgent_cli/' 'drewgent_cli/'
    #   git grep -l "minimax-m2.7" -- 'source/drewgent-agent/tests/' 'tests/'
    ```
  - Step 6-3 grep sweep에 test mirror 별도 추가:
    ```bash
    git grep -l "M2.7" -- 'tests/test_setup_model_selection.py' \
        'source/drewgent-agent/tests/test_setup_model_selection.py'
    ```
  - test 파일 수정 시 **fixture를 harden** — `assert first_model == "minimax-m3"` 같은 entry-position check로 미래 drift 자동 감지
- **drift impact**:
  - test가 옛 모델에 pin → CI는 옛 모델 fixture로 검증 → production은 새 모델로 동작 → "test는 통과하지만 production은 검증 못 됨" 상태
  - setup wizard E2E 테스트가 M3 안 뜨는 채로 통과 → 사용자가 M3 못 고름
- **flip 후 검증 한 줄 명령**:
  ```bash
  # 6 spots 일관성 한 번에 확인
  for p in drewgent_cli/models.py drewgent_cli/setup.py \
           source/drewgent-agent/drewgent_cli/models.py source/drewgent-agent/drewgent_cli/setup.py \
           tests/test_setup_model_selection.py source/drewgent-agent/tests/test_setup_model_selection.py; do
    echo "=== $p ==="; grep -E "minimax-m3|MiniMax-M3" "$p" | head -3
  done
  ```

## Verification Checklist

- [ ] Production code N개 syntax check OK
- [ ] model_metadata.py catalog에 NewModel entry 존재, context size 정확
- [ ] Legacy model entry 보존 (주석 포함)
- [ ] Docs N개 업데이트 완료
- [ ] Reference doc 작성 (필요시)
- [ ] CHANGELOG.md prepend 완료
- [ ] In-scope grep에서 OldModel 참조 0건 (legacy catalog 보존 entry 제외)
- [ ] Out-of-scope 후보 사용자 보고 완료
- [ ] Follow-up patch 적용 시 **재grep**으로 out-of-scope 파일도 0건 확인
- [ ] Follow-up patch 적용 시 CHANGELOG sub-bullet entry 추가 확인
- [ ] Memory 영구 저장 완료 (follow-up 결정 포함)
- [ ] **Multi-source catalog/config 복제본 모두 검색** — `find`로 모든 위치 파악, 각 위치에 migration 적용 확인
- [ ] **Provider model list (`drewgent_cli/models.py`) 별도 grep** — catalog만 추가하고 provider list 빠뜨리지 않았는지
- [ ] **Top-level symlink freshness** — `ls -la`로 symlink가 최신 canonical을 가리키는지
- [ ] **Test file mirror sweep** (P13 / Pattern E) — `tests/test_setup_model_selection.py` (top + source 2 spots)가 새 모델 첫 entry로 flip됐는지, `git grep`로 2 spots 모두 hit 확인
- [ ] **6-spot rule 검증** — flip 후 production 4 + test 2 = 6 spots 모두 새 모델 노출 확인 (`git grep -l "minimax-m3" -- '*.py' | wc -l` ≥ 4 + 같은 명령 `tests/` 한정 ≥ 2)

## 9단계 (Audit Mode): 기존 migration claim 검증

사용자가 *"M3로 마이그레이션 됐다는데 진짜?"* 식으로 **이미 claimed된 migration의 진실성**을 물을 때 쓰는 모드. 새 migration을 하는 게 아니라 **filesystem = truth** 원칙으로 기존 claim을 검증.

### 9-1. 트리거 신호

- "선언되어 있는데 실제로 됐는지 확인해줘"
- "M3 / GPT-5 / Claude 4.6 등 새 모델이 추가됐다고 들었는데 적용된 거야?"
- CHANGELOG / memory entry는 존재하는데 실제 session header가 옛 모델인 경우
- "auxiliary는 바뀌었는데 인터랙티브 세션은 그대로" 같은 inconsistency 제보

### 9-2. Audit 절차 (migrate 안 하고 verify만)

**Step 1**: noise 제거하고 양쪽 모델명 동시 grep

```python
# 핵심 패턴: 옛 + 새 모델명을 동시에
PATTERNS = {
    "M2.7": re.compile(r'"MiniMax-M2\.7"|MiniMax-M2\.7(?!-h)|minimax-m2\.7'),
    "M2.7-highspeed": re.compile(r"MiniMax-M2\.7-highspeed"),
    "M3": re.compile(r"MiniMax-M3\b|minimax-m3"),
    ...
}

# exclude noise
EXCLUDE_PARTS = {"sessions", ".git", "node_modules", "Library", "pastes", "archive", ...}
```

**Step 2**: "옛 모델이 아직 어디 살아있나"만 정렬해서 표시. 75개 파일 406 hits 같은 큰 숫자 나오면 정상 — 75개 중 진짜 코드/설정 vs 캐시/문서/주석 분류가 핵심.

**Step 3**: 분류 — 실제 runtime 영향도 순

| 우선순위 | 파일 종류 | 영향 |
|---|---|---|
| **P0 (블로커)** | `config.yaml`, `P5-ego/config/config.yaml` | main runtime + cheap/fallback/search 모델 — 이게 M2.7이면 **지금 session 그대로 M2.7** |
| **P1 (보이는 UI)** | `drewgent_cli/models.py`, `drewgent_cli/setup.py` | provider catalog — `/model` picker에 M3 안 뜸 |
| **P1 (catalog)** | `agent/model_metadata.py` | context size lookup — entry 없으면 fallback (보통 옛 모델 사이즈) |
| **P2 (테스트)** | `tests/test_*model*.py` | 검증 게이트 — 그대로 두면 신규 catalog mismatch |
| **P3 (문서)** | `CHANGELOG.md`, `website/docs/...`, `skills/.../SKILL.md` | trail only — declare만 돼있어도 OK |

**Step 4**: Session header = ground truth

```
대화 시작 헤더의 "Model: MiniMax-M2.7"이 절대적인 ground truth.
config.yaml에 M3라고 적혀있어도 session header가 M2.7이면 실제로는 M2.7.
```

→ header가 M2.7이면 config L3 grep 결과는 M3여야 정상. **불일치 = bug**.

### 9-3. Claim vs Reality 갭을 찾을 때 자주 보는 패턴

**Pattern A — "auxiliary only"** (가장 흔함)
- auxiliary_client.py, scripts/*, plugins/memory/* → M3 patch됨
- config.yaml, models.py catalog, setup.py → M2.7 그대로
- CHANGELOG는 "auxiliary N개 patched"만 강조 → runtime 미변경
- **진짜 영향**: cron worker는 1M context, 인터랙티브는 204K context → inconsistency

**Pattern B — "frozen copy only"**
- `P0-brainstem/agent/model_metadata.py`에만 M3 entry 추가됨
- canonical `source/.../agent/model_metadata.py`는 그대로
- runtime이 import하는 건 canonical이라 M3 못 씀
- **대응**: `find`로 두 위치 다 hit 확인 후 canonical 우선 patch

**Pattern C — "catalog yes, provider list no"**
- `model_metadata.py`에 M3: 1048576 추가됨
- `drewgent_cli/models.py`의 `minimax: [...]` list에는 M3 없음
- 사용자가 `/model`로 minimax provider 선택해도 M3 안 보임
- **대응**: provider list도 별도 patch 필요 (P9 pitfall과 연결)

**Pattern D — "config L3 lowercase vs proper case"**
- `config.yaml` L3: `model: minimax-m2.7` (소문자) — historical finding (M2.7→M3 migration audit)
- 다른 곳들: `MiniMax-M2.7` (proper case) — historical finding
- LLM API가 case-insensitive면 동작은 OK지만 catalog 표기와 mismatch
- → M3 마이그레이션 시 catalog 표기 형식 (`MiniMax-M3` proper case) 통일 결정 (역사적 기록)

### 9-4. Audit 결과 보고 템플릿

```
실제 상태:

M3로 이미 옮겨진 곳:
- agent/auxiliary_client.py L67-68: minimax → MiniMax-M3  ✅
- scripts/run_kanban_worker.py L123: MiniMax-M3  ✅
- ...

M2.7에 그대로 박혀있는 곳:
- config.yaml L3: `model: minimax-m2.7`  ❌ (historical — was the main runtime config at audit time)
- config.yaml L58, L81...
- P5-ego/config/config.yaml 동일 4곳  ❌
- drewgent_cli/models.py L146-152: provider catalog에 M3 없음  ❌
- drewgent_cli/setup.py L121-122: 동일  ❌
- agent/model_metadata.py L117: provider-level 204800 (M2.7 사이즈)  ❌
- **tests/test_setup_model_selection.py (top + source 2 spots)**: 첫 entry `minimax-m2.7`  ❌ (historical audit finding — M2.7→M3 migration)
```

→ 사용자에게 어느 옵션으로 fix할지 결정 요청 (전체 flip / selective / noop)

### 9-5. Pattern E — "test files pinned" (6-spot drift)
- **증상**: production은 M3, test는 M2.7 — **같은 "M3 is default" claim이 production과 test 사이에서 inconsistent**
- **발견 방법**:
  ```bash
  # test mirror sweep (historical: M2.7→M3 migration)
  # git grep -l "minimax-m2.7" -- 'tests/test_*' 'source/drewgent-agent/tests/test_*'
  # → 1건이라도 hit하면 production flip scope가 test에 미치지 못한 것
  ```
- **왜 중요한가**: test가 M2.7에 pin돼있으면
  - CI는 M2.7 fixture로 setup wizard 검증 → 통과
  - 사용자가 M3를 못 고르는 상태가 통과된 채 "OK"로 마감
  - production이 M3로 flip된 순간 E2E drift 발생
- **대응**: 6-spot rule (P13 pitfall 참조) — 4 production + 2 test spots 모두 sweep
  - flip 후 `git grep -l "minimax-m3" -- '*.py' | wc -l` ≥ 4 (production mirror 확인)
  - 같은 명령을 `tests/` 한정으로: `git grep -l "minimax-m3" -- 'tests/test_*' 'source/.../tests/test_*' | wc -l` ≥ 2 (test mirror 확인)
- **Test fixture harden (회피 패턴)**: 단순히 모델명을 추가하는 게 아니라 **첫 entry 체크**로 미래 drift 자동 감지:
  ```python
  # Before: 모델이 list에 있는지 정도만 체크
  assert "minimax-m3" in models

  # After: 첫 entry가 새 모델인지 체크
  assert models[0] == "minimax-m3"  # drift 발생 시 즉시 fail
  ```

### 9-5. Pattern E — "test files pinned" (6-spot drift)
- **증상**: production은 M3, test는 M2.7 — **같은 "M3 is default" claim이 production과 test 사이에서 inconsistent**
- **발견 방법**:
  ```bash
  # test mirror sweep (historical: M2.7→M3 migration)
  # git grep -l "minimax-m2.7" -- 'tests/test_*' 'source/drewgent-agent/tests/test_*'
  # → 1건이라도 hit하면 production flip scope가 test에 미치지 못한 것
  ```
- **왜 중요한가**: test가 M2.7에 pin돼있으면
  - CI는 M2.7 fixture로 setup wizard 검증 → 통과
  - 사용자가 M3를 못 고르는 상태가 통과된 채 "OK"로 마감
  - production이 M3로 flip된 순간 E2E drift 발생
- **대응**: 6-spot rule (P13 pitfall 참조) — 4 production + 2 test spots 모두 sweep
  - flip 후 `git grep -l "minimax-m3" -- '*.py' | wc -l` ≥ 4 (production mirror 확인)
  - 같은 명령을 `tests/` 한정으로: `git grep -l "minimax-m3" -- 'tests/test_*' 'source/.../tests/test_*' | wc -l` ≥ 2 (test mirror 확인)
- **Test fixture harden (회피 패턴)**: 단순히 모델명을 추가하는 게 아니라 **첫 entry 체크**로 미래 drift 자동 감지:
  ```python
  # Before: 모델이 list에 있는지 정도만 체크
  assert "minimax-m3" in models

  # After: 첫 entry가 새 모델인지 체크
  assert models[0] == "minimax-m3"  # drift 발생 시 즉시 fail
  ```

### 9-5. Pattern E — "test files pinned" (6-spot drift)
- **증상**: production은 M3, test는 M2.7 — **같은 "M3 is default" claim이 production과 test 사이에서 inconsistent**
- **발견 방법**:
  ```bash
  # test mirror sweep (historical: M2.7→M3 migration)
  # git grep -l "minimax-m2.7" -- 'tests/test_*' 'source/drewgent-agent/tests/test_*'
  # → 1건이라도 hit하면 production flip scope가 test에 미치지 못한 것
  ```
- **왜 중요한가**: test가 M2.7에 pin돼있으면
  - CI는 M2.7 fixture로 setup wizard 검증 → 통과
  - 사용자가 M3를 못 고르는 상태가 통과된 채 "OK"로 마감
  - production이 M3로 flip된 순간 E2E drift 발생
- **대응**: 6-spot rule (P13 pitfall 참조) — 4 production + 2 test spots 모두 sweep
  - flip 후 `git grep -l "minimax-m3" -- '*.py' | wc -l` ≥ 4 (production mirror 확인)
  - 같은 명령을 `tests/` 한정으로: `git grep -l "minimax-m3" -- 'tests/test_*' 'source/.../tests/test_*' | wc -l` ≥ 2 (test mirror 확인)
- **Test fixture harden (회피 패턴)**: 단순히 모델명을 추가하는 게 아니라 **첫 entry 체크**로 미래 drift 자동 감지:
  ```python
  # Before: 모델이 list에 있는지 정도만 체크
  assert "minimax-m3" in models

  # After: 첫 entry가 새 모델인지 체크
  assert models[0] == "minimax-m3"  # drift 발생 시 즉시 fail
  ```

### 9-6. Pitfall (audit mode 전용)

- **P10: CHANGELOG "Done"을 신뢰하지 말 것** — CHANGELOG는 intent 기록, reality 아님. header가 옛 모델이면 grep으로 옛 모델이 어디 살아있는지 직접 확인. `禁filesystem_truth`의 migration-domain 적용.
- **P11: session header가 ground truth** — config 다 바꿔도 session 재시작 전에는 옛 모델. header = "현재 실제로 호출되는 모델"의 single source of truth.
- **P12: noise 카테고리 분리 필수** — sessions/ JSON 한 개가 grep 50+ hits 만들어내서 진짜 변경 위치 묻힘. EXCLUDE_PARTS로 먼저 prune 안 하면 audit이 사실상 불가능.

## Related

- [[P4-cortex/growth/INTEGRATION_PROTOCOL]] — 3-file integration 원칙
- [[P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁/禁task_qa_gate.neuron]] — verification 단계
- [[P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁/禁karpathy_coding_principles.neuron]] — surgical changes, scope 준수
- [[P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁/禁filesystem_truth.neuron]] — audit mode의 governance 근거 (CHANGELOG 신뢰 X, filesystem = truth)

## Related

- [[P4-cortex/growth/INTEGRATION_PROTOCOL]] — 3-file integration 원칙
- [[P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁/禁task_qa_gate.neuron]] — verification 단계
- [[P0-brainstem/brain/Drewgent-brain/P0-brainstem/禁/禁karpathy_coding_principles.neuron]] — surgical changes, scope 준수
