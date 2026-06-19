# M-LOG Analysis Pipeline

## Architecture Overview

The m-log application processes saju (四柱) data through a 4-layer analysis pipeline:

## Data Flow

```
PDC (PersonalDateCalculator, external API)
  ↓ raw JSON (pillars, tenGods, daewoon cycles, saewoon/wolun)
worker.ts (thin router)
  ↓ delegates to controller + injects analysisReport
src/controllers/saju.ts (handleAnalyze → fetches PDC)
src/analysis/engine.ts (analyze → computes what PDC doesn't)
  ↓ enriches response with analysisReport
Frontend (renderer.js — passive renderer)
```

## Report Pipeline

```
/analyze    → PDC data + analysisReport (used by SPA dashboard)
/report     → PDC data + just5Data injection → LLM (DeepSeek) → log report
/report/comprehensive → PDC data → LLM → polish → monthly report
/report/dating → PDC data + engine/compatibility → LLM → dating report
```

## L0~L3 Analysis Layers

| Layer | Name | Components | Purpose |
|-------|------|-----------|---------|
| L0 | 원국 (Natal) | 4 pillars (year, month, day, time) | Lifetime baseline — ohang scores, spectrum, hapChung, tenGods |
| L1 | 대운 (Decade) | L0 + current daewoon pillar | 10-year shift — combined ohang/spectrum, delta direction |
| L2 | 세운 (Annual) | L0 + L1 + current saewoon pillar | Year theme — daewoon-saewoon relationship, delta direction |
| L3 | 월운 (Monthly) | Current month's wolun entry from PDC | Monthly guidance — season, impulsiveness (extracted from PDC) |

## Persona Determination

The persona is determined by the **dominant element** (highest ohangScore), with 4 versions per element based on the dominant sheng/ke relationship:

```typescript
const dominantOhang = sorted ohangScore entries[0];
const personaData = PERSONA.personas[dominantOhang];  // 5 base personas
```

Data source: `src/data/persona-keywords.json`

## 6-Category Keyword Mapping

The 6 analysis categories (기질/유형, 재능, 호불호, 관계방식, 적합역할, 삶의흐름) are derived from the **spectrum position** (매우추상/추상/중화/현상/매우현상):

```typescript
const spectrumKey = spectrum.position;
const spectrumData = PERSONA.spectrumKeywords[spectrumKey];
categories: {
  trait: spectrumData.trait,      // ① 기질/유형
  talent: spectrumData.talent,    // ② 재능
  relationship: spectrumData.relationship,  // ④ 관계방식
}
```

## just5Data Injection (for report controller compatibility)

The legacy report controller (`controllers/report.ts`) expects data in `just5Data` format. When `just5Data` is missing, worker.ts injects computed data:

```typescript
(body as any).just5Data = {
  기질형스펙트럼: report.spectrum,
  오행집계: report.ohang.score,
  layer1: { 대운분석: { ... } },
  layer2: { 세운_오행점수: ..., 대운세운관계: ..., 올해테마: ... },
  persona: { mainOhang, name, essence, keywords },
  profile: { 오행프로파일: { spectrum, ohang, 주요특성 } },
};
```

## Source Files

| File | Role |
|------|------|
| `src/analysis/types.ts` | AnalysisReport, OhangScore, Spectrum, LayerShift, CurrentLuck types |
| `src/analysis/engine.ts` | analyze(), calcOhangScore, calcSpectrum, calcHapChung, calcTenGod, findCurrentLuck |
| `src/data/saju-constants.json` | Master: 천간/지지/오행/합충 data |
| `src/data/persona-keywords.json` | 5 personas + 4 versions + spectrum keyword tables |
| `src/utils/llm.ts` | callDeepSeek, callNvidiaWithFallback, callLLMJson, extractJsonObject |
| `src/controllers/report.ts` | handleGenerateFreeLogReport, handleGenerateReport |
| `src/controllers/comprehensive-report.ts` | handleGenerateComprehensiveReport (DeepSeek → NVIDIA + polish) |
| `src/controllers/dating-report.ts` | handleGenerateDatingReport (3 subtypes) |
