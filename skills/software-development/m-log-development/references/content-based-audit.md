# Content-Based Gap Audit Methodology

When comparing original vs new framework implementations, don't just check file existence. Verify feature parity through content analysis.

## Process

1. **Inventory both sides** — List every file/module from the original by category (views, components, CSS, utilities, calculations, standalone HTML).

2. **Map to new equivalents** — For each original module, determine what replaces it in the new framework. Possible outcomes:
   - `✅ Converted` — exists with equivalent functionality
   - `❌ Missing` — no equivalent exists (gap)
   - `🗑️ Intentional delete` — was dead code (Quintax, Just5)
   - `⚠️ Partial` — exists but lacks features (e.g., report page shows raw JSON instead of formatted output)

3. **Content-based feature extraction** — For each critical page, extract specific features from the original source code:
   ```
   # Regex-based feature presence check
   features = [
     ("WongukBoard", "wongukBoard", "pillar"),
     ("Sinsal 12신살", "sinsal", "sinsal"),
     ("희용신 분석", "yongsin", "yongsin"),
     ...
   ]
   for name, orig_pat, new_pat in features:
     orig_has = bool(re.search(orig_pat, orig_code, re.I))
     new_has = bool(re.search(new_pat, new_code, re.I))
   ```
   This catches features that exist in original but were silently dropped.

4. **Check fallback chains** — When removing features that provided data to other modules, verify the consumers have proper fallbacks:
   ```js
   // Good — safe to remove just5 if this pattern exists
   const data = just5Data?.field || sajuData?.field || {}
   // Bad — crash if just5 is removed
   const data = just5Data.field
   ```

5. **Navigate the full user flow** — Before calling any page "done", trace the complete path:
   Landing → Launcher → Input → Result → Report/Payment/Compare
   If any link in the chain is broken (307, 404, redirect loop), the page is not ready.

6. **Check the "has real logic, never routed" trap** — Search for exported functions in controllers that were never imported or routed. A function with 500 lines of real business logic is still dead code if no route ever calls it.

## Output format

```markdown
| Feature | Original | New | Status |
|---------|----------|-----|--------|
| WongukBoard | 4-pillar grid | 4-pillar grid | ✅ |
| Sinsal tab | year/day base | year/day base | ✅ |
| Desire tab | `generateDesireReportHtml` | placeholder | ❌ |
```

## When to audit

- After completing a batch of page conversions
- When the user expresses dissatisfaction with quality ("대충 mock 데이터 박아놓고")
- Before declaring a major milestone complete
