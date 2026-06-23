# 계정-명식 통합 온보딩 기획

## 대전제

"계정과 명식을 하나의 덩어리로 묶어, 사용자가 로그인만 하면 자신의 분석 대시보드가 바로 펼쳐지게 한다."

---

## 현재 문제

1. 로그인과 명식 입력이 분리됨 — 로그인해도 명식이 없으면 빈 대시보드
2. 명식을 입력해도 계정에 자동 연결되지 않음 (별도 history 저장)
3. Log 리포트를 매번 수동 생성해야 함
4. `ai_reports` 캐싱이 작동하지 않음 (테이블 미적용)

---

## 제안: 계정-명식 통합 플로우

### A. 가입/로그인 → 명식 등록 (통합)

```
[온보딩 페이지] → 소셜/이메일 가입
                    ↓
              [첫 명식 등록]
              - 생년월일시 입력
              - "이 명식을 내 계정의 기본 명식으로 설정"
                    ↓
              [분석 대시보드] (자동 진입)
              - 원국 + 타임라인 + Log 리포트 (자동 생성)
```

**변경 사항:**
- 가입 직후 BirthForm으로 자동 이동
- `POST /api/analyze` + 세션 → 자동으로 `users.primary_saju_id` 업데이트
- 명식 등록과 동시에 `myeongsiks_v2`, `history_v2`, `analysis_core` 저장
- Log 리포트 자동 생성 + `ai_reports`에 캐싱 ("분석하기" 버튼 사라짐)

### B. 대시보드 = 계정의 분석 (로그인 기준)

```
[로그인]
    ↓
[대시보드]
    ├─ 현재 계정의 primary_saju 기준
    ├─ 원국(WongukBoard) + 타임라인
    ├─ Log 리포트 (ai_reports 캐시)
    │    ├─ 캐시 있음 & 현재 월 → 즉시 표시
    │    └─ 캐시 없음 or 월 변경 → "새로운 월 분석하기" 버튼
    └─ 프리미엄 리포트 CTA
```

**변경 사항:**
- `POST /api/report/free-log` → 월(month) 파라미터 추가
- `ai_reports` 캐시 키: `{myeongsik_id}_{year}_{month}_free`
- DashboardView: `renderAiReportHubSection()`에서 캐시 확인 후 조건부 렌더링
- "분석하기" 버튼 → "이번 달 분석 다시하기" (캐시 있을 때) / "분석 시작" (캐시 없을 때)

### C. DB 캐시 활성화 (`ai_reports`)

- `wrangler d1 execute m_log_db --remote --file=migrations/0012_add_ai_reports.sql` (배포 전 1회)
- `POST /api/report/free-log` 응답을 `ai_reports`에 저장
- `GET /api/report/free-log?myeongsik_id=X&year=Y&month=Z` → 캐시 조회 후 있으면 반환
- 캐시 만료: 월 변경 시 (프론트에서 `currentMonth`와 캐시의 `month` 비교)

### D. Log 리포트 = 월간 분석

"월운까지를 기준으로 분석하니, 한 번 했으면 월이 바뀌기 전까지는 계속 보여준다"

**변경 사항:**
- 현재 free-log 리포트는 `fortuneIndices.daewoon` 기준 → `wolun`까지 포함
- 리포트 스코프를 명확히: "원국 + 현재 대운 + 현재 월운" → 매월 갱신되는 월간 리포트로 개념 정립
- **명식 분석(원국/타임라인)은 월 변경과 무관** — 항상 고정
- **Log 리포트만 월 변경 감지**
- 월 변경 감지: 프론트에서 `new Date().getMonth()`와 캐시 month 비교
- 월 변경 시: 자동 재생성 ❌ → **"N월 나의 로그 리포트 분석 시작" 버튼 표시 + 알림**
- 알림: `showToast('N월 리포트', 'N월의 나의 로그 리포트 분석이 가능합니다')`

---

## 파일 변경 목록

| 파일 | 변경 |
|------|------|
| `public/app/js/views/MyPageView.js` | **신규** — 마이페이지 |
| `src/controllers/user.ts` | **신규** — 계정/명식/결제 정보 API |
| `src/controllers/report.ts` | free-log 엔드포인트에 월 파라미터 추가, `ai_reports` 저장/조회 로직 연결 |
| `src/controllers/auth.ts` | 가입/로그인 후 primary_saju 자동 설정 |
| `src/controllers/saju.ts` | 분석 후 `primary_saju_id` 업데이트 + Log 리포트 트리거 |
| `src/db/queries.ts` | `getCachedReport`/`saveReportCache` (이미 있음, `ai_reports` 테이블 생성 후 활성화) |
| `public/app/js/app.js` | `#/my-page` 라우트 추가 |
| `public/app/js/views/DashboardView.js` | Log 리포트를 자동 표시, "분석하기" → 월 변경 감지로 전환 |
| `public/app/js/views/InputView.js` | 첫 분석 후 대시보드 자동 진입 + 계정 연동 |
| `public/app/js/components/layouts/AppShell.js` | 로그인 상태에 따른 마이페이지 링크, 아바타(일간 간지 카드) |
| `migrations/0012_add_ai_reports.sql` | 이미 생성됨. 배포 시 `wrangler d1 execute`로 적용 |

---

## 검증

1. 신규 가입 → 명식 등록 → 대시보드 (Log 리포트 자동 표시)
2. 같은 달 재접속 → 캐시된 리포트 즉시 표시 (API 호출 없음)
3. 월 변경 → "새로운 분석" 버튼 표시
4. DB 캐시 확인: `ai_reports` 테이블에 row 존재

---

## 오픈 질문

1. 계정에 여러 명식 등록은 언제 지원? (현재 Phase 1: 1계정 1명식)
2. Log 리포트 자동 생성 → 로딩 시간 30~60초. 첫 진입 시 기다리게 할지, 백그라운드 생성 후 알림?
   - 제안: 첫 생성 시 스켈레톤 UI + 완료 알림
