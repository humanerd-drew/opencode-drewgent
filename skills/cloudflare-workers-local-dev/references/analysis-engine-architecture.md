# Analysis Engine Architecture (m-log)

## File structure
```
src/
├── analysis/          ← L0~L3 computation engine
│   ├── engine.ts      ← Core: ohang scores, spectrum, hapChung, tenGod, layers
│   ├── types.ts       ← AnalysisReport, LayerShift, CurrentLuck types
│   └── README.md      ← Status and todo
├── controllers/       ← API handlers (7 files: saju, auth, report, history, etc.)
├── data/              ← Static data
│   ├── saju-constants.json   ← Master: stems, branches, elements, relations
│   └── persona-keywords.json ← 5 personas + 4 versions + 6 categories
├── utils/
│   ├── llm.ts         ← Unified DeepSeek → NVIDIA callers
│   ├── crypto.ts      ← Session signing, verification
│   ├── cors.ts        ← CORS + security headers
│   └── email.ts       ← Resend email
├── engine/            ← NAS original (compatibility, dating)
├── db/                ← D1 queries
└── worker.ts          ← Router + dispatch (12 routes)
```

## Data flow
```
request → worker.ts router → controller → external API (PDC)
                                          → analysis/engine.ts → analysisReport
                                          → response with analysisReport injected
```

## Key patterns
- **PDC priority**: Use PDC's tenGods, direction, wolun directly. Engine only computes what PDC doesn't
- **Layer accumulation**: Each layer adds 2 chars to the pillar array, recalculates ohang+spectrum, compares delta
- **Persona**: Dominant ohangScore element → 5 personas (wood/fire/earth/metal/water), each with 4 sheng/ke versions
- **6 categories**: Spectrum position → trait/talent/relationship keyword lookup
