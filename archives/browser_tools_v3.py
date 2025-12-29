"""Atomic web scraping tools - let the agent decide the strategy."""

import asyncio
import json
import sys
from contextlib import asynccontextmanager
from typing import Optional
from urllib.parse import urljoin

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from selectolax.parser import HTMLParser
import datefinder

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

BROWSER_CONFIG = BrowserConfig(
    headless=True,
    verbose=True,
    extra_args=["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"]
)

@asynccontextmanager
async def _browser():
    async with AsyncWebCrawler(config=BROWSER_CONFIG) as crawler:
        yield crawler


def _is_valid_date(date_obj) -> bool:
    return 1900 <= date_obj.year <= 2100


def _extract_date(text: str) -> Optional[str]:
    """Extract first valid date from text."""
    try:
        dates = list(datefinder.find_dates(text))
        for date_obj in dates:
            if _is_valid_date(date_obj):
                return date_obj.strftime("%Y-%m-%d")
    except:
        pass
    return None


def _extract_links_from_html(html: str, base_url: str) -> list[dict]:
    """Extract all links with dates from HTML."""
    links = []
    if not html:
        return links
    
    tree = HTMLParser(html)
    for link in tree.css("a[href]"):
        href = link.attributes.get('href', '')
        if not href or href.startswith('#'):
            continue
        
        full_url = urljoin(base_url, href)
        link_data = {
            "url": full_url,
            "text": link.text(strip=True)
        }
        
        # Try to extract date
        search_text = f"{href} {link.text(strip=True)}"
        if link.parent:
            search_text += f" {link.parent.text(strip=True)}"
        
        if date := _extract_date(search_text):
            link_data["date"] = date
        
        links.append(link_data)
    
    return links


# ========== TOOL 1: Fetch Page ==========

class FetchPageSchema(BaseModel):
    url: str = Field(description="URL to fetch")
    wait_for: Optional[str] = Field(None, description="CSS selector to wait for before extracting")


class FetchPage(BaseTool):
    """Load a page and extract all links with dates.
    
    Returns HTML structure info + extracted links. Agent decides next action.
    """
    name: str = "fetch_page"
    description: str = (
        "Load URL and extract all links with dates. "
        "Returns page summary (markdown text with headings, titles, pagination indicators), "
        "links, and hints about pagination/scroll controls. "
        "Use page_summary to understand layout and see text like 'Page 1 of 50' or 'Load more'."
    )
    args_schema: type[FetchPageSchema] = FetchPageSchema
    
    def _run(self, url: str, wait_for: str = None) -> str:
        return asyncio.run(self._arun(url, wait_for))
    
    async def _arun(self, url: str, wait_for: str = None) -> str:
        try:
            async with _browser() as crawler:
                result = await crawler.arun(
                    url=url,
                    config=CrawlerRunConfig(
                        cache_mode=CacheMode.BYPASS,
                        wait_for=wait_for,
                        page_timeout=60000,
                        delay_before_return_html=2.0,
                        excluded_tags=['script', 'style'],
                        markdown_generator=DefaultMarkdownGenerator(),
                        simulate_user=True,
                        magic=True
                    )
                )
                
                if not result.success:
                    return json.dumps({"success": False, "error": result.error_message})
                
                # Extract links
                links = _extract_links_from_html(result.cleaned_html, url)
                
                # Look for common controls (hints for agent)
                tree = HTMLParser(result.cleaned_html)
                hints = {
                    "has_next_button": bool(tree.css('a[rel="next"], a.next, button.next, a.next-page')),
                    "has_prev_button": bool(tree.css('a[rel="prev"], a.prev, button.prev')),
                    "has_pagination": bool(tree.css('.pagination, nav[aria-label*="pagination" i]')),
                    "has_load_more": bool(tree.css('button:contains("Load"), button:contains("More")')),
                    "page_height": "tall" if len(result.cleaned_html) > 50000 else "normal"
                }
                
                # Extract page summary from markdown - skip navigation, get content
                markdown_full = result.markdown or ""
                
                # Strategy: Skip common navigation patterns and get to main content
                skip_patterns = [
                    "Skip to content",
                    "Search for:",
                    "Main navigation",
                    "## ",  # Usually first real heading after nav
                    "# "    # Or top-level heading
                ]
                
                content_start = 0
                for pattern in skip_patterns:
                    if pattern in markdown_full:
                        idx = markdown_full.find(pattern)
                        # For headings, include them; for nav skip past
                        if pattern.startswith("#"):
                            content_start = max(content_start, idx)
                        else:
                            content_start = max(content_start, idx + len(pattern) + 100)
                        break
                
                # Extract meaningful chunk, remove nav links pattern
                page_summary = markdown_full[content_start:content_start + 2000]
                
                # Filter out lines that look like navigation (just link after link)
                lines = page_summary.split("\n")
                filtered_lines = []
                consecutive_short_links = 0
                
                for line in lines:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    # Skip lines that are just navigation links (short, no context)
                    if stripped.startswith("* [") and len(stripped) < 60:
                        consecutive_short_links += 1
                        if consecutive_short_links < 3:  # Keep first few to show structure
                            filtered_lines.append(stripped)
                    else:
                        consecutive_short_links = 0
                        filtered_lines.append(stripped)
                
                page_summary = "\n".join(filtered_lines[:30])  # Max 30 lines for readability
                
                return json.dumps({
                    "success": True,
                    "url": result.url,
                    "page_summary": page_summary,
                    "links": links,
                    "total_links": len(links),
                    "links_with_dates": len([l for l in links if l.get("date")]),
                    "hints": hints
                }, indent=2)
                
        except Exception as e:
            return json.dumps({"success": False, "error": f"{type(e).__name__}: {str(e)}"})


