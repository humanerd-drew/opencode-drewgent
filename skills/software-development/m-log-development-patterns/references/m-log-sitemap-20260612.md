# M-LOG 사이트맵 (2026-06-12 조사)

## 디렉토리 구조

### `src/` (56개 파일)

```
src/
├── analysis/          (3 files)
│   ├── engine.ts      — 분석 엔진 (오행, 스펙트럼, 합충, L1/L2, persona)
│   ├── README.md
│   └── types.ts
├── controllers/       (7 files)
│   ├── auth.ts        — Naver/Google OAuth + email/password
│   ├── comprehensive-report.ts — 대세월운 종합 리포트 (수정: 2026-06-12)
│   ├── dating-report.ts — 연애 리포트 (analyze/compatibility/divorce)
│   ├── history.ts     — 조회 기록 CRUD
│   ├── myeongsik.ts   — 명식 저장/조회
│   ├── payment.ts     — PortOne 결제 검증 + D1 저장
│   ├── report.ts      — free log 리포트 생성
│   └── saju.ts        — 사주 분석 + iljin + locations
├── data/
│   ├── ontology/ontology.ts  — Postziping 온톨로지 로더
│   ├── ontology/postziping/  — 원본 온톨로지 문서 (~12,700 lines, ~600KB)
│   ├── persona-keywords.json
│   └── saju-constants.json
├── db/queries.ts      — 모든 D1 쿼리 통합
├── engine/            (19 files) — 궁합/연애 분석 엔진
│   ├── compatibility-engine.ts
│   ├── atoms/         — 오행별 atom
│   ├── ui-atoms/      — UI 렌더링 atom
│   └── ...
├── quintax/           (6 files)
├── utils/
│   ├── cors.ts
│   ├── crypto.ts      — 세션 서명/검증
│   ├── email.ts
│   └── llm.ts         — DeepSeek + NVIDIA fallback 공유 LLM 호출러
├── love-profiles.ts
└── worker-quintax.ts
```

### `public/` (배포 assets)

```
public/
├── index.html
├── worker.ts              ← DEAD: assets dir 안에 있는 worker 복사본 (실행 안 됨)
├── app/
│   ├── index.html         ← SPA 엔트리
│   ├── css/               (22 files)
│   ├── js/
│   │   ├── app.js         ← SPA 라우터
│   │   ├── views/         (12 views)
│   │   ├── components/    (21 components)
│   │   ├── core/          (Router.js, Component.js)
│   │   ├── calculations/  (desire-skills.js, types.js)
│   │   └── ...legacy JS files (ganji.js, parser.js, renderer.js...)
│   └── shared/            (core/, theme/, ui/ — via sync:local)
├── app.bak.1781188417/    ← DEAD: 백업 디렉토리
├── assets/ (logo)
└── data/ (sinsal-guide.json)
```

### `frontend/` (개발 소스)

`public/`과 거의 동일한 구조. 차이점:
- `frontend/dev/` 디렉토리 추가 보유 (모놀리식 레거시)
- `frontend/assets/` — vite 빌드 산출물 (index-B1hwDY-q.js 등)
- Router.js line 25: `localStorage.getItem()` (public은 `sessionStorage`)

---

## API 라우트 (worker.ts 기준, 15개)

| Method | Path | Controller | 인증 |
|--------|------|-----------|------|
| POST | `/api/analyze` | saju.ts | 선택 |
| POST | `/api/iljin` | saju.ts | 선택 |
| GET | `/api/auth/naver` | auth.ts | - |
| GET | `/api/auth/callback/naver` | auth.ts | - |
| GET | `/api/auth/google` | auth.ts | - |
| GET | `/api/auth/callback/google` | auth.ts | - |
| GET | `/api/auth/me` | auth.ts | cookie |
| GET | `/api/auth/logout` | auth.ts | cookie |
| GET | `/api/auth/dev-login` | auth.ts | - |
| POST | `/api/auth/register` | auth.ts | - |
| POST | `/api/auth/login` | auth.ts | - |
| PATCH | `/api/user/profile` | auth.ts | cookie |
| POST | `/api/payment/verify` | payment.ts | cookie/anon |
| GET | `/api/payment/check` | payment.ts | cookie/anon |
| GET | `/api/history` | history.ts | cookie |
| POST | `/api/history` | history.ts | cookie |
| DELETE | `/api/history/:id` | history.ts | cookie |
| GET | `/api/meongsik` | myeongsik.ts | cookie |
| POST | `/api/meongsik` | myeongsik.ts | cookie |
| GET | `/api/locations` | saju.ts | - |
| POST | `/api/report` | report.ts | cookie |
| POST | `/api/report/generate` | report.ts | cookie |
| POST | `/api/report/free-log` | report.ts | cookie |
| POST | `/api/dating/*` | dating-report.ts | cookie |
| POST | `/api/report/comprehensive` | comprehensive-report.ts | cookie/fingerprint |
| GET | `/api/just5/analyze` | stub | - |

