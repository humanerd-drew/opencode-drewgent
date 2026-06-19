# Layer-Based Analysis Engine (L0-L3)

## Pattern Overview

When building a 사주/fortune-telling analysis engine that computes progressive layers of insight from natal chart data, structure as cumulative pillar addition:

```typescript
L0 (8 pillars)  = year + month + day + time           → birth chart essence
L1 (10 pillars) = L0 + current daewoon (2 chars)       → 10-year trend   + ohang delta + spectrum shift
L2 (12 pillars) = L1 + current saewoon (2 chars)       → annual theme    + daewoon-saewoon relation
L3 (14 pillars) = L2 + current wolun (2 chars)         → monthly impulse + seasonal context
```

## API Integration Pattern

The external calculator (PDC) returns raw data. The analysis engine wraps it:

```
Calculator API → analysis engine (L0-L3) → analysisReport
                                            ↓
                                    formatted for: just5Data → AI prompt → LLM → polish
```

## Key Techniques

### 1. Cumulative Pillar Array

```typescript
let l1Pillars = pillarsArray;  // L0 base
if (daewoon) {
  const dwP = splitGanji(daewoon.ganji);  // "辛卯" → { cheongan: "辛", jiji: "卯" }
  l1Pillars = [...l1Pillars, dwP];        // L1 = L0 + daewoon
}
if (saewoon) {
  const swP = splitGanji(saewoon.ganji);
  const l2Pillars = [...l1Pillars, swP];  // L2 = L1 + saewoon
}
```

### 2. Spectrum Delta = Layer Shift Direction

| Delta | Meaning |
|-------|---------|
| < -0.5 | `추상방향` — toward introspection |
| > +0.5 | `현상방향` — toward execution |
| -0.5 to +0.5 | `유지` — stable |

### 3. Daewoon-Saewoon Relationship

Compare the dominant Ohang of the daewoon and saewoon pillars:

| Relationship | Condition |
|-------------|-----------|
| 동일 | dwOhang === swOhang |
| 대운이 세운을 생 | SANGSAENG_MAP: dwOhang → swOhang |
| 세운이 대운을 생 | SANGSAENG_MAP: swOhang → dwOhang |
| 대운이 세운을 극 | SANGGEUK_MAP: dwOhang → swOhang |
| 세운이 대운을 극 | SANGGEUK_MAP: swOhang → dwOhang |

### 4. L3 (Wolun/월운) — No Calculation Needed

The external PDC API already provides 월운 data in each saewoon entry:

```typescript
// PDC response structure:
daewoon.cycles[i].saewoon[j].wolun  // Array of 12 monthly entries
// Each wolun entry:
{ month: 1, ganji: "己丑", cheongan: "己", jiji: "丑", tenGods: {...}, hapChung: [...] }
```

**Do NOT reimplement monthly pillar calculation.** The PDC API's SajuAnalyzer
already handles the 절기-based calculation. Just extract the current month:

```typescript
const wolunData = currentSw.wolun?.find(w => w.month === currentMonth);
```

### 5. Birth Year from Calculator Input

The calculator returns `input.date` as `"1991-07-24"` format — NOT `input.year`.
Always parse:
```typescript
const birthYear = input.date
  ? parseInt(input.date.split('-')[0])
  : input.year;
```

## Report Controller Data Bridge

The report controller expects `just5Data` format, but the analysis engine produces
`analysisReport`. Bridge via dual-layer injection:

1. **Router layer** (`worker.ts`): Compute analysis → inject as `just5Data` into request body
2. **Controller layer** (`report.ts`): Fallback chain `just5Data → sajuData → {}`
