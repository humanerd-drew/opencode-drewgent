---
title: notion-knowledge-sync
trigger: "사용자가 특정 도메인의 지식을 정리/조회할 때 — Notion을 집필 환경으로, 로컬 md를 에이전트 메모리로 연결"
provenance:
  session: "2026-07-08 pilates-knowledge-architecture"
  decision: "3-layer Lazy Fresh Cache: INDEX.md (경량 인덱스) + md cache (검색/크로스리ference 가능) + Notion API (stale 검증). 중간 레이어인 플러그인/MCP가 아닌 스킬로 선택 — Notion MCP가 인터페이스를 이미 제공하므로 패턴만 문서화"
created: 2026-07-08
tags: [brain, notion, knowledge, sync, cache]
---

# Notion Knowledge Sync

Notion 페이지를 에이전트의 **추론 가능한 로컬 메모리**로 동기화하는 패턴.

## 철학

```
Notion (집필/수정 환경 + Notion AI)  ── Lazy Fresh Cache ──▶  Agent (추론/맥락 환경)
       ↑ 항상 최신, 사람이 편집                           ↑ stale 위험, 복사본
       ↑ 사용자의 작업 중심지                              ↑ grep/cross-ref/추론 가능해야 함
```

**핵심 원칙:** "항상 Notion에 물어보지 않는다" — 로컬 md로 추론하고, 의심될 때만 확인한다.

## 아키텍처: 3-Layer Lazy Fresh Cache

```
Layer 1: INDEX.md
  - "무엇이 존재하는가" + "무엇이 어디에 연결되어 있는가"
  - 키워드 → 페이지 매핑, 페이지 간 관계
  - 경량, 수동 관리 가능

Layer 2: md cache (P2-hippocampus/{domain}/)
  - 각 파일에 notion_id + last_edited_at (Notion의 실제 수정 시각)
  - grep/rg로 전체 검색 가능
  - 여러 페이지 동시 참조 → 크로스레퍼런스 추론

Layer 3: Notion API (실시간 검증)
  - 응답 직전에 last_edited_time만 확인 (API 1회, body 없음)
  - 변경 감지 시에만 re-fetch
```

## 디렉토리 구조

```
P2-hippocampus/{domain}/
├── INDEX.md               # 키워드 맵 + 관계 그래프
├── _cache_meta.json       # stale 감지 시계 (notion_id → last_edited_at)
│
├── theory/                # 이론, 역사, 원리
├── exercise/              # 실전, 방법론, 시퀀스
├── business/              # 운영, 마케팅, 전략
├── references/            # 참고자료, 논문
└── ...                    # 도메인에 따라 카테고리 자유롭게
```

## _cache_meta.json 스키마

```json
{
  "$schema": "loragent:notion-knowledge-sync:cache-meta:v1",
  "domain": "pilates",
  "created_at": "2026-07-08T12:00:00Z",
  "notion_search_query": "필라테스",
  "entries": [
    {
      "notion_id": "11ba7532-...",
      "local_path": "theory/neuro-aroma-course.md",
      "title": "뉴로아로마 필라테스 전문가 자격과정",
      "last_edited_at": "2026-07-07T09:09:00Z",
      "last_synced_at": "2026-07-08T12:00:00Z",
      "category": "theory",
      "tags": ["neuro-aroma", "curriculum", "certification"],
      "relations": [
        {"target": "리포머-뉴로아로마.md", "type": "실전적용"},
        {"target": "50분-레슨-전략.md", "type": "비즈니스연계"}
      ]
    }
  ]
}
```

## Agent 행동 규칙

### 지식 요청 시

```
1. 요청받은 주제로 P2-hippocampus/{domain}/ 검색 (grep/rg)
2. 찾은 md 파일들의 frontmatter / _cache_meta.json 확인
3. last_edited_at != Notion 현재 last_edited_time 이면:
   → API로 re-fetch 후 md 갱신
   → _cache_meta.json 갱신
4. fresh 캐시로 응답 구성
5. 관련 페이지도 같이 로드 (INDEX.md relations 참조)
```

### 새 도메인 초기화 시

```
1. 사용자 키워드 수신
2. Notion API search: keyword로 검색 → 전체 목록 확보 (has_more 처리)
3. 분류:
   - DB 타입 → API 전용 (구조 보존)
   - Page 타입 → 핵심/상황형/제외 로 Tier 분류
4. INDEX.md 생성 (키워드 맵 + 관계 추론)
5. 핵심 페이지 md 캐싱
6. _cache_meta.json 생성
7. 완료 보고
```

### 크로스레퍼런스 규칙

- INDEX.md의 `relations` 배열은 양방향 — A→B 관계를 발견하면 B→A도 자동 추가
- "이 주제 조회 시 연관 페이지도 같이 로드"는 relations에 따라 결정
- 크로스레퍼런스는 Agent의 판단으로 보강 가능 (INDEX.md는 기본 맵)

## stale 감지 전략

| 상황 | 동작 |
|------|------|
| 캐시 없음 (신규) | Notion API로 fetch |
| last_edited_at 동일 | 캐시 사용 (API 호출 0) |
| last_edited_at 다름 | re-fetch 후 갱신 |
| Notion API 실패 | 캐시 사용 + "캐시 사용 (Notion 응답 없음)" 명시 |
| 페이지 삭제됨 | 캐시에 `archived: true` 표시, 사용자에게 알림 |

## 에이전틱 메모리 부합 여부 체크리스트

- [x] 로컬 md = grep/크로스레퍼런스/동시참조 가능 → 추론에 직접 사용
- [x] last_edited_at으로 시의성 확보 → 과거 데이터로 답변 방지
- [x] API 호출 최소화 (실제 변경됐을 때만) → 효율
- [x] 페이지 간 관계를 INDEX.md에 명시 → 맥락 누락 방지
- [x] 캐시와 API의 명시적 분리 → "이건 캐시다" 메타인지 가능

## Notion API 사용법 요약

| 작업 | 툴 |
|------|-----|
| 키워드 검색 | `notion_API-post-search(query, page_size=100)` |
| 페이지 내용 | `notion_API-retrieve-page-markdown(page_id)` |
| DB 쿼리 | `notion_API-query-data-source(data_source_id, filter/sorts)` |
| 메타만 확인 | `notion_API-retrieve-a-page(page_id)` (properties만, body 없음) |

## upstream 컨트리뷰션 노트

- 위치: `@action/skills/brain/notion-knowledge-sync/`
- 의존성: Notion MCP (`@notionhq/notion-mcp-server`) — opencode.jsonc에 등록 필수
- 기존 `knowledge.db`/`recall` 시스템과 보완 관계 (대체 아님)
- `sync-template.sh`로 템플릿 푸시 시 `notion-indexer.py` 내 토큰 참조 `{env:NOTION_TOKEN}`인지 확인
