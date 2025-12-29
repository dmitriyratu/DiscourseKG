"""AI-powered browser tools using Crawl4AI (Playwright-based) for intelligent web scraping."""

import asyncio
import json
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from selectolax.parser import HTMLParser
import datefinder

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from playground.agent_logger import get_logger

# Configuration
ENABLE_LOGGING = True
MAX_MARKDOWN_CHARS = 15000
MAX_LINKS = 150
MAX_BUTTONS = 50
MAX_DATES = 50
MAX_SCROLL_ATTEMPTS = 50
SCROLL_NO_CHANGE_THRESHOLD = 2
NETWORK_IDLE_TIMEOUT_MS = 8000
SCROLL_WAIT_MS = 2000
CLICK_WAIT_MS = 3000

# Windows async support
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

NAVIGATION_TAGS = {'nav', 'header', 'footer', 'aside'}

# Browser configuration
BROWSER_CONFIG = BrowserConfig(
    headless=True,
    verbose=True,
    extra_args=["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"],
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# JavaScript snippets as constants
JS_NETWORK_IDLE = f"""
    await new Promise(resolve => {{
        let timeout;
        const checkIdle = () => {{
            clearTimeout(timeout);
            timeout = setTimeout(resolve, 1000);
        }};
        const observer = new PerformanceObserver(() => checkIdle());
        observer.observe({{ entryTypes: ['resource'] }});
        checkIdle();
        setTimeout(resolve, {NETWORK_IDLE_TIMEOUT_MS});
    }});
"""

JS_SCROLL_TEMPLATE = f"""
    let scrollAttempts = 0;
    const maxScrolls = {MAX_SCROLL_ATTEMPTS};
    let prevHeight = 0;
    let noChangeCount = 0;
    let reachedEnd = false;
    
    while (scrollAttempts < maxScrolls) {{
        prevHeight = document.body.scrollHeight;
        window.scrollTo(0, document.body.scrollHeight);
        await new Promise(r => setTimeout(r, {SCROLL_WAIT_MS}));
        
        if (document.body.scrollHeight === prevHeight) {{
            noChangeCount++;
            if (noChangeCount >= {SCROLL_NO_CHANGE_THRESHOLD}) {{
                reachedEnd = true;
                break;
            }}
        }} else {{
            noChangeCount = 0;
        }}
        
        scrollAttempts++;
    }}
    
    window.__scrollMetadata = {{
        reached_end: reachedEnd,
        scroll_attempts: scrollAttempts,
        final_height: document.body.scrollHeight
    }};
"""

JS_METADATA_EXTRACTOR = """
    const meta = window.__scrollMetadata || {reached_end: false, scroll_attempts: 0};
    const metaDiv = document.createElement('div');
    metaDiv.id = '__scroll_metadata_element__';
    metaDiv.style.display = 'none';
    metaDiv.textContent = JSON.stringify(meta);
    document.body.appendChild(metaDiv);
"""


@dataclass
class LinkStats:
    """Statistics collected during single iteration over links."""
    transcript_dates: list[str]
    transcript_count: int
    links_with_dates_count: int


def _extract_link_stats(links: list[dict]) -> LinkStats:
    """Extract statistics from links in a single pass."""
    transcript_dates = []
    transcript_count = 0
    links_with_dates_count = 0
    
    for link in links:
        if 'transcript' in link.get('url', ''):
            transcript_count += 1
            if date := link.get("date"):
                transcript_dates.append(date)
        if link.get("date"):
            links_with_dates_count += 1
    
    return LinkStats(transcript_dates, transcript_count, links_with_dates_count)


@asynccontextmanager
async def _crawl4ai_browser():
    """Yields AsyncWebCrawler instance with standard config."""
    async with AsyncWebCrawler(config=BROWSER_CONFIG) as crawler:
        yield crawler


def _get_run_config(
    js_code: Optional[list[str]] = None,
    delay: float = 5.0,
    wait_for: Optional[str] = None
) -> CrawlerRunConfig:
    """Returns standardized CrawlerRunConfig with smart waiting for dynamic content."""
    return CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        word_count_threshold=10,
        exclude_external_links=False,
        wait_for=wait_for,
        page_timeout=60000,
        delay_before_return_html=delay,
        excluded_tags=['script', 'style'],
        markdown_generator=DefaultMarkdownGenerator(
            content_source="cleaned_html",
            options={"ignore_links": False, "body_width": 0}
        ),
        verbose=True,
        js_code=js_code,
        wait_for_images=False,
        simulate_user=True,
        magic=True
    )