# ========== TOOL 2: Scroll Page ==========

class ScrollPageSchema(BaseModel):
    url: str = Field(description="URL currently loaded")
    scroll_count: int = Field(3, description="Number of times to scroll (default 3)")
    wait_ms: int = Field(1000, description="Milliseconds to wait between scrolls (default 1000)")


class ScrollPage(BaseTool):
    """Scroll page N times and extract updated content.
    
    Agent calls this when they see hints of more content below.
    """
    name: str = "scroll_page"
    description: str = (
        "Scroll page down N times and return updated content. "
        "Returns page_summary to see if new text/headings appeared, plus updated links. "
        "Use when page appears to have infinite scroll or lazy loading. "
        "Check page_summary for indicators like 'Showing items 51-100' to confirm new content loaded."
    )
    args_schema: type[ScrollPageSchema] = ScrollPageSchema
    
    def _run(self, url: str, scroll_count: int = 3, wait_ms: int = 1000) -> str:
        return asyncio.run(self._arun(url, scroll_count, wait_ms))
    
    async def _arun(self, url: str, scroll_count: int = 3, wait_ms: int = 1000) -> str:
        try:
            js_code = f"""
                for (let i = 0; i < {scroll_count}; i++) {{
                    window.scrollTo(0, document.body.scrollHeight);
                    await new Promise(r => setTimeout(r, {wait_ms}));
                }}
            """
            
            async with _browser() as crawler:
                result = await crawler.arun(
                    url=url,
                    config=CrawlerRunConfig(
                        cache_mode=CacheMode.BYPASS,
                        js_code=[js_code],
                        page_timeout=60000,
                        delay_before_return_html=2.0,
                        excluded_tags=['script', 'style'],
                        markdown_generator=DefaultMarkdownGenerator()
                    )
                )
                
                if not result.success:
                    return json.dumps({"success": False, "error": result.error_message})
                
                links = _extract_links_from_html(result.cleaned_html, url)
                
                # Brief summary to detect if new content loaded after scroll
                markdown_full = result.markdown or ""
                
                # Skip navigation, find content
                content_start = 0
                for pattern in ["Skip to content", "##", "#"]:
                    if pattern in markdown_full:
                        idx = markdown_full.find(pattern)
                        content_start = max(content_start, idx if pattern.startswith("#") else idx + 100)
                        break
                
                summary_chunk = markdown_full[content_start:content_start + 1000]
                lines = [l.strip() for l in summary_chunk.split("\n") if l.strip()]
                
                # Filter out excessive nav links
                filtered = []
                nav_count = 0
                for line in lines:
                    if line.startswith("* [") and len(line) < 60:
                        nav_count += 1
                        if nav_count < 3:
                            filtered.append(line)
                    else:
                        nav_count = 0
                        filtered.append(line)
                
                page_summary = "\n".join(filtered[:20])
                
                return json.dumps({
                    "success": True,
                    "url": result.url,
                    "scrolled": scroll_count,
                    "page_summary": page_summary,
                    "links": links,
                    "total_links": len(links),
                    "links_with_dates": len([l for l in links if l.get("date")])
                }, indent=2)
                
        except Exception as e:
            return json.dumps({"success": False, "error": f"{type(e).__name__}: {str(e)}"})


