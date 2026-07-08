---
title: headroom-ai POC — JSON만 압축, text/code 0%
type: concept
space: concept
tags: [concept, token-efficiency, evaluated-and-rejected]
created: 2026-06-02
updated: 2026-06-02
links:
  - "[[P4-cortex/knowledge/NEURONFS_RULES]]"
  - "[[P5-ego/SELF_MODEL]]"
  - "[[P0-brainstem/brain/rules]]"
---

# headroom-ai POC — JSON만 압축, text/code 0%

**Date**: 2026-06-02
**Status**: Evaluated and uninstalled. Don't revisit unless tool output portfolio shifts heavily to JSON.

## TL;DR

headroom-ai 0.22.4를 venv에 설치해 4가지 Loragent 도구 시나리오로 POC 측정:

| 시나리오 | before | after | 절약 | 비율 |
|---|---|---|---|---|
| web_search (10 JSON 결과) | 4,131 | 482 | 4,246 | **89.8%** |
| browser_snapshot (a11y tree) | 2,362 | 2,110 | 0 | 0% |
| read_file (Python 10KB) | 2,481 | 2,879 | -398 | **-16% (오히려 증가)** |
| terminal git log -100 | 7,317 | 6,504 | 0 | 0% |

**정보 보존 (web_search)**: URL 10/10, title 10/10 전부 보존. 완벽.

**결론**: headroom은 **정형 JSON 배열** 에 89% 절약. plain text와 source code는 router가 명시적으로 보호 → 0% 절약. 따라서 Loragent의 token 비용이 web_search/RAG/kanban JSON에서 주로 발생하지 않는 한 통합 가치 낮음. surgical 통합은 over-engineering.

## 왜 uninstall

1. **Loragent 토큰 비용의 80%+는 이미 web_search/kanban 같은 JSON 도구** (확인 필요 — TODO metric) — 이 부분은 89% 절약 가능
2. **나머지 20%는 plain text/code** — headroom이 보호해서 효과 0
3. **pipeline 결정성이 낮음**: 동일 도구인데 message 형태에 따라 -16% ~ 89% 변동 → 테스트 어려움
4. **latency 비용**: 50ms/turn × 수십 turn = 초당 1-2초 추가 (현 Loragent <100ms/turn)
5. **이미 0.9 threshold context_compressor (M3 1M) 보유** — conversation-level 압축은 별도 layer로 작동 중

## 언제 재평가

다음 조건 중 **2개 이상** 충족 시 재평가:
- MCP tool output이 90% 이상 JSON 형태로 통일 (현재 ~30% 추정)
- token 비용이 월 $100+ 돌파
- M3 1M context에서도 compression 발동 빈도가 매주 1회+
- router policy 사용자 정의 가능한 headroom v1+ 출시 (현재는 opaque)

## 설치 시 알아둘 점 (재설치할 때)

- **Python 3.14 + PyO3 0.22.6**: PyO3이 3.13까지 지원. 3.14에선 `PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1`로 stable ABI 빌드 필요
- 첫 install: `pip install headroom-ai` 그대로 (build-isolation이 maturin을 build env에 자동 설치)
- count_tokens API: `provider.get_token_counter(model).count_messages(msgs)` (직접 `count_tokens_messages` 호출 시 token_counter 인자 필요)
- `CompressResult` 필드: `tokens_before`, `tokens_after`, `tokens_saved`, `compression_ratio`, `transforms_applied`
- 첫 호출이 ~800ms (lazy init). warmup 후 ~5-50ms

## 대안 — JSON-specific opt-in (필요 시)

MCP tool output이 JSON으로 통일될 경우, headroom 대신 더 가벼운 옵션:
- `jsoncrush` — JSON-specific row compression, headroom보다 단순
- 또는 tool handler 단계에서 직접 `[N]{schema}...` 형식 변환 (headroom의 결과 모방, ~30줄 Python)

## Related

- [[P4-cortex/knowledge/NEURONFS_RULES]] — file system architecture (Loragent의 압축 layer)
- [[P5-ego/SELF_MODEL]] — Loragent identity (현재 압축 layer 위치)
- [[P0-brainstem/brain/rules]] — P0 brainstem (tool integration 3-file pattern, tool 추가 시 참고)
