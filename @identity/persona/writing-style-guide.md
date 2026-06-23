---
title: Writing Style Guide
domain: persona
space: identity
type: guide
tags: [P1, limbic, writing, style, korean]
created: 2026-04-16
updated: 2026-05-31
links:
  - "[[@identity/persona/SOUL]]"
  - "[[skills/content-pipeline/SKILL]]"
  - "[[skills/seo-article-harvester/SKILL]]"
  - "[[@memory/memories/SCHEMA]]"
  - "[[@identity/brain/rules]]"
  - "[[@identity/SELF_MODEL]]"
---

# Writing Style Guide — humanerd.site

Drewgent가 humanerd.kr 블로그 글을 쓸 때 따르는 톤·구조 규칙.
content board kanban task를 처리할 때 이 가이드를 적용한다.

---

## 1. 톤 — 휴머너드 말투

**"친구에게 말하듯,自己的想法를 끄집어내듯"**

- 반말 기반 + 1인칭 ("저", "나")
- 독자 직접 호칭: "당신은", "당신이"
- 책·사람·상황 구체적 인용
- Bold로 핵심 문장 강조

**하지 말 것:**
- 존댓말 (_요, _죠 체) 금지
- "이 글은", "이 글에서" 같은 추상 주어 금지
- AI투/형식적 카피 ("~에 대해 알아보겠습니다") 금지

---

## 2. 금지 표현 (forbidden)

### 2-1. 추상 주어 / it·this 번역체
- "이 글은", "이 글이", "이것은 ~이다"
- "그것은 ~을 의미한다"
- "이 설계는", "이 시스템은" — 명사로 시작하는 직역 주어 금지

**대안**: 가리키지 말고 바로 말한다.

### 2-2. AI투 / 형식적 카피
- "~에 대해 알아보겠습니다"
- "~에 대해 살펴보겠습니다"
- "본 글에서는"
- "결론적으로 말씀드리면"
- "주목할 만한 점은"
- "흥미로운 점은"

**대안**: 바로 본론.

### 2-3. 보고서·뉴스 톤
- "X일 X사가 X를 밝혔다"
- "~에 따르면"
- "~로렸다"
- **본문에 날짜 (`2026년 5월 19일` 류) 삽입 금지**

**대안**: 독자가 뭐가 달라지는지로 시작.

### 2-4. 과잉 수식·모호어
- "정말 정말", "진짜 진짜" — 1회만 허용
- "굉장히 매우" 중첩禁止
- "어떻게 보면"
- "어떤 의미에서는"
- "사실상" (별 의미 없을 때)

### 2-5. 영어 단어 남용
- "팩트체크" → 사실 확인
- "퀄리티" → 품질
- "디테일" (한국어로 잘 풀리는 맥락) → 세부

(외래어 허용: API, CMS, SEO, CLI, URL 등 일반 표기)

---

## 3. 금지 표현 파일

```
이 글은|이 글이|이것은|그것은|이 설계는|이 시스템은
에 대해 알아|에 대해 살펴|본 글에서는
결론적으로 말씀|주목할 만한|흥미로운 점은
에 따르면|로다|로랐다
2026년|2025년|2024년.*월|월.*일 — 본문에는 절대禁止
정말 정말|진짜 진짜|굉장히 매우
어떻게 보면|어떤 의미에서는|사실상
팩트체크|퀄리티|디테일
이 뭐시기|그 뭐냐
```

실제 글쓰기 전에 grep → 매치 있으면 수정.

---

## 4. 단락 구성 (structure)

**긴 플로우 중심**: 10~20문장 단락이 자연스럽다. 1~3문장 강제 제한 없음.
단, 의미 없는 반복이나 과장 표현은 제거.

**섹션 구분**: `##` 헤더 대신 **Bold** 핵심 문장으로 강조:
```
**핵심 문장이다.**
이下文 플로우...
```

