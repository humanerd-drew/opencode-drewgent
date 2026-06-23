# M-LOG UX 전면 개선 계획

## 대전제

"사용자가 M-LOG를 처음 열었을 때부터 유료 리포트를 구매할 때까지의 흐름을 매끄럽게 만든다. 법적 리스크를 해결하고, 전환율을 높인다."

---

## Phase 1: 온보딩 + 가입 UX (신규)

### 1.1 온보딩 페이지 (신규 제작)
- **현재**: 없음. 바로 BirthForm 입력 화면.
- **개선**: 실제 앱 스크린샷을 활용한 온보딩 페이지 제작
  - C→A→T→A 형식: "사주 입력 → 분석 → 리포트 → 인사이트"
  - 각 단계별 실제 앱 스크린샷 (리포트 화면, 대시보드, 결제 화면)
  - 로그인 없이도 "미리보기" 체험 CTA
  - 하단: 소셜 로그인 / 이메일 가입 버튼
- 온보딩 페이지 라우트: `/` (기존 root index.html을 온보딩 페이지로 교체)
  - 또는 `/onboard` 신규 라우트 + root는 간단한 스플래시 → `/onboard` 리디렉트

**변경 파일**:
- 신규: `public/onboard.html` (또는 `public/index.html` 교체)
- 신규: `public/app/js/onboard.js`
- 수정: `public/app/css/home.css` (온보딩 스타일 추가)

### 1.2 로그인/회원가입 UX 개선
- **현재**: `alert()` 에러 표시, 인라인 validation 없음
- **개선**: 인라인 폼 validation, 에러 메시지 UI 통일
- 소셜 로그인 버튼에 hover/focus 상태 개선

**변경 파일**: `public/app/js/views/InputView.js`, `public/app/shared/core/auth.js`

### 1.3 가입 후 첫 명식 등록 가이드
- **현재**: 로그인 후 대시보드로 바로 이동 (빈 화면 또는 이전 데이터)
- **개선**: 첫 로그인 감지 → "첫 명식을 등록하세요" 가이드 오버레이

**변경 파일**: `public/app/js/views/DashboardView.js` (init/mounted)

---

## Phase 2: 명식 입력 UX 개선

### 2.1 날짜 선택기
- **현재**: YYYY / MM / DD 각각 숫자 직접 입력
- **개선**: `<input type="date">` 기본 지원 (2026년 현 브라우저 모두 지원)
  - ponytail 원칙: "네이티브 플랫폼 기능으로 되나?" → use it
  - `<input type="date">` 하나로 Y/M/D 통합
  - 한국 로케일 적용: `lang="ko"` + `datepicker-ko` 커스텀

**변경 파일**: `public/app/js/components/organisms/BirthForm.js`

### 2.2 시간 선택기
- **현재**: 0-23 직접 타이핑
- **개선**: `<select>` 시간/분 셀렉터 (0~23시, 0~59분)

**변경 파일**: `public/app/js/components/organisms/BirthForm.js`

### 2.3 출생지 선택
- **현재**: 텍스트 autocomplete (동작함)
- **개선**: 현재 구조 유지, UI 스타일만 개선

**변경 파일**: `public/app/css/components/form.css`

---

## Phase 3: 결제 UX 개선 (🟥 법적 리스크)

### 3.1 개인정보 제3자 제공 동의 체크박스
- **현재**: 없음
- **개선**: 결제 버튼 위에 체크박스 추가
  - 카카오페이 동의 문구 (구매자명, 휴대폰번호, 이메일, 상품명, 결제 금액 → 카카오페이)
  - 네이버페이 동의 문구 (동일 항목 → 네이버파이낸셜)
  - 선택된 결제 수단에 따라 동의 문구 동적 변경
  - 동의하지 않으면 결제 버튼 비활성화

**변경 파일**: `public/app/js/views/PaymentView.js`

### 3.2 결제자 필수 정보 강화
- **현재**: phone 선택, email 빈값 가능
- **개선**: phone 필수 + validation, email 필수 + validation
  - UX: "결제 인증을 위해 휴대폰 번호가 필요합니다"
  - UX: "영수증 발송을 위해 이메일이 필요합니다"

**변경 파일**: `public/app/js/views/PaymentView.js`