---

## SPA 라우트 (app.js 기준, 12 routes)

| Hash Route | View Class | 비고 |
|-----------|-----------|------|
| `/input` | InputView | 생년월일 입력 |
| `/dashboard` | DashboardView | 메인 대시보드 |
| `/quintax` | QuintaxView | |
| `/just5` | Just5View | |
| `/compare` | CompareView | 명식 비교 |
| `/report-desire` | ReportDesireView | 욕망 리포트 |
| `/report-ai` | ReportAiView | 7주 라이브 리포트 |
| `/report-luck` | ReportComprehensiveView | ← ReportLuckView 아님 |
| `/payment` | PaymentView | PortOne 결제 |
| `/report-dating` | ReportDatingView | 연애 리포트 |
| `/report-desire-deep` | ReportDesireDeepView | 심층 욕망 분석 |
| `/report-comprehensive` | ReportComprehensiveView | 대세월운 종합 리포트 |

---

## DB 스키마 (from migrations/ + src/db/queries.ts)

### users
| Column | Type | Notes |
|--------|------|-------|
| id | TEXT PK | |
| email | TEXT UNIQUE NOT NULL | |
| name | TEXT | |
| picture | TEXT | |
| created_at | DATETIME | |
| marketing_consent | BOOLEAN DEFAULT 0 | (from 0002) |
| provider | TEXT | (from 0004) naver/google/email |
| password_hash | TEXT | (from 0005) |
| primary_saju_id | TEXT → history(id) | (from 0003) |

### history
| Column | Type | Notes |
|--------|------|-------|
| id | TEXT PK | |
| user_id | TEXT NOT NULL → users(id) | |
| label | TEXT NOT NULL | |
| form_data | TEXT NOT NULL | JSON |
| saju_data | TEXT NOT NULL | JSON |
| timestamp | DATETIME | |

### purchases
| Column | Type | Notes |
|--------|------|-------|
| id | TEXT PK | |
| user_id | TEXT → users(id) | nullable (anonymous pay) |
| anonymous_id | TEXT | nullable |
| report_type | TEXT NOT NULL | desire/ai/luck/comprehensive/... |
| fingerprint | TEXT NOT NULL | 명식 fingerprint |
| tx_id | TEXT | PortOne tx ID |
| payment_id | TEXT | PortOne payment ID |
| amount | INTEGER DEFAULT 3800 | |
| status | TEXT DEFAULT 'completed' | completed/refunded |
| purchased_at | TEXT NOT NULL | |

Indexes: `(user_id, report_type, fingerprint)`, `(anonymous_id, report_type, fingerprint)`

### history_v2 — migrated from v1
### myeongsiks_v2 — multi-profile per user
### ai_reports — cached LLM reports
### analysis_core — batch analysis results

---

## 발견된 문제 (2026-06-12)

1. **Router.js**: `public/`은 `sessionStorage`, `frontend/`은 `localStorage` — tab refresh 시 public은 redirect 실패
2. **dating-report.ts**: `../utils/report-utils` import 대상 없음 (파일缺失) — dating-report 내에 인라인 정의된 함수로 대체되었지만 import 문이 남아 있음
3. **public/app.bak.1781188417/**: 방치된 백업 디렉토리 (~182 files)
4. **public/worker.ts**: assets 디렉토리 안에 있는 worker 복사본 — 실행되지 않는 데드 파일
5. **sync:local**: `../packages/` 경로가 존재하지 않음 — 모든 cp 명령이 2>/dev/null로 실패
6. **ONTOLOGY_CTX**: Postziping 관계론 온톨로지 — 대세월운 분석에 무관
7. **polishReport merge 검증**: 70% length 조건으로 윤문 변경이 조용히 reject됨

---

## 참고: RESTRUCTURE-PLAN.md

`/Users/drew/m-log/RESTRUCTURE-PLAN.md`에 Phase 1~3 리팩토링 계획 저장됨.
