---
title: SEO Article Harvester — 크롤링 도구 참고자료
type: document
space: concept
tags: [concept]
created: 2026-05-20
updated: 2026-05-20
links:
  - "[[@action/skills/SKILL-INDEX]]"
  - "[[skills/seo-article-harvester/SKILL]]"
---



# SEO Article Harvester — 크롤링 도구 참고자료

## Scrapling (https: //github.com/D4Vinci/Scrapling)

Python 라이브러리. Cloudflare 우회 + 동적 페이지 렌더링 지원.

### 설치
```bash
pip install scrapling
```

### 기본 사용법
```python
import scrapling
import asyncio

async def crawl(url): 
    page = await scrapling.async_get(url)
    # CSS selector로 본문 추출
    content = page.as_etree()
    article = content.cssselect("article") or content.cssselect("main")
    if article: 
        text = " ".join(article[0].itertext())
    return text[: 3000]

asyncio.run(crawl("https: //example.com/article"))
```

### Cloudflare 우회
Scrapling은 Cloudflare 체크 시 자동으로 우회 시도. User-agent, cookie handling 내장.

### 주의
- asyncio 기반 — 동기 코드에서 호출 시 `asyncio.run()`으로 감싸야 함
- 동적 페이지 렌더링 시 최대 30초 대기

---

## Firecrawl

MCP server로 동작. Mendable의 웹 크롤링 엔진.

### 설치 (MCP server)
```bash
npx -y @mendable/firecrawl-mcp
```

### 사용법 (MCP tool call)
```
mcp__firecrawl__crawl --url "https: //example.com/article"
```

### 반환 구조
```json
{
  "title": "Article Title"
  "content": "Full article text..."
  "url": "https://example.com/article"
  "timestamp": "2025-05-14T..."
}
```

### 특징
- Readability 내장 — 본문만 추출
- Cloudflare/Bot 탐지 우회
- 배치 크롤링 지원

---

## Related
- [[skills/seo-article-harvester/SKILL]]

- [[@action/skills/SKILL-INDEX]]