### 3.3 PortOne SDK 미로드 시 mock 제거
- **현재**: `fallbackPayment()`가 mock 성공 처리
- **개선**: SDK 로드 재시도 (3회, 2초 간격) → 실패 시 에러 메시지

**변경 파일**: `public/app/js/views/PaymentView.js`

### 3.4 서버 amount 검증 추가
- **현재**: status만 확인
- **개선**: `verifyData.amount.amount === body.amount` 일치 확인 + `verifyData.currency === 'KRW'`

**변경 파일**: `src/controllers/payment.ts`

---

## Phase 4: 대시보드 UX 개선

### 4.1 `template()` 내 inline 함수 추출 (Phase 2)
- **현재**: 682줄 template(), 6개 inline 함수, `isCheonganCombination` 중복
- **개선**: inline 함수를 별도 모듈로 추출 + DashboardView.template()을 1/3로 축소

**변경 파일**:
- 신규: `dashboard-sections/TemplateHelpers.js`
- 수정: `DashboardView.js` template()

### 4.2 제한(restricted) 사용자 UX — 프리뷰 확대
- **현재**: 분석 데이터 전체 블러 (saju.ts에서 analysis 통째로 삭제)
- **개선**:
  - `saju.ts`: `delete result.data.analysis` 제거 (희용신/격국/근/생왕고/합충은 보임)
  - `delete result.data.sinsal`만 유지 (12신살만 블러)
  - DashboardView restricted branch: 희용신/격국/근/생왕고/합충을 블러 없이 표시
  - 12신살 섹션만 블러 + "🔒 로그인하고 12신살 분석 보기" CTA

**변경 파일**:
- `src/controllers/saju.ts` — `delete result.data.analysis` 제거
- `DashboardView.js` template() restricted branch — yongsin/heesin/gyeokguk 표시, sinsal만 블러

### 4.3 AppShell 분할 (향후)
- **현재**: 970줄 단일 파일
- **개선**: HeaderSection / NavSection / HistorySection 등 분할
- Phase 4에서 수행 (우선순위 낮음)

---

## Phase 5: 리포트 UX 개선

### 5.1 LLM 생성 진행률 표시
- **현재**: 로딩 스피너만 (30~60초)
- **개선**: 단계별 진행 상태 표시
  - "① 명식 데이터 분석 중..." → "② 온톨로지 컨텍스트 로딩..." → "③ AI 분석 생성 중..." → "④ 리포트 마무리 중..."
  - 각 단계 완료 시 체크 표시

**변경 파일**: `public/app/js/views/ReportComprehensiveView.js`, `public/app/js/views/ReportDatingView.js`

### 5.2 ai_reports 캐싱 활용
- **현재**: migration만 추가, DB 캐싱 로직은 있으나 테이블 없어서 silent fail
- **개선**: `wrangler d1 execute`로 migration 적용 → 캐싱 활성화하여 재생성 시 30~60초 → 0초

**변경 파일**: `migrations/0012_add_ai_reports.sql` (이미 생성됨, 배포 시 적용만 필요)

---

## 실행 순서 및 의존성

```
Phase 1 (온보딩)
  └── Phase 2 (명식 입력) — 온보딩 후 첫 입력이므로
       └── Phase 3 (결제) — 입력 → 분석 → 결제 흐름의 마지막 단계
            └── Phase 5 (리포트) — 결제 후 리포트 생성
Phase 4 (대시보드) — 독립적으로 언제든 가능
```

## 검증 방법

각 Phase 완료 후:
1. `npm run dev` 로컬 기동 확인
2. 데스크탑 크롬에서 전체 플로우 수동 테스트 (입력 → 분석 → 결제 → 리포트)
3. 모바일 뷰포트(375px, 414px)에서 동작 확인
4. `grep -r "Paddle" public/ frontend/` — Paddle 잔여 참조 확인
5. Phase 3 완료 후: PortOne SDK 미로드 시 mock 경로 차단 확인

## 오픈 질문

1. 온보딩 페이지 라우트: `/` (root 교체) vs `/onboard` (신규)?
2. 온보딩 스크린샷: 기존 앱에서 직접 캡처 필요 (현재 로컬에서 실행 중인 앱 활용)
