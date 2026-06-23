---
title: - skills/project/kis-autonomous-bot-debug/SKILL
type: skill
space: outcome
tags: [outcome]
created: 2026-05-20
updated: 2026-05-20
links:
  - "[[@action/skills/SKILL-INDEX]]"
---

space: outcome
type: document

# Skill Gym

Drewgent 에이전트의 스킬 활용을 주기적으로 분석하여 **미사용 스킬의 활용 가능성을 추천**하고, **삭제 고려 대상을 표시**하는 자기反省 시스템.

## 목적

1. **인지적 사각지대 해소** — 사용자가 모르는 스킬을 "있었네요"로 전환
2. **오케스트레이터 편향 보완** — routing 바이어스를 의외성 메커니즘으로 보완
3. **스킬 건강도 감사** — 방치된 스킬의 유지 가치를 정기적으로 검토

## 용어 정의

| 용어 | 정의 |
|------|------|
| **미사용 스킬** | skill_view()로 최근 로드된 적 없는 스킬 (state.db 기준) |
| **후보 풀 (candidate pool)** | never_used + used_old (7일 이상 미사용) 스킬 |
| **관련성 점수 (relevance)** | 0.0~1.0. Drewgent 메모리 + 세션 키워드 vs 스킬 description 매칭 |
| **의외성 점수 (surprise)** | 0.0~1.0. 최근 사용 스킬과 카테고리 거리가 클수록 높음 |
| **종합 점수 (combined)** | relevance × 0.6 + surprise × 0.4 |
| **삭제 후보** | never_used 스킬 중 파일 크기 큰 순 (단순히 크다고 지우는 게 아님) |

## Phase 1 — Weekly: 미사용 스킬 추천

### 실행 방법

```
python3 ~/.drewgent/skills/skill-gym/scripts/gather_skill_data.py --since-days 30
```

출력된 JSON을 분석하여 Discord 보고서를 작성합니다.

### 보고서 작성 규칙

**보고서는 반드시 다음 구조를 따릅니다:**

```
## 🏋️ Skill Gym Weekly Report — {날짜}

**프로젝트 맥락 키워드:** [상위 5개]
**대상 기간:** 최근 {since_days}일

### 📊 현황
- 총 스킬: {total_skills}
- 사용 중 (7일 이내): {used_recently}
- 장기 미사용 (7일 초과): {used_old}
- 한 번도 사용 안 함: {never_used}

### 🎯 추천 스킬 (종합 점수 순, 상위 6개)

---

#### [{index}. {name}] **{category}**

| 지표 | 점수 |
|------|------|
| 관련성 | {relevance}/1.0 |
| 의외성 | {surprise}/1.0 |
| 종합 | {combined}/1.0 |
| 마지막 사용 | {last_used or '없음'} |

**설명:** {description}

**활용 시나리오:** {scenario}

---

### 💡 활용 방법

스킬을 로드하려면:
```
/{slugified_name}
```

### ⚠️ 참고
- 의외성 점수는 카테고리 거리를 기반으로 랜덤 변동이 있습니다
- 추천은 판단 보조 도구이며, 최종 판단은 사용자에게 있습니다
- 관련성 점수는 Drewgent 메모리 + 세션 키워드 기반입니다
```

### 조합 점수 산출 로직

```python
combined_score = relevance * 0.6 + surprise * 0.4

# 관련성 (0.0~1.0)
- Drewgent memories (MEMORY.md, insights/) + 최근 세션 JSONL에서 키워드 추출
- 각 스킬의 name + description + category + tags 매칭
- 매칭률 × 2 (너무 낮으면 부스트)

# 의외성 (0.0~1.0)
- 최근 14일 내 사용한 스킬의 카테고리 집합 S_used 정의
- 후보 스킬의 카테고리가 S_used와 겹치면 → surprise 낮음 (0.1~0.4)
- 후보 스킬의 카테고리가 S_used와 다르면 → surprise 높음 (0.6~1.0)
- 카테고리 정보 없으면 랜덤 (0.4~0.9)
```

### Phase 2 — Monthly: 삭제 후보 표시

**매월 1회, 삭제 고려 대상을 "표시만" 합니다.**

