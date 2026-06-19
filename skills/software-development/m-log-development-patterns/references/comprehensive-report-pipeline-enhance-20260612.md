# Comprehensive Report Pipeline Enhancement (2026-06-12)

## Changes Made

### 1. Source Data: Raw JSON → Structured Narrative

**Problem:** LLM received `{ saju: saju.data, persona: persona }` as raw JSON. Had to parse array structures to find current luck. No pre-computed directionality.

**Fix:** Import `analyze()` from `../analysis/engine`, run after saju data fetch, build structured source with explicit sections:

```typescript
const sourceLines = [
  '[사주 기본 정보]',
  `일간(일원): ${dayMaster}`,
  `사주 기둥: 연간(...) 연지(...) 월간(...) ...`,
  `격국: ${gyeokguk}`, `용신: ${yongsin}`,
  '',
  '[오행 점수]', `목: ${wood} 화: ${fire} ...`,
  '[기질 스펙트럼]', `위치: ${position} (값: ${totalValue})`,
  '[합충 관계]', ...hapChung.map(...),
  '',
  '[현재 대운 (10년 단위 큰 흐름)]',
  `간지: ${dwGanji} (${startAge}세 시작, 방향: ${direction})`,
  `대운 결합 오행: 목(${l1.combinedOhang.wood}) 화(...) ...`,
  `대운 스펙트럼 변화량: ${l1.spectrumDelta} (방향: ${l1.direction})`,
  '',
  '[현재 세운 (올해의 흐름)]',
  `간지: ${swGanji} (${year}년)`,
  `세운 결합 오행: ...`,
  `대운-세운 관계: ${l2.relation}`,
  `올해 테마: ${l2.theme}`,
  '',
  '[현재 월운 (이번 달의 흐름)]',
  `간지: ${wlGanji} (${month}월)`,
  '',
  '[페르소나]', `주 오행: ${mainOhang}`, `페르소나: ${name}`,
].filter(Boolean).join('\n');
```

### 2. Hanja → Hangul Conversion in Source Data

Added STEM_MAP + BRANCH_MAP + toHangul() helper to convert all hanja ganji in the structured source data to hangul before passing to LLM:

```typescript
const STEM_MAP: Record<string, string> = {
  '甲':'갑','乙':'을','丙':'병','丁':'정','戊':'무','己':'기',
  '庚':'경','辛':'신','壬':'임','癸':'계'
};
const BRANCH_MAP: Record<string, string> = {
  '子':'자','丑':'축','寅':'인','卯':'묘','辰':'진','巳':'사',
  '午':'오','未':'미','申':'신','酉':'유','戌':'술','亥':'해'
};
const toHangul = (s: string) =>
  (s || '').split('').map(c => STEM_MAP[c] || BRANCH_MAP[c] || c).join('');
```

Applied to: saju pillars dayMaster, all ganji values, daewoon/saewoon/wolun ganji.

### 3. Timeout: 30s → 55s

`callLLMJson` default timeout `30000` → `55000`. Matches dating-report.

Observed API call times:
- 1st call: 57,743ms total (was hitting 30s limit)
- 2nd call: 34,995ms (same user)

### 4. max_tokens: Main 4000→5000, Polish max 4500→6000

Main LLM call: `4000` → `5000`
Polish token formula: `Math.min(4500, ...)` → `Math.min(6000, ...)`, base `Math.max(1200, ...)` → `Math.max(1500, ...)`, additive `+300` → `+500`

### 5. Polish Prompt: 5 patterns → 14 patterns

Added 절대 보존 항목 section + A-2, A-8, A-9, D-2, D-3, H, I, C-11 patterns. Now matches dating-report's coverage.

### 6. Main Prompt: Added `## 분석 필수 규칙` + `## 표현 규칙`

- 400자 minimum per section
- At least 1 data reference per section
- 사주→일상 언어 번역 instruction
- "가능성이 있습니다" ≤ 3 times
- 각 라벨 문단 1~3문장
- Output proofreading (조사 누락, 번역투 교정)
- **한자 금지**: 천간/지지를 한글로만 표기 (갑을병정..., 자축인묘...)
- **문단 시각화**: 6단계 사이 빈 줄, 각 단계 첫 문장 핵심 요약, 전환어 금지

**한자 금지 배경:** 유저가 대세월운 리포트 출력에서 `辛卯(편관-비견)`, `乙辛충` 등 한자를 지적. 가독성 저하 및 전문 용어 장벽. 소스 데이터의 `toHangul()`로 한글 변환 후 전달.

### 7. Logging: console.log/console.warn added at every pipeline step

| Log point | Message |
|-----------|---------|
| LLM call start | `[Comprehensive] LLM call starting (maxTokens=5000, timeout=55000ms)` |
| DeepSeek success | `[Comprehensive] DeepSeek OK (12345ms)` |
| DeepSeek fail | `[Comprehensive] DeepSeek API error (status) after ...ms: ...` |
| NVIDIA fail | `[Comprehensive] DeepSeek error after ...ms: ...` |
| Polish start | `[Comprehensive] Polish starting (5 fields, 4123 chars, 3500 tokens)` |
| Polish merge | `[Comprehensive] Polish done: 3/5 fields merged` |
| Polish fail | `[Comprehensive] Polish failed: ... Returning original.` |

### 8. Files Changed

- `src/controllers/comprehensive-report.ts` — all pipeline changes
- NAS: `SynologyDrive-Log-Project/m-log/src/controllers/comprehensive-report.ts`

### 9. Key Finding: Source Data Was the Root Cause of "딱딱한 문장"

The user initially attributed stiff writing to the prompt being too rigid. The actual root cause was that **the LLM had to work too hard to understand the data** — raw JSON without structure. Once the engine's pre-computed values were passed as labeled narrative, the LLM could focus on writing style instead of data parsing.

**Lesson:** When LLM output reads like a template being filled in, the data is the problem — not the prompt. Fix the data structure first, then adjust the prompt.

### 10. Remaining (not yet implemented): Paragraph visualization via AiView card structure

The user requested the comprehensive report's render structure follow the "나의 Log 리포트" (ReportAiView) card deck pattern:

```
BEFORE (current comprehensive): glass-panel card with formatContent() label pairs
AFTER (proposed): card deck with bg-secondary, border-radius, emoji section titles
```

Each layer card would have the same visual structure as AiView:
```html
<div style="background:var(--bg-secondary);padding:1.25rem;border-radius:8px;border:1px solid var(--border-color);">
  <strong style="color:var(--sys-primary);">📈 외재 조건 (L0)</strong>
  <div style="color:var(--text-secondary);margin-top:0.5rem;">
    ${formatContent(content)}
  </div>
</div>
```

Not implemented yet — the user confirmed the approach is correct but the task was deferred.
