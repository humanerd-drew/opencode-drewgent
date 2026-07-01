---
name: im-not-ai
description: "AI(ChatGPT·Claude·Gemini)가 쓴 한글 텍스트를 사람이 쓴 글처럼 윤문한다. 번역투·영어인용·기계적병렬·AI관용구·피동태·접속사·리듬균일·이모지 등 10카테고리 60+ 패턴 탐지. 'AI 티 없애줘', '번역투 고쳐', '사람이 쓴 것처럼' 트리거."
trigger: "WordPress 콘텐츠 작성 전 반드시 로드. Korean text humanization."
source: "https://github.com/epoko77-ai/im-not-ai (MIT)"
created: 2026-06-26
updated: 2026-06-26
links:
  - "[[creative/humanizer]]"
  - "[[../P1-limbic/persona/writing-style-guide]]"
---

# im-not-ai — 한글 AI 티 제거기

**반드시 읽을 것:** 이 스킬은 WordPress 한글 콘텐츠 생성 전에 **항상** 로드한다 (`writing-style-guide.md §8`).

AI가 쓴 한국어 텍스트의 AI 티를 탐지·제거한다. 내용은 건드리지 않고 문체·리듬·표현만 자연스럽게 바꾼다.

## 분류 체계 (10대 카테고리)

| ID | 대분류 | 예시 |
|----|--------|------|
| A | **번역투** | ~를 통해, ~에 대해, ~에 있어서, 이중 피동 |
| B | 영어 인용·용어 과다 | 괄호 병기, 번역 가능한 영어 그대로 |
| C | 구조적 AI 패턴 | 첫째/둘째/셋째, 불릿·헤딩 과다, 연결어미 뒤 쉼표 |
| D | AI 특유 관용구 | 결론적으로, 시사하는 바가 크다, 주목할 만하다 |
| E | 리듬 균일성 | 문장 길이 표준편차 낮음, 종결어미 반복 |
| F | 수식·중복 | 매우, 정말, ~적/~성/~화 |
| G | Hedging | ~할 수 있을 것으로 보인다 |
| H | 접속사 남발 | 또한/따라서/즉/나아가 문두 연속 |
| I | 형식명사 과다 | 것, 점, 수, 바, ~할 필요가 있다 |
| J | 시각 장식 남용 | 과도한 볼드/따옴표/대시 |

## 철칙

1. **의미 불변** — 사실·주장·수치·고유명사·인용문 100% 보존
2. **근거 기반** — 분류 체계에 없는 구간은 건드리지 않음
3. **과윤문 금지** — 변경률 30% 초과 시 경고, 50% 초과 시 롤백

## 사용법

텍스트를 붙여넣고 요청:
- "AI 티 없애줘"
- "번역투 고쳐줘"
- "사람이 쓴 것처럼 윤문해줘"

## 참고 파일

- `references/quick-rules.md` — 슬림 룰북 (S1/S2 핵심 패턴)
- `references/ai-tell-taxonomy.md` — 분류 체계 본진 (60+ 패턴)
- `references/rewriting-playbook.md` — 카테고리별 처방
- `references/scholarship.md` — 학술 인용 SSOT