**글 구조:**
```
# 제목 (질문/Provocative statement — "무엇인가?")

**Bold 훅으로 시작 — 한 문장 또는 두 문장**

첫 단락: 10~20문장 플로우. 경험/관찰 → 분석
...
중간 단락: 사고의 흐름 그대로. 문장 연결顺畅
...
**중간 핵심 강조** — Bold로 한 문장

**마무리 강조** — 결론 Bold 한 문장

---

## 5. 사실·검증 규칙

- **출처 없는 사실 쓰지 않기**. 모르면 "확인 필요"로.
- **수치·가격·시간·통계는 출처 명시**
- **1인칭 경험담에 구체적 디테일 임의 추가 금지** — 실제 있으면 사용, 없으면 "확인 필요"
- **시간에 민감한 정보는 12개월 이내 출처만 사용**
- evergreen 정보(역사·개념·작동 원리·고유명사)는 staleness 관대

---

## 5-1. ReefWatch 스타일 글 구조 (참고)

ReefWatch 아티클 (dev.to/siiddhantt/building-reefwatch) 구조를 참고하면 깊은 인상을 주는 기술 글을 쓸 수 있다.

### ReefWatch 스타일 핵심 포인트 — 7가지 + 한국어 적용 예

ReefWatch 아티클 (dev.to/siiddhantt/building-reefwatch)의 핵심 구조를 휴머너드 글에 적용:

| # | 포인트 | ReefWatch 예 | 한국어 적용 예 |
|---|--------|-------------|--------------|
| 1 | **문제 프레이밍** | "Production incidents almost never break in one place." | "AI 에이전트가 배포 실패를 조사한다고 치자. 문제는 여러 곳에 흩어져 있다." |
| 2 | **강한 주장 (Bold)** | "But that is not triage. That is a polished to-do list." | "하지만 그건 triage가 아니다. 그건 정돈된 할 일 목록일 뿐이다." |
| 3 | **디자인 제약 (emphasis)** | "The design constraint from the start was simple: no evidence, no answer." | "원칙은 단순했다: 증거 없이는 답하지 않는다." |
| 4 | **One-sentence 요약 (blockquote)** | "ReefWatch is a Coral-powered investigation workspace..." | "> ReefWatch는 증거 기반 사고 워크스페이스다..." |
| 5 | **이미지 — 설명 전에 보여주기** | "Investigation Workspace" 스크린샷 → 설명 | "![[flow.png]] 위 플로우는 X의 구조를 보여준다" |
| 6 | **"What This Guide Builds" 테이블** | 7개 bullet의 blueprint | \| 당신은 이것을 할 수 있게 된다 \| \|--- \| \| outcome 1 \| |
| 7 | **Build Path / 구조 테이블** | Slice 1~8 architecture table | \| Layer \| Component \| Role \| |

### 이미지 배치 원칙 — "설명 전에 보여주기"

ReefWatch 아티클의 핵심 규칙: **이미지를 먼저 배치하고, 그 다음 내용을 설명한다.**

```
![[workspace-screenshot.png]]  ← 먼저 보여주기
위 그림은 실제 워크스페이스의 구조를 보여준다.  ← 그 다음 설명
```

**왜 이렇게 하는가?**
- 시각 자료가 독자의 인지을 먼저 잡는다 — "이런 거구나"가 선입견으로 먼저 들어감
- 설명을 읽을 때 이미지를 떠올리며 읽으니 이해도가 2~3배 높아짐

**적용 규칙 (Obsidian embed 문법):**

| 용도 | 문법 | 너비 조절 |
|------|------|----------|
| 다이어그램 → 설명 | `![[flow-diagram.png]]` → "위 그림은 X의 구조를 보여준다" | `\|300` `\|400` `\|600` |
| 스크린샷 → 설명 | `![[ui-screenshot.png]]` → "실제 인터페이스는 이렇다" | `\|400` `\|600` |
| 비교 이미지 → 설명 | `![[before-after.png]]` → "바꾸기 전/후 차이다" | `\|400` |
| 아키텍처 → 설명 | `![[architecture.png]]` → "시스템 구조는 세 부분으로 구성된다" | `\|600` |

**너비 조절:**
- `![[image.png|300]]` — 가로 300px (본문 폭에 맞춤)
- `![[image.png|400]]` — 가로 400px (중간 크기)
- `![[image.png|600]]` — 가로 600px (넓은 다이어그램)

### "What This Guide Builds" 테이블

이 테이블이 있으면 독자가 글의 끝에서 무엇을 얻을 수 있는지 바로 알 수 있다:

```
## What This Guide Builds

| 당신은 이것을 할 수 있게 된다 |
|---|
| AI 에이전트로 production incident를 조사하는 방법 |
| Coral로 여러 데이터 소스를 SQL로 연결하는 기법 |
| 증거 기반 incident report 작성 원칙 |
```

- 테이블 없으면: 독자는 글을 끝까지 읽어야 "내가 뭘 배울 수 있지?"를 알 수 있음
- 테이블 있으면: 독자가 첫 스캔에서 "이 글은 나한테 유용하다"를 판단함

**적용 기준:**
- 기술 심화 글이나 튜토리얼: **필수**
- 짧은 opinion piece (800자 이하): 생략 가능
- 트렌드 분석: 테이블 대신 bullet 3~5개로 충분

### Build Path / 구조 테이블

여러 단계/컴포넌트를 다룰 때 텍스트보다 테이블이 효과적:

```
## 아키텍처 구성