def _build_smart_selector(element) -> str:
    """Builds a robust CSS selector for an element."""
    tag = element.tag
    
    if elem_id := element.attributes.get('id'):
        return f"#{elem_id}"
    
    if elem_class := element.attributes.get('class'):
        classes = [c for c in elem_class.split() if not c.startswith('js-')]
        if classes:
            return f"{tag}.{classes[0]}"
    
    if text := element.text(strip=True)[:20].replace("'", "\\'"):
        return f"{tag}:has-text('{text}')"
    
    return tag


def _extract_date_from_context(href: str, link_text: str, parent_text: str) -> Optional[str]:
    """Extract date from URL, link text, and parent context using datefinder."""
    search_parts = [
        href.replace('-', ' ').replace('/', ' '),
        link_text,
        parent_text
    ]
    search_text = " ".join(filter(None, search_parts))
    
    date_matches = list(datefinder.find_dates(search_text))
    if date_matches:
        return date_matches[0].strftime("%Y-%m-%d")
    return None


def _extract_scroll_metadata(tree: HTMLParser) -> dict:
    """Extract scroll metadata from injected DOM element."""
    try:
        meta_elem = tree.css_first('#__scroll_metadata_element__')
        if meta_elem and (meta_text := meta_elem.text(strip=True)):
            return json.loads(meta_text)
    except (json.JSONDecodeError, AttributeError) as e:
        print(f"[DEBUG] Failed to parse scroll metadata: {e}")
    
    return {"reached_end": False, "scroll_attempts": 0}


def _log_tool_execution(
    logger,
    url: str,
    scroll: bool,
    click_selector: Optional[str],
    wait_for_selector: Optional[str],
    extra_delay: float,
    output_data: dict,
    stats: LinkStats,
    dates_count: int,
    scroll_meta: dict,
    output_size: int,
    markdown_truncated: bool,
    is_error: bool = False
):
    """Centralized logging for tool execution."""
    if is_error:
        logger.log_tool_call(
            tool_name="inspect_page",
            inputs={
                "url": url,
                "scroll": scroll,
                "click_selector": click_selector,
                "wait_for_selector": wait_for_selector,
                "extra_delay": extra_delay
            },
            output=output_data,
            metadata={"status": "error", "error_type": output_data.get("error_type", "Unknown")}
        )
    else:
        logger.log_tool_call(
            tool_name="inspect_page",
            inputs={
                "url": url,
                "scroll": scroll,
                "click_selector": click_selector,
                "wait_for_selector": wait_for_selector,
                "extra_delay": extra_delay
            },
            output=output_data,
            metadata={
                "num_links": len(output_data.get("links", [])),
                "num_links_with_dates": stats.links_with_dates_count,
                "num_buttons": len(output_data.get("buttons", [])),
                "num_unique_dates": dates_count,
                "date_range": output_data.get("date_range", {}),
                "scroll_metadata": scroll_meta,
                "markdown_truncated": markdown_truncated,
                "output_size_chars": output_size
            }
        )
        print(f"\n[InspectPage] {output_size} chars | "
              f"Links: {len(output_data.get('links', []))} ({stats.links_with_dates_count} with dates) | "
              f"Scroll: {scroll_meta}\n")


class InspectPageSchema(BaseModel):
    url: str
    scroll: bool = Field(False, description="Whether to scroll down the page to trigger infinite scroll/lazy loading.")
    click_selector: Optional[str] = Field(None, description="CSS selector to click before extracting content (e.g. 'button.load-more').")
    wait_for_selector: Optional[str] = Field(None, description="CSS selector to wait for before extracting (for dynamic content).")
    extra_delay: float = Field(0.0, description="Additional seconds to wait after page load (for heavy JS sites).")


