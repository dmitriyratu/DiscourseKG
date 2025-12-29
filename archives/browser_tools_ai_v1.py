"""AI-powered browser tools using Crawl4AI (Playwright-based) for intelligent web scraping."""

import asyncio
import json
import re
import sys
from contextlib import asynccontextmanager
from typing import Dict, List, Optional
from urllib.parse import urlparse, urljoin

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
from selectolax.parser import HTMLParser

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Windows async support for Playwright
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Shared Browser Configuration
BROWSER_CONFIG = BrowserConfig(
    headless=True,
    verbose=False,
    user_data_dir="./.browser_cache", 
    extra_args=["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"],
)

def _is_valid_url(url: str) -> bool:
    """Returns True if URL has http/https scheme and domain."""
    try:
        result = urlparse(url)
        return bool(result.scheme in ("http", "https") and result.netloc)
    except Exception:
        return False

def _get_interactive_elements(html_content: str) -> List[Dict]:
    """Returns interactive element metadata for the agent to analyze."""
    try:
        tree = HTMLParser(html_content)
        candidates = tree.css("button, a, [role='button'], input[type='button'], input[type='submit']")
        elements = []

        for elem in candidates:
            href = elem.attributes.get("href")
            
            # Skip mailto/tel links
            if href and href.startswith(("mailto:", "tel:")):
                continue
            
            text = elem.text(strip=True)
            aria_label = elem.attributes.get("aria-label")
            element_id = elem.attributes.get("id")
            
            # Keep elements with identifiable attributes
            if text or aria_label or element_id:
                elements.append({
                    "tag": elem.tag,
                    "text": text,
                    "aria_label": aria_label,
                    "id": element_id,
                    "classes": elem.attributes.get("class", "").split(),
                    "href": href,
                })

        return elements[-30:]
    except Exception as e:
        return [{"error": str(e)}]

def _get_link_context(elem) -> str:
    """Returns subset of text from parent elements."""
    max_chars = 400
    try:
        current = elem
        for _ in range(3):
            if not current.parent:
                break
            current = current.parent
            context = current.text(strip=True)
            if len(context) >= 20:
                return context[:max_chars]
        return elem.text(strip=True)[:max_chars]
    except Exception:
        return ""

def _is_in_navigation(elem) -> bool:
    """Returns True if element has nav/header/footer ancestor."""
    current = elem
    while current.parent:
        current = current.parent
        if current.tag in {'nav', 'header', 'footer'}:
            return True
    return False

def _extract_links_smart(html_content: str, base_url: str) -> List[Dict]:
    """Returns list of dicts: {title, url, context}. Skips nav/header/footer links."""
    try:
        tree = HTMLParser(html_content)
        main = tree.css_first('main, article, [role="main"]') or tree.root
        seen_urls = set()
        links = []
        
        for a_tag in main.css('a[href]'):
            if _is_in_navigation(a_tag):
                continue
                
            try:
                href = urljoin(base_url, a_tag.attributes.get('href', ''))
                text = a_tag.text(strip=True)
                
                # Filter invalid/duplicate/short links
                if not _is_valid_url(href) or href in seen_urls or not text or len(text) < 3:
                    continue

                links.append({
                    "title": text,
                    "url": href,
                    "context": _get_link_context(a_tag)
                })
                seen_urls.add(href)
                
            except Exception:
                continue
        
        return links
    except Exception as e:
        print(f"extract_links_smart failed: {e}")
        return []

@asynccontextmanager
async def _crawl4ai_browser():
    """Yields AsyncWebCrawler instance with standard config."""
    async with AsyncWebCrawler(config=BROWSER_CONFIG) as crawler:
        yield crawler

def _get_run_config(js_code: Optional[List[str]] = None, delay: float = 2.0) -> CrawlerRunConfig:
    """Returns standardized CrawlerRunConfig."""
    return CrawlerRunConfig(
        cache_mode=CacheMode.ENABLED,
        word_count_threshold=10,
        exclude_external_links=False,
        wait_for="body",
        page_timeout=30000,
        delay_before_return_html=delay,
        excluded_tags=['script', 'style'],
        markdown_generator=DefaultMarkdownGenerator(
            content_source="cleaned_html",
            content_filter=PruningContentFilter(threshold=0.48, threshold_type="fixed", min_word_threshold=10),
            options={"ignore_links": False, "body_width": 0}
        ),
        verbose=False,
        js_code=js_code
    )

class InspectPageSchema(BaseModel):
    url: str

class InspectPage(BaseTool):
    name: str = "inspect_page"
    description: str = (
        "Analyze a webpage structure and content. "
        "Args: url (str). "
        "Returns: {title, description, markdown, interactive_elements}. "
        "Use 'interactive_elements' to find buttons for pagination/navigation."
    )
    args_schema: type[InspectPageSchema] = InspectPageSchema
    
    def _run(self, url: str) -> str:
        return asyncio.run(self._arun(url))
    
    async def _arun(self, url: str) -> str:
        try:
            async with _crawl4ai_browser() as crawler:
                result = await crawler.arun(url=url, config=_get_run_config())
                
                if not result.success:
                    return json.dumps({"error": f"Crawl failed: {result.error_message}"})
                
                markdown_content = (result.markdown.fit_markdown or result.markdown.raw_markdown) if result.markdown else ""

                return json.dumps({
                    "title": result.metadata.get("title", "Untitled"),
                    "description": result.metadata.get("description", ""),
                    "interactive_elements": _get_interactive_elements(result.html),
                    "markdown": markdown_content,                    
                }, indent=2)
                
        except Exception as e:
            return json.dumps({"error": f"Unexpected error: {type(e).__name__}: {str(e)}"})

class GetLinksSchema(BaseModel):
    url: str
    click_selector: Optional[str] = Field(
        default=None, 
        description="CSS selector to click before extracting (from interactive_elements)"
    )

class GetLinks(BaseTool):
    name: str = "get_links"
    description: str = (
        "Extract links from webpage, optionally clicking an element first. "
        "Args: url (str), click_selector (optional str). "
        "Returns: {links, total_found, interactive_elements}."
    )
    args_schema: type[GetLinksSchema] = GetLinksSchema
    
    def _run(self, url: str, click_selector: Optional[str] = None) -> str:
        return asyncio.run(self._arun(url, click_selector))
    
    async def _arun(self, url: str, click_selector: Optional[str] = None) -> str:
        try:
            async with _crawl4ai_browser() as crawler:
                js_code = [
                    f"document.querySelector('{click_selector}')?.click();",
                    "await new Promise(r => setTimeout(r, 3000));",
                ] if click_selector else None
                
                config = _get_run_config(js_code=js_code, delay=3.0 if click_selector else 2.0)
                result = await crawler.arun(url=url, config=config)
                
                if not result.success:
                    return json.dumps({"error": f"Crawl failed: {result.error_message}"})
                
                links = _extract_links_smart(result.cleaned_html or result.html, url)
                
                return json.dumps({
                    "links": links,
                    "total_found": len(links),
                    "interactive_elements": _get_interactive_elements(result.html) # Re-evaluate options after click
                }, indent=2)
                
        except Exception as e:
            return json.dumps({"error": f"Unexpected error: {type(e).__name__}: {str(e)}"})