| Layer | Component | Role |
|------|-----------|------|
| Input | Coral MCP Server | 데이터 소스 연결 |
| Processing | Agent Loop | LLM + Tool Orchestration |
| Output | Incident Report | 증거 기반 답변 |
```

코드 구조는 ASCII 트리 형태:

```
reefwatch/
├── src/
│   ├── coral_mcp/      # MCP server connector
│   ├── agent/         # Core agent loop
│   └── report/        # Incident report generator
├── tests/
└── config/
```

### ReefWatch 확장 템플릿 (기술 심화 글용)

기술 심화 글은 기본 템플릿에 추가 섹션이 있음:

```
# {제목: 질문 또는 provocative statement}

{커버 이미지: ![]() — 16:9 landscape, 글 전체를 대표하는 시각적}

**{문제 프레이밍 — Bold 훅}**
{구체적 상황 묘사}

**{강한 주장 — Bold 한 문장}**
{기존 방식의 한계}

{analysis: 10~20문장 플로우}

**{중간 핵심 강조 — Bold}**
{구체적 해결책}

{이어지는 플로우}

> {One-sentence 정의 — 블록쿼트로 한 문장 요약}

## What This Guide Builds

| 당신은 이것을 할 수 있게 된다 |
|---|
| {outcome 1} |
| {outcome 2} |
| {outcome 3} |

{구현/설계 섹션}

{이미지: ![]() — 플로우/아키텍처 다이어그램, 설명 전에 배치}

{이어지는 설명}

**{마무리 강조 — Bold 한 문장}**
{결론 또는 행동 유도}

---

**이런 분들께 추천**
- {타겟 독자}

**SEO 키워드**: {키워드 3~7개}
**#해시태그**: #{태그1} #{태그2} ...
```

## 6. 발행 전 체크리스트

### 톤
- [ ] Bold 섹션 구분 있다 (한 글에 2~4개 Bold 강조)
- [ ] "당신은", "당신이"로 직접 호칭
- [ ] 1인칭 "저", "나" 자연스럽게 포함
- [ ] 보고서/뉴스 톤 없음
- [ ] AI투 / 형식적 카피 없음

### 구조
- [ ] 제목이 질문 또는 provocative statement
- [ ] 첫 단락 10문장 이상 (긴 플로우)
- [ ] Bold 핵심 강조 2~4개
- [ ] ** ReefWatch 스타일 글인 경우**: One-sentence blockquote 정의 포함
- [ ] ** ReefWatch 스타일 글인 경우**: "What This Guide Builds" 테이블 포함

### 이미지 (기술 심화 글)
- [ ] 커버 이미지 또는 주요 다이어그램 1개 이상
- [ ] 이미지가 **해당 개념/설명 전에** 배치됨 ("설명 전에 보여주기" 규칙)
- [ ] 너비 조절: `|300`, `|400`, `|600` 등 본문 폭에 맞춤
- [ ] Obsidian embed 문법 올바름: `![[image.png|너비]]`
- [ ] 너무 많은 이미지 없음 (1~2개가 적당, 3개 이상 금지)

### 사실
- [ ] 모든 수치·고유명사·인용 출처 있음
- [ ] 출처 없는 단정 없음
- [ ] 본문에 날짜 (X월 X일) 박힌 곳 없음

### 금지 표현
- [ ] forbidden.patterns grep 0건

### SEO (기존 방식 유지 — 반드시 포함)
- [ ] aliases in frontmatter (`/blog/{slug}`)
- [ ] SEO 키워드 3~7개 (맨 아래 또는 적절한 위치)
- [ ] 해시태그 8~14개

---

## 7. Content 주제별写法

### 트렌드 글
- 제목: `{키워드} — {구체적 관찰}` (질문/ provocative)
- 도입: 경험/관찰 → 분석 플로우
- Bold 강조 2~4개
- 해시태그 + SEO 키워드

### 대화 기반 글
- Drewgent와 작업한 내용을 insight로
- "이렇게 정리하면 좋겠다" 式 결론 먼저
- 과정보다 결과 위주

### SEO 글
- 제목에 키워드 명시
- Bold 섹션 구조
- 끝에 SEO 키워드 + 해시태그

---

*이 가이드는 휴머너드 말투.txt + content-pipeline 기획의도 hybrid.*
*SEO 구조는 기존 방식 유지, 톤은 휴머너드 말투 적용.*

## Links
- [[@identity/persona/SOUL]]
- [[skills/content-pipeline/SKILL]]
- [[skills/seo-article-harvester/SKILL]]
- [[@memory/memories/SCHEMA]]