class InspectPage(BaseTool):
    """Extract structured page data for agent analysis with smart waiting for dynamic content.
    
    Handles JavaScript-heavy sites (React, Vue, Angular) by waiting for network idle.
    
    Parameters:
    - url: Target webpage URL
    - scroll: Enable for infinite-scroll (auto-scrolls until no new content detected)
    - click_selector: CSS selector to click before extraction
    - wait_for_selector: CSS selector to wait for (optional, for specific dynamic elements)
    - extra_delay: Additional seconds to wait for heavy JS sites (default: 0)
    
    Returns JSON with:
    - summary: Quick overview (total transcripts, date range) - CHECK THIS FIRST!
    - date_range: {oldest_transcript_date, newest_transcript_date}
    - scroll_metadata: {scroll_enabled, reached_end, scroll_attempts} - CHECK reached_end!
    - title/description: Page metadata
    - links[]: All links with context hints AND associated dates (date field per link)
    - unique_dates[]: All unique dates found across links
    - buttons[]: Clickable elements
    - markdown: Clean page content
    
    IMPORTANT: 
    - Each link object may have a "date" field extracted from URL/text/parent element
    - If scroll_metadata.reached_end is False, there may be more content to load!
    """
    name: str = "inspect_page"
    description: str = (
        "Extract structured webpage data with smart dynamic content handling. "
        "Waits for network idle automatically. "
        "Returns: {summary, date_range, scroll_metadata, links[] (with dates), unique_dates[], buttons[], markdown}. "
        "CHECK scroll_metadata.reached_end - if False, more content may exist!"
    )
    args_schema: type[InspectPageSchema] = InspectPageSchema
    
    def _run(self, url: str, scroll: bool = False, click_selector: str = None, 
             wait_for_selector: str = None, extra_delay: float = 0.0) -> str:
        return asyncio.run(self._arun(url, scroll, click_selector, wait_for_selector, extra_delay))
    
    async def _arun(self, url: str, scroll: bool = False, click_selector: str = None,
                    wait_for_selector: str = None, extra_delay: float = 0.0) -> str:
        try:
            js_code = [JS_NETWORK_IDLE]
            
            if click_selector:
                js_code.extend([
                    f"const el = document.querySelector('{click_selector}'); if(el) el.click();",
                    f"await new Promise(r => setTimeout(r, {CLICK_WAIT_MS}));"
                ])

            if scroll:
                js_code.append(JS_SCROLL_TEMPLATE)
            
            if extra_delay > 0:
                js_code.append(f"await new Promise(r => setTimeout(r, {int(extra_delay * 1000)}));")

            if scroll:
                js_code.append(JS_METADATA_EXTRACTOR)
            
            total_delay = 5.0 + extra_delay
            async with _crawl4ai_browser() as crawler:
                result = await crawler.arun(
                    url=url,
                    config=_get_run_config(js_code, total_delay, wait_for_selector)
                )
                
                if not result.success:
                    return json.dumps({"error": f"Crawl failed: {result.error_message}"})
                
                markdown_content = (result.markdown.fit_markdown or result.markdown.raw_markdown) if result.markdown else ""
                markdown_truncated = len(markdown_content) > MAX_MARKDOWN_CHARS
                if markdown_truncated:
                    markdown_content = markdown_content[:MAX_MARKDOWN_CHARS] + "\n\n[...truncated for length...]"

                links = []
                buttons = []
                dates_found = []
                scroll_result = {"reached_end": False, "scroll_attempts": 0}
                
                if result.cleaned_html:
                    tree = HTMLParser(result.cleaned_html)
                    
                    if scroll:
                        scroll_result = _extract_scroll_metadata(tree)
                    
                    # Extract links with dates
                    for link in tree.css("a[href]"):
                        if not (href := link.attributes.get('href', '')) or href.startswith('#'):
                            continue
                        
                        link_text = link.text(strip=True)
                        parent_text = link.parent.text(strip=True) if link.parent else ""
                        link_date = _extract_date_from_context(href, link_text, parent_text)
                        
                        parent_tag = link.parent.tag if link.parent else ''
                        link_data = {
                            "url": urljoin(url, href),
                            "text": link_text,
                            "title": link.attributes.get('title', ''),
                            "aria_label": link.attributes.get('aria-label', ''),
                            "context": {
                                "parent_tag": parent_tag,
                                "in_navigation_area": parent_tag in NAVIGATION_TAGS
                            },
                            "date": link_date
                        }
                        
                        links.append(link_data)
                    
                    # Extract buttons
                    for btn in tree.css("button, a.btn, a.button, [role='button'], input[type='submit'], [onclick]"):
                        if not (text := btn.text(strip=True)) or len(text) > 100:
                            continue
                        
                        buttons.append({
                            "text": text,
                            "selector": _build_smart_selector(btn),
                            "href": btn.attributes.get('href', ''),
                            "context": {
                                "classes": btn.attributes.get('class', ''),
                                "type": btn.attributes.get('type', ''),
                                "aria_label": btn.attributes.get('aria-label', '')
                            }
                        })

                # Calculate stats in single pass
                stats = _extract_link_stats(links)
                
                scroll_metadata = {
                    "scroll_enabled": scroll,
                    "reached_end": scroll_result.get("reached_end", False),
                    "scroll_attempts": scroll_result.get("scroll_attempts", 0)
                }
                
                # Deduplicate and limit dates
                dates_found = sorted(set(dates_found))[:MAX_DATES]
                
                # Determine date range
                date_range = {}
                if stats.transcript_dates:
                    sorted_dates = sorted(set(stats.transcript_dates))
                    date_range = {
                        "oldest_transcript_date": sorted_dates[0],
                        "newest_transcript_date": sorted_dates[-1],
                        "total_transcript_dates": len(sorted_dates)
                    }
                elif dates_found:
                    date_range = {
                        "oldest_date": dates_found[0],
                        "newest_date": dates_found[-1],
                        "total_unique_dates": len(dates_found)
                    }
                
                # Create summary
                summary = {
                    "total_links": len(links),
                    "total_transcript_links": stats.transcript_count,
                }
                if date_range:
                    if 'oldest_transcript_date' in date_range:
                        summary["transcript_date_range"] = f"{date_range['oldest_transcript_date']} to {date_range['newest_transcript_date']}"
                        summary["total_transcript_dates"] = date_range['total_transcript_dates']
                    else:
                        summary["date_range"] = f"{date_range.get('oldest_date', 'N/A')} to {date_range.get('newest_date', 'N/A')}"
                
                output_data = {
                    "summary": summary,
                    "date_range": date_range,
                    "scroll_metadata": scroll_metadata,
                    "title": result.metadata.get("title", "Untitled"),
                    "description": result.metadata.get("description", ""),
                    "links": links[:MAX_LINKS],
                    "unique_dates": dates_found,
                    "buttons": buttons[:MAX_BUTTONS],
                    "markdown": markdown_content
                }
                
                output = json.dumps(output_data, indent=2)

                if ENABLE_LOGGING:
                    _log_tool_execution(
                        get_logger(), url, scroll, click_selector, wait_for_selector, extra_delay,
                        output_data, stats, len(dates_found), scroll_metadata, len(output), markdown_truncated
                    )
                
                return output
                
        except Exception as e:
            error_output = {"error": f"Unexpected error: {type(e).__name__}: {str(e)}", "error_type": type(e).__name__}
            
            if ENABLE_LOGGING:
                _log_tool_execution(
                    get_logger(), url, scroll, click_selector, wait_for_selector, extra_delay,
                    error_output, LinkStats([], 0, 0), 0, {}, 0, False, is_error=True
                )
            
            return json.dumps({"error": error_output["error"]})

