---
title: opencode-knowledge-convention
trigger: "Knowledge management convention for @drewgent/opencode-knowledge plugin"
provenance:
  session: "2026-07-04 memory-bank-plugin-discussion"
  decision: "plugin hooks 버그로 인해 규칙 강제로 대체. 호출되면 자동으로 동작."
created: 2026-07-04
---

# Knowledge Management Convention

이 convention은 `@drewgent/opencode-knowledge` 플러그인 설치 시 적용된다.
`remember()`, `recall()`, `memory-stats()` 툴이 제공될 때 반드시 따라야 할 규칙.

## Rules (Tier 1 — Autonomous)

### R1: 세션 시작 시 자동 recall
```
세션 시작 직후, 무조건 recall("recent decisions|active context") 호출
결과가 있으면 system context에 통합하여 응답 품질 향상
```

### R2: 과거 맥락 언급 시 즉시 검색
```
사용자가 "저번에", "아까", "전에", "그때", "예전에" 등 과거 맥락 언급
→ 지체 없이 recall() 호출 후 응답
```

### R3: 결정/선호/패턴 발견 시 즉시 저장
```
다음 패턴 발견 시 remember()로 즉시 저장:
- 명시적 결정 ("이걸로 하자", "X 선택")
- 사용자 선호 ("나는 Y 방식이 좋아")
- 반복 작업 패턴 ("이건 항상 Z로 해결")
- 아키텍처 결정 ("이유 때문에 X 선택")
- 금지/규칙 ("절대 하지마")
```

### R4: 세션 종료 시 저장 확인
```
세션이 자연스럽게 종료될 때:
- memory-stats() 호출
- 오늘 저장된 사실이 0이면, 놓친 게 없는지 확인
```

### R5: Secrets 절대 저장 금지
```
API key, 토큰, 비밀번호, 개인정보는 절대 remember()로 저장하지 않음
→ vault_cli가 canonical path
→ 실수로 들어갔으면 즉시 remove (수동)
```

## Storage

- **파일 위치**: `~/.drewgent/.opencode/knowledge.db`
- **엔진**: SQLite + FTS5 (built-in full-text search)
- **FTS5 기능**: stemming, ranking, phrase matching, boolean operators
- **types**: fact, decision, preference, pattern, session
- **세션 저장**: sessions 테이블 (id, title, message_count)
- **보안**: 평문. secrets 저장 금지.

## 의존성

- opencode 1.17.10+
- tools/ 디렉토리 자동 발견 기능
- 별도 서버/DB/API key 불필요
