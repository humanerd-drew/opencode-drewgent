# m-log 천간/지지 데이터 통합 사례

## 배경

m-log는 사주(사주팔자) 분석 Cloudflare Workers 프로젝트로, 천간(10개) 및 지지(12개) 데이터가 3군데에 중복 정의되어 있었다.

| 위치 | 데이터 | 역할 |
|------|--------|------|
| `public/app/js/constants.js` | STEMS, BRANCHES, THREE_HARMONIES 등 | 프론트엔드 렌더링 |
| `worker.ts` (iljin 핸들러) | CHEONGAN, JIJI, tenGods, samhapGroups | POST /api/iljin 응답 생성 |
| `src/quintax/analyzer.ts` | CHEONGAN_OHANG, JIJI_OHANG | 오행 점수 계산 |

## 해결: JSON 마스터

### 생성 파일

`src/data/saju-constants.json` (3.3KB)

- 천간 10개: 문자, 오행, 음양
- 지지 12개: 문자, 오행, 음양, 장간(hidden)
- branchMainStems: 각 지지의 주요 장간
- 오행 5개: 표시용 이름, 색상
- tenGods: 10신 이름 배열
- relations: 육충, 육합, 삼합, 방합, 천간충, 천간합

### 변경된 파일

| 파일 | 변경 내용 |
|------|-----------|
| `worker.ts` | `import SAJU` → inline 배열을 `SAJU.stemList`, `SAJU.branchMainStems`, `SAJU.tenGods`, `Object.values(SAJU.relations.threeHarmonies)` 등으로 대체 |
| `src/quintax/analyzer.ts` | `import SAJU` → `CHEONGAN_OHANG`, `JIJI_OHANG`을 SAJU.stems/branches에서 파생하도록 변경 |
| `public/app/js/constants.js` | JSDoc 주석에 마스터 위치 명시 (프론트는 사본 유지) |

### 제약 조건

- **별도 Cloudflare Worker**: `worker.ts`와 `src/quintax/`는 서로 다른 Worker로 배포되어 런타임 공유 불가. JSON import는 각 Worker가 빌드 시 자체 번들에 포함하는 방식으로 해결.
- **프론트엔드/백엔드 경계**: 브라우저는 Node.js/Workers의 JSON import 메커니즘을 사용할 수 없음. 프론트는 독립 사본 유지.

### 검증

변경 전후 iljin API 응답이 동일함을 확인:

```bash
# Before: inline data → after: SAJU import
# Both produce:
curl -s http://localhost:8787/api/iljin -X POST \
  -H "Content-Type: application/json" \
  -d '{"dayMaster":"甲","monthBranch":"寅","targetYear":2026,"targetMonth":6}'
# → success: true, days: 30, first.ganji: "丙午"
```
