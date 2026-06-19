# M-LOG v2 Restructure (2026-06-13)

## Motivation
- `public/` vs `frontend/` 이원화로 배포마다 파일 누락/불일치
- `sync:local`이 `../packages/` 경로 없어 항상 실패
- `public/app.bak.*/`, `public/worker.ts` 방치된 데드 파일
- `dating-report.ts`에서 `../utils/report-utils` import 대상 없음
- `report.ts`에서 `../../frontend/data/sinsal-guide.json` import (frontend 의존)
- `locationData.ts` 루트 레벨 방치

## Changes Made

### New structure: `~/m-log-v2/`
```
m-log-v2/
├── src/
│   ├── worker.ts              (moved from root, paths rewritten)
│   ├── controllers/
│   ├── analysis/ + engine/
│   ├── utils/ + db/
│   └── data/                  (sinsal-guide.json copied here)
├── public/                    (clean, no app.bak, no frontend/)
├── migrations/
├── locationData.ts            (copied from root)
├── wrangler.jsonc             (main: "src/worker.ts")
└── package.json               (sync:local removed)
```

### Import fixes
| File | 전 | 후 |
|------|----|----|
| `src/worker.ts` | `'./src/controllers/...'` | `'./controllers/...'` |
| `src/controllers/report.ts` | `'../../frontend/data/...'` | `'../data/...'` |
| `src/controllers/dating-report.ts` | `from '../utils/report-utils'` | REMOVED (all inline) |

### Dead/removed
- `public/worker.ts`, `public/app.bak.*/`
- `frontend/` (entire parallel dir), `frontend/dev/`
- `sync:local` from package.json

### Fixed
- `Router.js`: `sessionStorage` → `localStorage`
- `wrangler.jsonc`: `main: "src/worker.ts"`
