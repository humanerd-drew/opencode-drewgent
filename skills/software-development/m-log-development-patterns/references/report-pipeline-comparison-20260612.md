# Report Pipeline Comparison: Comprehensive vs Dating (2026-06-12)

## Overview

Both report controllers share the same 4-stage pipeline architecture but differ significantly in maturity, logging, timeout handling, and error recovery. This document captures the detailed comparison for future refactoring.

## Pipeline Stage Comparison

### Stage 1: Data Assembly

```typescript
// Common pattern: fetch saju API + persona API → assemble data → pass to LLM
```

**Comprehensive:**
```typescript
const [sRes, pRes] = await Promise.all([
    fetchWithTimeout(sajuApiEndpoint, {...}, 15000),
    fetchWithTimeout(`${personaApiEndpoint}analyze`, {...}, 15000)
]);
const data = { saju: saju.data, persona: persona };
```

**Dating:**
```typescript
// Uses the same saju + persona API calls, but additionally:
import { getLoveProfile } from '../love-profiles';
// Builds structured love profile data for the LLM
```

### Stage 2: System Prompt Assembly

**Comprehensive:**
```typescript
const keys = "layer0, layer1, layer2, layer3, synthesis";
const sys = ONTOLOGY_CTX + '\n\n' + buildSystemPrompt(keys);
```

**Dating:**
```typescript
const ontologyCtx = getOntologyContext(mode as any);  // 'analyze' | 'compatibility' | 'divorce'
sys = ontologyCtx + '\n\n' + buildAnalyzeSystemPrompt(!!data.me, keys);
```

### Stage 3: Main LLM Call

**Comprehensive:**
```typescript
report = await callLLMJson(env, sys, userContent, keys, 4000, 0.25);
// timeout defaults to 30000ms
```

**Dating:**
```typescript
const report = await callLLMJson(env, sys, userContent, keys, getMaxTokens(mode, data), temp);
// timeout defaults to 55000ms
```

### Stage 4: Polish

Both use similar `callLLMJson` + `POLISH_SYSTEM_PROMPT` + merge with 70% length check.

**Dating adds:**
```typescript
console.log(`[Dating Polish] Starting polish step (...)`);
// ...
console.warn(`[Dating Polish] Failed, returning original: ${e.message}`);
```

**Comprehensive lacks any polish logging.**

## Key Differences

| Area | Comprehensive | Dating | Impact |
|------|-------------|--------|--------|
| callLLMJson source | Inline in controller | `../utils/llm.ts` (shared) | Duplicated code, divergence risk |
| Timeout | 30s | 55s | Comprehensive borderline for slow DeepSeek |
| Polish patterns | 5 | 12+ | Less effective polish |
| 절대 보존 항목 | None | Yes | Merge reject risk higher |
| console.log | None | Start + failure | Debugging impossible |
| Fallback | Error msg | Static report | UX degradation |
| Max tokens | 4000 fixed | 2600-3200 dynamic | Over-provisioned |
| Evidence grounding | None | "1개 이상 근거 언급" | Less rigorous output |

## Recommend Actions

**Implemented (2026-06-12):**
- ✅ Increase timeout from 30s to 55s (comprehensive-report.ts callLLMJson default 55s)
- ✅ Add polish start/failure logging (console.log/console.warn in comprehensive-report.ts polishReport)
- ✅ Expand POLISH_SYSTEM_PROMPT with dating's patterns (5 → 14 patterns)
- ✅ Add 절대 보존 항목 to comprehensive's polish prompt
- ✅ Add "근거 기반 강제" to main system prompt
- ✅ Add min character length per section (400 chars for L0~L3, 300 for synthesis)
- ✅ Add "사주→일상 번역" instruction to main prompt
- ✅ Increase max_tokens (4000→5000 main, 4500→6000 polish)

**Still pending:**
- ❌ Move comprehensive's callLLMJson to use shared ../utils/llm.ts 
- ❌ Replace error message fallback with structured static fallback
