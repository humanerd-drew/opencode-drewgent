# AGENTS.md Template — Agent-Oriented Project Map

Place at project root. Future agent sessions read this first to orient.

## Required Sections

### 1. 원칙
```
- **src/ 하나만** — 모든 소스코드가 src/ 아래에 있음
- **도메인 기준 분리** — user, saju, report, payment, db, api, ui
- **파일명 = 동사-명사.kebab-case.ts** — 검색어로 바로 찾을 수 있게
- **api/는 thin layer** — 라우트만 있고 비즈니스 로직은 각 도메인에 위임
- **AGENTS.md 먼저 읽을 것**
```

### 2. 디렉토리 구조 (트리로)
```
src/
├── user/           계정/인증/프로필/기록
├── saju/           사주 계산/분석 엔진
├── report/         리포트 생성 + LLM 프롬프트
├── payment/        결제 검증/연동
├── db/             D1 쿼리/스키마/마이그레이션
├── api/            Hono 라우트 (thin layer + 미들웨어)
├── ui/             Svelte SPA 프론트엔드
├── config/         환경 설정
└── utils/          공통 유틸
```

### 3. 파일명 규칙
```
- 동사-명사.kebab-case.ts
- 예: get-daewoon.ts, verify-payment.ts, oauth-naver.ts
- 검색어 = 파일명의 일부
```

### 4. 검색 테이블 (가장 중요)
```
| 검색어 | 파일 |
|---|---|
| 결제 검증 | src/payment/verify-payment.ts |
| 로그인/인증 | src/user/sign-in.ts, src/user/oauth-naver.ts |
| 대운 조회 | src/saju/get-daewoon.ts |
```

### 5. 현재 상태 (선택사항)
```
## 현재 상태
- ✅ Phase 1: 완료
- 🚧 Phase 2: 진행중
- ⬜ Phase 3: 대기
```

### 6. 다가올 리팩토링 (선택사항)
```
### 다가올 리팩토링
- `src/saju/saju-controller.ts` → calculate-pillars.ts, get-daewoon.ts 분리
```

## When to Create

- User says "폴더 구조 체계화", "직관적으로", "에이전트가 바로 찾게"
- User corrects your proposed structure as not different enough ("이전과 다를바 없어보이는데")
- Project has grown beyond 50+ source files with unclear boundaries
- Multiple developers/agents will work on the codebase
- **Create BEFORE any code changes, not after. AGENTS.md is Phase 0.**

## What Makes It "Agent-Findable"

The structure is agent-findable when:

1. **Search-driven**: The search table (section 4) directly maps every search term an agent would type to exactly one file path
2. **Verb-noun naming**: File names start with a verb (verify, generate, calculate) followed by a noun (payment, report, daewoon) — agents search for verbs
3. **Domain over layer**: `payment/verify-payment.ts` (domain) not `controllers/payment.ts` (layer)
4. **Depth ≤ 3**: Any file is reachable within 3 directory levels from src/
5. **No role-in-name**: No "controller" / "service" / "handler" in filenames — the domain directory tells you the role

**Test**: Ask "If an agent types `grep -rl 'verify' src/payment/`, do they get the right file? If not, restructure."
