# Analysis Engine Injection Pattern

## Problem
An existing API endpoint returns raw data from an external service. You want to add computed analysis without breaking existing consumers and without modifying the external service.

## Pattern: Transparent Enrichment

The API layer (worker.ts router) calls a pure compute engine *after* the external API returns, then injects the computed data into the response. The controller/handler doesn't change — enrichment happens at the routing layer.

```
request → router → controller (calls external API) → raw response
                                                      ↓
                                              injectAnalysisReport()
                                                      ↓
                                              enriched response
```

## Implementation

### 1. Pure Compute Engine

Create a separate module with zero side effects — no I/O, no imports of framework types:

```typescript
// src/analysis/engine.ts — pure compute
import SAJU from '../data/saju-constants.json';

export interface AnalysisInput {
  pillars: Record<string, { cheongan: string; jiji: string }>;
  dayMaster?: string;
  gender?: string;
  birthYear?: number;
  currentYear?: number;
  currentMonth?: number;
  daewoonCycles?: Array<{ index: number; ganji: string; startAge: number; saewoon?: any[] }>;
}

export function analyze(input: AnalysisInput): AnalysisReport {
  // Pure computation: ohang scores, spectrum, pillar elements, hapChung, tenGods...
  // No API calls, no I/O, no framework dependencies
}
```

### 2. Injection in Router Layer

```typescript
// worker.ts — router layer
import { handleAnalyze } from './src/controllers/saju';
import { analyze } from './src/analysis/engine';

// Route handler calls controller, then enriches
const response = await handleAnalyze(request, env, url, ctx);
return await injectAnalysisReport(response, env);
```

### 3. Backward-Compatible Enrichment

The injection function clones the original response, parses the JSON, adds the computed data, and returns a new response with the same HTTP status and headers:

```typescript
async function injectAnalysisReport(response: Response, env: Env): Promise<Response> {
  const clone = response.clone();
  try {
    const body = await clone.json() as any;
    if (body?.success && body?.data?.pillars) {
      body.data.analysisReport = analyze({
        pillars: body.data.pillars,
        dayMaster: body.data.analysis?.dayMaster,
        gender: body.input?.gender,
        birthYear: body.input?.year,
        currentYear: new Date().getFullYear(),
        currentMonth: new Date().getMonth() + 1,
        daewoonCycles: body.data.daewoon?.cycles,
      });
      return new Response(JSON.stringify(body), {
        status: response.status,
        headers: response.headers,  // preserves CORS + security headers
      });
    }
  } catch { /* non-fatal — return original */ }
  return response;
}
```

### 4. Report Content (AnalysisReport)

```typescript
interface AnalysisReport {
  ohang: { score: OhangScore; missing: string[]; excess: string[] };
  spectrum: { totalValue: number; position: string; ohangScore: OhangScore; mainSangsaeng: string; missingOhang: string[]; excessOhang: string[] };
  hapChung: HapChungEntry[];
  tenGod: TenGodAnalysis;
  currentLuck: { daewoon: CurrentDaewoon | null; saewoon: CurrentSaewoon | null; wolun: null };
  pillarElements: PillarElement[];
}
```

## Key Rules

1. **Engine is pure.** No I/O, no framework types, no `env` access.
2. **Injection is non-destructive.** If parsing fails, return original response unchanged.
3. **Injection preserves all headers.** CORS, CSP, Content-Type must survive.
4. **Frontend sees the new field but doesn't break without it.** Use optional chaining: `data.analysisReport?.ohang?.score` with fallback to existing behavior.

## When This Pattern Works Best

- An external API or legacy handler already produces a response, and you want to augment it
- The computation is deterministic (same input → same output)
- New fields should be invisible to existing consumers until they opt in
- You're migrating from "frontend computes" to "backend pre-computes" (passive renderer pattern)
