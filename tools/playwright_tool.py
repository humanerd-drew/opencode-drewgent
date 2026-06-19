#!/usr/bin/env python3
"""
Playwright Browser Tool for Drewgent Agent (MiniMax M2.7 Compatible)

Vision 없이 DOM/text 기반으로 UI 분석 및 조작이 가능합니다.

주요 기능:
- URL 이동 및 내용 추출
- DOM 요소 클릭/입력
- 텍스트 기반 UI 분석
- JavaScript 실행
"""

import asyncio
import json
import os
import re
from typing import Any, Dict, List, Optional
from pathlib import Path

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


# Global browser instance
_browser: Optional[Browser] = None
_context: Optional[BrowserContext] = None


async def get_browser() -> Browser:
    """Get or create browser instance"""
    global _browser
    if _browser is None or not _browser.is_connected():
        playwright = await async_playwright().start()
        _browser = await playwright.chromium.launch(headless=True)
    return _browser


async def get_context() -> BrowserContext:
    """Get or create browser context"""
    global _context
    browser = await get_browser()
    if _context is None or not _context.browser:
        _context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        )
    return _context


async def pw_navigate(url: str, wait_until: str = "domcontentloaded") -> Dict[str, Any]:
    """Navigate to URL and return page info"""
    context = await get_context()
    page = await context.new_page()

    try:
        response = await page.goto(url, wait_until=wait_until, timeout=30000)

        # Get basic info
        title = await page.title()
        url = page.url

        # Get text content (no screenshots for text model)
        content = await page.content()

        # Extract text content
        text_content = await page.inner_text("body")

        # Get links
        links = await page.query_selector_all("a")
        link_info = []
        for link in links[:50]:  # Limit to 50
            href = await link.get_attribute("href")
            text = await link.inner_text()
            if href:
                link_info.append({"text": text.strip(), "href": href})

        # Get forms
        forms = await page.query_selector_all("form")
        form_info = []
        for form in forms[:10]:
            action = await form.get_attribute("action")
            method = await form.get_attribute("method")
            inputs = await form.query_selector_all("input")
            form_info.append(
                {"action": action, "method": method, "input_count": len(inputs)}
            )

        # Get headings
        headings = {}
        for tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            els = await page.query_selector_all(tag)
            headings[tag] = [await el.inner_text() for el in els[:10]]

        await page.close()

        return {
            "success": True,
            "url": url,
            "title": title,
            "status": response.status if response else None,
            "text_content": text_content[:5000],  # Limit text
            "links": link_info,
            "forms": form_info,
            "headings": headings,
            "content_length": len(content),
        }

    except Exception as e:
        await page.close()
        return {"success": False, "error": str(e)}


async def pw_click(selector: str) -> Dict[str, Any]:
    """Click an element"""
    context = await get_context()
    page = await context.new_page()

    try:
        # Find the element
        element = await page.query_selector(selector)
        if not element:
            await page.close()
            return {"success": False, "error": f"Element not found: {selector}"}

        # Get element info before click
        tag = await element.evaluate("el => el.tagName")
        text = await element.inner_text()

        # Click
        await element.click(timeout=5000)
        await page.wait_for_load_state("domcontentloaded")

        # Get result
        title = await page.title()
        new_url = page.url

        await page.close()

        return {
            "success": True,
            "clicked": {"tag": tag, "text": text[:100]},
            "new_url": new_url,
            "title": title,
        }

    except Exception as e:
        await page.close()
        return {"success": False, "error": str(e)}


async def pw_type(
    selector: str, text: str, press_enter: bool = False
) -> Dict[str, Any]:
    """Type into an element"""
    context = await get_context()
    page = await context.new_page()

    try:
        element = await page.query_selector(selector)
        if not element:
            await page.close()
            return {"success": False, "error": f"Element not found: {selector}"}

        await element.fill(text)

        if press_enter:
            await element.press("Enter")

        await page.wait_for_load_state("domcontentloaded")

        await page.close()

        return {"success": True, "typed": text[:100], "new_url": page.url}

    except Exception as e:
        await page.close()
        return {"success": False, "error": str(e)}


