# PDC (PersonalDateCalculator) Isolation Principle

PDC is the external saju calculation API (deployed as a separate Cloudflare Worker).
**Calculations within PDC must NOT be duplicated in the main application.**

## Why

- PDC is the canonical source for all astronomical and calendar calculations.
- Bug fixes and corrections happen in PDC only. Duplicating logic creates drift.
- PDC is intentionally isolated to prevent agents from "over-engineering" and breaking core logic.

## What to NOT Recalculate

| PDC Provides | App Should Not |
|---|---|
| `data.pillars` (4 pillars) | Recalculate ganji from birth date |
| `data.tenGods` | Compute ten gods from stem/branch |
| `data.daewoon.direction` (forward/backward) | Compute direction from gender+yearStem |
| `data.daewoon.cycles[].saewoon[].wolun[]` | Compute monthly fortune cycle |

## What the App Engine SHOULD Compute

- **Spectrum/position** — PDC doesn't compute Qi-Zhi-Xing spectrum
- **Ohang scores** — PDC returns raw pillars, not aggregated element scores
- **Layer analysis (L1/L2)** — PDC returns daewoon/saewoon entries; app combines layers
- **Persona** — Determined from ohang score distribution, not from PDC
- **6-category keywords** — Mapped from spectrum position, not from PDC

## Integration Pattern

```
PDC → raw JSON → app engine transforms → structured AnalysisReport → report pipeline
```

The app's `analyze()` function takes PDC output + optional extra inputs and produces AnalysisReport. It never calls PDC's internal calculation functions.