# ========== TOOL 3: Click Element ==========

class ClickElementSchema(BaseModel):
    url: str = Field(description="Current page URL")
    selector: str = Field(description="CSS selector of element to click (e.g., 'a.next', 'button.load-more')")
    wait_for: Optional[str] = Field(None, description="CSS selector to wait for after click")


class ClickElement(BaseTool):
    """Click an element (button, link) and return updated content.
    
    Agent uses this for pagination, "Load More" buttons, etc.
    """
    name: str = "click_element"
    description: str = (
        "Click element by CSS selector and return new page content. "
        "Use for Next buttons, Load More buttons, or any clickable navigation. "
        "Returns page_summary showing new page layout/text, new URL if navigation occurred, plus extracted links. "
        "Check page_summary for pagination indicators like 'Page 2' to confirm navigation."
    )
    args_schema: type[ClickElementSchema] = ClickElementSchema
    
    def _run(self, url: str, selector: str, wait_for: str = None) -> str:
        return asyncio.run(self._arun(url, selector, wait_for))
    
    async def _arun(self, url: str, selector: str, wait_for: str = None) -> str:
        try:
            async with _browser() as crawler:
                # First check if it's a link (has href)
                result = await crawler.arun(
                    url=url,
                    config=CrawlerRunConfig(
                        cache_mode=CacheMode.BYPASS,
                        page_timeout=60000
                    )
                )
                
                if not result.success:
                    return json.dumps({"success": False, "error": result.error_message})
                
                tree = HTMLParser(result.cleaned_html)
                elements = tree.css(selector)
                
                if not elements:
                    return json.dumps({
                        "success": False,
                        "error": f"Element not found: {selector}"
                    })
                
                element = elements[0]
                
                # If has href, navigate directly
                href = element.attributes.get('href')
                if href:
                    next_url = urljoin(url, href)
                    result = await crawler.arun(
                        url=next_url,
                        config=CrawlerRunConfig(
                            cache_mode=CacheMode.BYPASS,
                            wait_for=wait_for,
                            page_timeout=60000,
                            delay_before_return_html=2.0,
                            excluded_tags=['script', 'style'],
                            markdown_generator=DefaultMarkdownGenerator(),
                            simulate_user=True
                        )
                    )
                else:
                    # Click via JavaScript
                    click_js = f"document.querySelector('{selector}')?.click();"
                    result = await crawler.arun(
                        url=url,
                        config=CrawlerRunConfig(
                            cache_mode=CacheMode.BYPASS,
                            js_code=[click_js],
                            wait_for=wait_for,
                            page_timeout=60000,
                            delay_before_return_html=3.0,
                            excluded_tags=['script', 'style'],
                            markdown_generator=DefaultMarkdownGenerator()
                        )
                    )
                
                if not result.success:
                    return json.dumps({"success": False, "error": result.error_message})
                
                links = _extract_links_from_html(result.cleaned_html, result.url)
                
                # Page summary for new page after click
                markdown_full = result.markdown or ""
                
                content_start = 0
                for pattern in ["Skip to content", "##", "#"]:
                    if pattern in markdown_full:
                        idx = markdown_full.find(pattern)
                        content_start = max(content_start, idx if pattern.startswith("#") else idx + 100)
                        break
                
                summary_chunk = markdown_full[content_start:content_start + 1000]
                lines = [l.strip() for l in summary_chunk.split("\n") if l.strip()]
                
                filtered = []
                nav_count = 0
                for line in lines:
                    if line.startswith("* [") and len(line) < 60:
                        nav_count += 1
                        if nav_count < 3:
                            filtered.append(line)
                    else:
                        nav_count = 0
                        filtered.append(line)
                
                page_summary = "\n".join(filtered[:20])
                
                return json.dumps({
                    "success": True,
                    "previous_url": url,
                    "current_url": result.url,
                    "navigated": result.url != url,
                    "clicked_selector": selector,
                    "page_summary": page_summary,
                    "links": links,
                    "total_links": len(links),
                    "links_with_dates": len([l for l in links if l.get("date")])
                }, indent=2)
                
        except Exception as e:
            return json.dumps({"success": False, "error": f"{type(e).__name__}: {str(e)}"})