async def pw_extract(selector: str) -> Dict[str, Any]:
    """Extract content from selector"""
    context = await get_context()
    page = await context.new_page()

    try:
        elements = await page.query_selector_all(selector)

        results = []
        for el in elements[:20]:  # Limit to 20
            tag = await el.evaluate("el => el.tagName")
            text = await el.inner_text()
            html = await el.inner_html()
            results.append({"tag": tag, "text": text.strip()[:500], "html": html[:500]})

        await page.close()

        return {"success": True, "count": len(results), "elements": results}

    except Exception as e:
        await page.close()
        return {"success": False, "error": str(e)}


async def pw_snapshot() -> Dict[str, Any]:
    """Get current page snapshot (text only, no screenshot)"""
    context = await get_context()
    pages = context.pages

    if not pages:
        return {"success": False, "error": "No active pages"}

    page = pages[-1]

    try:
        title = await page.title()
        url = page.url
        text_content = await page.inner_text("body")

        # Get visible text
        visible_text = await page.evaluate("""
            () => {
                const elements = document.querySelectorAll('p, h1, h2, h3, h4, h5, h6, li, td, th, span, div');
                return Array.from(elements)
                    .filter(el => el.offsetParent !== null)
                    .map(el => el.innerText.trim())
                    .filter(t => t.length > 0)
                    .slice(0, 100)
                    .join('\\n');
            }
        """)

        return {
            "success": True,
            "url": url,
            "title": title,
            "text_content": text_content[:5000],
            "visible_text": visible_text[:3000],
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


async def pw_evaluate(script: str) -> Dict[str, Any]:
    """Execute JavaScript"""
    context = await get_context()
    pages = context.pages

    if not pages:
        return {"success": False, "error": "No active pages"}

    page = pages[-1]

    try:
        result = await page.evaluate(script)
        return {"success": True, "result": str(result)[:1000]}
    except Exception as e:
        return {"success": False, "error": str(e)}


# Tool schemas
TOOLS = {
    "pw_navigate": {
        "name": "pw_navigate",
        "description": "Navigate to a URL and extract page content (text-based, no screenshots). Returns title, text content, links, forms, and headings.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to navigate to"},
                "wait_until": {
                    "type": "string",
                    "description": "When to consider loaded: 'domcontentloaded', 'load', 'networkidle'",
                    "default": "domcontentloaded",
                },
            },
            "required": ["url"],
        },
    },
    "pw_click": {
        "name": "pw_click",
        "description": "Click an element by CSS selector. Returns new page state.",
        "parameters": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS selector (e.g., 'button', '#id', '.class', 'a[href]')",
                }
            },
            "required": ["selector"],
        },
    },
    "pw_type": {
        "name": "pw_type",
        "description": "Type text into an input field. Optionally press Enter.",
        "parameters": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS selector for input element",
                },
                "text": {"type": "string", "description": "Text to type"},
                "press_enter": {
                    "type": "boolean",
                    "description": "Press Enter after typing",
                    "default": False,
                },
            },
            "required": ["selector", "text"],
        },
    },
    "pw_extract": {
        "name": "pw_extract",
        "description": "Extract content from elements matching a CSS selector.",
        "parameters": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "CSS selector"}
            },
            "required": ["selector"],
        },
    },
    "pw_snapshot": {
        "name": "pw_snapshot",
        "description": "Get current page snapshot (URL, title, text content). No screenshot.",
        "parameters": {"type": "object", "properties": {}},
    },
    "pw_evaluate": {
        "name": "pw_evaluate",
        "description": "Execute arbitrary JavaScript on the page.",
        "parameters": {
            "type": "object",
            "properties": {
                "script": {
                    "type": "string",
                    "description": "JavaScript code to execute",
                }
            },
            "required": ["script"],
        },
    },
}


if __name__ == "__main__":
    # Test
    async def test():
        result = await pw_navigate("https://example.com")
        print(json.dumps(result, indent=2))

    asyncio.run(test())
