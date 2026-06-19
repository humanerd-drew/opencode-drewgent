# External API Priority Principle

## The Lesson

When an external API (e.g. `saju-calculator-api`) already returns computed data,
**use it instead of recalculating.** The user's exact words:

> "PDC에서 가져오는 결과를 대입하면 되는데 왜 자꾸 너네들을 계산하려고 하지?"

Translation: "Just use the results from the PDC — why do you keep trying to
recalculate everything yourself?"

## Application

Before implementing any calculation or transformation:

1. **Check what the external API already returns.** Send a sample request and
   inspect ALL fields in the response. Don't assume something isn't there.
2. **Cross-reference the response structure against your implementation plans.**
   If the API already provides it, use it directly. Transform format only if
   needed (e.g. `'forward'` → `'순행'`).
3. **Only implement calculations for data the API doesn't provide.**
   - API has tenGods? → use it, don't recalculate
   - API has daewoon direction? → map it, don't re-derive
   - API has monthly wolun arrays? → extract, don't recompute
4. **Keep a clear boundary:** engine.ts should only compute what PDC can't:
   ohang scores, spectrum, pillar element mappings, layer shifts (L1/L2).

## Checklist

Before implementing a calculation:

| Question | If YES | If NO |
|----------|--------|-------|
| Does the external API return this data? | Use the API value directly or transform format | Implement the calculation |
| Is this a new metric the API doesn't know about? | Proceed with implementation | Reconsider — it may already exist |
| Is this data derivable from existing API fields? | Derive it in a thin adapter, not a full reimplementation | Push the calculation upstream if it's fundamental |

## Why This Matters

- **The PDC (PersonalDateCalculator) was deliberately externalized** because
  saju calculations require extensive correction/bug-fixing. Internal copies
  diverge and become wrong.
- **Recalculating duplicates effort and introduces drift.** Each recalculated
  field is a maintenance burden and a potential source of inconsistency.
- **The user corrected this explicitly.** Future sessions should not repeat
  this mistake.

## Related

- `requesting-code-review` SKILL.md → Iterative Development Loop
- `requesting-code-review` → references/multi-worker-master-data.md
