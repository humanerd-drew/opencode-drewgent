# AGENTS.md Template

> 프로젝트 루트에 두는 AI 에이전트 길잡이 파일. 모든 세션에서 가장 먼저 읽는다.

## Why AGENTS.md

프로젝트 구조가 아무리 직관적이어도, **에이전트는 검색 키워드로 파일을 찾는다**. AGENTS.md는 검색어→파일 경로 맵 + 프로젝트별 컨벤션 + 현재 상태를 한 파일에 담는다.

## Template

```markdown
# {프로젝트명} Agent Map

> 이 파일을 먼저 읽어라. 폴더 구조와 파일명 규칙을 정의한다.

## 원칙
- **src/ 하나만** — 모든 소스코드가 src/ 아래에 있음
- **도메인 기준 분리** — {도메인1}, {도메인2}, ...
- **파일명 = 동사-명사.kebab-case.ts** — 검색어로 바로 찾을 수 있게
- **AGENTS.md 먼저 읽을 것**

## 디렉토리 구조
```
src/
├── {domain1}/    설명
├── {domain2}/    설명
└── {domain3}/    설명
```

## 파일명 규칙
- `동사-명사.kebab-case.ts`
- 예: `verify-payment.ts`, `get-compatibility.ts`
- 검색어 = 파일명의 일부

## 자주 찾는 것
| 검색어 | 파일 |
|---|---|
| {기능1} | `src/{domain}/{file}.ts` |
| {기능2} | `src/{domain}/{file}.ts` |

## 백엔드 패턴
```
api/route-xxx.ts (라우터) → {domain}/{logic}.ts (비즈니스 로직) → db/{query}.ts (DB)
```

## 현재 상태
- ✅ 완료된 작업
- 🚧 진행 중인 작업
- ⬜ 남은 작업
```

## Rules for AI agents

1. **Always read AGENTS.md first** in any session for this project
2. **Update AGENTS.md** when adding/removing/renaming key files
3. **Search by verb** — find `verify-payment.ts` not `payment.ts`
4. **File name = what it does**, not what it is