# ========== TOOL 4: Analyze Links ==========

class AnalyzeLinksSchema(BaseModel):
    all_links: list[dict] = Field(description="All links collected so far")
    new_links: list[dict] = Field(description="Links from most recent fetch/scroll/click")


class AnalyzeLinks(BaseTool):
    """Compare link sets to detect duplicates and measure progress.
    
    Helps agent decide if should continue or stop.
    """
    name: str = "analyze_links"
    description: str = (
        "Analyze link collection progress. "
        "Returns unique count, duplicates, date coverage. "
        "Helps agent decide if should continue collecting or if reached end of content."
    )
    args_schema: type[AnalyzeLinksSchema] = AnalyzeLinksSchema
    
    def _run(self, all_links: list[dict], new_links: list[dict]) -> str:
        try:
            # Find unique URLs
            all_urls = set(l['url'] for l in all_links)
            new_urls = set(l['url'] for l in new_links)
            
            truly_new = new_urls - all_urls
            duplicates = new_urls & all_urls
            
            # Merge and deduplicate
            merged = {l['url']: l for l in all_links}
            for l in new_links:
                if l['url'] not in merged:
                    merged[l['url']] = l
            
            unique_links = list(merged.values())
            links_with_dates = [l for l in unique_links if l.get('date')]
            
            # Date coverage
            dates = [l['date'] for l in links_with_dates]
            date_range = f"{min(dates)} to {max(dates)}" if dates else "No dates"
            
            # Recommendation
            if len(truly_new) == 0:
                recommendation = "No new unique links found. Likely reached end of content."
            elif len(truly_new) < 3:
                recommendation = "Very few new links. May be near end of content."
            elif len(duplicates) / max(len(new_urls), 1) > 0.7:
                recommendation = "High duplicate ratio. Possibly scrolled past new content."
            else:
                recommendation = "Good progress. Continue if more data needed."
            
            return json.dumps({
                "unique_total": len(unique_links),
                "unique_with_dates": len(links_with_dates),
                "new_unique": len(truly_new),
                "duplicates": len(duplicates),
                "date_range": date_range,
                "recommendation": recommendation,
                "merged_links": unique_links
            }, indent=2)
            
        except Exception as e:
            return json.dumps({"error": f"{type(e).__name__}: {str(e)}"})


# ========== TOOL 5: Filter Links ==========

class FilterLinksSchema(BaseModel):
    links: list[dict] = Field(description="Links to filter")
    url_contains: Optional[str] = Field(None, description="URL must contain this string")
    date_start: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    date_end: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    must_have_date: bool = Field(True, description="Only include items with dates")
    limit: Optional[int] = Field(None, description="Max results to return")


class FilterLinks(BaseTool):
    """Filter links by URL pattern and date range."""
    name: str = "filter_links"
    description: str = (
        "Filter collected links by URL pattern, date range, etc. "
        "Returns matching links that meet specified criteria."
    )
    args_schema: type[FilterLinksSchema] = FilterLinksSchema
    
    def _run(self, links: list[dict], url_contains: str = None, date_start: str = None,
             date_end: str = None, must_have_date: bool = True, limit: int = None) -> str:
        try:
            filtered = links.copy()
            
            if url_contains:
                filtered = [l for l in filtered if url_contains.lower() in l.get('url', '').lower()]
            
            if must_have_date:
                filtered = [l for l in filtered if l.get('date')]
            
            if date_start or date_end:
                date_filtered = []
                for item in filtered:
                    item_date = item.get('date')
                    if not item_date:
                        continue
                    if date_start and item_date < date_start:
                        continue
                    if date_end and item_date > date_end:
                        continue
                    date_filtered.append(item)
                filtered = date_filtered
            
            # Sort by date descending
            if filtered:
                filtered = sorted(filtered, key=lambda x: x.get('date', ''), reverse=True)
            
            output = filtered[:limit] if limit else filtered
            
            return json.dumps({
                "matched": output,
                "total_matched": len(filtered),
                "total_input": len(links)
            }, indent=2)
            
        except Exception as e:
            return json.dumps({"error": f"{type(e).__name__}: {str(e)}"})