```
### 🗑️ 삭제 고려 대상 (현재 미사용 스킬, 파일 크기순)

> ⚠️ 아래 스킬은 한 번도 사용된 적이 없으며 용량이 큽니다.
> 최종 판단은 사용자의 몫입니다. Drewgent가 임의로 삭제하지 않습니다.

| 스킬 | 카테고리 | 설명 | 크기 |
|------|---------|------|------|
| {name} | {category} | {desc[:50]}... | {size}KB |

```

## 데이터 소스

```
┌─────────────────────────────────────────────────────────┐
│  데이터 소스                                              │
│                                                         │
│  state.db (messages.tool_calls)                        │
│    → skill_view(name=...) 호출 파싱                      │
│    → timestamp, session_id 추출                        │
│    → Schema v6 기준: 2026-04-08 이후 기록               │
│                                                         │
│  ~/.drewgent/memories/                                  │
│    → MEMORY.md (키워드 추출)                            │
│    → insights/ recent 노트들                           │
│    → entities/ (환경/선호도 맥락)                      │
│                                                         │
│  ~/.drewgent/sessions/session_*.json                   │
│    → 최근 10개 세션에서 user 메시지 키워드 추출         │
│                                                         │
│  ~/.drewgent/skills/*/SKILL.md                        │
│    → 전체 스킬 목록 + frontmatter(description, category, tags) │
└─────────────────────────────────────────────────────────┘
```

## 제한 사항

1. **state.db는 2026-04-08 이후 기록** — 그 이전 사용 이력은 추적 불가
2. **관련성 점수는 키워드 매칭 기반** — Ollama 연동 시 semantic 검색으로 확장 가능 ⭐
3. **의외성: 경로 기반 카테고리 단위** — frontmatter `category` 없으면 `skills/{category}/{skill}` 경로에서 추출
4. **삭제 권유가 아님** — 최종 판단은 사용자. Drewgent는 표시만 함

## Ollama 연동 (향후 확장)

Ollama가 연결되면 relevance 점수를 semantic 검색으로 보강할 수 있습니다:

```python
# compute_relevance_score()에 아래 패턴으로 끼워넣기:
import requests

def _get_ollama_embedding(text: str, model: str = "nomic-embed-text") -> list[float]:
    """Ollama embedding API 호출"""
    resp = requests.post(
        "http://<OLLAMA_HOST>:11434/api/embeddings",
        json={"model": model, "prompt": text}
    )
    return resp.json()["embedding"]

def compute_relevance_score_ollama(skill: dict, project_texts: list[str]) -> float:
    """Ollama 기반 semantic 관련성 (설정 시 활성화)"""
    skill_text = f"{skill['name']} {skill['description']} {' '.join(skill.get('tags', []))}"
    skill_emb = _get_ollama_embedding(skill_text)
    scores = [cosine_similarity(skill_emb, _get_ollama_embedding(t)) for t in project_texts]
    return max(scores) if scores else 0.0
```

Ollama 연결이 확인되면 스크립트에 `--use-ollama` 플래그를 추가하고 함수를 교체합니다.

## 트리거 조건

| 상황 | 행동 |
|------|------|
| Cron job (주 1회, 월요일 09:00) | phase 1 추천 보고서 생성 |
| Cron job (월 1회,，每月第一周一 09:00) | phase 2 삭제 후보 보고서 생성 |
| 사용자가 `/skill-gym` 호출 | 즉시 분석 + 보고서 생성 |

## 스킬 설치 확인

이 스킬이 정상 작동하려면:

1. `~/.drewgent/state.db`에 읽기 권한
2. `~/.drewgent/skills/`에 스킬 목록 존재
3. `~/.drewgent/memories/`에 MEMORY.md 존재

스크립트를 직접 실행하여 확인할 수 있습니다:

```bash
python3 ~/.drewgent/skills/skill-gym/scripts/gather_skill_data.py | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f\"총 스킬: {d['summary']['total_skills']}\")
print(f\"후보 풀: {d['summary']['candidate_pool']}\")
print(f\"추천 상위 3:\")
for r in d['recommendations'][:3]:
    print(f\"  {r['name']} (combined={r['combined_score']})\")
"
```

## Related
- [[@action/skills/SKILL-INDEX]]
