# Multi-Worker Projects: Data Sharing Across Separate Cloudflare Workers

## Problem

A project may contain **multiple wrangler configurations** (e.g. `wrangler.jsonc` + `wrangler.quintax.jsonc`), each deploying a **separate Cloudflare Worker**. These workers cannot share imports at runtime — they're independent deployments.

Yet domain data (천간/지지/오행 mappings, lookup tables, business constants) is often duplicated across them, creating inconsistency risk.

## Solution: JSON Bridge Pattern

1. **Create a master JSON file** at a shared path (e.g. `src/data/domain-constants.json`)
2. All Workers import the same JSON at build time — each Worker bundles its own copy, but source is synchronized
3. Frontend (browser JS) keeps a standalone copy with a prominent comment pointing to the master

```
src/data/saju-constants.json  ← SINGLE SOURCE OF TRUTH
    ↑ import                   ↑ import               ↑ (comment reference)
worker.ts (main)        analyzer.ts (quintax)    constants.js (frontend)
```

### Requirements

- TypeScript: `"resolveJsonModule": true` in tsconfig
- Cloudflare Workers: native JSON import support (esbuild-based)
- Frontend: cannot import JSON directly (browser limitation) → keep as JS copy with master reference comment

### Implementation Pattern

```typescript
// Backend Worker (worker.ts)
import SAJU from './src/data/saju-constants.json';
// Use SAJU.stemList, SAJU.branches, SAJU.relations.* instead of hardcoded arrays

// Backend Worker (src/quintax/analyzer.ts)
import SAJU from '../data/saju-constants.json';
// Derive mappings at module init time:
const CHEONGAN_OHANG: Record<string, Ohang> = {};
for (const [char, data] of Object.entries(SAJU.stems)) {
  CHEONGAN_OHANG[char] = data.element as Ohang;
}
```

### What Goes in the Master vs What Stays Local

| In Master JSON | Keep Local |
|---------------|------------|
| Core domain entities (stems, branches, elements) | Computed/derived data (spectrum scores) |
| Lookup tables (element mappings, yin-yang) | UI display config (colors, styles) |
| Relationship data (합충 groups, label names) | Business logic (상생/상극 calculations) |
| Ordered arrays for index-based access | TypeScript type definitions |

### When Not to Use This Pattern

- Data is trivially small (2-3 entries) — inline is fine
- Workers are on completely different update cycles
- Each worker needs a different subset/resolution of the data
