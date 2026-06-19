# Comprehensive Report (대세월운 종합 리포트) Output Schema

## JSON Structure

```typescript
{
  layer0: string,      // 외재 조건
  layer1: string,      // 신체·에너지 조건
  layer2: string,      // 주의·정서·애착 조건
  layer3: string,      // 의미·관계·행동 조건
  synthesis: string    // 종합 요약
}
```

Each value is a flat string containing labeled paragraphs in "라벨명: 내용" format, separated by blank lines.

## Ontology Layers

### L0 — 외재 조건 (External Conditions)
- 시기 (timing)
- 역할 (role)
- 돈 (money)
- 권력 (power)
- 가족 (family)
- 직업 (career)
- 사회환경 (social environment)
- 사건 (events)

### L1 — 신체·에너지 조건 (Physical & Energy Conditions)
- 수면 (sleep)
- 회복 (recovery)
- 각성 (arousal)
- 피로 (fatigue)
- 건강 (health)
- 감각 (senses)
- 생리 리듬 (biological rhythm)

### L2 — 주의·정서·애착 조건 (Attention, Emotion & Attachment)
- 주의력 (attention)
- 실행기능 (executive function)
- 충동 (impulse)
- 불안 (anxiety)
- 회피 (avoidance)
- 상처 (wounds)
- 내적작동모델 (internal working model)

### L3 — 의미·관계·행동 조건 (Meaning, Relationship & Behavior)
- 욕망 (desire)
- 자기서사 (self-narrative)
- 역할 선택 (role selection)
- 관계 반응 (relationship response)
- 실제 행동 (actual behavior)
- 개입 레버 (intervention levers)

## Reasoning Chain (per layer, 6 steps)

Each layer0–layer3 string must include these 6 labeled sections in order:

1. **무엇이 변했는가** — 구체적인 오행/합충/신살 변화 (대운·세운·월운 각 층위를 모두 고려)
2. **그 변화가 어떤 경험으로 나타나는가** — 실제 체감하는 삶의 영역과 구체적 장면
3. **기본 반응은 무엇인가** — 무의식적으로 나오는 반응 패턴과 경향
4. **더 나은 반응 레버는 무엇인가** — 의식적으로 선택할 수 있는 대안 행동과 대처법
5. **그 반응이 어떤 결과를 만들 가능성이 있는가** — 단기 결과와 장기 영향 예측
6. **근거등급은 무엇인가** — 온톨로지 근거 강도 (확실/강함/중간/약함/추정 중 하나)

## Synthesis Section

The `synthesis` key is a cross-cutting summary with 4 items:

- 전체 관점에서 무엇이 변했는가
- 가장 영향력이 큰 변화와 그 이유
- 전체적으로 권장하는 대응 레버
- 예상되는 단기/장기 결과

## Temporal Dimension Handling

Unlike the old structure (which had separate layer1=대운, layer2=세운, layer3=월운), the temporal dimensions are now **embedded within each ontology layer's reasoning chain**. The "무엇이 변했는가" step in each layer should address all three time horizons:

- 대운 (10-year great fortune)
- 세운 (annual fortune)
- 월운 (monthly fortune)

## Data Flow

```
명식 사주(person) 
 → saju API + persona API fetch 
 → getOntologyContext('analyze') + buildSystemPrompt(keys)
 → callLLMJson(env, sys, userContent, "layer0,layer1,layer2,layer3,synthesis", 4000, 0.25)
   → response_format: { type: "json_object" }
   → validates via hasRequiredKeys (each key must be non-empty string)
 → polishReport(report, env, keys) (윤문, POLISH_SYSTEM_PROMPT)
   → 내부 callLLMJson 실패 시 catch → 원문 그대로 반환 (무음 실패)
   → LLM 응답 성공해도 merge 조건(val.length >= orig.length * 0.7) 탈락 시 변경 없음
 → return { success: true, data: report }
```

### polishReport merge validation pitfall

```typescript
// comprehensive-report.ts line 128-133
for (const key of keyList) {
    const orig = report[key];
    const val = polished[key];
    if (typeof val === "string" && val.trim().length > 50 
        && val.trim().length >= (typeof orig === "string" ? orig.length * 0.7 : 0)) {
        merged[key] = val;  // ← 70% 미만이면 이 줄 실행 안 됨
    }
}
return merged;
```

윤문 LLM이 성공해도 polished 텍스트가 원문보다 30% 이상 짧아지면 merge가 reject된다. AI 톤 제거가 문장을 간결하게 만드는 작업이라 이 조건에 자주 걸린다. 변경이 전부 reject되면 `merged`는 원본 복사본에 불과하므로 윤문이 없었던 것처럼 보인다. catch 블록 로그도 없음.

**진단 방법:** wrangler dev 로그에서 `[Comprehensive]` prefix 확인. DeepSeek/NVIDIA 에러가 찍히면 provider 실패. 안 찍히면 merge reject.

## Frontend Rendering

```javascript
// ReportComprehensiveView.js
const layerKeys = ['layer0','layer1','layer2','layer3','synthesis'];
const titles = ['외재 조건', '신체·에너지 조건', '주의·정서·애착 조건', '의미·관계·행동 조건', '종합 — 무엇이 변했는가'];
const subLabels = [
  '시기, 역할, 돈, 권력, 가족, 직업, 사회환경, 사건',
  '수면, 회복, 각성, 피로, 건강, 감각, 생리 리듬',
  '주의력, 실행기능, 충동, 불안, 회피, 상처, 내적작동모델',
  '욕망, 자기서사, 역할 선택, 관계 반응, 실제 행동, 개입 레버',
  '4개 레이어를 관통하는 핵심 변화와 권장 대응 방향'
];
// Each card: L0 — 외재 조건 / sub-label / formatContent(content)
```

The existing `formatContent()` method splits by ":" to render labels in bold and descriptions in secondary color.

## History

- **2026-06-12**: Changed from 3 temporal layers (layer1=대운, layer2=세운, layer3=월운) to 4 ontology layers (layer0~3) + synthesis
- **2026-06-12**: Auto-submit on mount REMOVED. User must click Submit to trigger API call.
- Prior structure: temporal-only, each layer was a single string with ontology content mixed in

## Route & Purchase Notes

- The `#/report-luck` route also serves this view (both `#/report-comprehensive` and `#/report-luck` → ReportComprehensiveView)
- Purchase keys: `comprehensive` AND `luck` are both accepted. Payment redirect uses `type=luck` for backward compatibility.
- After payment: user sees the form with a "✅ 이미 결제 완료" message. They must click Submit to generate the report. No auto-generation.
